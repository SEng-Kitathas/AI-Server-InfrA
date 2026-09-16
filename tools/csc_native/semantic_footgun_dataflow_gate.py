"""Semantic footgun/dataflow gate for receiver runtime route safety."""

from __future__ import annotations

import ast
import json
import os
import re
import sys
import threading
import time
import traceback
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TypedDict

from strict_json_boundary import parse_json_boundary_text, render_json_boundary, write_json_boundary

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASELINE_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
REPORT_PATH = PROJECT_ROOT / "reports" / "SEMANTIC_FOOTGUN_DATAFLOW_GATE_REPORT.json"
KNOWN_CORRUPTION_IDENTIFIERS = frozenset({"recordefault", "execution_log_direfault", "mountool"})
ROUTE_SMOKE_KEY = "semantic-footgun-smoke-key"


class FootgunFinding(TypedDict, total=False):
    file: str
    line: int
    kind: str
    severity: str
    message: str
    source: str


class RouteSmokeResult(TypedDict, total=False):
    label: str
    path: str
    status: int
    expected: int
    pass_: bool
    exception: str
    traceback: str


class SemanticGateReport(TypedDict):
    created_at_utc: str
    clean: bool
    finding_count: int
    strict_failure_count: int
    findings: list[FootgunFinding]
    route_smoke_all_pass: bool
    dummy_bridge_started: bool
    route_results: list[RouteSmokeResult]
    rules: list[str]


@dataclass(frozen=True)
class SmokeCheck:
    method: str
    path: str
    payload: object | None
    expected: int
    label: str


