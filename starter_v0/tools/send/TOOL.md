---
name: send
track: bonus
kind: action
provider: Telegram Bot API
requires_env: [TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]
inputs: [text, confirmed]
outputs: [status, message, message_id]
side_effect: true
requires_confirmation: true
---
# send

Posts research digests to a Telegram chat via Bot API `sendMessage`.

## Confirmation boundary

- Call with `confirmed=false` (default) first. The tool returns `status=needs_confirmation` and **never** hits the network.
- Only call again with `confirmed=true` after the **user** explicitly approves the exact draft text (UI Confirm button or a clear yes in chat).
- The model must never invent user approval. Do not set `confirmed=true` on the first send request.

## Errors

Returns an error dict (does not raise) when token/chat id is missing, Telegram rejects the request, the network times out, or the text exceeds 4096 characters.
