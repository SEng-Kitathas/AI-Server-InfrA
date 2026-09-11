"""Lab HTTP routes for health, tool catalog, dispatch, batch dispatch, and result handles."""

from __future__ import annotations
from typing import Any

from collections.abc import MutableMapping
from pathlib import Path
import hashlib
import json
import os
import re
import atexit
import subprocess
import sys
from dataclasses import dataclass
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

from flask import Blueprint, current_app, jsonify, request

from .execution_routes import execution_readiness
from .runtime_config import LAB_BATCH_CONFIG
from .lab_results import (
    RESULT_INLINE_SAFE_BYTES,
    RESULT_PREVIEW_MAX_CHARS,
    RESULT_RANGE_MAX_BYTES,
    get_result,
    read_result_range,
    result_metadata,
    result_path,
    store_result,
    summarize_payload,
)
from .server_hardening import safe_json_dumps
from .lab_schema_validation import validate_schema_value
from .schema_vnext_runtime import (
    compose as schema_vnext_compose,
    execute as schema_vnext_execute,
    invoke as schema_vnext_invoke,
    observe as schema_vnext_observe,
    orient as schema_vnext_orient,
    resume as schema_vnext_resume,
    transfer as schema_vnext_transfer,
)
from .lab_tools import (
    LabToolError,
    dispatch_tool,
    list_tools,
    server_native_router_descriptor,
    tool_catalog_response,
    tool_lab_health,
)

JsonRecord = MutableMapping[str, Any]
from .shared_core import PROJECTS_ROOT, ensure_parent, mount_summary, require_valid_api_key, utc_now
from .control_plane_models import BatchExecutorTelemetry, BackgroundResultEnvelope

lab_bp = Blueprint("lab", __name__, url_prefix="/lab")


_BATCH_EXECUTOR_LOCK = threading.RLock()
_BATCH_EXECUTOR: ThreadPoolExecutor | None = None
_BACKGROUND_BATCHES_SUBMITTED = 0


_BATCH_EXECUTOR_STATS_LOCK = threading.RLock()
_BATCH_EXECUTOR_TELEMETRY = BatchExecutorTelemetry()

BATCH_DATAFLOW_MAX_STEPS = 30
BATCH_DATAFLOW_MAX_RESOLVED_PAYLOAD_BYTES = 65_536
BATCH_STEP_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$")

_RUNTIME_IDENTITY_CACHE: JsonRecord | None = None
_RUNTIME_PROJECT_CATALOG_LIMIT = 128


def _runtime_git_text(*args: str) -> str | None:
    repo_root = Path(__file__).resolve().parents[2]
    try:
        cp = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    value = (cp.stdout or "").strip()
    return value if cp.returncode == 0 and value else None


def _runtime_identity() -> JsonRecord:
    global _RUNTIME_IDENTITY_CACHE
    if _RUNTIME_IDENTITY_CACHE is None:
        repo_root = Path(__file__).resolve().parents[2]
        head = _runtime_git_text("rev-parse", "HEAD")
        tree = _runtime_git_text("rev-parse", "HEAD^{tree}")
        branch = _runtime_git_text("symbolic-ref", "--quiet", "--short", "HEAD")
        _RUNTIME_IDENTITY_CACHE = {
            "product": "PCMMAD Laboratory Runtime",
            "generation": "V30",
            "release_state": "engineering_current",
            "source_head": head,
            "source_tree": tree,
            "source_branch": branch,
            "source_root": str(repo_root),
            "schema_primary": "v11.0 capability microkernel",
            "schema_compatibility": "v10.3 compact 30-operation surface",
            "identity_law": "RUNTIME_ENGINEERING_IDENTITY != HISTORICAL_PACKAGE_LINEAGE",
        }
    return dict(_RUNTIME_IDENTITY_CACHE)


def _project_catalog() -> JsonRecord:
    rows: list[str] = []
    partial = False
    error: str | None = None
    try:
        if PROJECTS_ROOT.is_dir():
            for child in sorted(PROJECTS_ROOT.iterdir(), key=lambda item: item.name.casefold()):
                if not child.is_dir() or child.name.startswith("."):
                    continue
                if len(rows) >= _RUNTIME_PROJECT_CATALOG_LIMIT:
                    partial = True
                    break
                rows.append(child.name)
    except OSError as exc:
        error = f"{type(exc).__name__}: {exc}"
    return {
        "root": str(PROJECTS_ROOT),
        "projects": rows,
        "count": len(rows),
        "partial": partial,
        "error": error,
    }


def _batch_stat_inc(name: str, amount: int = 1) -> None:
    with _BATCH_EXECUTOR_STATS_LOCK:
        _BATCH_EXECUTOR_TELEMETRY.inc(name, amount)


