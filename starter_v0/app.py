from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chat import (
    execute_tool_call_with_send_guard,
    now_iso,
    run_model_tool_loop,
    safe_slug,
    trim_history,
    write_transcript,
)
from env_loader import load_lab_env
from providers import make_provider
from telegram_delivery import TelegramDeliveryController
from tools import TOOL_FUNCTIONS, load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version

ARTIFACTS_DIR = ROOT / "artifacts"
TRANSCRIPTS_DIR = ROOT / "transcripts"
RUNS_DIR = ROOT / "runs"

load_lab_env(ROOT)

st.set_page_config(
    page_title="Research Agent — Tool Eval & Live Chat",
    page_icon="🔬",
    layout="wide",
)


def init_new_session(
    provider_name: str,
    model_name: str | None,
    version_label: str,
    system_prompt_path: Path,
    tools_path: Path,
    history_window: int,
    max_tool_rounds: int,
) -> None:
    artifact_ver = build_artifact_version(version_label, system_prompt_path, tools_path)
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = "_".join([
        safe_slug(version_label),
        safe_slug(provider_name),
        timestamp,
    ])
    transcript_path = TRANSCRIPTS_DIR / f"{transcript_id}.transcript.json"

    default_model = model_name
    if not default_model:
        try:
            prov = make_provider(provider_name)
            default_model = getattr(prov, "default_model", None)
        except Exception:
            default_model = None

    st.session_state.transcript_path = transcript_path
    st.session_state.transcript = {
        "transcript_id": transcript_id,
        **artifact_version_dict(artifact_ver),
        "provider": provider_name,
        "model": default_model,
        "system_prompt": str(system_prompt_path.relative_to(ROOT) if system_prompt_path.is_relative_to(ROOT) else system_prompt_path),
        "tools": str(tools_path.relative_to(ROOT) if tools_path.is_relative_to(ROOT) else tools_path),
        "history_window": history_window,
        "max_tool_rounds": max_tool_rounds,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "turns": [],
    }
    st.session_state.history = []
    st.session_state.turn_index = 0
    st.session_state.session_key = f"{provider_name}:{model_name or ''}:{artifact_ver.artifact_version}"
    st.session_state.telegram_ctrl = TelegramDeliveryController()
    st.session_state.pending_telegram = None
    st.session_state.telegram_delivery = None
    st.session_state.telegram_send_lock = False


# ---------------- Sidebar ----------------
with st.sidebar:
    st.title("🔬 Research Agent")
    st.caption("Day 03 Lab v2 — Tool Eval & Live Multi-Turn Chat")

    provider_name = st.selectbox(
        "Model Provider",
        options=["openrouter", "openai", "anthropic", "gemini", "ollama"],
        index=0,
    )
    model_override = st.text_input(
        "Model Override (để trống dùng mặc định)",
        value="",
        placeholder="e.g. openai/gpt-4o-mini or qwen2.5:7b",
    ).strip() or None

    version_label = st.selectbox(
        "Artifact Version Label",
        options=["v0", "v1", "v2", "v3", "v4-local", "v5-local"],
        index=3,
    )

    col_w, col_r = st.columns(2)
    with col_w:
        history_window = st.number_input("History Window", min_value=1, max_value=20, value=5)
    with col_r:
        max_tool_rounds = st.number_input("Max Tool Rounds", min_value=1, max_value=10, value=4)

    system_prompt_path = ARTIFACTS_DIR / "system_prompt.md"
    tools_path = ARTIFACTS_DIR / "tools.yaml"
    artifact_ver = build_artifact_version(version_label, system_prompt_path, tools_path)

    st.markdown("### 📌 Artifact Hash")
    st.code(artifact_ver.artifact_version, language="text")

    if st.button("🔄 Bắt đầu phiên Chat mới (New Transcript)", use_container_width=True):
        init_new_session(
            provider_name=provider_name,
            model_name=model_override,
            version_label=version_label,
            system_prompt_path=system_prompt_path,
            tools_path=tools_path,
            history_window=int(history_window),
            max_tool_rounds=int(max_tool_rounds),
        )
        st.rerun()

    st.divider()
    st.markdown("### 🔑 Trạng thái API Keys (`.env`)")
    key_badges = []
    for k in [
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
        "TAVILY_API_KEY",
        "FIRECRAWL_API_KEY",
        "RAPIDAPI_KEY",
        "TELEGRAM_BOT_TOKEN",
    ]:
        has_key = bool(os.getenv(k))
        icon = "✅" if has_key else "⚪"
        key_badges.append(f"{icon} `{k}`")
    st.markdown("  \n".join(key_badges))


