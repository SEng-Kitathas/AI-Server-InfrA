"""Execution lab-tool registration surface for sync and async project commands."""

from __future__ import annotations

import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from dataclasses import dataclass
from lab_tool_primitives import ToolPayload, ToolResult, payload_str, payload_value
from pathlib import Path
from server_hardening import run_subprocess_envelope
from typing import Any, Callable


AI_WAIT_DEFAULT_SECONDS = 8
AI_WAIT_MAX_SECONDS = 30
AI_WAIT_DEFAULT_OUTPUT_BYTES = 4096
AI_WAIT_MAX_OUTPUT_BYTES = 16384
ACTIVE_JOB_STATUSES = {"RUNNING", "SUBMITTED", "QUEUED", "STARTING", "TERMINATING"}


@dataclass(frozen=True)
class ExecutionIdentity:
    project_id: str
    job_id: str


@dataclass(frozen=True)
class CommandRequestSpec:
    error_cls: type[Exception]
    request_optional_positive_int: Callable[..., int | None]
    default_timeout_seconds: int | None
    default_stdout_max_bytes: int | None
    default_stderr_max_bytes: int | None
    max_timeout_seconds: int | None
    max_output_bytes: int | None


@dataclass(frozen=True)
class CommandRequest:
    project_id: str
    command: list[str]
    args: list[str]
    cwd: str | None
    timeout_seconds: int | None
    stdout_max_bytes: int | None
    stderr_max_bytes: int | None


@dataclass(frozen=True)
class WaitRequest:
    identity: ExecutionIdentity
    timeout_seconds: int | None
    max_bytes: int | None


def _require_identity(error_cls: type[Exception], payload: ToolPayload) -> ExecutionIdentity:
    project_id = payload_str(payload, "project_id").strip()
    job_id = payload_str(payload, "job_id").strip()
    if not project_id or not job_id:
        raise error_cls("BAD_REQUEST", "project_id and job_id are required", 400)
    return ExecutionIdentity(project_id=project_id, job_id=job_id)


def _read_command_array(
    error_cls: type[Exception], payload: ToolPayload
) -> tuple[list[str], list[str]]:
    command = payload_value(payload, "command")
    args = payload_value(payload, "args") or []
    if (
        not isinstance(command, list)
        or not command
        or not all(isinstance(x, str) and x for x in command)
    ):
        raise error_cls("BAD_REQUEST", "command must be a non-empty string array", 400)
    if not isinstance(args, list) or not all(isinstance(x, str) for x in args):
        raise error_cls("BAD_REQUEST", "args must be a string array", 400)
    return command, args


def _command_request(payload: ToolPayload, spec: CommandRequestSpec) -> CommandRequest:
    command, args = _read_command_array(spec.error_cls, payload)
    return CommandRequest(
        project_id=payload_str(payload, "project_id").strip(),
        command=command,
        args=args,
        cwd=payload_str(payload, "cwd").strip() or None,
        timeout_seconds=spec.request_optional_positive_int(
            payload.get("timeout_seconds", spec.default_timeout_seconds),
            spec.default_timeout_seconds,
            minimum=1,
            maximum=spec.max_timeout_seconds,
        ),
        stdout_max_bytes=spec.request_optional_positive_int(
            payload.get("stdout_max_bytes", spec.default_stdout_max_bytes),
            spec.default_stdout_max_bytes,
            minimum=1024,
            maximum=spec.max_output_bytes,
        ),
        stderr_max_bytes=spec.request_optional_positive_int(
            payload.get("stderr_max_bytes", spec.default_stderr_max_bytes),
            spec.default_stderr_max_bytes,
            minimum=1024,
            maximum=spec.max_output_bytes,
        ),
    )


def _wait_request(
    error_cls: type[Exception],
    payload: ToolPayload,
    *,
    request_optional_positive_int: Callable[..., int | None],
    max_output_bytes: int | None,
) -> WaitRequest:
    return WaitRequest(
        identity=_require_identity(error_cls, payload),
        timeout_seconds=request_optional_positive_int(
            payload.get("timeout_seconds", AI_WAIT_DEFAULT_SECONDS),
            AI_WAIT_DEFAULT_SECONDS,
            minimum=1,
            maximum=AI_WAIT_MAX_SECONDS,
        ),
        max_bytes=request_optional_positive_int(
            payload.get("max_bytes", AI_WAIT_DEFAULT_OUTPUT_BYTES),
            AI_WAIT_DEFAULT_OUTPUT_BYTES,
            minimum=1024,
            maximum=min(AI_WAIT_MAX_OUTPUT_BYTES, max_output_bytes) if max_output_bytes else AI_WAIT_MAX_OUTPUT_BYTES,
        ),
    )