def _batch_stat_set(name: str, value: object) -> None:
    with _BATCH_EXECUTOR_STATS_LOCK:
        _BATCH_EXECUTOR_TELEMETRY.set(name, value)


def _background_active_dec() -> None:
    with _BATCH_EXECUTOR_STATS_LOCK:
        active = max(0, int(_BATCH_EXECUTOR_TELEMETRY.background_batches_active) - 1)
        _BATCH_EXECUTOR_TELEMETRY.set("background_batches_active", active)


def _batch_stat_snapshot() -> JsonRecord:
    with _BATCH_EXECUTOR_STATS_LOCK:
        return _BATCH_EXECUTOR_TELEMETRY.to_dict()


def _background_worker_target() -> int:
    workers = LAB_BATCH_CONFIG.background_workers
    if workers is None:
        return min(128, max(16, (os.cpu_count() or 8) * 8))
    return max(1, workers)


def _ensure_batch_executor() -> ThreadPoolExecutor:
    global _BATCH_EXECUTOR
    with _BATCH_EXECUTOR_LOCK:
        if _BATCH_EXECUTOR is None:
            _BATCH_EXECUTOR = ThreadPoolExecutor(
                max_workers=_background_worker_target(), thread_name_prefix="pcmmad-lab-bg"
            )
        return _BATCH_EXECUTOR


def _shutdown_batch_executor() -> None:
    global _BATCH_EXECUTOR
    with _BATCH_EXECUTOR_LOCK:
        executor = _BATCH_EXECUTOR
        _BATCH_EXECUTOR = None
    if executor is not None:
        executor.shutdown(wait=False, cancel_futures=False)


atexit.register(_shutdown_batch_executor)


MOUNT_PROBE_TIMEOUT_SECONDS = 1.5


_MOUNT_PROBE_SCRIPT = r"""
import json
import os
from pathlib import Path
import sys

raw = sys.argv[1]
path = Path(raw)
exists = False
writable = False
error = None
try:
    exists = path.exists()
    if exists and path.is_dir():
        writable = os.access(raw, os.W_OK)
except (OSError, ValueError, TypeError) as exc:
    error = f"{type(exc).__name__}: {exc}"
print(json.dumps({"exists": bool(exists), "writable": bool(writable), "error": error}))
"""


def _probe_one_mount(mount: JsonRecord) -> JsonRecord:
    name = str(mount.get("name") or "")
    raw_path = str(mount.get("path") or "")
    base: JsonRecord = {
        "name": name,
        "path": raw_path,
        "exists": False,
        "writable": False,
        "error": None,
    }
    try:
        completed = subprocess.run(
            [sys.executable, "-c", _MOUNT_PROBE_SCRIPT, raw_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=MOUNT_PROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        base["error"] = (
            f"TimeoutError: mount probe exceeded {MOUNT_PROBE_TIMEOUT_SECONDS:.1f}s"
        )
        return base
    except (OSError, ValueError, TypeError) as exc:
        base["error"] = f"{type(exc).__name__}: {exc}"
        return base
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "mount probe failed").strip()
        base["error"] = f"ProbeProcessError: {detail[:500]}"
        return base
    try:
        payload = json.loads((completed.stdout or "").strip())
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        base["error"] = f"ProbeDecodeError: {exc}"
        return base
    if not isinstance(payload, dict):
        base["error"] = "ProbeDecodeError: mount probe payload was not an object"
        return base
    base["exists"] = bool(payload.get("exists"))
    base["writable"] = bool(payload.get("writable"))
    error = payload.get("error")
    base["error"] = str(error) if error else None
    return base


def _probe_mounts() -> list[JsonRecord]:
    mounts = [dict(mount) for mount in mount_summary()]
    if not mounts:
        return []
    # Filesystem calls against dead/removable/network mounts can block for tens of
    # seconds at the OS layer. Probe each mount in an independently killable child
    # process and run those probes concurrently so aggregate health stays bounded.
    workers = min(8, len(mounts))
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="pcmmad-mount-probe") as pool:
        return list(pool.map(_probe_one_mount, mounts))


def _merge_lab_status(
    boot_degraded: bool,
    lab_status: JsonRecord,
    execution_status: JsonRecord,
    mounts: list[JsonRecord],
) -> str:
    if boot_degraded:
        return "degraded"
    if lab_status.get("status") != "online":
        return "degraded"
    if execution_status.get("status") != "online":
        return "degraded"
    if any(
        (not bool(mount.get("exists"))) or (not bool(mount.get("writable"))) for mount in mounts
    ):
        return "degraded"
    return "online"