# Ensure session is initialized
expected_key = f"{provider_name}:{model_override or ''}:{artifact_ver.artifact_version}"
if "transcript" not in st.session_state or st.session_state.get("session_key") != expected_key:
    init_new_session(
        provider_name=provider_name,
        model_name=model_override,
        version_label=version_label,
        system_prompt_path=system_prompt_path,
        tools_path=tools_path,
        history_window=int(history_window),
        max_tool_rounds=int(max_tool_rounds),
    )
if "telegram_ctrl" not in st.session_state:
    st.session_state.telegram_ctrl = TelegramDeliveryController()
for _key, _default in (
    ("pending_telegram", None),
    ("telegram_delivery", None),
    ("telegram_send_lock", False),
):
    if _key not in st.session_state:
        st.session_state[_key] = _default


def _sync_telegram_session_from_ctrl() -> None:
    ctrl: TelegramDeliveryController = st.session_state.telegram_ctrl
    st.session_state.telegram_send_lock = ctrl.send_lock
    if ctrl.pending_text:
        st.session_state.pending_telegram = {
            "text": ctrl.pending_text,
            "created_at": now_iso(),
            "source_turn": st.session_state.turn_index,
        }
    else:
        st.session_state.pending_telegram = None
    if ctrl.last_status:
        st.session_state.telegram_delivery = {
            "status": ctrl.last_status,
            "message": ctrl.last_message,
            "result": ctrl.last_result,
        }


def _set_pending_telegram_from_result(result: dict[str, Any]) -> None:
    pending = result.get("pending_send")
    draft = ""
    if isinstance(pending, dict):
        draft = str(pending.get("text") or "")
    if not draft:
        for event in reversed(result.get("tool_events") or []):
            if event.get("tool") != "send":
                continue
            tool_result = event.get("result") or {}
            if isinstance(tool_result, dict) and (
                tool_result.get("status") == "needs_confirmation"
                or tool_result.get("awaiting_confirmation")
            ):
                draft = str(tool_result.get("text") or (event.get("args") or {}).get("text") or "")
                break
    if draft.strip():
        st.session_state.telegram_ctrl.set_pending(draft)
        _sync_telegram_session_from_ctrl()


def process_user_turn(user_text: str) -> None:
    system_prompt = system_prompt_path.read_text(encoding="utf-8")
    tool_declarations = load_tool_declarations(tools_path)
    openai_tools = to_openai_tools(tool_declarations)

    st.session_state.turn_index += 1
    turn_idx = st.session_state.turn_index

    messages = [
        {"role": "system", "content": system_prompt},
        *trim_history(st.session_state.history, int(history_window)),
        {"role": "user", "content": user_text},
    ]

    turn_record: dict[str, Any] = {
        "turn_index": turn_idx,
        "started_at": now_iso(),
        "user": user_text,
        "status": "started",
        "assistant_text": None,
        "rounds": [],
        "tool_events": [],
    }

    try:
        provider = make_provider(provider_name)
        st.session_state.transcript["model"] = model_override or getattr(provider, "default_model", None)
        result = run_model_tool_loop(
            provider=provider,
            messages=messages,
            tools=openai_tools,
            model=model_override,
            max_tool_rounds=int(max_tool_rounds),
            tool_executor=execute_tool_call_with_send_guard,
        )
        turn_record.update(result)
        assistant_text = result["assistant_text"]
        st.session_state.history.append({"role": "user", "content": user_text})
        st.session_state.history.append({"role": "assistant", "content": assistant_text})
        if result.get("status") == "waiting_for_confirmation":
            _set_pending_telegram_from_result(result)
    except Exception as exc:
        turn_record.update({
            "status": "provider_error",
            "assistant_text": f"⚠️ Lỗi kết nối Provider ({type(exc).__name__}): {exc}",
            "error": f"{type(exc).__name__}: {str(exc)}",
        })

    turn_record["ended_at"] = now_iso()
    st.session_state.transcript["turns"].append(turn_record)
    write_transcript(st.session_state.transcript_path, st.session_state.transcript)