@dataclass(frozen=True)
class ExecutionToolDeps:
    error_cls: type[Exception]
    request_optional_positive_int: Callable[..., int | None]
    resolve_cwd: Callable[[str, str | None], Path]
    exec_env: Callable[[ToolPayload], dict[str, str]]
    finalize_job: Callable[..., ToolResult]
    read_job: Callable[..., ToolResult]
    tail_text: Callable[[Path, int | None], tuple[str, bool]]
    execution_modes: set[str]
    max_output_bytes: int | None
    default_timeout_seconds: int | None
    default_stdout_max_bytes: int | None
    default_stderr_max_bytes: int | None
    max_timeout_seconds: int | None
    submit_job: Callable[..., Any]
    terminate_job: Callable[[str, str], Any]
    utc_now: Callable[[], str]


def _execution_deps(deps: ToolPayload) -> ExecutionToolDeps:
    return ExecutionToolDeps(
        error_cls=deps["error_cls"],
        request_optional_positive_int=deps["request_optional_positive_int"],
        resolve_cwd=deps["resolve_cwd"],
        exec_env=deps["exec_env"],
        finalize_job=deps["finalize_job"],
        read_job=deps["read_job"],
        tail_text=deps["tail_text"],
        execution_modes=deps["execution_modes"],
        max_output_bytes=deps["max_output_bytes"],
        default_timeout_seconds=deps["default_timeout_seconds"],
        default_stdout_max_bytes=deps["default_stdout_max_bytes"],
        default_stderr_max_bytes=deps["default_stderr_max_bytes"],
        max_timeout_seconds=deps["max_timeout_seconds"],
        submit_job=deps["submit_job"],
        terminate_job=deps["terminate_job"],
        utc_now=deps["utc_now"],
    )


def _command_spec(dep: ExecutionToolDeps) -> CommandRequestSpec:
    return CommandRequestSpec(
        error_cls=dep.error_cls,
        request_optional_positive_int=dep.request_optional_positive_int,
        default_timeout_seconds=dep.default_timeout_seconds,
        default_stdout_max_bytes=dep.default_stdout_max_bytes,
        default_stderr_max_bytes=dep.default_stderr_max_bytes,
        max_timeout_seconds=dep.max_timeout_seconds,
        max_output_bytes=dep.max_output_bytes,
    )


def _resolved_command_request(
    payload: ToolPayload, dep: ExecutionToolDeps
) -> tuple[CommandRequest, Path]:
    request = _command_request(payload, _command_spec(dep))
    return request, dep.resolve_cwd(request.project_id, request.cwd)


def _sync_execution_payload(payload: ToolPayload, dep: ExecutionToolDeps) -> ToolResult:
    request, cwd = _resolved_command_request(payload, dep)
    result = run_subprocess_envelope(
        request.command + request.args,
        cwd=cwd,
        timeout_seconds=request.timeout_seconds,
        stdout_max_bytes=request.stdout_max_bytes,
        stderr_max_bytes=request.stderr_max_bytes,
    )
    result["project_id"] = request.project_id
    return result


def _python_execution_payload(payload: ToolPayload, dep: ExecutionToolDeps) -> ToolResult:
    request, cwd = _resolved_command_request(payload, dep)
    code = payload_str(payload, "code")
    if not code:
        raise dep.error_cls("BAD_REQUEST", "code is required", 400)
    with tempfile.NamedTemporaryFile("w", suffix=".py", encoding="utf-8", delete=False) as tmp:
        tmp.write(code)
        tmp_path = Path(tmp.name)
    try:
        result = run_subprocess_envelope(
            [sys.executable, str(tmp_path)],
            cwd=cwd,
            timeout_seconds=request.timeout_seconds,
            stdout_max_bytes=request.stdout_max_bytes,
            stderr_max_bytes=request.stderr_max_bytes,
        )
        result["project_id"] = request.project_id
        result["runner"] = sys.executable
        return result
    finally:
        tmp_path.unlink(missing_ok=True)


