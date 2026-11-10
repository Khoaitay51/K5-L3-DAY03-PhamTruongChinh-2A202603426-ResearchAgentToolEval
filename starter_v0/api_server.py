from __future__ import annotations

import argparse
import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent import ResearchAgent
from chat import run_model_tool_loop
from env_loader import load_lab_env
from providers import make_provider
from tools import TOOL_FUNCTIONS, load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version

ARTIFACTS_DIR = ROOT / "artifacts"
load_lab_env(ROOT)


class AgentAPIHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw.strip() else {}

    def do_GET(self) -> None:
        if self.path in ("/", "/health"):
            ver = build_artifact_version("live", ARTIFACTS_DIR / "system_prompt.md", ARTIFACTS_DIR / "tools.yaml")
            self._send_json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "service": "research-agent-api",
                    **artifact_version_dict(ver),
                    "registered_tools": list(TOOL_FUNCTIONS.keys()),
                },
            )
            return

        if self.path == "/tools":
            decls = load_tool_declarations(ARTIFACTS_DIR / "tools.yaml")
            self._send_json(HTTPStatus.OK, {"tools": decls})
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found", "path": self.path})

    def do_POST(self) -> None:
        try:
            body = self._read_json()
        except Exception as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json", "message": str(exc)})
            return

        provider_name = body.get("provider", "openrouter")
        model = body.get("model")
        version = body.get("version", "v0")
        query = body.get("query") or body.get("message") or ""
        messages = body.get("messages") or ([{"role": "user", "content": query}] if query else [])

        if not messages:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "missing_input", "message": "Provide 'query', 'message', or 'messages' in JSON body."},
            )
            return

        try:
            system_prompt_path = ARTIFACTS_DIR / "system_prompt.md"
            tools_path = ARTIFACTS_DIR / "tools.yaml"
            system_prompt = system_prompt_path.read_text(encoding="utf-8")
            artifact_ver = build_artifact_version(version, system_prompt_path, tools_path)
            declarations = load_tool_declarations(tools_path)
            openai_tools = to_openai_tools(declarations)
            provider = make_provider(provider_name)
            selected_model = model or getattr(provider, "default_model", None)

            if self.path == "/run":
                agent = ResearchAgent(provider, system_prompt=system_prompt, tools=openai_tools, model=model)
                run = agent.run(messages, tool_choice=body.get("tool_choice"))
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "provider": provider_name,
                        "model": selected_model,
                        **artifact_version_dict(artifact_ver),
                        "text": run.text,
                        "tool_calls": [{"name": c.name, "args": c.args} for c in run.tool_calls],
                        "tool_results": run.tool_results,
                    },
                )
                return

            if self.path == "/chat":
                full_messages = [{"role": "system", "content": system_prompt}, *messages]
                outcome = run_model_tool_loop(
                    provider=provider,
                    messages=full_messages,
                    tools=openai_tools,
                    model=model,
                    max_tool_rounds=int(body.get("max_tool_rounds", 4)),
                )
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "provider": provider_name,
                        "model": selected_model,
                        **artifact_version_dict(artifact_ver),
                        **outcome,
                    },
                )
                return

            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found", "path": self.path})
        except Exception as exc:
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": type(exc).__name__, "message": str(exc)},
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="HTTP API server for Research Agent (curl-friendly).")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), AgentAPIHandler)
    print(f"Research Agent HTTP API listening on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