def confirm_and_send_telegram() -> None:
    ctrl: TelegramDeliveryController = st.session_state.telegram_ctrl
    draft = ctrl.pending_text or ""
    outcome = ctrl.confirm_and_send(TOOL_FUNCTIONS["send"])
    _sync_telegram_session_from_ctrl()

    st.session_state.turn_index += 1
    result = outcome.get("result") or {}
    ok = outcome.get("status") == "sent"
    skipped = outcome.get("status") == "skipped_duplicate"
    turn_record: dict[str, Any] = {
        "turn_index": st.session_state.turn_index,
        "started_at": now_iso(),
        "user": "[UI] Confirm & Send Telegram",
        "status": "telegram_send" if ok else ("telegram_send_skipped" if skipped else "telegram_send_failed"),
        "assistant_text": (
            f"✅ Đã gửi Telegram thành công"
            + (f" (message_id={result.get('message_id')})." if result.get("message_id") else ".")
            if ok
            else (
                "ℹ️ " + str(outcome.get("message"))
                if skipped
                else f"❌ Gửi Telegram thất bại: {outcome.get('message')}"
            )
        ),
        "rounds": [],
        "tool_events": [{
            "tool": "send",
            "args": {"text": draft, "confirmed": True},
            "result": result if result else {"status": outcome.get("status"), "message": outcome.get("message")},
        }],
        "ended_at": now_iso(),
    }
    if ok or skipped:
        st.session_state.history.append({"role": "user", "content": "Xác nhận gửi Telegram."})
        st.session_state.history.append({"role": "assistant", "content": turn_record["assistant_text"]})
    st.session_state.transcript["turns"].append(turn_record)
    write_transcript(st.session_state.transcript_path, st.session_state.transcript)


def cancel_pending_telegram() -> None:
    ctrl: TelegramDeliveryController = st.session_state.telegram_ctrl
    draft_preview = ctrl.pending_text or ""
    ctrl.cancel()
    _sync_telegram_session_from_ctrl()
    st.session_state.turn_index += 1
    turn_record = {
        "turn_index": st.session_state.turn_index,
        "started_at": now_iso(),
        "user": "[UI] Cancel Telegram Send",
        "status": "telegram_cancelled",
        "assistant_text": "Đã hủy gửi Telegram. Không có tin nhắn nào được gửi.",
        "rounds": [],
        "tool_events": [{
            "tool": "send",
            "args": {"text": draft_preview, "confirmed": False},
            "result": {"status": "cancelled", "message": "User cancelled before send."},
        }],
        "ended_at": now_iso(),
    }
    st.session_state.history.append({"role": "user", "content": "Hủy gửi Telegram."})
    st.session_state.history.append({"role": "assistant", "content": turn_record["assistant_text"]})
    st.session_state.transcript["turns"].append(turn_record)
    write_transcript(st.session_state.transcript_path, st.session_state.transcript)


# ---------------- Main Tabs ----------------
tab_chat, tab_transcripts, tab_runs, tab_artifacts = st.tabs([
    "💬 Live Chat & Tool Trace",
    "📜 Transcripts JSON",
    "📊 Eval Runs",
    "🛠️ Prompt & Tools",
])

