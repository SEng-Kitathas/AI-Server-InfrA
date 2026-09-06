"""Shared helpers for receiver resilience gates."""

from __future__ import annotations

import json
import os
import sys
import shutil
import threading
import time
import zipfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TypedDict

from strict_json_boundary import parse_json_boundary_text, render_json_boundary, write_json_boundary

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASELINE_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
TRACE_PROJECT_ID = "route_trace_tmp_full_route_gate"
GATE_KEY = "receiver-resilience-gate-key"
GATE_RUNTIME_ROOT = PROJECT_ROOT / ".pcmmad_gate_runtime"
GATE_PROJECTS_ROOT = GATE_RUNTIME_ROOT / "projects"


class JsonRecord(TypedDict, total=False):
    ok: bool


class ProbeResult(TypedDict, total=False):
    name: str
    route: str
    method: str
    category: str
    status: int
    expected_statuses: list[int]
    pass_: bool
    json_object: bool
    ok_field: object
    error_code: str | None
    body_sample: object
    exception: str


@dataclass(frozen=True)
class ProbeCase:
    name: str
    route: str
    method: str
    expected_statuses: tuple[int, ...]
    category: str
    payload: JsonRecord | None = None
    headers: dict[str, str] | None = None
    require_json: bool = True
    require_ok: bool | None = None