def _register_sync_execution_tools(
    register_tool: Callable[..., Any], dep: ExecutionToolDeps
) -> None:
    @register_tool(
        "execution.run",
        "Run a command synchronously inside a project cwd.",
        "high",
        category="execution",
        approval_required=True,
        side_effect_class="execution",
        effect_traits=["executes_code", "spawns_process", "arbitrary_process_side_effects", "project_mutation_fenced"],
    )
    def tool_execution_run(payload: ToolPayload) -> ToolResult:
        return _sync_execution_payload(payload, dep)

    @register_tool(
        "python.run",
        "Execute inline Python with project-scoped cwd.",
        "high",
        category="execution",
        approval_required=True,
        side_effect_class="execution",
        effect_traits=["executes_code", "spawns_process", "arbitrary_process_side_effects", "project_mutation_fenced"],
    )
    def tool_python_run(payload: ToolPayload) -> ToolResult:
        return _python_execution_payload(payload, dep)


def _as_tool_result(job: Any) -> ToolResult:
    if hasattr(job, "to_dict"):
        return job.to_dict()
    if isinstance(job, dict):
        return job
    raise TypeError(f"unsupported execution job type: {type(job).__name__}")


def _submit_async_job_payload(payload: ToolPayload, dep: ExecutionToolDeps) -> ToolResult:
    """Delegate async submission to the canonical durable scheduler."""
    return _as_tool_result(dep.submit_job(payload))


def _register_async_submit_tool(register_tool: Callable[..., Any], dep: ExecutionToolDeps) -> None:
    @register_tool(
        "execution.submit",
        "Submit an async execution job.",
        "high",
        category="execution",
        approval_required=True,
        side_effect_class="execution",
        effect_traits=["creates_durable_state", "queues_work", "executes_code", "arbitrary_process_side_effects", "project_mutation_fenced", "requires_explicit_project_mutation_authority"],
        idempotency_semantics="keyed_replay_when_keyed",
    )
    def tool_execution_submit(payload: ToolPayload) -> ToolResult:
        return _submit_async_job_payload(payload, dep)


def _job_output_payload(
    request: WaitRequest, job: ToolResult, dep: ExecutionToolDeps
) -> ToolResult:
    stdout_text, stdout_truncated = dep.tail_text(Path(job["stdout_path"]), request.max_bytes)
    stderr_text, stderr_truncated = dep.tail_text(Path(job["stderr_path"]), request.max_bytes)
    return {
        "project_id": request.identity.project_id,
        "job_id": request.identity.job_id,
        "status": job.get("status"),
        "stdout": stdout_text,
        "stderr": stderr_text,
        "stdout_truncated": stdout_truncated,
        "stderr_truncated": stderr_truncated,
        "bytes_returned": len(stdout_text.encode("utf-8")) + len(stderr_text.encode("utf-8")),
        "max_bytes": request.max_bytes,
        "last_update_time": dep.utc_now(),
    }


def _parse_epoch(value: object) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except (TypeError, ValueError, OverflowError):
        return None


def _file_signal(path_value: object, now: float) -> tuple[int, float | None]:
    path = Path(str(path_value or ""))
    try:
        stat = path.stat()
    except (OSError, ValueError):
        return 0, None
    return int(stat.st_size), max(0.0, now - float(stat.st_mtime))


def _progress_class(job: ToolResult, heartbeat_age: float | None, output_age: float | None) -> str:
    status = str(job.get("status") or "UNKNOWN").upper()
    supervision = str(job.get("supervision_state") or "").lower()
    stage = str(job.get("stage") or "").lower()
    if status not in ACTIVE_JOB_STATUSES:
        return "TERMINAL"
    if status == "QUEUED":
        return "QUEUED"
    if status == "TERMINATING" or "cancel" in stage:
        return "TERMINATING"
    if any(token in supervision for token in ("lost", "unsupervised", "stale")):
        return "SUPERVISION_UNCERTAIN"
    freshest = min(x for x in (heartbeat_age, output_age) if x is not None) if any(
        x is not None for x in (heartbeat_age, output_age)
    ) else None
    if freshest is not None and freshest <= 5.0:
        return "PROGRESSING"
    if freshest is not None and freshest <= 30.0:
        return "QUIESCENT"
    if status in {"SUBMITTED", "STARTING"}:
        return "STARTING"
    return "POSSIBLY_STALLED"