with tab_chat:
    st.subheader("Research Agent — Live Multi-Round Interaction")
    st.caption(
        f"Mọi lượt hội thoại đều tự động ghi vào `{st.session_state.transcript_path.relative_to(ROOT)}` "
        f"(Đã ghi **{len(st.session_state.transcript['turns'])}** lượt — Yêu cầu tối thiểu ≥ 3 lượt)."
    )

    # Quick scenario buttons for Step 5
    st.markdown("**⚡ Câu hỏi mẫu (Step 5 — 3 kịch bản bắt buộc):**")
    q_cols = st.columns(5)
    sample_prompts = [
        ("1️⃣ Research tin AI", "Tin AI hôm nay có gì nổi bật?"),
        ("2️⃣ Thiếu thông tin (Clarify)", "Tóm tắt vài tweet mới nhất giúp mình"),
        ("2️⃣b Bổ sung Account", "Của Andrej Karpathy (@karpathy) nhé, lấy 5 bài"),
        ("3️⃣ Gửi Telegram (Chưa confirm)", "Gửi bản tin AI vừa rồi lên kênh Telegram giúp mình"),
        ("4️⃣ Tra cứu arXiv", "Tìm 3 bài báo arXiv gần đây về AI agent evaluation"),
    ]
    triggered_prompt: str | None = None
    for col, (btn_label, prompt_text) in zip(q_cols, sample_prompts):
        with col:
            if st.button(btn_label, use_container_width=True, help=prompt_text):
                triggered_prompt = prompt_text

    st.divider()

    # Render turns
    for turn in st.session_state.transcript["turns"]:
        with st.chat_message("user"):
            st.markdown(turn["user"])

        with st.chat_message("assistant"):
            status = turn.get("status", "")
            badge_map = {
                "answered": "🟢 `answered`",
                "waiting_for_user": "🟡 `waiting_for_user` (Clarify)",
                "waiting_for_confirmation": "🟡 `waiting_for_confirmation` (Telegram)",
                "telegram_send": "🟢 `telegram_send`",
                "telegram_send_failed": "🔴 `telegram_send_failed`",
                "telegram_cancelled": "⚪ `telegram_cancelled`",
                "max_tool_rounds": "🟠 `max_tool_rounds`",
                "provider_error": "🔴 `provider_error`",
            }
            st.caption(f"Turn #{turn['turn_index']} • Status: {badge_map.get(status, status)}")

            if turn.get("rounds"):
                with st.expander(f"🔧 Tool Calls & Execution Trace ({len(turn.get('tool_events', []))} tool calls)", expanded=False):
                    for r in turn["rounds"]:
                        st.markdown(f"**Round {r['round']}**")
                        if r.get("tool_calls"):
                            st.json(r["tool_calls"])
                        if r.get("tool_results"):
                            st.markdown("*Tool Results:*")
                            st.json(r["tool_results"])
            elif turn.get("tool_events"):
                with st.expander(f"🔧 Tool Events ({len(turn['tool_events'])})", expanded=False):
                    st.json(turn["tool_events"])

            st.markdown(turn.get("assistant_text") or "_(Không có nội dung phản hồi)_")

    pending = st.session_state.get("pending_telegram")
    delivery = st.session_state.get("telegram_delivery")
    if pending or delivery:
        st.divider()
        st.markdown("### 📨 Telegram Bonus Delivery")
        tg_token_ok = bool(os.getenv("TELEGRAM_BOT_TOKEN"))
        tg_chat_ok = bool(os.getenv("TELEGRAM_CHAT_ID"))
        st.caption(
            f"Config: {'✅' if tg_token_ok else '⚪'} `TELEGRAM_BOT_TOKEN` · "
            f"{'✅' if tg_chat_ok else '⚪'} `TELEGRAM_CHAT_ID`"
        )
        if delivery:
            status = delivery.get("status")
            if status == "sent":
                st.success(delivery.get("message") or "Sent.")
            elif status == "cancelled":
                st.info(delivery.get("message") or "Cancelled.")
            elif status == "awaiting_confirmation":
                st.warning(delivery.get("message") or "Awaiting confirmation.")
            elif status == "skipped_duplicate":
                st.info(delivery.get("message") or "Duplicate send blocked.")
            else:
                st.error(delivery.get("message") or "Telegram delivery error.")
        if pending:
            st.markdown("**Nội dung chuẩn bị gửi:**")
            st.text_area(
                "Draft",
                value=str(pending.get("text") or ""),
                height=180,
                disabled=True,
                label_visibility="collapsed",
                key=f"tg_draft_{pending.get('created_at', 'x')}",
            )
            c_confirm, c_cancel = st.columns(2)
            with c_confirm:
                if st.button(
                    "✅ Confirm & Send",
                    use_container_width=True,
                    type="primary",
                    disabled=bool(st.session_state.get("telegram_send_lock")),
                    key="tg_confirm_send",
                ):
                    confirm_and_send_telegram()
                    st.rerun()
            with c_cancel:
                if st.button("❌ Cancel", use_container_width=True, key="tg_cancel_send"):
                    cancel_pending_telegram()
                    st.rerun()

    user_input = st.chat_input("Nhập yêu cầu nghiên cứu (ví dụ: Tin AI hôm nay, tweet của @sama, đọc URL, gửi Telegram...)")
    active_query = triggered_prompt or user_input
    if active_query:
        with st.spinner("Agent đang suy luận và gọi tool..."):
            process_user_turn(active_query)
        st.rerun()

