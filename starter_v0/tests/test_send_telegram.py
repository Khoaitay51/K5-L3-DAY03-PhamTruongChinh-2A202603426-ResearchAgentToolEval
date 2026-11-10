"""Unit tests for Telegram bonus delivery (send tool + confirmation controller)."""
from __future__ import annotations

import requests

from chat import execute_tool_call_with_send_guard
from conftest import FakeResponse
from providers.base import ToolCall
from telegram_delivery import TelegramDeliveryController
from tools import TOOL_FUNCTIONS
from tools.send.tool import TELEGRAM_TEXT_LIMIT

send_tool = TOOL_FUNCTIONS["send"]


def test_send_confirmed_false_requires_confirmation_and_skips_network(fake_http) -> None:
    calls = fake_http(FakeResponse({"ok": True, "result": {"message_id": 1}}))
    result = send_tool(text="Bản tin AI", confirmed=False)

    assert result["status"] == "needs_confirmation"
    assert result["awaiting_confirmation"] is True
    assert result["text"] == "Bản tin AI"
    assert calls == []


def test_send_confirmed_true_missing_token_returns_config_error(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    calls = fake_http(FakeResponse({"ok": True}))
    result = send_tool(text="hello", confirmed=True)

    assert result["status"] == "error"
    assert result["error"] == "ConfigurationError"
    assert "TELEGRAM_BOT_TOKEN" in result["message"]
    assert calls == []


def test_send_confirmed_true_missing_chat_id_returns_config_error(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-xyz")
    calls = fake_http(FakeResponse({"ok": True}))
    result = send_tool(text="hello", confirmed=True)

    assert result["status"] == "error"
    assert result["error"] == "ConfigurationError"
    assert "TELEGRAM_CHAT_ID" in result["message"]
    assert calls == []


def test_send_telegram_api_error_returns_failure(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bad-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "999")
    fake_http(FakeResponse(
        {"ok": False, "description": "Unauthorized"},
        status_code=401,
    ))
    result = send_tool(text="hello", confirmed=True)

    assert result["status"] == "error"
    assert result["error"] == "TelegramAPIError"
    assert "TELEGRAM_BOT_TOKEN" in result["message"] or "Unauthorized" in result["message"]


def test_send_telegram_api_success_returns_sent(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "good-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "813945208")
    calls = fake_http(FakeResponse({"ok": True, "result": {"message_id": 42}}))

    result = send_tool(text="Digest OK", confirmed=True)

    assert result["status"] == "sent"
    assert result["message_id"] == 42
    assert len(calls) == 1
    assert calls[0]["method"] == "POST"
    assert "good-token" in calls[0]["url"]
    assert calls[0]["json"]["chat_id"] == "813945208"
    assert calls[0]["json"]["text"] == "Digest OK"
    assert "parse_mode" not in calls[0]["json"]


def test_cancel_does_not_call_telegram(fake_http) -> None:
    calls = fake_http(FakeResponse({"ok": True, "result": {"message_id": 1}}))
    ctrl = TelegramDeliveryController()
    ctrl.set_pending("Draft will be cancelled")
    outcome = ctrl.cancel()

    assert outcome["status"] == "cancelled"
    assert ctrl.pending_text is None
    assert calls == []


def test_confirm_and_send_blocks_duplicate_clicks(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "good-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    calls = fake_http(FakeResponse({"ok": True, "result": {"message_id": 7}}))

    ctrl = TelegramDeliveryController()
    ctrl.set_pending("Only once")
    first = ctrl.confirm_and_send(send_tool)
    second = ctrl.confirm_and_send(send_tool)

    assert first["status"] == "sent"
    assert second["status"] == "skipped_duplicate"
    assert len(calls) == 1


def test_streamlit_guard_never_trusts_model_confirmed_true(fake_http) -> None:
    calls = fake_http(FakeResponse({"ok": True, "result": {"message_id": 1}}))
    event = execute_tool_call_with_send_guard(
        ToolCall("send", {"text": "Secret draft", "confirmed": True})
    )
    assert event["args"]["confirmed"] is False
    assert event["result"]["status"] == "needs_confirmation"
    assert event["result"]["text"] == "Secret draft"
    assert calls == []


def test_send_rejects_oversized_message(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "good-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    calls = fake_http(FakeResponse({"ok": True}))
    result = send_tool(text="x" * (TELEGRAM_TEXT_LIMIT + 1), confirmed=True)

    assert result["status"] == "error"
    assert result["error"] == "ValidationError"
    assert calls == []


def test_send_network_timeout_returns_error(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "good-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    fake_http(requests.Timeout("timed out"))
    result = send_tool(text="hello", confirmed=True)
    assert result["status"] == "error"
    assert result["error"] == "Timeout"
