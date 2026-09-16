"""Lab HTTP routes for health, tool catalog, dispatch, batch dispatch, and result handles."""

from __future__ import annotations
from typing import Any

from collections.abc import MutableMapping
from pathlib import Path
import hashlib
import json
import os
import atexit
import subprocess
import sys
from dataclasses import dataclass
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

from flask import Blueprint, current_app, jsonify, request

from execution_routes import execution_readiness
from runtime_config import LAB_BATCH_CONFIG
from lab_results import (
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
from server_hardening import safe_json_dumps
from schema_vnext_runtime import (
    compose as schema_vnext_compose,
    execute as schema_vnext_execute,
    invoke as schema_vnext_invoke,
    observe as schema_vnext_observe,
    orient as schema_vnext_orient,
    resume as schema_vnext_resume,
    transfer as schema_vnext_transfer,
)
from lab_tools import (
    LabToolError,
    dispatch_tool,
    list_tools,
    server_native_router_descriptor,
    tool_catalog_response,
    tool_lab_health,
)

JsonRecord = MutableMapping[str, Any]
from shared_core import ensure_parent, mount_summary, require_valid_api_key, utc_now
from control_plane_models import BatchExecutorTelemetry, BackgroundResultEnvelope

lab_bp = Blueprint("lab", __name__, url_prefix="/lab")


_BATCH_EXECUTOR_LOCK = threading.RLock()
_BATCH_EXECUTOR: ThreadPoolExecutor | None = None
_BACKGROUND_BATCHES_SUBMITTED = 0


_BATCH_EXECUTOR_STATS_LOCK = threading.RLock()
_BATCH_EXECUTOR_TELEMETRY = BatchExecutorTelemetry()


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


def _batch_step_result(idx: int, step: dict) -> dict:
    tool_name = str(step.get("tool_name", "")).strip()
    payload = step.get("payload") or {}
    authority = step.get("authority") or {}
    expected_contract_digest = step.get("expected_contract_digest")
    try:
        return {
            "index": idx,
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
    if parallelism > 1 and not stop_on_error:
        return _parallel_map_ordered(steps, _batch_step_result, parallelism)
    results: list[dict] = []
    for idx, raw_step in enumerate(steps):
        step = _validate_batch_step(idx, raw_step)
        result = _batch_step_result(idx, step)
        results.append(result)
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

_VNEXT_CONTRACT_PATH = Path(__file__).with_name("pcmmad_lab_action_schema_v11_0_capability_microkernel_8.json")
_VNEXT_CANONICAL = {
    "orient": ("/lab/vnext/orient", "orientCapabilities"),
    "invoke": ("/lab/vnext/invoke", "invokeCapability"),
    "flow": ("/lab/batch", "flowCapabilities"),
    "compose": ("/lab/vnext/compose", "composePlan"),
    "execute": ("/lab/vnext/execute", "executePlan"),
    "observe": ("/lab/vnext/observe", "observeRuntime"),
    "resume": ("/lab/vnext/resume", "resumeContinuation"),
    "transfer": ("/lab/vnext/transfer", "transferData"),
}
_VNEXT_LEGACY = {
    "/orient": "orient",
    "/invoke": "invoke",
    "/compose": "compose",
    "/execute": "execute",
    "/observe": "observe",
    "/resume": "resume",
    "/transfer": "transfer",
    "/vnext/flow": "flow",
    "/vnext/orientCapabilities": "orient",
    "/vnext/invokeCapability": "invoke",
    "/vnext/composePlan": "compose",
    "/vnext/executePlan": "execute",
    "/vnext/observeRuntime": "observe",
    "/vnext/resumeContinuation": "resume",
    "/vnext/transferData": "transfer",
}

def _vnext_openapi() -> dict:
    try:
        raw=json.loads(_VNEXT_CONTRACT_PATH.read_text(encoding="utf-8-sig"))
        return raw if isinstance(raw,dict) else {}
    except Exception:
        return {}

def _vnext_contract(operation: str) -> dict:
    canonical,operation_id=_VNEXT_CANONICAL[operation]
    doc=_vnext_openapi()
    op=((doc.get("paths") or {}).get(canonical) or {}).get("post") or {}
    schema=((((op.get("requestBody") or {}).get("content") or {}).get("application/json") or {}).get("schema") or {})
    ref=str(schema.get("$ref") or "")
    name=ref.rsplit("/",1)[-1] if ref else None
    component=((doc.get("components") or {}).get("schemas") or {}).get(name or "") or {}
    props=component.get("properties") or {}
    required=component.get("required") or []
    return {
        "canonical_path":canonical,
        "method":"POST",
        "operation_id":operation_id,
        "request_schema":name,
        "required":[str(x) for x in required],
        "accepted_fields":sorted(str(x) for x in props),
    }

def _vnext_correction(operation: str, classification: str, status: int=400, *, detail=None):
    payload={
        "ok":False,
        "error_code":"INGRESS_CORRECTION",
        "classification":classification,
        "message":"Recognized PCMMAD Action ingress is not in the current accepted shape.",
        "correction":_vnext_contract(operation),
        "time":utc_now(),
    }
    if detail is not None:
        payload["detail"]=detail
    return jsonify(payload),status

@lab_bp.before_request
def _vnext_shape_guard():
    path=request.path
    by_path={meta[0]:op for op,meta in _VNEXT_CANONICAL.items()}
    operation=by_path.get(path)
    if operation is None or request.method!="POST":
        return None
    ae=_auth()
    if ae:
        return ae
    if not request.is_json:
        return _vnext_correction(operation,"NON_JSON_CURRENT_CALL",415)
    body=request.get_json(silent=True)
    if not isinstance(body,dict):
        return _vnext_correction(operation,"MALFORMED_CURRENT_CALL",400,detail={"reason":"JSON body must be an object"})
    contract=_vnext_contract(operation)
    accepted=set(contract.get("accepted_fields") or [])
    required=set(contract.get("required") or [])
    unknown=sorted(set(body)-accepted) if accepted else []
    missing=sorted(x for x in required if x not in body)
    if unknown or missing:
        return _vnext_correction(
            operation,
            "MALFORMED_CURRENT_CALL",
            400,
            detail={"unknown_fields":unknown,"missing_required":missing},
        )
    return None

def _vnext_legacy_view(operation: str):
    def view():
        ae=_auth()
        if ae:
            return ae
        return _vnext_correction(
            operation,
            "RECOGNIZED_LEGACY_ROUTE",
            400,
            detail={"legacy_path":request.path,"received_method":request.method},
        )
    return view

def _vnext_wrong_method_view(operation: str):
    def view():
        ae=_auth()
        if ae:
            return ae
        return _vnext_correction(
            operation,
            "WRONG_METHOD",
            405,
            detail={"received_method":request.method},
        )
    return view

for _idx,(_route,_operation) in enumerate(_VNEXT_LEGACY.items()):
    lab_bp.add_url_rule(
        _route,
        endpoint=f"_vnext_legacy_{_idx}",
        view_func=_vnext_legacy_view(_operation),
        methods=["GET","POST","PUT","PATCH","DELETE"],
    )

for _idx,(_operation,(_canonical,_opid)) in enumerate(_VNEXT_CANONICAL.items()):
    _relative=_canonical[len("/lab"):] if _canonical.startswith("/lab") else _canonical
    lab_bp.add_url_rule(
        _relative,
        endpoint=f"_vnext_wrong_method_{_idx}",
        view_func=_vnext_wrong_method_view(_operation),
        methods=["GET","PUT","PATCH","DELETE"],
    )

def _schema_vnext_request_payload() -> JsonRecord:
    request_payload = request.get_json(silent=False, force=True)
    if not isinstance(request_payload, dict):
        raise LabToolError("BAD_JSON", "JSON body must be an object", 400)
    return request_payload


def _schema_vnext_http_call(fn) -> object:
    ae = _auth()
    if ae:
        return ae
    try:
        return jsonify(fn(_schema_vnext_request_payload()))
    except LabToolError as exc:
        return _error(exc.error_code, exc.message, exc.status, **exc.extra)
    except FileNotFoundError:
        return _error("NOT_FOUND", "referenced Runtime object was not found", 404)
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as exc:
        return _error("SCHEMA_VNEXT_FAILED", str(exc), 500)


@lab_bp.post("/vnext/orient")
def lab_vnext_orient() -> object:
    return _schema_vnext_http_call(schema_vnext_orient)


@lab_bp.post("/vnext/invoke")
def lab_vnext_invoke() -> object:
    return _schema_vnext_http_call(schema_vnext_invoke)


@lab_bp.post("/vnext/compose")
def lab_vnext_compose() -> object:
    return _schema_vnext_http_call(schema_vnext_compose)


@lab_bp.post("/vnext/execute")
def lab_vnext_execute() -> object:
    return _schema_vnext_http_call(schema_vnext_execute)


@lab_bp.post("/vnext/observe")
def lab_vnext_observe() -> object:
    return _schema_vnext_http_call(schema_vnext_observe)


@lab_bp.post("/vnext/resume")
def lab_vnext_resume() -> object:
    return _schema_vnext_http_call(schema_vnext_resume)


@lab_bp.post("/vnext/transfer")
def lab_vnext_transfer() -> object:
    return _schema_vnext_http_call(schema_vnext_transfer)
