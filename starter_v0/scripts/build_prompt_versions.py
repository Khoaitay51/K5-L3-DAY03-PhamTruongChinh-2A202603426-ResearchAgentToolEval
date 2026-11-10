"""Rebuild historical system_prompt snapshots for v0→v3 comparison runs."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "prompt_versions"
CUR = ROOT / "artifacts" / "system_prompt.md"


def sha12(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # v0: original ambiguous baseline from first lab commit
    v0_text = subprocess.check_output(
        ["git", "show", "ff7427d:starter_v0/artifacts/system_prompt.md"],
        cwd=ROOT.parent,
        text=True,
    )
    (OUT / "v0_system_prompt.md").write_text(v0_text if v0_text.endswith("\n") else v0_text + "\n", encoding="utf-8")

    cur = CUR.read_text(encoding="utf-8")
    if not cur.endswith("\n"):
        cur += "\n"
    (OUT / "v3_system_prompt.md").write_text(cur, encoding="utf-8")

    multi_v3 = (
        "   - **Multi-turn Context**: Use earlier turns only as context to fill in or update parameters "
        "(handle, limit, timeframe, URL, topic, tool choice) for the latest user turn. "
        'If the user switches source (e.g., "Bỏ Twitter, chuyển sang tìm trên web tin tức"), '
        "call ONLY the new tool (`lookup`) and do NOT also call the superseded tool (`social_search`/`timeline`)."
    )
    multi_v2 = (
        "   - **Multi-turn Context**: Use earlier turns only as context to fill in or update parameters "
        "(handle, limit, timeframe, URL, topic, tool choice) for the latest user turn. "
        "Do not re-run tools for earlier turns that were superseded."
    )
    v2 = cur.replace(multi_v3, multi_v2)
    if v2 == cur:
        raise SystemExit("Failed to derive v2 prompt from current v3 (multi-turn replace missed)")
    (OUT / "v2_system_prompt.md").write_text(v2, encoding="utf-8")

    send_v2 = (
        "2. **Mandatory Confirmation Before External Actions (`wrong_boundary`)**:\n"
        "   - Sending/publishing to Telegram is a side-effect action. Never send automatically.\n"
        '   - On the first request to send/post/publish (e.g., "Đăng bản tin này lên Telegram giúp mình"), '
        'ALWAYS call `clarify` with `response_type="yes_no"` to ask confirmation first. '
        'Never use `response_type="text"` for this confirmation, and do not call `send` yet.\n'
        "   - Only after the user explicitly says yes may you call `send` "
        "(UI path may use `confirmed=false` then Confirm & Send). "
        "Never invent approval; do not reuse an old approval for a different draft."
    )
    send_v1 = (
        "2. **Mandatory Confirmation Before External Actions (`wrong_boundary`)**:\n"
        "   - Sending/publishing to Telegram is a side-effect action. Never send automatically.\n"
        "   - On the first request to send/post/publish, do **one** of:\n"
        '     1. Call `clarify` with `response_type="yes_no"` asking the user to approve the exact draft, OR\n'
        "     2. Call `send` with the draft text and `confirmed=false` so the UI can ask for confirmation.\n"
        "   - Never set `confirmed=true` unless the user has explicitly approved the exact text "
        "in this conversation (or via the Confirm & Send UI).\n"
        "   - Do not reuse an old approval for a different draft."
    )
    v1 = v2.replace(send_v2, send_v1)
    if v1 == v2:
        raise SystemExit("Failed to derive v1 prompt from v2 (send-boundary replace missed)")
    (OUT / "v1_system_prompt.md").write_text(v1, encoding="utf-8")

    for ver in ("v0", "v1", "v2", "v3"):
        path = OUT / f"{ver}_system_prompt.md"
        print(f"{ver}: {path.name} hash={sha12(path)} bytes={path.stat().st_size}")


if __name__ == "__main__":
    main()