with tab_transcripts:
    st.subheader("📜 Danh sách Transcripts (`starter_v0/transcripts/`)")
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    transcript_files = sorted(TRANSCRIPTS_DIR.glob("*.transcript.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not transcript_files:
        st.info("Chưa có file transcript nào. Hãy chat ở tab **Live Chat** hoặc chạy `python chat.py` để tạo transcript.")
    else:
        selected_tf = st.selectbox(
            "Chọn file transcript để xem:",
            options=transcript_files,
            format_func=lambda p: f"{p.name} ({p.stat().st_size} bytes)",
        )
        if selected_tf:
            content_str = selected_tf.read_text(encoding="utf-8")
            st.download_button(
                label=f"⬇️ Tải xuống {selected_tf.name}",
                data=content_str,
                file_name=selected_tf.name,
                mime="application/json",
            )
            st.json(json.loads(content_str))

with tab_runs:
    st.subheader("📊 Kết quả Eval Runs (`starter_v0/runs/`)")
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    run_files = sorted(RUNS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not run_files:
        st.info("Chưa có file run nào trong `starter_v0/runs/`. Hãy chạy `python run_eval.py` để tạo log.")
    else:
        selected_rf = st.selectbox(
            "Chọn file eval run:",
            options=run_files,
            format_func=lambda p: p.name,
        )
        if selected_rf:
            run_data = json.loads(selected_rf.read_text(encoding="utf-8"))
            summary = run_data.get("summary", {})
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Case Accuracy", f"{summary.get('case_accuracy', 0):.1%}")
            m2.metric("Tool Routing Acc", f"{summary.get('tool_routing_accuracy', 0):.1%}")
            m3.metric("Argument Acc", f"{summary.get('argument_accuracy', 0):.1%}")
            m4.metric("Multi-turn Acc", f"{summary.get('multiturn_accuracy', 0):.1%}")
            st.json(run_data)

with tab_artifacts:
    st.subheader("🛠️ System Prompt & Tool Declarations hiện tại")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**`artifacts/system_prompt.md`** (hash: `{artifact_ver.prompt_hash[:12]}`)")
        st.code(system_prompt_path.read_text(encoding="utf-8"), language="markdown")
    with c2:
        st.markdown(f"**`artifacts/tools.yaml`** (hash: `{artifact_ver.tools_hash[:12]}` — {len(TOOL_FUNCTIONS)} tools registered)")
        st.code(tools_path.read_text(encoding="utf-8"), language="yaml")