@dataclass(frozen=True)
class BackgroundBatchRunSpec:
    project_id: str
    handle: str
    submitted_at: str
    steps: list[dict]
    stop_on_error: bool
    parallelism: int


@dataclass(frozen=True)
class BackgroundWriteSpec:
    project_id: str
    handle: str
    payload: JsonRecord
    label: str = "lab_batch"
    tool_name: str = "lab.batch"


def _write_background_result(spec: BackgroundWriteSpec) -> JsonRecord:
    body = BackgroundResultEnvelope(
        project_id=spec.project_id,
        handle=spec.handle,
        label=spec.label,
        tool_name=spec.tool_name,
        created_at=utc_now(),
        payload=spec.payload,
    )
    path = result_path(spec.project_id, spec.handle)
    ensure_parent(path)
    path.write_text(safe_json_dumps(body.to_dict()), encoding="utf-8")
    return body.to_dict()


def _parallel_map_ordered(steps: list[dict], worker: object, parallelism: int) -> list[dict]:
    executor = _ensure_batch_executor()
    effective_parallelism = max(1, min(parallelism, _background_worker_target()))
    _batch_stat_inc("foreground_parallel_dispatches")
    semaphore = threading.Semaphore(effective_parallelism)
    ordered: dict[int, dict] = {}
    futures = []

    def _guarded(idx: int, step: dict) -> dict:
        with semaphore:
            return worker(idx, step)

    for idx, step in enumerate(steps):
        futures.append((idx, executor.submit(_guarded, idx, step)))
    for idx, future in futures:
        ordered[idx] = future.result()
    return [ordered[i] for i in sorted(ordered)]


def _batch_ref_paths(value: object) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, dict):
        if set(value) == {"$ref"} and isinstance(value.get("$ref"), str):
            refs.add(str(value["$ref"]).strip())
        else:
            for child in value.values():
                refs.update(_batch_ref_paths(child))
    elif isinstance(value, list):
        for child in value:
            refs.update(_batch_ref_paths(child))
    return refs


def _batch_lookup_ref(ref: str, prior: dict[str, dict]) -> object:
    parts = [part for part in str(ref).split(".") if part]
    if len(parts) < 2:
        raise LabToolError("BATCH_REF_INVALID", f"dataflow reference must include step id and field path: {ref!r}", 400)
    step_id = parts[0]
    if step_id not in prior:
        raise LabToolError("BATCH_REF_UNRESOLVED", f"dataflow reference is not a completed prior step: {ref}", 409)
    value: object = prior[step_id]
    for part in parts[1:]:
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            raise LabToolError("BATCH_REF_UNRESOLVED", f"dataflow reference field cannot be resolved: {ref}", 409)
    return value


def _batch_resolve_refs(value: object, prior: dict[str, dict]) -> object:
    if isinstance(value, dict):
        if set(value) == {"$ref"}:
            return _batch_lookup_ref(str(value["$ref"]), prior)
        return {str(key): _batch_resolve_refs(child, prior) for key, child in value.items()}
    if isinstance(value, list):
        return [_batch_resolve_refs(child, prior) for child in value]
    return value


def _batch_contains_dataflow(steps: list[dict]) -> bool:
    return any(
        bool(_batch_ref_paths(step.get("payload") or {}))
        for step in steps
        if isinstance(step, dict)
    )


def _validate_batch_dataflow_shape(steps: list[dict], parallelism: int) -> None:
    if len(steps) > BATCH_DATAFLOW_MAX_STEPS:
        raise LabToolError("BATCH_LIMIT_EXCEEDED", f"batch exceeds maximum {BATCH_DATAFLOW_MAX_STEPS} steps", 400)
    seen: set[str] = set()
    has_refs = False
    for idx, raw in enumerate(steps):
        step = _validate_batch_step(idx, raw)
        step_id = str(step.get("id") or "").strip()
        if step_id:
            if step_id in seen:
                raise LabToolError("BAD_REQUEST", f"step {idx} id is duplicate: {step_id!r}", 400)
        refs = _batch_ref_paths(step.get("payload") or {})
        if refs:
            has_refs = True
            if not step_id:
                raise LabToolError("BATCH_REF_INVALID", f"dataflow step {idx} must have an id", 400)
            for ref in refs:
                source_id = ref.split(".", 1)[0]
                if source_id not in seen:
                    raise LabToolError(
                        "BATCH_REF_FORWARD_OR_UNKNOWN",
                        f"step {step_id or idx} references non-prior step {source_id}",
                        400,
                    )
        if step_id:
            seen.add(step_id)
    if has_refs and parallelism != 1:
        raise LabToolError(
            "BATCH_DATAFLOW_REQUIRES_SEQUENTIAL",
            "dataflow batches remain sequential until the closed scheduler-effect profile is qualified",
            409,
        )