def _suggested_recheck_seconds(progress_class: str) -> int:
    return {
        "TERMINAL": 0,
        "QUEUED": 10,
        "STARTING": 5,
        "PROGRESSING": 15,
        "QUIESCENT": 30,
        "POSSIBLY_STALLED": 10,
        "SUPERVISION_UNCERTAIN": 5,
        "TERMINATING": 5,
    }.get(progress_class, 15)


def _progress_receipt(identity: ExecutionIdentity, job: ToolResult, dep: ExecutionToolDeps, *, wait_timed_out: bool = False) -> ToolResult:
    now = time.time()
    started_epoch = _parse_epoch(job.get("started_at")) or _parse_epoch(job.get("submitted_at"))
    elapsed_ms = int(max(0.0, now - started_epoch) * 1000) if started_epoch is not None else job.get("duration_ms")
    heartbeat_bytes, heartbeat_age = _file_signal(job.get("worker_heartbeat_path"), now)
    stdout_bytes, stdout_age = _file_signal(job.get("stdout_path"), now)
    stderr_bytes, stderr_age = _file_signal(job.get("stderr_path"), now)
    output_ages = [x for x in (stdout_age, stderr_age) if x is not None]
    output_age = min(output_ages) if output_ages else None
    progress_class = _progress_class(job, heartbeat_age, output_age)
    failure = job.get("failure_digest")
    return {
        "project_id": identity.project_id,
        "job_id": identity.job_id,
        "status": job.get("status"),
        "stage": job.get("stage"),
        "progress_class": progress_class,
        "wait_timed_out": bool(wait_timed_out),
        "actually_started": bool(job.get("started_at")),
        "elapsed_ms": elapsed_ms,
        "queue_position": job.get("queue_position"),
        "supervision_state": job.get("supervision_state"),
        "worker_heartbeat_age_seconds": round(heartbeat_age, 3) if heartbeat_age is not None else None,
        "output_age_seconds": round(output_age, 3) if output_age is not None else None,
        "output_available": bool(stdout_bytes or stderr_bytes),
        "stdout_bytes": stdout_bytes,
        "stderr_bytes": stderr_bytes,
        "return_code": job.get("return_code"),
        "failure_digest": failure if failure else None,
        "result_artifacts": job.get("result_artifact_targets") or [],
        "artifact_registration_status": job.get("artifact_registration_status"),
        "suggested_recheck_seconds": _suggested_recheck_seconds(progress_class),
        "bulk_output_tool": "execution.output",
        "decision_note": (
            "terminal; inspect bounded output/result artifacts if needed"
            if progress_class == "TERMINAL"
            else "work remains active; return control to the operator instead of waiting indefinitely"
        ),
    }


def _completed_wait_payload(
    request: WaitRequest, job: ToolResult, dep: ExecutionToolDeps
) -> ToolResult:
    stdout_text, stdout_truncated = dep.tail_text(
        Path(job.get("stdout_path", "")), request.max_bytes
    )
    stderr_text, stderr_truncated = dep.tail_text(
        Path(job.get("stderr_path", "")), request.max_bytes
    )
    receipt = _progress_receipt(request.identity, job, dep, wait_timed_out=False)
    receipt.update(
        {
            "stdout_excerpt": stdout_text,
            "stderr_excerpt": stderr_text,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
            "excerpt_max_bytes": request.max_bytes,
        }
    )
    return receipt


def _timed_out_wait_payload(request: WaitRequest, job: ToolResult, dep: ExecutionToolDeps) -> ToolResult:
    return _progress_receipt(request.identity, job, dep, wait_timed_out=True)


def _wait_request_from_payload(payload: ToolPayload, dep: ExecutionToolDeps) -> WaitRequest:
    return _wait_request(
        dep.error_cls,
        payload,
        request_optional_positive_int=dep.request_optional_positive_int,
        max_output_bytes=dep.max_output_bytes,
    )


