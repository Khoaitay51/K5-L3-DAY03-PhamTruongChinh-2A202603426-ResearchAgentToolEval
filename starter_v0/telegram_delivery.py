from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


SendFn = Callable[..., dict[str, Any]]


@dataclass
class TelegramDeliveryController:
    """Pure confirmation state for Telegram bonus delivery (Streamlit-safe)."""

    pending_text: str | None = None
    send_lock: bool = False
    last_status: str | None = None
    last_message: str | None = None
    last_result: dict[str, Any] | None = field(default=None, repr=False)

    def set_pending(self, text: str) -> dict[str, Any]:
        draft = (text or "").strip()
        self.pending_text = draft or None
        self.send_lock = False
        self.last_status = "awaiting_confirmation"
        self.last_message = "Draft ready. Confirm to send to Telegram."
        self.last_result = None
        return {"status": self.last_status, "message": self.last_message, "text": self.pending_text}

    def cancel(self) -> dict[str, Any]:
        self.pending_text = None
        self.send_lock = False
        self.last_status = "cancelled"
        self.last_message = "Telegram delivery cancelled. No message was sent."
        self.last_result = {"status": "cancelled"}
        return {"status": self.last_status, "message": self.last_message}

    def confirm_and_send(self, send_fn: SendFn) -> dict[str, Any]:
        # Lock is checked first so a second Confirm click after success cannot
        # fall through to "no pending draft" and must not hit Telegram again.
        if self.send_lock:
            self.last_status = "skipped_duplicate"
            self.last_message = "Send already in progress or completed for this draft. Not sending again."
            return {"status": self.last_status, "message": self.last_message, "result": self.last_result}

        if not self.pending_text:
            self.last_status = "error"
            self.last_message = "No pending Telegram draft to send."
            self.last_result = {"status": "error", "message": self.last_message}
            return {"status": self.last_status, "message": self.last_message, "result": self.last_result}

        self.send_lock = True
        result = send_fn(text=self.pending_text, confirmed=True)
        self.last_result = result

        if result.get("status") == "sent":
            self.last_status = "sent"
            mid = result.get("message_id")
            self.last_message = (
                f"Sent to Telegram successfully (message_id={mid})."
                if mid is not None
                else "Sent to Telegram successfully."
            )
            self.pending_text = None
            return {"status": self.last_status, "message": self.last_message, "result": result}

        self.last_status = "error"
        self.last_message = result.get("message") or result.get("error") or "Telegram send failed."
        # Unlock so the user can fix config and retry the same draft.
        self.send_lock = False
        return {"status": self.last_status, "message": self.last_message, "result": result}