def _batch_step_result(idx: int, step: dict, prior: dict[str, dict] | None = None) -> dict:
    tool_name = str(step.get("tool_name", "")).strip()
    payload = step.get("payload") or {}
    if prior is not None:
        payload = _batch_resolve_refs(payload, prior)
        resolved_bytes = len(safe_json_dumps(payload).encode("utf-8"))
        if resolved_bytes > BATCH_DATAFLOW_MAX_RESOLVED_PAYLOAD_BYTES:
            raise LabToolError(
                "BATCH_DATAFLOW_PAYLOAD_TOO_LARGE",
                f"resolved step payload exceeds {BATCH_DATAFLOW_MAX_RESOLVED_PAYLOAD_BYTES} bytes; pass a result handle instead",
                413,
                resolved_bytes=resolved_bytes,
            )
    authority = step.get("authority") or {}
    expected_contract_digest = step.get("expected_contract_digest")
    identity = {"id": str(step.get("id"))} if step.get("id") else {}
    try:
        return {
            "index": idx,
            **identity,
            **dispatch_tool(
                tool_name,
                payload,
                authority=authority,
                expected_contract_digest=expected_contract_digest,
            ),
        }
    except LabToolError as exc:
        return {
            "index": idx,
            **identity,
            "ok": False,
            "tool": tool_name,
            "error_code": exc.error_code,
            "message": exc.message,
            "status": exc.status,
            **exc.extra,
        }


def _validate_batch_step(idx: int, step: object) -> dict:
    if not isinstance(step, dict):
        raise LabToolError("BAD_REQUEST", f"step {idx} must be an object", 400)
    if not str(step.get("tool_name", "")).strip():
        raise LabToolError("BAD_REQUEST", f"step {idx} missing tool_name", 400)
    if "authority" in step and not isinstance(step.get("authority"), dict):
        raise LabToolError("BAD_REQUEST", f"step {idx} authority must be an object", 400)
    step_id = str(step.get("id") or "").strip()
    if step_id and not BATCH_STEP_ID_RE.fullmatch(step_id):
        raise LabToolError("BAD_REQUEST", f"step {idx} id is invalid: {step_id!r}", 400)
    if _batch_ref_paths(step.get("authority") or {}):
        raise LabToolError("BATCH_AUTHORITY_REF_FORBIDDEN", "dataflow references are forbidden in authority envelopes", 400)
    return step


def _batch_response_payload(results: list[dict], parallelism: int) -> dict:
    return {
        "ok": True,
        "count": len(results),
        "results": results,
        "parallelism": parallelism,
        "background": False,
        "atomic": False,
    }


def _bounded_foreground_batch_response(request_payload: dict, response: JsonRecord) -> JsonRecord:
    project_id = str(request_payload.get("project_id", "")).strip()
    if not project_id:
        return response
    raw = safe_json_dumps(response)
    requested = int(request_payload.get("result_handle_threshold_chars", 12000))
    # A caller may lower the threshold, but cannot raise it beyond the server's
    # constrained-client safety ceiling.
    threshold = max(1000, min(requested, 12000))
    force = bool(request_payload.get("store_result", False))
    if not force and len(raw) <= threshold:
        return response
    meta = store_result(
        project_id,
        response,
        label=str(request_payload.get("result_label", "lab_batch")),
        tool_name="lab.batch",
    )
    return {
        "ok": True,
        "count": int(response.get("count", 0)),
        "parallelism": int(response.get("parallelism", 1)),
        "background": False,
        "atomic": False,
        "stored": True,
        "handle": meta["handle"],
        "bytes": meta["bytes"],
        "sha256": meta["sha256"],
        "summary": summarize_payload(response),
    }


def _batch_request_payload() -> dict:
    request_payload = request.get_json(silent=False, force=True)
    if not isinstance(request_payload, dict):
        raise LabToolError("BAD_JSON", "JSON body must be an object", 400)
    return request_payload


def _execute_batch_steps(steps: list[dict], stop_on_error: bool, parallelism: int) -> list[dict]:
    _validate_batch_dataflow_shape(steps, parallelism)
    if parallelism > 1 and not stop_on_error:
        return _parallel_map_ordered(steps, _batch_step_result, parallelism)
    results: list[dict] = []
    prior: dict[str, dict] = {}
    for idx, raw_step in enumerate(steps):
        step = _validate_batch_step(idx, raw_step)
        result = _batch_step_result(idx, step, prior)
        results.append(result)
        step_id = str(step.get("id") or "").strip()
        if step_id:
            prior[step_id] = result
        if stop_on_error and not result.get("ok", False):
            break
    return results