class DummyBrowserBridge(BaseHTTPRequestHandler):
    mode = "success"

    def _send(self, value: object, status: int = 200) -> None:
        raw = render_json_boundary(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _body(self) -> object:
        size = int(self.headers.get("content-length", "0") or "0")
        if size <= 0:
            return {}
        try:
            return parse_json_boundary_text(self.rfile.read(size).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            return {}

    def do_GET(self) -> None:
        if self.mode == "malformed":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{bad-json")
            return
        if self.mode == "error":
            self._send({"ok": False, "error": "dummy bridge error"}, 503)
            return
        if self.path.startswith("/health"):
            self._send({"ok": True, "status": "online", "bridge": "dummy-resilience"})
        elif self.path.startswith("/sessions"):
            self._send({"ok": True, "sessions": [{"session_id": "resilience-session"}]})
        else:
            self._send({"ok": False}, 404)

    def do_POST(self) -> None:
        if self.mode == "malformed":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{bad-json")
            return
        if self.mode == "error":
            self._send({"ok": False, "error": "dummy bridge error"}, 503)
            return
        body = self._body()
        if self.path.startswith("/screenshot"):
            session_id = body.get("session_id") if isinstance(body, dict) else None
            self._send({"ok": True, "path": "dummy/resilience.png", "session_id": session_id})
        elif self.path.startswith("/content"):
            self._send({"ok": True, "content": "<html>RESILIENCE</html>"})
        elif self.path.startswith("/evaluate"):
            self._send({"ok": True, "result": "RESILIENCE"})
        else:
            self._send({"ok": True, "path": self.path, "payload": body})

    def log_message(self, *_args: object) -> None:
        return


def configure_gate_environment() -> None:
    """Bind every mutable receiver surface to an isolated project-local test root."""

    roots = {
        "PCMMAD_ROOT": GATE_RUNTIME_ROOT,
        "PCMMAD_PROJECTS_ROOT": GATE_PROJECTS_ROOT,
        "PCMMAD_SYSTEM_ROOT": GATE_RUNTIME_ROOT / "system",
        "PCMMAD_SANDBOX_ROOT": GATE_RUNTIME_ROOT / "sandbox",
        "PCMMAD_TEMP_ROOT": GATE_RUNTIME_ROOT / "temp",
    }
    for name, path in roots.items():
        path.mkdir(parents=True, exist_ok=True)
        os.environ[name] = str(path)
    os.environ["PCMMAD_MOUNTS_JSON"] = json.dumps(
        {
            "root": str(GATE_RUNTIME_ROOT),
            "projects": str(GATE_PROJECTS_ROOT),
            "system": str(GATE_RUNTIME_ROOT / "system"),
            "sandbox": str(GATE_RUNTIME_ROOT / "sandbox"),
            "temp": str(GATE_RUNTIME_ROOT / "temp"),
        }
    )
    os.environ["GITHOME_API_KEY"] = GATE_KEY


def start_dummy_bridge(mode: str = "success") -> ThreadingHTTPServer:
    """Start an isolated bridge on an OS-assigned port and publish its actual URL."""

    DummyBrowserBridge.mode = mode
    server = ThreadingHTTPServer(("127.0.0.1", 0), DummyBrowserBridge)
    host, port = server.server_address[:2]
    os.environ["PCMMAD_BROWSER_BRIDGE_URL"] = f"http://{host}:{port}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    time.sleep(0.05)
    return server


def prepare_trace_project() -> Path:
    configure_gate_environment()
    project_root = GATE_PROJECTS_ROOT / TRACE_PROJECT_ID
    if project_root.exists():
        shutil.rmtree(project_root)
    (project_root / "reports").mkdir(parents=True, exist_ok=True)
    workspace = project_root / "data" / "route_trace_workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    (project_root / "reports" / "route_trace_written.txt").write_text(
        "route trace written file\n", encoding="utf-8"
    )
    (workspace / "sample.txt").write_text("route trace sample\n", encoding="utf-8")
    with zipfile.ZipFile(workspace / "sample.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("inside.txt", "route trace zip content\n")
    with zipfile.ZipFile(workspace / "slip.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("../slip.txt", "bad\n")
    return project_root


def create_client() -> object:
    configure_gate_environment()
    if str(BASELINE_ROOT) not in sys.path:
        sys.path.insert(0, str(BASELINE_ROOT))
    from app_factory import create_app

    app = create_app()
    app.testing = True
    return app.test_client()


def authorized_headers() -> dict[str, str]:
    return {"X-GitHome-Key": GATE_KEY}


def _response_for_case(client: object, case: ProbeCase, headers: dict[str, str]) -> object:
    if case.method == "GET":
        return client.get(case.route, headers=headers)
    return client.post(case.route, json=case.payload, headers=headers)


def _probe_passes(case: ProbeCase, status: int, json_object: bool, ok_field: object) -> bool:
    status_ok = status in case.expected_statuses
    json_ok = True if not case.require_json else json_object
    ok_ok = True if case.require_ok is None else ok_field is case.require_ok
    return bool(status_ok and json_ok and ok_ok)


def _probe_result_from_response(case: ProbeCase, response: object) -> ProbeResult:
    body = response.get_json(silent=True)
    json_object = isinstance(body, dict)
    ok_field = body.get("ok") if json_object else None
    error_code = body.get("error_code") if json_object else None
    return ProbeResult(
        name=case.name,
        route=case.route,
        method=case.method,
        category=case.category,
        status=response.status_code,
        expected_statuses=list(case.expected_statuses),
        pass_=_probe_passes(case, response.status_code, json_object, ok_field),
        json_object=json_object,
        ok_field=ok_field,
        error_code=str(error_code) if error_code is not None else None,
        body_sample=body if json_object else response.get_data(as_text=True)[:1000],
    )


def _probe_exception_result(case: ProbeCase, exc: BaseException) -> ProbeResult:
    return ProbeResult(
        name=case.name,
        route=case.route,
        method=case.method,
        category=case.category,
        expected_statuses=list(case.expected_statuses),
        pass_=False,
        exception=f"{type(exc).__name__}: {exc}",
    )


def run_probe(client: object, case: ProbeCase) -> ProbeResult:
    headers = case.headers if case.headers is not None else authorized_headers()
    try:
        return _probe_result_from_response(case, _response_for_case(client, case, headers))
    except (RuntimeError, ValueError, TypeError, OSError, AssertionError, AttributeError) as exc:
        return _probe_exception_result(case, exc)


def report_payload(
    name: str, approach: str, results: list[ProbeResult], extra: JsonRecord | None = None
) -> JsonRecord:
    failures = [result for result in results if not result.get("pass_")]
    unexpected_500 = [result for result in results if int(result.get("status", 0) or 0) == 500]
    payload: JsonRecord = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "gate_name": name,
        "approach": approach,
        "levels": {
            "nano": "individual probe",
            "micro": "route family / boundary class",
            "meso": "gate matrix",
            "macro": "claim gate",
        },
        "clean": not failures and not unexpected_500,
        "probe_count": len(results),
        "failure_count": len(failures),
        "unexpected_500_count": len(unexpected_500),
        "failures": failures,
        "unexpected_500": unexpected_500,
        "results": results,
    }
    if extra:
        payload.update(extra)
    return payload


def shutdown_test_runtime() -> None:
    """Stop runtime workers explicitly so embedded gate runners terminate deterministically."""

    try:
        from execution_routes import _shutdown_scheduler

        _shutdown_scheduler()
    except (ImportError, RuntimeError):
        pass
    try:
        from lab_routes import _shutdown_batch_executor

        _shutdown_batch_executor()
    except (ImportError, RuntimeError):
        pass


def write_report(path: Path, payload: JsonRecord) -> None:
    write_json_boundary(path, payload)
    sys.stdout.write(render_json_boundary({"report": str(path), "clean": payload["clean"]}) + "\n")
    if not payload["clean"]:
        raise SystemExit(1)
