"""Full receiver route trace gate.

Embodies PROBE -> DERIVE -> VERIFY -> EMBODY -> RECURSE for every Flask route.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import shutil
import tempfile
import threading
import time
import traceback
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
REPORT_PATH = PROJECT_ROOT / "reports" / "RECEIVER_FULL_ROUTE_TRACE_GATE_REPORT.json"
TRACE_KEY = "receiver-full-route-trace-key"
TRACE_PROJECT_ID = "route_trace_tmp_full_route_gate"
GATE_RUNTIME_ROOT = PROJECT_ROOT / ".pcmmad_gate_runtime_full_route"
GATE_PROJECTS_ROOT = GATE_RUNTIME_ROOT / "projects"


class JsonRecord(TypedDict, total=False):
    ok: bool


JsonObject = JsonRecord


class TraceResult(TypedDict, total=False):
    rule: str
    endpoint: str
    method: str
    label: str
    nano_probe: str
    micro_family: str
    meso_route_index: int
    macro_claim_effect: str
    status: int
    expected_statuses: list[int]
    pass_: bool
    ok_field: object
    error_code: str | None
    content_type: str
    json_object: bool
    body_sample: object
    exception: str
    traceback: str


class RouteCoverage(TypedDict):
    route_count: int
    covered_route_count: int
    missing_routes: list[str]


@dataclass(frozen=True)
class TraceCase:
    rule: str
    method: str
    label: str
    expected_statuses: tuple[int, ...]
    payload_factory: Callable[["TraceContext"], JsonObject | None] = lambda _ctx: None
    path_factory: Callable[["TraceContext"], str] | None = None
    require_json_object: bool = True
    require_ok_true: bool = False
    nano_probe: str = "route_contract"
    micro_family: str = "general"
    macro_claim_effect: str = "blocks_runtime_working"


@dataclass
class TraceContext:
    project_id: str
    trace_root: Path
    zip_path: Path
    sample_file: str
    commit_id: str = "missing-commit-for-route-trace"
    execution_job_id: str = "missing-job-for-route-trace"
    lab_result_handle: str = "missing-handle-for-route-trace"
    run_id: str = ""


@dataclass(frozen=True)
class TraceInvocation:
    case: TraceCase
    route: JsonObject
    ctx: TraceContext


class DummyBrowserBridge(BaseHTTPRequestHandler):
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
            parsed = parse_json_boundary_text(self.rfile.read(size).decode("utf-8"))
            return parsed
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def do_GET(self) -> None:
        if self.path.startswith("/health"):
            self._send({"ok": True, "status": "online", "bridge": "dummy-route-trace"})
        elif self.path.startswith("/sessions"):
            self._send({"ok": True, "sessions": [{"session_id": "route-trace-session"}]})
        else:
            self._send({"ok": False}, 404)

    def do_POST(self) -> None:
        body = self._body()
        if self.path.startswith("/screenshot"):
            session_id = body.get("session_id") if isinstance(body, dict) else None
            self._send({"ok": True, "path": "dummy/route-trace.png", "session_id": session_id})
        elif self.path.startswith("/content"):
            self._send({"ok": True, "content": "<html>ROUTE TRACE</html>"})
        elif self.path.startswith("/evaluate"):
            self._send({"ok": True, "result": "ROUTE_TRACE"})
        else:
            self._send({"ok": True, "path": self.path, "payload": body})

    def log_message(self, *_args: object) -> None:
        return


def _configure_gate_environment() -> None:
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
        {name.removeprefix("PCMMAD_").removesuffix("_ROOT").lower(): str(path)
         for name, path in roots.items()}
    )
    os.environ["GITHOME_API_KEY"] = TRACE_KEY


def _start_dummy_bridge() -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", 0), DummyBrowserBridge)
    host, port = server.server_address[:2]
    os.environ["PCMMAD_BROWSER_BRIDGE_URL"] = f"http://{host}:{port}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    time.sleep(0.05)
    return server


def _prepare_context() -> TraceContext:
    _configure_gate_environment()
    project_root = GATE_PROJECTS_ROOT / TRACE_PROJECT_ID
    if project_root.exists():
        shutil.rmtree(project_root)
    trace_root = project_root / "data" / "route_trace_workspace"
    trace_root.mkdir(parents=True, exist_ok=True)
    (project_root / "reports").mkdir(parents=True, exist_ok=True)
    (project_root / "reports" / "route_trace_written.txt").write_text(
        "route trace written file\n", encoding="utf-8"
    )
    sample_rel = "data/route_trace_workspace/sample.txt"
    sample_path = project_root / sample_rel
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    sample_path.write_text("route trace sample\nCONSTRAINT route trace\n", encoding="utf-8")
    zip_path = trace_root / "sample.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("inside.txt", "route trace zip content\n")
    return TraceContext(
        TRACE_PROJECT_ID, trace_root, zip_path, sample_rel, run_id=str(time.time_ns())
    )


def _project(ctx: TraceContext) -> JsonObject:
    return {"project_id": ctx.project_id}


def _project_reports(ctx: TraceContext) -> JsonObject:
    return {"project_id": ctx.project_id, "path": "reports", "recursive": False, "limit": 10}


def _project_files_list(ctx: TraceContext) -> JsonObject:
    return {
        "project_id": ctx.project_id,
        "path": "reports",
        "recursive": False,
        "contains": "ROUTE_TRACE_SENTINEL_NO_MATCH",
        "limit": 5,
    }


def _project_files_read(ctx: TraceContext) -> JsonObject:
    return {
        "project_id": ctx.project_id,
        "path": "reports/route_trace_written.txt",
        "max_bytes": 10000,
    }


def _project_files_search(ctx: TraceContext) -> JsonObject:
    return {
        "project_id": ctx.project_id,
        "path": "reports",
        "query": "route_trace",
        "recursive": True,
        "limit": 10,
    }


def _project_context_rehydrate(ctx: TraceContext) -> JsonObject:
    return {
        "project_id": ctx.project_id,
        "path": "reports",
        "topic": "route trace",
        "budget_bytes": 2000,
        "debug": False,
    }


def _write_project_file(ctx: TraceContext) -> JsonObject:
    return {
        "project_id": ctx.project_id,
        "path": "reports/route_trace_written.txt",
        "content": "route_trace written file\n",
        "mode": "overwrite",
    }


def _read_many(ctx: TraceContext) -> JsonObject:
    return {
        "project_id": ctx.project_id,
        "paths": ["reports/route_trace_written.txt"],
        "max_bytes_each": 10000,
    }


def _run_sync(ctx: TraceContext) -> JsonObject:
    return {
        "project_id": ctx.project_id,
        "command": [sys.executable],
        "args": ["-c", "import sys; sys.stdout.write('route-trace-sync\\n')"],
        "timeout_seconds": 10,
        "stdout_max_bytes": 10000,
        "stderr_max_bytes": 10000,
    }


def _run_python(ctx: TraceContext) -> JsonObject:
    return {
        "project_id": ctx.project_id,
        "code": "import sys; sys.stdout.write('route-trace-python\\n')",
        "timeout_seconds": 10,
        "stdout_max_bytes": 10000,
        "stderr_max_bytes": 10000,
    }


def _execution_submit(ctx: TraceContext) -> JsonObject:
    return {
        "project_id": ctx.project_id,
        "command": [sys.executable],
        "args": ["-c", "import sys; sys.stdout.write('route-trace-execution\\n')"],
        "timeout_seconds": 10,
        "stdout_max_bytes": 10000,
        "stderr_max_bytes": 10000,
        "idempotency_key": f"route-trace-execution-submit-{ctx.run_id}",
    }


def _execution_status(ctx: TraceContext) -> JsonObject:
    return {"project_id": ctx.project_id, "job_id": ctx.execution_job_id}


def _execution_output(ctx: TraceContext) -> JsonObject:
    return {"project_id": ctx.project_id, "job_id": ctx.execution_job_id, "max_bytes": 10000}


def _execution_list(ctx: TraceContext) -> JsonObject:
    return {"project_id": ctx.project_id, "limit": 20}


def _execution_register(ctx: TraceContext) -> JsonObject:
    return {
        "project_id": ctx.project_id,
        "source_path": "reports/route_trace_written.txt",
        "artifact_class": "notes.maintenance",
        "logical_name": "route_trace_registered.txt",
        "operation": "create",
        "idempotency_key": "route-trace-register",
    }


def _execution_replay(ctx: TraceContext) -> JsonObject:
    return {"project_id": ctx.project_id, "job_id": ctx.execution_job_id, "timeout_seconds": 10}


def _execution_terminate(ctx: TraceContext) -> JsonObject:
    return {"project_id": ctx.project_id, "job_id": ctx.execution_job_id}


def _execution_wait(ctx: TraceContext) -> JsonObject:
    return {"project_id": ctx.project_id, "job_id": ctx.execution_job_id, "timeout_seconds": 1}


def _zip_read(ctx: TraceContext) -> JsonObject:
    return {"zip_path": str(ctx.zip_path), "entries": ["inside.txt"], "max_entry_bytes": 10000}


def _files_tree(ctx: TraceContext) -> JsonObject:
    return {"path": str(ctx.trace_root), "depth": 2, "limit": 20}


def _journal_append(ctx: TraceContext) -> JsonObject:
    return {
        "project_id": ctx.project_id,
        "entry_type": "route_trace",
        "title": "Route trace",
        "content": "route trace journal entry",
        "tags": ["route-trace"],
        "session_id": "route-trace-session",
    }


def _journal_read(ctx: TraceContext) -> JsonObject:
    return {"project_id": ctx.project_id, "limit": 10}


def _checkpoint(ctx: TraceContext) -> JsonObject:
    return {"project_id": ctx.project_id, "checkpoint_name": "route_trace_checkpoint"}


def _legacy_plan(ctx: TraceContext) -> JsonObject:
    return {
        "project_id": ctx.project_id,
        "artifact_class": "notes.maintenance",
        "logical_name": "route_trace_plan.txt",
        "operation": "create",
        "content": "route trace plan content\n",
    }


def _legacy_commit(ctx: TraceContext) -> JsonObject:
    return {
        "project_id": ctx.project_id,
        "artifact_class": "notes.maintenance",
        "logical_name": "route_trace_commit.txt",
        "operation": "create",
        "content": "route trace commit content\n",
        "session_id": "route-trace-session",
        "commit_id": "route-trace-commit",
        "idempotency_key": "route-trace-commit-key",
    }


def _project_status(ctx: TraceContext) -> JsonObject:
    return {"project_id": ctx.project_id, "commit_id": ctx.commit_id}


def _models_list(ctx: TraceContext) -> JsonObject:
    return {"project_id": ctx.project_id, "path": ".", "recursive": False, "limit": 5}


def _models_inspect(ctx: TraceContext) -> JsonObject:
    return {"project_id": ctx.project_id, "path": "missing-model.bin"}


def _archives_list(ctx: TraceContext) -> JsonObject:
    return {
        "project_id": ctx.project_id,
        "path": "data/route_trace_workspace",
        "recursive": True,
        "limit": 20,
    }


def _archives_inspect(ctx: TraceContext) -> JsonObject:
    return {
        "project_id": ctx.project_id,
        "path": "data/route_trace_workspace/sample.zip",
        "max_entries": 20,
    }


def _archives_extract(ctx: TraceContext) -> JsonObject:
    return {
        "project_id": ctx.project_id,
        "path": "data/route_trace_workspace/sample.zip",
        "destination_path": "data/route_trace_workspace/extracted",
        "selected_entries": ["inside.txt"],
        "overwrite": True,
    }


def _lab_dispatch(ctx: TraceContext) -> JsonObject:
    return {"tool_name": "lab.health", "payload": {}}


def _lab_batch(ctx: TraceContext) -> JsonObject:
    return {
        "project_id": ctx.project_id,
        "steps": [
            {"tool_name": "lab.health", "payload": {}},
            {"tool_name": "project.files.list", "payload": _project_files_list(ctx)},
        ],
        "stop_on_error": False,
        "parallelism": 1,
    }


def _lab_results_missing(ctx: TraceContext) -> JsonObject:
    return {"project_id": ctx.project_id, "handle": ctx.lab_result_handle, "summary_only": True}


def _research_search(_ctx: TraceContext) -> JsonObject:
    return {"q": "", "max_results": 1}


def _research_paper(_ctx: TraceContext) -> JsonObject:
    return {"paper_id": ""}


def _research_hunt(_ctx: TraceContext) -> JsonObject:
    return {"topic": "", "mode": "direct_hunt", "max_results": 1}


TRACE_CASES: tuple[TraceCase, ...] = (
    TraceCase(
        "/health", "GET", "legacy health", (200,), require_ok_true=True, micro_family="health"
    ),
    TraceCase(
        "/capabilities",
        "GET",
        "capabilities",
        (200,),
        require_json_object=True,
        micro_family="health",
    ),
    TraceCase(
        "/context/health",
        "GET",
        "context health",
        (200,),
        require_ok_true=True,
        micro_family="health",
    ),
    TraceCase(
        "/lab/health", "GET", "lab health", (200,), require_json_object=True, micro_family="lab"
    ),
    TraceCase(
        "/lab/tools", "GET", "lab tools", (200,), require_json_object=True, micro_family="lab"
    ),
    TraceCase(
        "/lab/mounts", "GET", "lab mounts", (200,), require_json_object=True, micro_family="lab"
    ),
    TraceCase(
        "/lab/mcp/manifest",
        "GET",
        "lab mcp manifest",
        (200,),
        require_json_object=True,
        micro_family="lab",
    ),
    TraceCase(
        "/manifest",
        "GET",
        "legacy manifest",
        (200, 400, 404),
        require_json_object=True,
        micro_family="legacy",
    ),
    TraceCase(
        "/research/health",
        "GET",
        "research health",
        (200,),
        require_json_object=True,
        micro_family="research",
    ),
    TraceCase(
        "/static/<path:filename>",
        "GET",
        "static missing",
        (404,),
        path_factory=lambda _ctx: "/static/route-trace-missing.txt",
        require_json_object=False,
        micro_family="static",
    ),
    TraceCase(
        "/status/<commit_id>",
        "GET",
        "legacy status missing",
        (400, 404),
        path_factory=lambda ctx: f"/status/{ctx.commit_id}",
        require_json_object=True,
        micro_family="legacy",
    ),
    TraceCase(
        "/project/init",
        "POST",
        "project init",
        (200,),
        _project,
        require_ok_true=True,
        micro_family="project",
    ),
    TraceCase(
        "/project/info",
        "POST",
        "project info",
        (200,),
        _project,
        require_ok_true=True,
        micro_family="project",
    ),
    TraceCase(
        "/project/manifest",
        "POST",
        "project manifest",
        (200,),
        _project,
        require_ok_true=True,
        micro_family="project",
    ),
    TraceCase(
        "/project/status",
        "POST",
        "project status missing",
        (404,),
        _project_status,
        require_json_object=True,
        micro_family="legacy",
    ),
    TraceCase(
        "/plan",
        "POST",
        "legacy plan",
        (200,),
        _legacy_plan,
        require_ok_true=True,
        micro_family="legacy",
    ),
    TraceCase(
        "/commit",
        "POST",
        "legacy commit",
        (200,),
        _legacy_commit,
        require_ok_true=True,
        micro_family="legacy",
    ),
    TraceCase(
        "/project/files/write",
        "POST",
        "project write file",
        (200,),
        _write_project_file,
        require_ok_true=True,
        micro_family="files",
    ),
    TraceCase(
        "/project/files/list",
        "POST",
        "project list files",
        (200,),
        _project_files_list,
        require_ok_true=True,
        micro_family="files",
    ),
    TraceCase(
        "/project/files/read",
        "POST",
        "project read file",
        (200,),
        _project_files_read,
        require_ok_true=True,
        micro_family="files",
    ),
    TraceCase(
        "/project/files/search",
        "POST",
        "project search files",
        (200,),
        _project_files_search,
        require_ok_true=True,
        micro_family="files",
    ),
    TraceCase(
        "/project/files/read_many",
        "POST",
        "project read many",
        (200,),
        _read_many,
        require_ok_true=True,
        micro_family="files",
    ),
    TraceCase(
        "/project/context/rehydrate",
        "POST",
        "context rehydrate",
        (200,),
        _project_context_rehydrate,
        require_ok_true=True,
        micro_family="context",
    ),
    TraceCase(
        "/run",
        "POST",
        "run sync",
        (200,),
        _run_sync,
        require_ok_true=True,
        micro_family="execution",
    ),
    TraceCase(
        "/run/python",
        "POST",
        "run python",
        (200,),
        _run_python,
        require_ok_true=True,
        micro_family="execution",
    ),
    TraceCase(
        "/project/execution/submit",
        "POST",
        "execution submit",
        (200,),
        _execution_submit,
        require_ok_true=True,
        micro_family="execution",
    ),
    TraceCase(
        "/project/execution/list",
        "POST",
        "execution list",
        (200,),
        _execution_list,
        require_ok_true=True,
        micro_family="execution",
    ),
    TraceCase(
        "/project/execution/status",
        "POST",
        "execution missing status",
        (404,),
        _execution_status,
        require_json_object=True,
        micro_family="execution",
    ),
    TraceCase(
        "/project/execution/output",
        "POST",
        "execution missing output",
        (404,),
        _execution_output,
        require_json_object=True,
        micro_family="execution",
    ),
    TraceCase(
        "/project/execution/wait",
        "POST",
        "execution missing wait",
        (404,),
        _execution_wait,
        require_json_object=True,
        micro_family="execution",
    ),
    TraceCase(
        "/project/execution/register",
        "POST",
        "execution register",
        (200, 409),
        _execution_register,
        require_json_object=True,
        micro_family="execution",
    ),
    TraceCase(
        "/project/execution/replay",
        "POST",
        "execution missing replay",
        (404,),
        _execution_replay,
        require_json_object=True,
        micro_family="execution",
    ),
    TraceCase(
        "/project/execution/terminate",
        "POST",
        "execution missing terminate",
        (404,),
        _execution_terminate,
        require_json_object=True,
        micro_family="execution",
    ),
    TraceCase(
        "/files/tree",
        "POST",
        "files tree",
        (200,),
        _files_tree,
        require_ok_true=True,
        micro_family="filesystem",
    ),
    TraceCase(
        "/zip/read",
        "POST",
        "zip read",
        (200,),
        _zip_read,
        require_ok_true=True,
        micro_family="archive",
    ),
    TraceCase(
        "/project/models/list",
        "POST",
        "models list",
        (200,),
        _models_list,
        require_ok_true=True,
        micro_family="models",
    ),
    TraceCase(
        "/project/models/inspect",
        "POST",
        "models missing inspect",
        (404,),
        _models_inspect,
        require_json_object=True,
        micro_family="models",
    ),
    TraceCase(
        "/project/archives/list",
        "POST",
        "archives list",
        (200,),
        _archives_list,
        require_ok_true=True,
        micro_family="archive",
    ),
    TraceCase(
        "/project/archives/inspect",
        "POST",
        "archives inspect",
        (200,),
        _archives_inspect,
        require_ok_true=True,
        micro_family="archive",
    ),
    TraceCase(
        "/project/archives/extract",
        "POST",
        "archives extract",
        (200,),
        _archives_extract,
        require_ok_true=True,
        micro_family="archive",
    ),
    TraceCase(
        "/project/journal/append",
        "POST",
        "journal append",
        (200,),
        _journal_append,
        require_ok_true=True,
        micro_family="journal",
    ),
    TraceCase(
        "/project/journal/read",
        "POST",
        "journal read",
        (200,),
        _journal_read,
        require_ok_true=True,
        micro_family="journal",
    ),
    TraceCase(
        "/project/checkpoints/create",
        "POST",
        "checkpoint create",
        (200,),
        _checkpoint,
        require_ok_true=True,
        micro_family="checkpoint",
    ),
    TraceCase(
        "/lab/dispatch",
        "POST",
        "lab dispatch",
        (200,),
        _lab_dispatch,
        require_ok_true=True,
        micro_family="lab",
    ),
    TraceCase(
        "/lab/batch",
        "POST",
        "lab batch",
        (200,),
        _lab_batch,
        require_ok_true=True,
        micro_family="lab",
    ),
    TraceCase(
        "/lab/results/get",
        "POST",
        "lab missing result",
        (404,),
        _lab_results_missing,
        require_json_object=True,
        micro_family="lab",
    ),
    TraceCase(
        "/research/arxiv/search",
        "POST",
        "research validation search",
        (400,),
        _research_search,
        require_json_object=True,
        micro_family="research",
    ),
    TraceCase(
        "/research/arxiv/paper",
        "POST",
        "research validation paper",
        (400,),
        _research_paper,
        require_json_object=True,
        micro_family="research",
    ),
    TraceCase(
        "/research/hunt",
        "POST",
        "research validation hunt",
        (400,),
        _research_hunt,
        require_json_object=True,
        micro_family="research",
    ),
)


def _cases() -> list[TraceCase]:
    return list(TRACE_CASES)


def _route_map(app: object) -> dict[str, JsonObject]:
    routes: dict[str, JsonObject] = {}
    for index, rule in enumerate(sorted(app.url_map.iter_rules(), key=lambda item: str(item.rule))):
        methods = sorted(method for method in rule.methods if method not in {"HEAD", "OPTIONS"})
        key = str(rule.rule)
        routes[key] = {
            "index": index,
            "rule": key,
            "endpoint": rule.endpoint,
            "methods": methods,
            "arguments": sorted(rule.arguments),
        }
    return routes


def _path(case: TraceCase, ctx: TraceContext) -> str:
    if case.path_factory is not None:
        return case.path_factory(ctx)
    return case.rule


def _payload(case: TraceCase, ctx: TraceContext) -> JsonObject | None:
    return case.payload_factory(ctx)


def _response_json(response: object) -> object:
    return response.get_json(silent=True)


def _result(
    invocation: TraceInvocation, status: int, body: object, content_type: str
) -> TraceResult:
    case = invocation.case
    route = invocation.route
    json_object = isinstance(body, dict)
    ok_field = body.get("ok") if json_object else None
    error_code = body.get("error_code") if json_object else None
    pass_status = status in case.expected_statuses and status < 500
    pass_json = True if not case.require_json_object else json_object
    pass_ok = True if not case.require_ok_true else ok_field is True
    return TraceResult(
        rule=case.rule,
        endpoint=str(route.get("endpoint", "")),
        method=case.method,
        label=case.label,
        nano_probe=case.nano_probe,
        micro_family=case.micro_family,
        meso_route_index=int(route.get("index", -1)),
        macro_claim_effect=case.macro_claim_effect,
        status=status,
        expected_statuses=list(case.expected_statuses),
        pass_=bool(pass_status and pass_json and pass_ok),
        ok_field=ok_field,
        error_code=str(error_code) if error_code is not None else None,
        content_type=content_type,
        json_object=json_object,
        body_sample=body if json_object else str(body)[:1000],
    )


def _exception_result(invocation: TraceInvocation, exc: BaseException) -> TraceResult:
    case = invocation.case
    route = invocation.route
    return TraceResult(
        rule=case.rule,
        endpoint=str(route.get("endpoint", "")),
        method=case.method,
        label=case.label,
        nano_probe=case.nano_probe,
        micro_family=case.micro_family,
        meso_route_index=int(route.get("index", -1)),
        macro_claim_effect=case.macro_claim_effect,
        expected_statuses=list(case.expected_statuses),
        pass_=False,
        exception=f"{type(exc).__name__}: {exc}",
        traceback=traceback.format_exc()[-4000:],
    )


def _run_case(client: object, headers: dict[str, str], invocation: TraceInvocation) -> TraceResult:
    case = invocation.case
    ctx = invocation.ctx
    try:
        if case.method == "GET":
            response = client.get(_path(case, ctx), headers=headers)
        else:
            response = client.post(_path(case, ctx), json=_payload(case, ctx), headers=headers)
        return _result(
            invocation, response.status_code, _response_json(response), response.content_type
        )
    except (RuntimeError, ValueError, TypeError, OSError, AssertionError, AttributeError) as exc:
        return _exception_result(invocation, exc)


def _coverage(routes: dict[str, JsonObject], cases: Iterable[TraceCase]) -> RouteCoverage:
    covered = {case.rule for case in cases}
    missing = sorted(set(routes) - covered)
    return {
        "route_count": len(routes),
        "covered_route_count": len(covered & set(routes)),
        "missing_routes": missing,
    }


def _run_trace_cases() -> tuple[RouteCoverage, list[TraceResult], bool]:
    from app_factory import create_app

    app = create_app()
    app.testing = True
    client = app.test_client()
    headers = {"X-GitHome-Key": TRACE_KEY}
    ctx = _prepare_context()
    routes = _route_map(app)
    cases = _cases()
    coverage = _coverage(routes, cases)
    results = [
        _run_case(client, headers, TraceInvocation(case, routes.get(case.rule, {}), ctx))
        for case in cases
    ]
    return coverage, results, True


def _boot_failure_report(exc: BaseException) -> tuple[RouteCoverage, list[TraceResult], bool]:
    coverage = {"route_count": 0, "covered_route_count": 0, "missing_routes": ["<app_boot>"]}
    results = [
        TraceResult(
            rule="<app_boot>",
            endpoint="<app_boot>",
            method="BOOT",
            label="app boot",
            nano_probe="app_boot",
            micro_family="boot",
            meso_route_index=-1,
            macro_claim_effect="blocks_runtime_working",
            expected_statuses=[200],
            pass_=False,
            exception=f"{type(exc).__name__}: {exc}",
            traceback=traceback.format_exc()[-4000:],
        )
    ]
    return coverage, results, False


def _family_counts(results: list[TraceResult]) -> dict[str, int]:
    families: dict[str, int] = {}
    for result in results:
        family = str(result.get("micro_family", "unknown"))
        families[family] = families.get(family, 0) + 1
    return families


def _trace_report_payload(
    coverage: RouteCoverage, results: list[TraceResult], dummy_bridge_started: bool
) -> JsonObject:
    failures = [result for result in results if not result.get("pass_")]
    unexpected_500 = [result for result in results if int(result.get("status", 0) or 0) >= 500]
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "approach": "PROBE_DERIVE_VERIFY_EMBODY_RECURSE",
        "levels": {
            "nano": "route case",
            "micro": "route family",
            "meso": "route map",
            "macro": "claim gate",
        },
        "clean": not failures and not coverage["missing_routes"],
        "dummy_bridge_started": dummy_bridge_started,
        "coverage": coverage,
        "case_count": len(results),
        "family_counts": _family_counts(results),
        "failure_count": len(failures),
        "unexpected_500_count": len(unexpected_500),
        "failures": failures,
        "unexpected_500": unexpected_500,
        "results": results,
    }


def _report() -> JsonObject:
    _configure_gate_environment()
    if str(BASELINE_ROOT) not in sys.path:
        sys.path.insert(0, str(BASELINE_ROOT))
    server = _start_dummy_bridge()
    try:
        try:
            coverage, results, _trace_started = _run_trace_cases()
        except (ImportError, RuntimeError, ValueError, OSError, TypeError) as exc:
            coverage, results, _trace_started = _boot_failure_report(exc)
        return _trace_report_payload(coverage, results, server is not None)
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()


def main() -> None:
    report = _report()
    write_json_boundary(REPORT_PATH, report)
    sys.stdout.write(
        render_json_boundary({"report": str(REPORT_PATH), "clean": report["clean"]}) + "\n"
    )
    if not report["clean"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