def _error(error_code: str, message: str, status: int, **extra: object) -> object:
    payload = {"ok": False, "error_code": error_code, "message": message, "time": utc_now()}
    payload.update(extra)
    return jsonify(payload), status


def _auth() -> object | None:
    try:
        require_valid_api_key(request.headers)
        return None
    except PermissionError as e:
        return _error("UNAUTHORIZED", str(e), 401)


@lab_bp.get("/health")
def lab_health() -> object:
    ae = _auth()
    if ae:
        return ae
    boot_report = current_app.config.get("PCMMAD_BOOT_REPORT", {})
    boot_degraded = bool(current_app.config.get("PCMMAD_BOOT_DEGRADED", False))
    lab_status = tool_lab_health()
    execution_status = execution_readiness()
    mounts = _probe_mounts()
    return jsonify(
        {
            "ok": True,
            "status": _merge_lab_status(boot_degraded, lab_status, execution_status, mounts),
            "router": True,
            "tool_count": len(list_tools()),
            "runtime_identity": _runtime_identity(),
            "project_catalog": _project_catalog(),
            "boot_report": boot_report,
            "lab_status": lab_status,
            "execution_readiness": execution_status,
            "mount_readiness": mounts,
            "background_batch_executor": {
                "configured_workers": _background_worker_target(),
                "alive": bool(_BATCH_EXECUTOR is not None),
                "submitted_batches": _BACKGROUND_BATCHES_SUBMITTED,
                "telemetry": _batch_stat_snapshot(),
            },
            "time": utc_now(),
            "server_native_router": server_native_router_descriptor().to_dict(),
        }
    )


@lab_bp.get("/tools")
def lab_tools_index() -> object:
    ae = _auth()
    if ae:
        return ae
    return jsonify(tool_catalog_response(operation_budget=30, action_count=30).to_dict())


@lab_bp.get("/mounts")
def lab_mounts() -> object:
    ae = _auth()
    if ae:
        return ae
    return jsonify({"ok": True, "mounts": mount_summary(), "time": utc_now()})


def _mcp_manifest_tool_card(tool: JsonRecord) -> JsonRecord:
    return {
        "name": tool.get("name"),
        "description": tool.get("description"),
        "category": tool.get("category"),
        "tags": tool.get("tags", []),
        "danger_tier": tool.get("danger_tier"),
        "approval_required": tool.get("approval_required"),
        "effective_approval_required": tool.get("effective_approval_required"),
        "mutating": tool.get("mutating"),
        "side_effect_class": tool.get("side_effect_class"),
        "effect_traits": tool.get("effect_traits", []),
        "capability_version": tool.get("capability_version"),
        "schema_version": tool.get("schema_version"),
        "schema_hash": tool.get("schema_hash"),
        "contract_digest": tool.get("contract_digest"),
        "availability": tool.get("availability", {}),
        "input_schema": tool.get("input_schema", {"type": "object"}),
        "output_schema": tool.get("output_schema", {"type": "object"}),
    }


def _manifest_digest(cards: list[JsonRecord]) -> str:
    canonical = [
        {
            "name": card.get("name"),
            "contract_digest": card.get("contract_digest"),
        }
        for card in cards
    ]
    raw = safe_json_dumps(canonical).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@lab_bp.get("/mcp/manifest")
def lab_mcp_manifest() -> object:
    ae = _auth()
    if ae:
        return ae
    cards = [_mcp_manifest_tool_card(tool) for tool in list_tools()]
    return jsonify(
        {
            "ok": True,
            "server_name": "pcmmad_lab",
            "protocol": "mcp-ready-shared-registry",
            "tool_count": len(cards),
            "manifest_digest": _manifest_digest(cards),
            "tools": cards,
            "time": utc_now(),
        }
    )