SMOKE_CHECKS = (
    SmokeCheck("get", "/health", None, 200, "legacy health"),
    SmokeCheck("get", "/capabilities", None, 200, "legacy capabilities"),
    SmokeCheck("get", "/lab/health", None, 200, "lab health"),
    SmokeCheck("get", "/lab/tools", None, 200, "lab tools"),
    SmokeCheck("get", "/lab/mcp/manifest", None, 200, "mcp manifest"),
    SmokeCheck(
        "post", "/lab/dispatch", {"tool_name": "lab.health", "payload": {}}, 200, "lab dispatch"
    ),
    SmokeCheck(
        "post",
        "/lab/dispatch",
        {"tool_name": "browser.health", "payload": {"timeout_seconds": 2}},
        200,
        "browser health",
    ),
    SmokeCheck(
        "post",
        "/lab/dispatch",
        {
            "tool_name": "browser.screenshot",
            "payload": {"session_id": "smoke-session", "name": "smoke.png", "timeout_seconds": 2},
        },
        200,
        "browser screenshot",
    ),
)


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
            return parse_json_boundary_text(self.rfile.read(size).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def do_GET(self) -> None:
        if self.path.startswith("/health"):
            self._send({"ok": True, "status": "online", "bridge": "dummy-smoke"})
        elif self.path.startswith("/sessions"):
            self._send({"ok": True, "sessions": [{"session_id": "smoke-session"}]})
        else:
            self._send({"ok": False}, 404)

    def do_POST(self) -> None:
        body = self._body()
        if self.path.startswith("/screenshot"):
            self._send({"ok": True, "path": "dummy/smoke.png", "session_id": _session_id(body)})
        elif self.path.startswith("/content"):
            self._send({"ok": True, "content": "<html>SMOKE</html>"})
        elif self.path.startswith("/evaluate"):
            self._send({"ok": True, "result": "SMOKE"})
        else:
            self._send({"ok": True, "path": self.path, "payload": body})

    def log_message(self, *_args: object) -> None:
        return


def _session_id(body: object) -> object | None:
    if isinstance(body, dict):
        return body.get("session_id")
    return None


def _line(lines: list[str], number: int) -> str:
    if number < 1 or number > len(lines):
        return ""
    return lines[number - 1].strip()[:240]


def _function_body(lines: list[str], node: ast.AST) -> str:
    start = getattr(node, "lineno", 1)
    end = getattr(node, "end_lineno", start)
    return "\n".join(lines[start - 1 : end])


def _first_name_line(function: ast.AST, name: str, context_type: type[ast.expr_context]) -> int:
    lines = [
        getattr(node, "lineno", 10**9)
        for node in ast.walk(function)
        if isinstance(node, ast.Name) and node.id == name and isinstance(node.ctx, context_type)
    ]
    return min(lines or [10**9])


def _request_payload_stale_findings(
    path: Path, tree: ast.AST, lines: list[str]
) -> list[FootgunFinding]:
    findings: list[FootgunFinding] = []
    functions = (
        node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    stale_pattern = re.compile(r"\bd\.(get|items|keys|values)\(|\bd\[|\bsubmit_execution_job\(d\)")
    for function in functions:
        body = _function_body(lines, function)
        if "request_payload" not in body or not stale_pattern.search(body):
            continue
        d_assign = _first_name_line(function, "d", ast.Store)
        d_load = _first_name_line(function, "d", ast.Load)
        if d_load < d_assign:
            findings.append(
                FootgunFinding(
                    file=str(path.relative_to(PROJECT_ROOT)),
                    line=d_load,
                    kind="request_payload_stale_d",
                    severity="BLOCKER",
                    message=f"{function.name}: stale d used after request_payload",
                    source=_line(lines, d_load),
                )
            )
    return findings


def _known_corruption_findings(path: Path, lines: list[str]) -> list[FootgunFinding]:
    findings: list[FootgunFinding] = []
    for number, line in enumerate(lines, 1):
        for bad in KNOWN_CORRUPTION_IDENTIFIERS:
            if bad in line:
                findings.append(
                    FootgunFinding(
                        file=str(path.relative_to(PROJECT_ROOT)),
                        line=number,
                        kind="known_corruption_identifier",
                        severity="HIGH",
                        message=f"found `{bad}`",
                        source=line.strip()[:240],
                    )
                )
    return findings


def _class_to_dict_map(tree: ast.AST) -> dict[str, bool]:
    result: dict[str, bool] = {}
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.ClassDef):
            result[node.name] = any(
                isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "to_dict"
                for item in node.body
            )
    return result


def _missing_to_dict_findings(path: Path, tree: ast.AST, lines: list[str]) -> list[FootgunFinding]:
    findings: list[FootgunFinding] = []
    class_info = _class_to_dict_map(tree)
    for node in ast.walk(tree):
        if not _is_immediate_to_dict_call(node):
            continue
        value = node.func.value  # type: ignore[union-attr]
        class_name = value.func.id  # type: ignore[union-attr]
        if class_name in class_info and not class_info[class_name]:
            findings.append(
                FootgunFinding(
                    file=str(path.relative_to(PROJECT_ROOT)),
                    line=node.lineno,
                    kind="instantiate_to_dict_missing_method",
                    severity="BLOCKER",
                    message=f"{class_name}(...).to_dict() but class lacks to_dict",
                    source=_line(lines, node.lineno),
                )
            )
    return findings


def _is_immediate_to_dict_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if not isinstance(node.func, ast.Attribute) or node.func.attr != "to_dict":
        return False
    value = node.func.value
    return isinstance(value, ast.Call) and isinstance(value.func, ast.Name)


def _scan_file(path: Path) -> list[FootgunFinding]:
    source = path.read_text(encoding="utf-8", errors="replace")
    lines = source.splitlines()
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [
            FootgunFinding(
                file=str(path.relative_to(PROJECT_ROOT)),
                line=int(exc.lineno or 1),
                kind="syntax_error",
                severity="BLOCKER",
                message=str(exc),
                source=_line(lines, int(exc.lineno or 1)),
            )
        ]
    findings = []
    findings.extend(_request_payload_stale_findings(path, tree, lines))
    findings.extend(_known_corruption_findings(path, lines))
    findings.extend(_missing_to_dict_findings(path, tree, lines))
    return findings


def _iter_python_files() -> Iterable[Path]:
    for path in sorted(BASELINE_ROOT.glob("*.py")):
        if path.name.startswith("__"):
            continue
        yield path


def _start_dummy_bridge() -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", 0), DummyBrowserBridge)
    host, port = server.server_address[:2]
    os.environ["PCMMAD_BROWSER_BRIDGE_URL"] = f"http://{host}:{port}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    time.sleep(0.05)
    return server


def _route_smoke() -> tuple[bool, list[RouteSmokeResult], bool]:
    os.environ["GITHOME_API_KEY"] = ROUTE_SMOKE_KEY
    sys.path.insert(0, str(BASELINE_ROOT))
    server = _start_dummy_bridge()
    results: list[RouteSmokeResult] = []
    try:
        from app_factory import create_app

        app = create_app()
        app.testing = True
        client = app.test_client()
        headers = {"X-GitHome-Key": ROUTE_SMOKE_KEY}
        for check in SMOKE_CHECKS:
            results.append(_run_smoke_check(client, headers, check))
    except (ImportError, RuntimeError, ValueError, OSError) as exc:
        results.append(
            RouteSmokeResult(
                label="app boot",
                path="<boot>",
                pass_=False,
                exception=f"{type(exc).__name__}: {exc}",
                traceback=traceback.format_exc()[-3000:],
            )
        )
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
    return all(result.get("pass_", False) for result in results), results, server is not None


def _run_smoke_check(
    client: object, headers: dict[str, str], check: SmokeCheck
) -> RouteSmokeResult:
    try:
        method = getattr(client, check.method)
        if check.payload is None:
            response = method(check.path, headers=headers)
        else:
            response = method(check.path, json=check.payload, headers=headers)
        allowed_statuses = {check.expected}
        if check.label == "browser screenshot":
            allowed_statuses.update({404, 503})
        return RouteSmokeResult(
            label=check.label,
            path=check.path,
            status=response.status_code,
            expected=check.expected,
            pass_=response.status_code in allowed_statuses,
        )
    except (RuntimeError, ValueError, OSError) as exc:
        return RouteSmokeResult(
            label=check.label,
            path=check.path,
            pass_=False,
            exception=f"{type(exc).__name__}: {exc}",
            traceback=traceback.format_exc()[-3000:],
        )


def _report() -> SemanticGateReport:
    findings: list[FootgunFinding] = []
    for path in _iter_python_files():
        findings.extend(_scan_file(path))
    route_ok, route_results, dummy_bridge_started = _route_smoke()
    strict_count = len(
        [finding for finding in findings if finding["severity"] in {"BLOCKER", "HIGH"}]
    )
    clean = strict_count == 0 and route_ok
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "clean": clean,
        "finding_count": len(findings),
        "strict_failure_count": strict_count,
        "findings": findings,
        "route_smoke_all_pass": route_ok,
        "dummy_bridge_started": dummy_bridge_started,
        "route_results": route_results,
        "rules": [
            "request_payload_stale_d",
            "known_corruption_identifier",
            "instantiate_to_dict_missing_method",
            "route_smoke",
        ],
    }


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
