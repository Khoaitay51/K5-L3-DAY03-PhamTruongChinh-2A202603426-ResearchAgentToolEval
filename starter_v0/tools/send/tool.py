from __future__ import annotations

import os
from typing import Any

import requests

from tools._shared import TIMEOUT

TELEGRAM_TEXT_LIMIT = 4096
TOOL_NAME = "send_telegram"


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def _config_error(message: str) -> dict[str, Any]:
    return {
        "tool": TOOL_NAME,
        "status": "error",
        "error": "ConfigurationError",
        "message": message,
    }


def send_telegram(text: str = "", confirmed: bool = False) -> dict[str, Any]:
    """Send text to Telegram only after explicit user confirmation.

    When ``confirmed`` is false the Telegram API is never called; the caller
    must show the draft to the user and re-invoke with ``confirmed=true``.
    """
    payload = text if isinstance(text, str) else str(text or "")
    is_confirmed = _as_bool(confirmed)

    if not is_confirmed:
        return {
            "tool": TOOL_NAME,
            "status": "needs_confirmation",
            "message": "Confirmation required before sending to Telegram. Show the draft to the user and only resend with confirmed=true after they approve.",
            "text": payload,
            "awaiting_confirmation": True,
        }

    if not payload.strip():
        return {
            "tool": TOOL_NAME,
            "status": "error",
            "error": "ValidationError",
            "message": "Cannot send an empty message to Telegram.",
        }

    if len(payload) > TELEGRAM_TEXT_LIMIT:
        return {
            "tool": TOOL_NAME,
            "status": "error",
            "error": "ValidationError",
            "message": (
                f"Message length {len(payload)} exceeds Telegram limit "
                f"of {TELEGRAM_TEXT_LIMIT} characters."
            ),
        }

    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_id = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()
    if not token:
        return _config_error("Missing TELEGRAM_BOT_TOKEN env var")
    if not chat_id:
        return _config_error("Missing TELEGRAM_CHAT_ID env var")

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": payload},
            timeout=TIMEOUT,
        )
    except requests.Timeout as exc:
        return {
            "tool": TOOL_NAME,
            "status": "error",
            "error": "Timeout",
            "message": f"Telegram API timed out: {exc}",
        }
    except requests.RequestException as exc:
        return {
            "tool": TOOL_NAME,
            "status": "error",
            "error": type(exc).__name__,
            "message": f"Network error calling Telegram API: {exc}",
        }

    try:
        body = response.json()
    except ValueError:
        body = {}

    if response.status_code >= 400 or not body.get("ok", False):
        description = ""
        if isinstance(body, dict):
            description = str(body.get("description") or body.get("error_code") or "")
        hint = description or response.text or f"HTTP {response.status_code}"
        lowered = hint.lower()
        if response.status_code in {401, 404} or "unauthorized" in lowered:
            hint = f"Invalid TELEGRAM_BOT_TOKEN or bot not found. Telegram said: {hint}"
        elif "chat not found" in lowered:
            hint = f"Invalid TELEGRAM_CHAT_ID or bot is not a member of the chat. Telegram said: {hint}"
        elif response.status_code == 403 or "bot was blocked" in lowered or "can't initiate" in lowered:
            hint = (
                "Bot cannot message this chat. Ask the user to open the bot and press Start "
                f"(or add the bot as channel admin). Telegram said: {hint}"
            )
        elif "message is too long" in lowered:
            hint = f"Message exceeds Telegram length limit. Telegram said: {hint}"
        return {
            "tool": TOOL_NAME,
            "status": "error",
            "error": "TelegramAPIError",
            "message": hint,
            "http_status": response.status_code,
            "telegram_ok": bool(body.get("ok")) if isinstance(body, dict) else False,
        }

    result = body.get("result") if isinstance(body, dict) else None
    message_id = result.get("message_id") if isinstance(result, dict) else None
    return {
        "tool": TOOL_NAME,
        "status": "sent",
        "message": "Message delivered to Telegram.",
        "message_id": message_id,
        "chat_id": chat_id,
    }