@lab_bp.post("/results/get")
def lab_results_get() -> object:
    ae = _auth()
    if ae:
        return ae
    try:
        request_payload = request.get_json(silent=False, force=True)
        if not isinstance(request_payload, dict):
            return _error("BAD_JSON", "JSON body must be an object", 400)
        project_id = str(request_payload.get("project_id", "")).strip()
        handle = str(request_payload.get("handle", "")).strip()
        if not project_id or not handle:
            return _error("BAD_REQUEST", "project_id and handle are required", 400)

        # Historical summary_only remains a compatibility alias.
        mode = str(request_payload.get("mode", "auto")).strip().lower() or "auto"
        if bool(request_payload.get("summary_only", False)):
            mode = "preview"
        if mode not in {"auto", "full", "metadata", "preview", "range"}:
            return _error("BAD_REQUEST", "mode must be auto|full|metadata|preview|range", 400)

        meta = result_metadata(project_id, handle)
        if mode == "metadata":
            return jsonify({"ok": True, "mode": "metadata", "time": utc_now(), **meta})

        if mode == "range":
            offset = max(0, int(request_payload.get("offset_bytes", 0)))
            length = max(1, min(int(request_payload.get("length_bytes", 32768)), RESULT_RANGE_MAX_BYTES))
            return jsonify(
                {
                    "ok": True,
                    "mode": "range",
                    "time": utc_now(),
                    **read_result_range(
                        project_id, handle, offset_bytes=offset, length_bytes=length
                    ),
                }
            )

        row = get_result(project_id, handle)
        if mode == "preview" or (mode == "auto" and int(meta["bytes"]) > RESULT_INLINE_SAFE_BYTES):
            preview_chars = max(200, min(int(request_payload.get("preview_chars", 1200)), RESULT_PREVIEW_MAX_CHARS))
            return jsonify(
                {
                    "ok": True,
                    "mode": "preview",
                    "project_id": project_id,
                    "handle": handle,
                    "bytes": meta["bytes"],
                    "sha256": meta["sha256"],
                    "label": meta.get("label"),
                    "tool_name": meta.get("tool_name"),
                    "created_at": meta.get("created_at"),
                    "summary": summarize_payload(row.get("payload"), preview_chars=preview_chars),
                    "full_available": True,
                    "range_available": True,
                    "time": utc_now(),
                }
            )

        return jsonify({"ok": True, "mode": "full", "time": utc_now(), **row})
    except FileNotFoundError:
        return _error("NOT_FOUND", "result handle not found", 404)
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as e:
        return _error("RESULT_GET_FAILED", str(e), 500)


@lab_bp.post("/dispatch")
def lab_dispatch() -> object:
    ae = _auth()
    if ae:
        return ae
    try:
        request_payload = request.get_json(silent=False, force=True)
        if not isinstance(request_payload, dict):
            return _error("BAD_JSON", "JSON body must be an object", 400)
        tool_name = str(request_payload.get("tool_name", "")).strip()
        payload = request_payload.get("payload") or {}
        authority = request_payload.get("authority") or {}
        expected_contract_digest = request_payload.get("expected_contract_digest")
        if not tool_name:
            return _error("BAD_REQUEST", "tool_name is required", 400)
        if not isinstance(payload, dict):
            return _error("BAD_REQUEST", "payload must be an object", 400)
        if not isinstance(authority, dict):
            return _error("BAD_REQUEST", "authority must be an object", 400)
        result = dispatch_tool(
            tool_name,
            payload,
            authority=authority,
            expected_contract_digest=expected_contract_digest,
        )
        return jsonify(result)
    except LabToolError as e:
        return _error(e.error_code, e.message, e.status, **e.extra)
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as e:
        return _error("LAB_DISPATCH_FAILED", str(e), 500)


def _background_batch_initial_payload(
    submitted_at: str, steps: list[dict], stop_on_error: bool, parallelism: int
) -> JsonRecord:
    return {
        "status": "RUNNING",
        "submitted_at": submitted_at,
        "count": len(steps),
        "stop_on_error": stop_on_error,
        "parallelism": parallelism,
    }


def _background_batch_completed_payload(submitted_at: str, results: list[dict]) -> JsonRecord:
    return {
        "status": "COMPLETED",
        "submitted_at": submitted_at,
        "finished_at": utc_now(),
        "count": len(results),
        "results": results,
    }


def _background_batch_failed_payload(submitted_at: str, exc: Exception) -> JsonRecord:
    return {
        "status": "FAILED",
        "submitted_at": submitted_at,
        "finished_at": utc_now(),
        "error": f"{type(exc).__name__}: {exc}",
    }


def _write_batch_result(project_id: str, handle: str, payload: JsonRecord) -> JsonRecord:
    return _write_background_result(
        BackgroundWriteSpec(project_id=project_id, handle=handle, payload=payload)
    )


def _run_background_batch(spec: BackgroundBatchRunSpec) -> None:
    _batch_stat_inc("background_batches_active")
    try:
        results = _execute_batch_steps(spec.steps, spec.stop_on_error, spec.parallelism)
        _write_batch_result(
            spec.project_id,
            spec.handle,
            _background_batch_completed_payload(spec.submitted_at, results),
        )
        _batch_stat_inc("background_batches_completed")
        _batch_stat_set("last_background_error", None)
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as exc:
        _write_batch_result(
            spec.project_id, spec.handle, _background_batch_failed_payload(spec.submitted_at, exc)
        )
        _batch_stat_inc("background_batches_failed")
        _batch_stat_set("last_background_error", f"{type(exc).__name__}: {exc}")
    finally:
        _background_active_dec()