def _finalized_job(identity: JobIdentity, dep: ExecutionToolDeps) -> ToolResult:
    try:
        return dep.finalize_job(
            identity.project_id,
            identity.job_id,
            dep.read_job(identity.project_id, identity.job_id),
        )
    except FileNotFoundError:
        raise dep.error_cls("NOT_FOUND", "job not found", 404)


def _wait_until_done(request: WaitRequest, dep: ExecutionToolDeps) -> ToolResult:
    timeout_seconds = min(
        AI_WAIT_MAX_SECONDS,
        max(1, int(request.timeout_seconds or AI_WAIT_DEFAULT_SECONDS)),
    )
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        job = _finalized_job(request.identity, dep)
        if str(job.get("status") or "").upper() not in ACTIVE_JOB_STATUSES:
            return _completed_wait_payload(request, job, dep)
        time.sleep(0.5)
    return _timed_out_wait_payload(
        request, _finalized_job(request.identity, dep), dep
    )


def _register_async_status_tools(register_tool: Callable[..., Any], dep: ExecutionToolDeps) -> None:
    @register_tool(
        "execution.status",
        "Read and finalize async execution job status.",
        "medium",
        category="execution",
        side_effect_class="read_reconcile",
        effect_traits=["reads_state", "reconciles_state", "may_advance_queue"],
    )
    def tool_execution_status(payload: ToolPayload) -> ToolResult:
        return _finalized_job(_require_identity(dep.error_cls, payload), dep)

    @register_tool(
        "execution.output",
        "Read bounded stdout/stderr for an async execution job.",
        "medium",
        category="execution",
        side_effect_class="read_reconcile",
        effect_traits=["reads_state", "reads_logs", "reconciles_state", "may_advance_queue"],
    )
    def tool_execution_output(payload: ToolPayload) -> ToolResult:
        request = _wait_request_from_payload(payload, dep)
        return _job_output_payload(request, _finalized_job(request.identity, dep), dep)

    @register_tool(
        "execution.progress",
        "Return a compact decision-grade progress receipt without bulk logs or long polling.",
        "low",
        category="execution",
        tags=["progress", "bounded", "ai-control"],
        side_effect_class="read_reconcile",
        effect_traits=["reads_state", "reconciles_state", "may_advance_queue"],
    )
    def tool_execution_progress(payload: ToolPayload) -> ToolResult:
        identity = _require_identity(dep.error_cls, payload)
        return _progress_receipt(identity, _finalized_job(identity, dep), dep)

    @register_tool(
        "execution.wait",
        "Bounded wait for terminal state; otherwise return a compact decision-grade progress receipt.",
        "medium",
        category="execution",
        tags=["wait", "progress", "bounded", "ai-control"],
        side_effect_class="read_reconcile",
        effect_traits=["reads_state", "bounded_wait", "reconciles_state", "may_advance_queue"],
    )
    def tool_execution_wait(payload: ToolPayload) -> ToolResult:
        return _wait_until_done(_wait_request_from_payload(payload, dep), dep)


def _register_async_terminate_tool(
    register_tool: Callable[..., Any], dep: ExecutionToolDeps
) -> None:
    @register_tool(
        "execution.terminate",
        "Terminate a running async job.",
        "critical",
        category="execution",
        approval_required=True,
        mutating=True,
    )
    def tool_execution_terminate(payload: ToolPayload) -> ToolResult:
        identity = _require_identity(dep.error_cls, payload)
        try:
            return _as_tool_result(dep.terminate_job(identity.project_id, identity.job_id))
        except FileNotFoundError:
            raise dep.error_cls("NOT_FOUND", "job not found", 404)


def register_execution_tools(
    register_tool: (
        Callable[
            ...,
            Callable[[Callable[[ToolPayload], ToolResult]], Callable[[ToolPayload], ToolResult]],
        ]
        | Callable[..., Any]
    ),
    **deps: Any,
) -> None:
    dep = _execution_deps(deps)
    _register_sync_execution_tools(register_tool, dep)
    _register_async_submit_tool(register_tool, dep)
    _register_async_status_tools(register_tool, dep)
    _register_async_terminate_tool(register_tool, dep)