def _submit_background_batch(
    project_id: str, steps: list[dict], stop_on_error: bool, parallelism: int
) -> JsonRecord:
    global _BACKGROUND_BATCHES_SUBMITTED
    handle = f"res-{uuid.uuid4().hex[:12]}"
    submitted_at = utc_now()
    _write_batch_result(
        project_id,
        handle,
        _background_batch_initial_payload(submitted_at, steps, stop_on_error, parallelism),
    )
    _BACKGROUND_BATCHES_SUBMITTED += 1
    _ensure_batch_executor().submit(
        _run_background_batch,
        BackgroundBatchRunSpec(project_id, handle, submitted_at, steps, stop_on_error, parallelism),
    )
    return {
        "ok": True,
        "background": True,
        "project_id": project_id,
        "handle": handle,
        "status": "RUNNING",
        "submitted_at": submitted_at,
    }


@lab_bp.post("/batch")
def lab_batch() -> object:
    ae = _auth()
    if ae:
        return ae
    try:
        request_payload = _batch_request_payload()
        steps = request_payload.get("steps") or []
        stop_on_error = bool(request_payload.get("stop_on_error", True))
        background = bool(request_payload.get("background", False))
        parallelism = max(1, int(request_payload.get("parallelism", 1)))
        if not isinstance(steps, list) or not steps:
            return _error("BAD_REQUEST", "steps must be a non-empty array", 400)
        _validate_batch_dataflow_shape(steps, parallelism)
        if background:
            project_id = str(request_payload.get("project_id", "")).strip()
            if not project_id:
                return _error("BAD_REQUEST", "project_id is required when background=true", 400)
            return jsonify(_submit_background_batch(project_id, steps, stop_on_error, parallelism))
        response = _batch_response_payload(
            _execute_batch_steps(steps, stop_on_error, parallelism), parallelism
        )
        return jsonify(_bounded_foreground_batch_response(request_payload, response))
    except LabToolError as e:
        return _error(e.error_code, e.message, e.status, **e.extra)
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as e:
        return _error("LAB_BATCH_FAILED", str(e), 500)

_SCHEMA_VNEXT_OPENAPI_PATH = Path(__file__).resolve().with_name(
    "pcmmad_lab_action_schema_v11_0_capability_microkernel_8.json"
)
_SCHEMA_VNEXT_REQUEST_COMPONENTS = {
    "orient": "OrientRequest",
    "invoke": "InvokeRequest",
    "compose": "ComposeRequest",
    "execute": "ExecuteRequest",
    "observe": "ObserveRequest",
    "resume": "ResumeRequest",
    "transfer": "TransferRequest",
}
_SCHEMA_VNEXT_OPENAPI_CACHE: JsonRecord | None = None
SCHEMA_VNEXT_MAX_REQUEST_BYTES = 1024 * 1024


def _schema_vnext_openapi() -> JsonRecord:
    global _SCHEMA_VNEXT_OPENAPI_CACHE
    if _SCHEMA_VNEXT_OPENAPI_CACHE is None:
        loaded = json.loads(_SCHEMA_VNEXT_OPENAPI_PATH.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise LabToolError("SCHEMA_INVALID", "v11 OpenAPI root must be an object", 500)
        _SCHEMA_VNEXT_OPENAPI_CACHE = loaded
    return _SCHEMA_VNEXT_OPENAPI_CACHE


def _schema_vnext_resolve_refs(value: object, *, stack: tuple[str, ...] = ()) -> object:
    if isinstance(value, list):
        return [_schema_vnext_resolve_refs(item, stack=stack) for item in value]
    if not isinstance(value, dict):
        return value
    ref = value.get("$ref")
    if ref is not None:
        ref_text = str(ref)
        prefix = "#/components/schemas/"
        if not ref_text.startswith(prefix):
            raise LabToolError("SCHEMA_INVALID", f"unsupported v11 schema reference: {ref_text}", 500)
        name = ref_text[len(prefix):]
        if name in stack:
            raise LabToolError("SCHEMA_INVALID", f"cyclic v11 schema reference: {name}", 500)
        components = (_schema_vnext_openapi().get("components") or {}).get("schemas") or {}
        target = components.get(name)
        if not isinstance(target, dict):
            raise LabToolError("SCHEMA_INVALID", f"missing v11 schema component: {name}", 500)
        resolved = _schema_vnext_resolve_refs(target, stack=(*stack, name))
        if len(value) == 1:
            return resolved
        merged = dict(resolved) if isinstance(resolved, dict) else {}
        for key, child in value.items():
            if key != "$ref":
                merged[key] = _schema_vnext_resolve_refs(child, stack=stack)
        return merged
    return {str(key): _schema_vnext_resolve_refs(child, stack=stack) for key, child in value.items()}


def _schema_vnext_raise_validation(code: str, message: str, status: int) -> None:
    raise LabToolError(code, message, status)


def _schema_vnext_request_payload(operation: str) -> JsonRecord:
    if not request.is_json:
        raise LabToolError("UNSUPPORTED_MEDIA_TYPE", "v11 request body must use application/json", 415)
    content_length = request.content_length
    if content_length is not None and int(content_length) > SCHEMA_VNEXT_MAX_REQUEST_BYTES:
        raise LabToolError(
            "REQUEST_TOO_LARGE",
            f"v11 request body exceeds {SCHEMA_VNEXT_MAX_REQUEST_BYTES} bytes",
            413,
        )
    cached = getattr(request, "_cached_data", None)
    raw = (
        bytes(cached)
        if isinstance(cached, (bytes, bytearray))
        else request.stream.read(SCHEMA_VNEXT_MAX_REQUEST_BYTES + 1)
    )
    if len(raw) > SCHEMA_VNEXT_MAX_REQUEST_BYTES:
        raise LabToolError(
            "REQUEST_TOO_LARGE",
            f"v11 request body exceeds {SCHEMA_VNEXT_MAX_REQUEST_BYTES} bytes",
            413,
        )
    try:
        request_payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LabToolError("BAD_JSON", "request body is not valid UTF-8 JSON", 400) from exc
    if not isinstance(request_payload, dict):
        raise LabToolError("BAD_JSON", "JSON body must be an object", 400)
    component_name = _SCHEMA_VNEXT_REQUEST_COMPONENTS.get(operation)
    if component_name is None:
        raise LabToolError("SCHEMA_INVALID", f"unknown v11 route schema: {operation}", 500)
    components = (_schema_vnext_openapi().get("components") or {}).get("schemas") or {}
    component = components.get(component_name)
    if not isinstance(component, dict):
        raise LabToolError("SCHEMA_INVALID", f"missing v11 request schema: {component_name}", 500)
    resolved = _schema_vnext_resolve_refs(component)
    if not isinstance(resolved, dict):
        raise LabToolError("SCHEMA_INVALID", f"resolved v11 request schema is invalid: {component_name}", 500)
    validate_schema_value(resolved, request_payload, "payload", raise_error=_schema_vnext_raise_validation)
    return request_payload


def _schema_vnext_http_call(fn, operation: str) -> object:
    ae = _auth()
    if ae:
        return ae
    try:
        return jsonify(fn(_schema_vnext_request_payload(operation)))
    except LabToolError as exc:
        return _error(exc.error_code, exc.message, exc.status, **exc.extra)
    except FileNotFoundError:
        return _error("NOT_FOUND", "referenced Runtime object was not found", 404)
    except RuntimeError as exc:
        message = str(exc)
        if message.startswith("NOT_FOUND:"):
            return _error("NOT_FOUND", message.split(":", 1)[1].strip(), 404)
        return _error("SCHEMA_VNEXT_FAILED", message, 500)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return _error("SCHEMA_VNEXT_FAILED", str(exc), 500)


@lab_bp.post("/vnext/orient")
def lab_vnext_orient() -> object:
    return _schema_vnext_http_call(schema_vnext_orient, "orient")


@lab_bp.post("/vnext/invoke")
def lab_vnext_invoke() -> object:
    return _schema_vnext_http_call(schema_vnext_invoke, "invoke")


@lab_bp.post("/vnext/compose")
def lab_vnext_compose() -> object:
    return _schema_vnext_http_call(schema_vnext_compose, "compose")


@lab_bp.post("/vnext/execute")
def lab_vnext_execute() -> object:
    return _schema_vnext_http_call(schema_vnext_execute, "execute")


@lab_bp.post("/vnext/observe")
def lab_vnext_observe() -> object:
    return _schema_vnext_http_call(schema_vnext_observe, "observe")


@lab_bp.post("/vnext/resume")
def lab_vnext_resume() -> object:
    return _schema_vnext_http_call(schema_vnext_resume, "resume")


@lab_bp.post("/vnext/transfer")
def lab_vnext_transfer() -> object:
    return _schema_vnext_http_call(schema_vnext_transfer, "transfer")
