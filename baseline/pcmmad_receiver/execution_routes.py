"""Execution routes for queued jobs, lifecycle, output windows, replay, and registration."""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
import atexit
import threading
import time
from dataclasses import dataclass
import uuid
from pathlib import Path
from typing import Any

if os.name == "nt":
    import windows_job_object as _wjo
else:
    _wjo = None
from collections.abc import MutableMapping

from flask import Blueprint, jsonify, request
from runtime_config import EXECUTION_CONFIG
from server_hardening import ManagedProcess, start_background_process
from control_plane_models import (
    CapacitySnapshot,
    CorruptJobFileRecord,
    ExecutionCapabilitiesEnvelope,
    ExecutionFailureDigest,
    ExecutionIdempotencyLedger,
    ExecutionIdempotencyRecord,
    ExecutionJobRecord,
    ExecutionReadinessEnvelope,
    ExecutionRegistrationRecord,
    ExecutionSubmitPayload,
    GlobalExecutionSnapshot,
    SchedulerTelemetry,
    TextWindow,
)

JsonObject = MutableMapping[str, Any]

from api_wire_models import (
    ExecutionListRequest,
    ExecutionListResponse,
    ExecutionOutputRequest,
    ExecutionOutputResponse,
    ExecutionRegisterRequest,
    ExecutionRegisterResponse,
    ExecutionReplayRequest,
    ExecutionStatusRequest,
    ExecutionStatusResponse,
    ExecutionTerminateRequest,
)
from server_hardening import safe_json_dumps, safe_json_loads, safe_project_cwd
from shared_core import (
    PROJECTS_ROOT,
    commits_ledger_path_for,
    ensure_parent,
    get_project_root,
    load_json,
    manifest_path_for,
    require_valid_api_key,
    resolve_target,
    save_json_atomic,
    sha256_file,
    utc_now,
    append_jsonl,
)

execution_bp = Blueprint("execution", __name__, url_prefix="/project/execution")
_RUNNING: dict[str, ManagedProcess] = {}
_RUNNING_LOCK = threading.RLock()
_ADMISSION_LOCK = threading.RLock()

DEFAULT_TIMEOUT_SECONDS = EXECUTION_CONFIG.default_timeout_seconds
MAX_TIMEOUT_SECONDS = EXECUTION_CONFIG.max_timeout_seconds
DEFAULT_STDOUT_MAX_BYTES = EXECUTION_CONFIG.default_stdout_max_bytes
DEFAULT_STDERR_MAX_BYTES = EXECUTION_CONFIG.default_stderr_max_bytes
MAX_OUTPUT_BYTES = EXECUTION_CONFIG.max_output_bytes
DEFAULT_LIST_LIMIT = 20

EXECUTION_MODES = ("one_shot", "bench", "replay", "ablation")


def _env_optional_positive_int(name: str, default: int | None) -> int | None:
    raw = str(os.environ.get(name, "" if default is None else default)).strip().lower()
    if raw in {"", "none"}:
        return default
    if raw in {"0", "-1", "unbounded", "unlimited", "inf", "infinite"}:
        return None
    value = int(raw)
    return None if value <= 0 else value


def _request_optional_positive_int(
    value: Any, default: int | None, *, minimum: int = 0, maximum: int | None = None
) -> int | None:
    if value is None or value == "":
        return default
    raw = str(value).strip().lower()
    if raw in {"0", "-1", "none", "unbounded", "unlimited", "inf", "infinite"}:
        return None
    ivalue = int(value)
    if ivalue < minimum:
        ivalue = minimum
    if maximum is not None and ivalue > maximum:
        ivalue = maximum
    return ivalue


def _limit_for_wire(value: int | None) -> int:
    return 0 if value is None else int(value)


EXECUTION_GLOBAL_CONCURRENCY = EXECUTION_CONFIG.global_concurrency
EXECUTION_PROJECT_CONCURRENCY = EXECUTION_CONFIG.project_concurrency
EXECUTION_GLOBAL_QUEUE_LIMIT = EXECUTION_CONFIG.global_queue_limit
EXECUTION_PROJECT_QUEUE_LIMIT = EXECUTION_CONFIG.project_queue_limit
EXECUTION_DRAIN_BATCH = EXECUTION_CONFIG.drain_batch
EXECUTION_SCHEDULER_INTERVAL_SECONDS = EXECUTION_CONFIG.scheduler_interval_seconds
_SCHEDULER_THREAD: threading.Thread | None = None
_SCHEDULER_STOP = threading.Event()


@dataclass(frozen=True)
class ExecutionTextWindowRequest:
    file_size: int | None = None
    max_bytes: int | None = None
    mode: str = "tail"
    offset_bytes: int | None = None
    length_bytes: int | None = None


@dataclass(frozen=True)
class RegistrationRecordBuildSpec:
    request_model: ExecutionRegisterRequest
    root: Path
    target: Path
    sha: str
    commit_id: str


@dataclass(frozen=True)
class RegistrationTargetSpec:
    project_id: str
    artifact_class: str
    logical_name: str
    operation: str
    expected_previous_sha256: str | None


@dataclass(frozen=True)
class ExecutionJobBuildSpec:
    replay_of: str | None
    job_id: str
    stdout_path: Path
    stderr_path: Path


JOB_STATUS_SUBMITTED = "SUBMITTED"
JOB_STATUS_QUEUED = "QUEUED"
JOB_STATUS_STARTING = "STARTING"
JOB_STATUS_RUNNING = "RUNNING"
JOB_STATUS_TERMINATING = "TERMINATING"
JOB_STATUS_COMPLETED = "COMPLETED"
JOB_STATUS_FAILED = "FAILED"
JOB_STATUS_TERMINATED = "TERMINATED"
JOB_STATUS_HOST_PREEMPTED = "HOST_PREEMPTED"

JOB_ACTIVE_STATUSES = frozenset(
    {JOB_STATUS_SUBMITTED, JOB_STATUS_QUEUED, JOB_STATUS_STARTING, JOB_STATUS_RUNNING, JOB_STATUS_TERMINATING}
)
JOB_TERMINAL_STATUSES = frozenset(
    {JOB_STATUS_COMPLETED, JOB_STATUS_FAILED, JOB_STATUS_TERMINATED, JOB_STATUS_HOST_PREEMPTED}
)

_SCHEDULER_STATS_LOCK = threading.RLock()
_SCHEDULER_TELEMETRY = SchedulerTelemetry()


def _scheduler_stat_inc(name: str, amount: int = 1) -> None:
    with _SCHEDULER_STATS_LOCK:
        _SCHEDULER_TELEMETRY.inc(name, amount)


def _scheduler_stat_set(name: str, value: Any) -> None:
    with _SCHEDULER_STATS_LOCK:
        _SCHEDULER_TELEMETRY.set(name, value)


def _scheduler_snapshot() -> JsonObject:
    with _SCHEDULER_STATS_LOCK:
        return _SCHEDULER_TELEMETRY.to_dict()


def _set_job_status(job: ExecutionJobRecord, status: str, stage: str) -> ExecutionJobRecord:
    job.status = status
    job.stage = stage
    return job


class ExecutionRequestError(Exception):
    def __init__(self, error_code: str, message: str, status: int = 400, **extra: Any) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status = status
        self.extra = extra


class ExecutionOverCapacity(ExecutionRequestError):
    def __init__(self, message: str, **extra: Any) -> None:
        super().__init__("EXECUTION_OVER_CAPACITY", message, 429, **extra)


def execution_capabilities() -> JsonObject:
    return ExecutionCapabilitiesEnvelope(
        execution_enabled=True,
        execution_modes=EXECUTION_MODES,
        max_timeout_seconds=_limit_for_wire(None),
        default_timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
        max_stdout_bytes=_limit_for_wire(None),
        max_stderr_bytes=_limit_for_wire(None),
        artifact_registration_enabled=True,
        termination_enabled=True,
        global_concurrency_limit=_limit_for_wire(EXECUTION_GLOBAL_CONCURRENCY),
        per_project_concurrency_limit=_limit_for_wire(EXECUTION_PROJECT_CONCURRENCY),
        global_queue_limit=_limit_for_wire(EXECUTION_GLOBAL_QUEUE_LIMIT),
        per_project_queue_limit=_limit_for_wire(EXECUTION_PROJECT_QUEUE_LIMIT),
        scheduler_interval_seconds=EXECUTION_SCHEDULER_INTERVAL_SECONDS,
        background_scheduler=True,
        scheduler_alive=bool(_SCHEDULER_THREAD and _SCHEDULER_THREAD.is_alive()),
    ).to_dict()


def _error(error_code: str, message: str, status: int, **extra: Any) -> object:
    payload = {"ok": False, "error_code": error_code, "message": message, "time": utc_now()}
    payload.update(extra)
    return jsonify(payload), status


def _job_output_texts(
    job: JsonObject | ExecutionJobRecord, max_bytes: int | None
) -> tuple[str, bool, str, bool]:
    record = _job_record(job)
    stdout_text, stdout_truncated = _tail_text(Path(record.stdout_path), max_bytes)
    stderr_text, stderr_truncated = _tail_text(Path(record.stderr_path), max_bytes)
    return stdout_text, stdout_truncated, stderr_text, stderr_truncated


def _auth() -> object | None:
    try:
        require_valid_api_key(request.headers)
        return None
    except PermissionError as e:
        return _error("UNAUTHORIZED", str(e), 401)


def _jobs_dir(project_id: str) -> Path:
    execution_log_dir = get_project_root(project_id) / "system" / "logs" / "execution"
    execution_log_dir.mkdir(parents=True, exist_ok=True)
    return execution_log_dir


def _job_dir(project_id: str, job_id: str) -> Path:
    job_dir = _jobs_dir(project_id) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_dir


def _job_path(project_id: str, job_id: str) -> Path:
    return _jobs_dir(project_id) / f"{job_id}.json"


def _read_job(project_id: str, job_id: str) -> ExecutionJobRecord:
    p = _job_path(project_id, job_id)
    if not p.exists():
        raise FileNotFoundError("job not found")
    return ExecutionJobRecord.from_dict(safe_json_loads(p.read_text(encoding="utf-8")))


def _write_job(project_id: str, job_id: str, job: ExecutionJobRecord | JsonObject) -> None:
    payload = job.to_dict() if isinstance(job, ExecutionJobRecord) else job
    save_json_atomic(_job_path(project_id, job_id), payload)


def _resolve_cwd(project_id: str, cwd_path: str | None) -> Path:
    return safe_project_cwd(get_project_root(project_id), cwd_path)


def _empty_text_window(
    *, mode: str, requested_bytes: int | None, offset_bytes: int | None = None
) -> tuple[str, bool, TextWindow]:
    return (
        "",
        False,
        TextWindow(
            mode=mode,
            file_size=0,
            requested_bytes=requested_bytes,
            returned_bytes=0,
            offset_bytes=offset_bytes,
        ),
    )


def _read_range_text_window(
    path: Path, request: ExecutionTextWindowRequest
) -> tuple[str, bool, TextWindow]:
    file_size = int(request.file_size or 0)
    start_offset = max(0, int(request.offset_bytes or 0))
    limit = request.length_bytes if request.length_bytes is not None else request.max_bytes
    if limit is None or limit <= 0:
        limit = max(1, file_size - start_offset)
    with path.open("rb") as handle:
        handle.seek(start_offset)
        data = handle.read(limit + 1)
    truncated = len(data) > limit or (start_offset + limit) < file_size
    if truncated:
        data = data[:limit]
    return (
        data.decode("utf-8", errors="replace"),
        truncated,
        TextWindow(
            mode="range",
            file_size=file_size,
            requested_bytes=limit,
            returned_bytes=len(data),
            offset_bytes=start_offset,
        ),
    )


def _read_full_text_window(
    path: Path, *, mode: str, file_size: int
) -> tuple[str, bool, TextWindow]:
    with path.open("rb") as handle:
        data = handle.read()
    return (
        data.decode("utf-8", errors="replace"),
        False,
        TextWindow(
            mode=mode,
            file_size=file_size,
            requested_bytes=None,
            returned_bytes=len(data),
            offset_bytes=0,
        ),
    )


def _read_bounded_text_window(
    path: Path, *, mode: str, file_size: int, max_bytes: int
) -> tuple[str, bool, TextWindow]:
    truncated = file_size > max_bytes
    with path.open("rb") as handle:
        if mode == "tail" and truncated:
            start_offset = max(0, file_size - max_bytes)
            handle.seek(start_offset)
        else:
            start_offset = 0
            handle.seek(0)
        data = handle.read(max_bytes)
    return (
        data.decode("utf-8", errors="replace"),
        truncated,
        TextWindow(
            mode=mode,
            file_size=file_size,
            requested_bytes=max_bytes,
            returned_bytes=len(data),
            offset_bytes=start_offset,
        ),
    )


def _normalized_text_window_request(
    options: JsonObject, file_size: int
) -> ExecutionTextWindowRequest:
    request = ExecutionTextWindowRequest(
        max_bytes=options.get("max_bytes"),
        mode=options.get("mode", "tail"),
        offset_bytes=options.get("offset_bytes"),
        length_bytes=options.get("length_bytes"),
    )
    mode = (request.mode or "tail").strip().lower()
    if mode not in {"tail", "head", "range", "all"}:
        mode = "tail"
    return ExecutionTextWindowRequest(
        file_size=file_size,
        max_bytes=None if mode == "all" else request.max_bytes,
        mode=mode,
        offset_bytes=request.offset_bytes,
        length_bytes=request.length_bytes,
    )


def _read_text_window(path: Path, **options: Any) -> tuple[str, bool, TextWindow]:
    if not path.exists():
        return _empty_text_window(
            mode=options.get("mode", "tail"),
            requested_bytes=options.get("max_bytes"),
            offset_bytes=options.get("offset_bytes"),
        )
    size = path.stat().st_size
    if size <= 0:
        return _empty_text_window(
            mode=options.get("mode", "tail"),
            requested_bytes=options.get("max_bytes"),
            offset_bytes=options.get("offset_bytes"),
        )
    request = _normalized_text_window_request(options, size)
    if request.mode == "range":
        return _read_range_text_window(path, request)
    if request.max_bytes is None or request.max_bytes <= 0:
        return _read_full_text_window(path, mode=request.mode, file_size=size)
    return _read_bounded_text_window(
        path, mode=request.mode, file_size=size, max_bytes=request.max_bytes
    )


def _tail_text(path: Path, max_bytes: int | None) -> tuple[str, bool]:
    text, truncated, _meta = _read_text_window(path, max_bytes=max_bytes, mode="tail")
    return text, truncated


def _job_record(job: JsonObject | ExecutionJobRecord) -> ExecutionJobRecord:
    return job if isinstance(job, ExecutionJobRecord) else ExecutionJobRecord.from_dict(job)


def _job_identity(job: JsonObject | ExecutionJobRecord) -> tuple[str, str]:
    record = _job_record(job)
    return record.project_id, record.job_id


def _failure_digest(
    job: JsonObject | ExecutionJobRecord, failure_kind: str, retryable: bool = False, **extra: Any
) -> ExecutionFailureDigest:
    record = _job_record(job)
    signal = record.extra.get("signal") if isinstance(record.extra, dict) else None
    return ExecutionFailureDigest(
        job_id=record.job_id,
        project_id=record.project_id,
        failure_kind=failure_kind,
        execution_state=record.status,
        stage=record.stage or "runtime",
        host_preempted=failure_kind == "HOST_PREEMPT",
        exit_code=record.return_code,
        signal=str(signal) if signal is not None else None,
        artifact_registration_status=record.artifact_registration_status,
        time_started=record.started_at,
        time_ended=record.finished_at,
        duration_ms=record.duration_ms,
        retryable=retryable,
        extra=extra,
    )


def _compute_duration_ms(job: JsonObject | ExecutionJobRecord) -> int | None:
    try:
        from datetime import datetime

        record = _job_record(job)
        if record.started_at and record.finished_at:
            a = datetime.fromisoformat(record.started_at)
            b = datetime.fromisoformat(record.finished_at)
            return max(0, int((b - a).total_seconds() * 1000))
    except (TypeError, ValueError, OverflowError):
        return None
    return None


def _append_job_journal(
    project_id: str, title: str, content: str, entry_type: str = "session_trace"
) -> None:
    path = get_project_root(project_id) / "system" / "journal" / "journal.jsonl"
    append_jsonl(
        path,
        {
            "time": utc_now(),
            "entry_type": entry_type,
            "title": title,
            "content": content,
            "tags": ["execution"],
        },
    )


def _update_manifest_entry(project_id: str, target: Path, artifact_class: str) -> None:
    manifest_path = manifest_path_for(project_id)
    manifest = load_json(manifest_path, {"updated_at": None, "files": {}})
    rel = str(target.relative_to(get_project_root(project_id)))
    manifest["files"][rel] = {
        "artifact_class": artifact_class,
        "sha256": sha256_file(target),
        "bytes": target.stat().st_size,
        "updated_at": utc_now(),
    }
    manifest["updated_at"] = utc_now()
    save_json_atomic(manifest_path, manifest)


def _record_commit(project_id: str, record: Any) -> None:
    append_jsonl(commits_ledger_path_for(project_id), record)


def _execution_idempotency_path(project_id: str) -> Path:
    return _jobs_dir(project_id) / "idempotency.json"


def _load_execution_idempotency(project_id: str) -> ExecutionIdempotencyLedger:
    return ExecutionIdempotencyLedger.from_dict(
        load_json(_execution_idempotency_path(project_id), {"keys": {}})
    )


def _save_execution_idempotency(project_id: str, data: ExecutionIdempotencyLedger) -> None:
    save_json_atomic(_execution_idempotency_path(project_id), data.to_dict())


def _payload_fingerprint(payload: ExecutionSubmitPayload) -> str:
    material = {
        "project_id": payload.project_id,
        "execution_mode": payload.execution_mode,
        "command": payload.command,
        "cwd": payload.cwd,
        "timeout_seconds": payload.timeout_seconds,
        "stdout_max_bytes": payload.stdout_max_bytes,
        "stderr_max_bytes": payload.stderr_max_bytes,
        "env_allowlist": payload.env_allowlist,
        "result_artifact_targets": payload.result_artifact_targets,
        "local_model_id": payload.local_model_id,
        "agent_role": payload.agent_role,
        "replay_of": payload.replay_of,
    }
    raw = safe_json_dumps(material)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _pid_alive(pid: Any) -> bool:
    try:
        pid_int = int(pid)
    except (TypeError, ValueError, OverflowError):
        return False
    if pid_int <= 0:
        return False
    try:
        os.kill(pid_int, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _iter_job_files(project_id: str | None = None) -> Any:
    if project_id:
        yield from _jobs_dir(project_id).glob("*.json")
        return
    if not PROJECTS_ROOT.exists():
        return
    for project_dir in PROJECTS_ROOT.iterdir():
        jobs_dir = project_dir / "system" / "logs" / "execution"
        if not jobs_dir.exists():
            continue
        yield from jobs_dir.glob("*.json")


def _load_job_file(path: Path) -> tuple[ExecutionJobRecord | None, str | None]:
    try:
        return ExecutionJobRecord.from_dict(safe_json_loads(path.read_text(encoding="utf-8"))), None
    except (OSError, ValueError, TypeError) as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _effective_running_count(project_id: str | None = None) -> int:
    seen: set[str] = set()
    count = 0
    with _RUNNING_LOCK:
        for job_id, proc in list(_RUNNING.items()):
            if proc.poll() is None:
                if project_id is None or _job_belongs_to_project(job_id, project_id):
                    count += 1
                    seen.add(job_id)
    for path in _iter_job_files(project_id):
        job, _ = _load_job_file(path)
        if not job:
            continue
        job_id = job.job_id
        if not job_id or job_id in seen:
            continue
        if job.status != "RUNNING":
            continue
        if _pid_alive(job.pid):
            count += 1
    return count


def _effective_queue_count(project_id: str | None = None) -> int:
    count = 0
    for path in _iter_job_files(project_id):
        job, _ = _load_job_file(path)
        if job and job.status == "QUEUED":
            count += 1
    return count


def _job_belongs_to_project(job_id: str, project_id: str) -> bool:
    try:
        job = _read_job(project_id, job_id)
    except (TypeError, ValueError, OverflowError):
        return False
    return _job_record(job).project_id == project_id


def _capacity_snapshot(project_id: str) -> CapacitySnapshot:
    return CapacitySnapshot(
        running_global=_effective_running_count(None),
        running_project=_effective_running_count(project_id),
        global_limit=EXECUTION_GLOBAL_CONCURRENCY,
        project_limit=EXECUTION_PROJECT_CONCURRENCY,
        queued_global=_effective_queue_count(None),
        queued_project=_effective_queue_count(project_id),
        global_queue_limit=_limit_for_wire(EXECUTION_GLOBAL_QUEUE_LIMIT),
        project_queue_limit=EXECUTION_PROJECT_QUEUE_LIMIT,
    )


def _readiness_queue_age(job: ExecutionJobRecord, now_epoch: float) -> float | None:
    if job.status != JOB_STATUS_QUEUED:
        return None
    try:
        from datetime import datetime

        submitted = datetime.fromisoformat(str(job.submitted_at)).timestamp()
        return max(0.0, now_epoch - submitted)
    except (TypeError, ValueError, OverflowError):
        return None


def _readiness_scan_jobs() -> (
    tuple[dict[str, CapacitySnapshot], list[str], list[str], float | None]
):
    per_project: dict[str, CapacitySnapshot] = {}
    corrupt_job_files: list[str] = []
    unsupervised_jobs: list[str] = []
    oldest_queued_age_seconds: float | None = None
    now_epoch = time.time()
    for path in _iter_job_files(None):
        job, error = _load_job_file(path)
        if error:
            corrupt_job_files.append(str(path))
            continue
        if not job:
            continue
        project_id = job.project_id.strip()
        if project_id and project_id not in per_project:
            per_project[project_id] = _capacity_snapshot(project_id)
        if job.status == JOB_STATUS_RUNNING and not _pid_alive(job.pid):
            unsupervised_jobs.append(str(job.job_id))
        age = _readiness_queue_age(job, now_epoch)
        oldest_queued_age_seconds = _max_optional_age(oldest_queued_age_seconds, age)
    return per_project, corrupt_job_files, unsupervised_jobs, oldest_queued_age_seconds


def _max_optional_age(current: float | None, candidate: float | None) -> float | None:
    if candidate is None:
        return current
    return candidate if current is None else max(current, candidate)


def _readiness_global_snapshot(oldest_queued_age_seconds: float | None) -> GlobalExecutionSnapshot:
    return GlobalExecutionSnapshot(
        running=_effective_running_count(None),
        queued=_effective_queue_count(None),
        global_limit=_limit_for_wire(EXECUTION_GLOBAL_CONCURRENCY),
        global_queue_limit=_limit_for_wire(EXECUTION_GLOBAL_QUEUE_LIMIT),
        oldest_queued_age_seconds=oldest_queued_age_seconds,
    )


def execution_readiness() -> JsonObject:
    # Readiness is observational. Do not serialize unrelated project mutations behind
    # a whole-tree diagnostic scan; tolerate a point-in-time eventually consistent view.
    per_project, corrupt_job_files, unsupervised_jobs, oldest_age = _readiness_scan_jobs()
    global_snapshot = _readiness_global_snapshot(oldest_age)
    telemetry = SchedulerTelemetry(**_scheduler_snapshot())
    status = (
        "degraded" if corrupt_job_files or unsupervised_jobs or telemetry.last_error else "online"
    )
    return ExecutionReadinessEnvelope(
        status=status,
        global_snapshot=global_snapshot,
        per_project=per_project,
        corrupt_job_files=corrupt_job_files,
        unsupervised_jobs=unsupervised_jobs,
        drain_batch=_limit_for_wire(EXECUTION_DRAIN_BATCH),
        scheduler_thread_alive=bool(_SCHEDULER_THREAD and _SCHEDULER_THREAD.is_alive()),
        scheduler_telemetry=telemetry,
    ).to_dict()


def _can_start_now(project_id: str) -> bool:
    snap = _capacity_snapshot(project_id)
    return (snap.global_limit is None or snap.running_global < snap.global_limit) and (
        snap.project_limit is None or snap.running_project < snap.project_limit
    )


def _queue_allowed(project_id: str) -> bool:
    snap = _capacity_snapshot(project_id)
    return (snap.global_queue_limit is None or snap.queued_global < snap.global_queue_limit) and (
        snap.project_queue_limit is None or snap.queued_project < snap.project_queue_limit
    )


def _worker_paths(job: ExecutionJobRecord) -> dict[str, Path]:
    root = _job_dir(job.project_id, job.job_id)
    return {
        "request": root / "worker_request.json",
        "heartbeat": root / "worker_heartbeat.json",
        "completion": root / "worker_completion.json",
        "cancel": root / "worker_cancel.request.json",
        "ownership_release": root / "worker_ownership.release.json",
        "control_stdout": root / "worker_control.stdout.log",
        "control_stderr": root / "worker_control.stderr.log",
    }


def _load_worker_receipt(job: ExecutionJobRecord, path_value: str | None) -> JsonObject | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.is_file():
        return None
    try:
        payload = safe_json_loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    if str(payload.get("job_id") or "") != job.job_id:
        return None
    if not job.worker_token or str(payload.get("worker_token") or "") != job.worker_token:
        return None
    return payload


def _heartbeat_fresh(payload: JsonObject | None, *, grace_seconds: float = 3.0) -> bool:
    if not payload:
        return False
    try:
        from datetime import datetime, timezone
        stamp = datetime.fromisoformat(str(payload.get("heartbeat_at") or "").replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            return False
        age = (datetime.now(timezone.utc) - stamp.astimezone(timezone.utc)).total_seconds()
        return -1.0 <= age <= grace_seconds
    except (TypeError, ValueError, OverflowError):
        return False


def _write_worker_request(job: ExecutionJobRecord) -> Path:
    paths = _worker_paths(job)
    token = uuid.uuid4().hex
    job.worker_token = token
    job.worker_request_path = str(paths["request"])
    job.worker_heartbeat_path = str(paths["heartbeat"])
    job.worker_completion_path = str(paths["completion"])
    job.worker_cancel_path = str(paths["cancel"])
    job.worker_ownership_release_path = str(paths["ownership_release"])
    for key in ("heartbeat", "completion", "cancel", "ownership_release"):
        paths[key].unlink(missing_ok=True)
    save_json_atomic(
        paths["request"],
        {
            "job_id": job.job_id,
            "worker_token": token,
            "command": list(job.command),
            "cwd": job.cwd,
            "env_allowlist": dict(job.env_allowlist),
            "stdout_path": job.stdout_path,
            "stderr_path": job.stderr_path,
            "heartbeat_path": job.worker_heartbeat_path,
            "completion_path": job.worker_completion_path,
            "cancel_path": job.worker_cancel_path,
            "ownership_release_path": job.worker_ownership_release_path,
            "job_object_name": job.job_object_name,
            "timeout_seconds": job.timeout_seconds,
        },
    )
    return paths["request"]


def _wait_for_ownership_ready(job: ExecutionJobRecord, proc: Any, timeout_seconds: float = 6.0) -> JsonObject:
    deadline = time.monotonic() + max(0.5, float(timeout_seconds))
    last: JsonObject | None = None
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"worker exited before ownership handshake rc={proc.returncode}")
        receipt = _load_worker_receipt(job, job.worker_heartbeat_path)
        if receipt is not None:
            last = receipt
            if str(receipt.get("state") or "").upper() == "OWNERSHIP_READY" and _heartbeat_fresh(receipt):
                return receipt
        time.sleep(0.03)
    raise RuntimeError(f"worker ownership handshake timeout; last={last}")


def _spawn_job(job: ExecutionJobRecord) -> ExecutionJobRecord:
    job_handle = None
    proc = None
    if os.name == "nt":
        if _wjo is None:
            raise RuntimeError("Windows Job Object support unavailable")
        job.job_object_name = f"Local\\PCMMAD_EXEC_{job.job_id}"
        job_handle = _wjo.create_named_job(job.job_object_name)
        _wjo.set_kill_on_close(job_handle, True)
    try:
        request_path = _write_worker_request(job)
        paths = _worker_paths(job)
        out_f = paths["control_stdout"].open("ab")
        err_f = paths["control_stderr"].open("ab")
        try:
            proc = start_background_process(
                [sys.executable, str(Path(__file__).with_name("execution_worker.py")), str(request_path)],
                cwd=_job_dir(job.project_id, job.job_id),
                stdout=out_f,
                stderr=err_f,
                env=os.environ.copy(),
            )
        finally:
            out_f.close()
            err_f.close()

        job.worker_launcher_pid = int(proc.pid)
        if job_handle is not None:
            _wjo.assign_pid(job_handle, proc.pid)
            receipt = _wait_for_ownership_ready(job, proc)
            actual_worker_pid = int(receipt.get("worker_pid") or 0)
            if actual_worker_pid <= 0:
                raise RuntimeError("ownership heartbeat missing actual worker PID")
            member_pids = set(_wjo.query_process_ids(job_handle))
            if actual_worker_pid not in member_pids:
                raise RuntimeError(
                    f"ownership heartbeat PID {actual_worker_pid} is not a member of {job.job_object_name}"
                )
            job.worker_pid = actual_worker_pid
            job.worker_creation_time_100ns = _wjo.process_creation_time_100ns(actual_worker_pid)
            save_json_atomic(
                Path(str(job.worker_ownership_release_path)),
                {
                    "job_id": job.job_id,
                    "worker_token": job.worker_token,
                    "worker_launcher_pid": int(proc.pid),
                    "worker_pid": actual_worker_pid,
                    "worker_creation_time_100ns": job.worker_creation_time_100ns,
                    "permit_spawn": True,
                    "released_at": utc_now(),
                },
            )
        else:
            job.worker_pid = int(proc.pid)

        with _RUNNING_LOCK:
            _RUNNING[job.job_id] = proc
        _set_job_status(job, JOB_STATUS_RUNNING, "ownership_released" if job_handle is not None else "worker_starting")
        job.started_at = utc_now()
        job.deadline_epoch = (
            (time.time() + int(job.timeout_seconds)) if job.timeout_seconds else None
        )
        job.pid = None
        job.supervision_state = "job_object_anchor" if job_handle is not None else "worker_capsule"
        job.queue_position = None
        return job
    except Exception:
        if job_handle is not None:
            try:
                _wjo.terminate(job_handle, exit_code=9)
            except Exception:
                pass
        if proc is not None and proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass
        raise
    finally:
        if job_handle is not None:
            try:
                job_handle.close()
            except Exception:
                pass


def _validated_execution_mode(value: Any, *, override: str | None = None) -> str:
    execution_mode = override or str(value or "one_shot")
    if execution_mode not in EXECUTION_MODES:
        raise ExecutionRequestError("INVALID_EXECUTION_MODE", "invalid execution_mode", 400)
    return execution_mode


def _validated_command_and_args(command: Any, args: Any) -> list[str]:
    if (
        not isinstance(command, list)
        or not command
        or not all(isinstance(x, str) and x for x in command)
    ):
        raise ExecutionRequestError("BAD_REQUEST", "command must be a non-empty string array", 400)
    if not isinstance(args, list) or not all(isinstance(x, str) for x in args):
        raise ExecutionRequestError("BAD_REQUEST", "args must be a string array", 400)
    return list(command) + list(args)


def _validated_output_limits(data: JsonObject) -> tuple[int | None, int | None, int | None]:
    timeout_seconds = _request_optional_positive_int(
        data.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS),
        DEFAULT_TIMEOUT_SECONDS,
        minimum=1,
        maximum=MAX_TIMEOUT_SECONDS,
    )
    stdout_max_bytes = _request_optional_positive_int(
        data.get("stdout_max_bytes", DEFAULT_STDOUT_MAX_BYTES),
        DEFAULT_STDOUT_MAX_BYTES,
        minimum=1024,
        maximum=MAX_OUTPUT_BYTES,
    )
    stderr_max_bytes = _request_optional_positive_int(
        data.get("stderr_max_bytes", DEFAULT_STDERR_MAX_BYTES),
        DEFAULT_STDERR_MAX_BYTES,
        minimum=1024,
        maximum=MAX_OUTPUT_BYTES,
    )
    return timeout_seconds, stdout_max_bytes, stderr_max_bytes


def _validated_env_allowlist(value: Any) -> dict[str, str]:
    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise ExecutionRequestError("BAD_REQUEST", "env_allowlist must be an object", 400)
    return {
        str(key): str(item)
        for key, item in value.items()
        if isinstance(key, str) and isinstance(item, str)
    }


def _validated_result_artifact_targets(value: Any) -> list[object]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ExecutionRequestError("BAD_REQUEST", "result_artifact_targets must be an array", 400)
    return list(value)


def _validated_journal_flags(data: JsonObject) -> dict[str, bool]:
    return {
        "journal_on_submit": bool(data.get("journal_on_submit", True)),
        "journal_on_complete": bool(data.get("journal_on_complete", False)),
        "journal_on_failure": bool(data.get("journal_on_failure", True)),
        "checkpoint_on_complete": bool(data.get("checkpoint_on_complete", False)),
    }


def _submit_payload_args(
    data: JsonObject, execution_mode_override: str | None
) -> tuple[str, str, list[str], tuple[int | None, int | None, int | None]]:
    project_id = str(data.get("project_id", ""))
    execution_mode = _validated_execution_mode(
        data.get("execution_mode"), override=execution_mode_override
    )
    command = _validated_command_and_args(data.get("command"), data.get("args") or [])
    return project_id, execution_mode, command, _validated_output_limits(data)


def _submit_payload_metadata(
    data: JsonObject, default_idempotency_key: str | None
) -> tuple[str | None, str | None, str]:
    local_model_id = data.get("local_model_id")
    agent_role = data.get("agent_role")
    idempotency_key = str(data.get("idempotency_key") or default_idempotency_key or "").strip()
    return (
        str(local_model_id) if local_model_id is not None else None,
        str(agent_role) if agent_role is not None else None,
        idempotency_key,
    )


def _submit_payload_core(
    data: JsonObject, execution_mode_override: str | None
) -> tuple[str, str, list[str], tuple[int | None, int | None, int | None], str]:
    project_id, execution_mode, command, output_limits = _submit_payload_args(
        data, execution_mode_override
    )
    try:
        cwd = _resolve_cwd(project_id, data.get("cwd"))
    except (OSError, ValueError, TypeError) as e:
        raise ExecutionRequestError("WORKDIR_INVALID", str(e), 400) from e
    return project_id, execution_mode, command, output_limits, str(cwd)


def _submit_payload_limits(
    core: tuple[str, str, list[str], tuple[int | None, int | None, int | None], str],
) -> tuple[int | None, int | None, int | None]:
    return core[3]


def _submit_payload_record_kwargs(
    data: JsonObject,
    replay_of: str | None,
    default_idempotency_key: str | None,
    core: tuple[str, str, list[str], tuple[int | None, int | None, int | None], str],
) -> JsonObject:
    project_id, execution_mode, command, _output_limits, cwd = core
    timeout_seconds, stdout_max_bytes, stderr_max_bytes = _submit_payload_limits(core)
    local_model_id, agent_role, idempotency_key = _submit_payload_metadata(
        data, default_idempotency_key
    )
    return {
        "project_id": project_id,
        "execution_mode": execution_mode,
        "command": command,
        "cwd": cwd,
        "cwd_rel": str(data.get("cwd") or "."),
        "timeout_seconds": timeout_seconds,
        "stdout_max_bytes": stdout_max_bytes,
        "stderr_max_bytes": stderr_max_bytes,
        "env_allowlist": _validated_env_allowlist(data.get("env_allowlist")),
        "result_artifact_targets": _validated_result_artifact_targets(
            data.get("result_artifact_targets")
        ),
        "local_model_id": local_model_id,
        "agent_role": agent_role,
        "idempotency_key": idempotency_key,
        "replay_of": replay_of,
    }


def _submit_payload_record(
    data: JsonObject,
    replay_of: str | None,
    default_idempotency_key: str | None,
    core: tuple[str, str, list[str], tuple[int | None, int | None, int | None], str],
) -> ExecutionSubmitPayload:
    payload_kwargs = _submit_payload_record_kwargs(data, replay_of, default_idempotency_key, core)
    return ExecutionSubmitPayload(**payload_kwargs, **_validated_journal_flags(data))


def _normalize_submit_payload(
    data: JsonObject,
    *,
    execution_mode_override: str | None = None,
    replay_of: str | None = None,
    default_idempotency_key: str | None = None,
) -> ExecutionSubmitPayload:
    core = _submit_payload_core(data, execution_mode_override)
    payload = _submit_payload_record(data, replay_of, default_idempotency_key, core)
    object.__setattr__(payload, "submission_fingerprint", _payload_fingerprint(payload))
    return payload


def _resolve_existing_idempotent_job(payload: ExecutionSubmitPayload) -> ExecutionJobRecord | None:
    idempotency_key = payload.idempotency_key
    if not idempotency_key:
        return None
    ledger = _load_execution_idempotency(payload.project_id)
    existing = ledger.keys.get(idempotency_key)
    if not existing:
        return None
    if existing.submission_fingerprint != payload.submission_fingerprint:
        raise ExecutionRequestError(
            "IDEMPOTENCY_KEY_CONFLICT",
            "idempotency_key already used for a different execution payload",
            409,
            existing_job_id=existing.job_id,
        )
    existing_job_id = str(existing.job_id)
    if not existing_job_id:
        return None
    job = _read_job(payload.project_id, existing_job_id)
    job = _finalize(payload.project_id, existing_job_id, job)
    job.replayed = True
    return job


def _execution_job_flags(payload: ExecutionSubmitPayload) -> JsonObject:
    return {
        "journal_on_submit": payload.journal_on_submit,
        "journal_on_complete": payload.journal_on_complete,
        "journal_on_failure": payload.journal_on_failure,
        "checkpoint_on_complete": payload.checkpoint_on_complete,
    }


def _execution_job_identity_kwargs(
    payload: ExecutionSubmitPayload, spec: ExecutionJobBuildSpec
) -> JsonObject:
    return {
        "project_id": payload.project_id,
        "job_id": spec.job_id,
        "execution_mode": payload.execution_mode,
        "replay_of": spec.replay_of,
        "command": payload.command,
        "cwd": payload.cwd,
        "cwd_rel": payload.cwd_rel,
    }


def _execution_job_runtime_kwargs(
    payload: ExecutionSubmitPayload, spec: ExecutionJobBuildSpec
) -> JsonObject:
    return {
        "status": JOB_STATUS_SUBMITTED,
        "stage": "submit",
        "submitted_at": utc_now(),
        "started_at": None,
        "deadline_epoch": None,
        "timeout_seconds": payload.timeout_seconds,
        "stdout_path": str(spec.stdout_path),
        "stderr_path": str(spec.stderr_path),
        "stdout_max_bytes": payload.stdout_max_bytes,
        "stderr_max_bytes": payload.stderr_max_bytes,
        "result_artifact_targets": payload.result_artifact_targets,
    }


def _execution_job_control_kwargs(payload: ExecutionSubmitPayload) -> JsonObject:
    return {
        "artifact_registration_status": "not_attempted",
        "truth_gate": "not_evaluated",
        "resource_gate": "not_evaluated",
        "feasibility_gate": "not_evaluated",
        "journal_on_submit": payload.journal_on_submit,
        "journal_on_complete": payload.journal_on_complete,
        "journal_on_failure": payload.journal_on_failure,
        "checkpoint_on_complete": payload.checkpoint_on_complete,
        "local_model_id": payload.local_model_id,
        "agent_role": payload.agent_role,
        "idempotency_key": payload.idempotency_key,
        "submission_fingerprint": payload.submission_fingerprint,
        "env_allowlist": payload.env_allowlist,
        "queue_position": None,
    }


def _execution_job_kwargs(
    payload: ExecutionSubmitPayload, spec: ExecutionJobBuildSpec
) -> JsonObject:
    return {
        **_execution_job_identity_kwargs(payload, spec),
        **_execution_job_runtime_kwargs(payload, spec),
        **_execution_job_control_kwargs(payload),
    }


def _build_execution_job(
    payload: ExecutionSubmitPayload, spec: ExecutionJobBuildSpec
) -> ExecutionJobRecord:
    return ExecutionJobRecord(**_execution_job_kwargs(payload, spec))


def _spawn_or_queue_job(job: ExecutionJobRecord) -> ExecutionJobRecord:
    project_id = job.project_id
    if _can_start_now(project_id):
        try:
            return _spawn_job(job)
        except (OSError, RuntimeError, ValueError, TypeError) as e:
            _set_job_status(job, JOB_STATUS_FAILED, "spawn_failure")
            job.finished_at = utc_now()
            job.failure_digest = _failure_digest(
                job, "SPAWN_FAILURE", retryable=False, stderr_excerpt=str(e), stdout_excerpt=""
            )
            _write_job(project_id, job.job_id, job)
            raise ExecutionRequestError(
                "SPAWN_FAILURE", str(e), 500, failure_digest=job.failure_digest
            ) from e
    if not _queue_allowed(project_id):
        raise ExecutionOverCapacity(
            "execution queue is full; refusing new work instead of oversubscribing the host",
            capacity=_capacity_snapshot(project_id),
        )
    job.status = JOB_STATUS_QUEUED
    job.stage = "queued"
    job.queue_position = _effective_queue_count(project_id) + 1
    return job


def _journal_job_submission(job: ExecutionJobRecord) -> None:
    if job.journal_on_submit:
        title = f"execution {job.status.lower()} {job.job_id}"
        content = f"Mode={job.execution_mode} Command={' '.join(job.command)}"
        _append_job_journal(job.project_id, title, content)


def _persist_idempotency_key(payload: ExecutionSubmitPayload, job_id: str) -> None:
    if not payload.idempotency_key:
        return
    ledger = _load_execution_idempotency(payload.project_id)
    ledger.keys[payload.idempotency_key] = ExecutionIdempotencyRecord(
        job_id=job_id,
        submission_fingerprint=payload.submission_fingerprint,
        recorded_at=utc_now(),
    )
    _save_execution_idempotency(payload.project_id, ledger)


def _prior_cwd_rel(prior: ExecutionJobRecord, project_id: str) -> str:
    if not prior.cwd:
        return "."
    try:
        return Path(prior.cwd).relative_to(get_project_root(project_id)).as_posix()
    except (ValueError, OSError, TypeError):
        return prior.cwd_rel or "."


def _replay_limits(
    prior: ExecutionJobRecord, replay: ExecutionReplayRequest
) -> tuple[int | None, int | None, int | None]:
    return (
        (
            replay.timeout_seconds
            if replay.timeout_seconds is not None
            else prior.timeout_seconds or DEFAULT_TIMEOUT_SECONDS
        ),
        (
            replay.stdout_max_bytes
            if replay.stdout_max_bytes is not None
            else prior.stdout_max_bytes or DEFAULT_STDOUT_MAX_BYTES
        ),
        (
            replay.stderr_max_bytes
            if replay.stderr_max_bytes is not None
            else prior.stderr_max_bytes or DEFAULT_STDERR_MAX_BYTES
        ),
    )


def _build_replay_submission_data(
    prior: ExecutionJobRecord,
    replay: ExecutionReplayRequest,
    project_id: str,
) -> JsonObject:
    timeout_seconds, stdout_max_bytes, stderr_max_bytes = _replay_limits(prior, replay)
    return {
        "project_id": project_id,
        "command": list(prior.command),
        "args": [],
        "execution_mode": "replay",
        "cwd": _prior_cwd_rel(prior, project_id),
        "timeout_seconds": timeout_seconds,
        "stdout_max_bytes": stdout_max_bytes,
        "stderr_max_bytes": stderr_max_bytes,
        "env_allowlist": replay.env_allowlist,
        "result_artifact_targets": replay.result_artifact_targets or prior.result_artifact_targets,
        "journal_on_submit": replay.journal_on_submit,
        "journal_on_complete": replay.journal_on_complete,
        "journal_on_failure": replay.journal_on_failure,
        "local_model_id": replay.local_model_id or prior.local_model_id,
        "agent_role": replay.agent_role or prior.agent_role,
        "idempotency_key": replay.idempotency_key,
    }


def _new_execution_job_spec(
    payload: ExecutionSubmitPayload, replay_of: str | None
) -> ExecutionJobBuildSpec:
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    job_dir = _job_dir(payload.project_id, job_id)
    return ExecutionJobBuildSpec(
        job_id=job_id,
        replay_of=replay_of,
        stdout_path=job_dir / "stdout.log",
        stderr_path=job_dir / "stderr.log",
    )


def _submit_job_locked(
    payload: ExecutionSubmitPayload, replay_of: str | None
) -> ExecutionJobRecord:
    existing = _resolve_existing_idempotent_job(payload)
    if existing is not None:
        return existing
    spec = _new_execution_job_spec(payload, replay_of)
    job = _spawn_or_queue_job(_build_execution_job(payload, spec))
    _journal_job_submission(job)
    _write_job(payload.project_id, spec.job_id, job)
    _ensure_scheduler_started()
    _persist_idempotency_key(payload, spec.job_id)
    started = _drain_queue_locked(payload.project_id)
    if started and job.status == JOB_STATUS_QUEUED:
        job = _read_job(payload.project_id, spec.job_id)
    job.replayed = False
    return job


def submit_execution_job(
    data: JsonObject,
    *,
    execution_mode_override: str | None = None,
    replay_of: str | None = None,
    default_idempotency_key: str | None = None,
) -> ExecutionJobRecord:
    payload = _normalize_submit_payload(
        data,
        execution_mode_override=execution_mode_override,
        replay_of=replay_of,
        default_idempotency_key=default_idempotency_key,
    )
    with _ADMISSION_LOCK:
        _ensure_scheduler_started()
        return _submit_job_locked(payload, replay_of)


def _running_census() -> tuple[int, dict[str, int]]:
    """Return effective global/per-project running counts from one durable-tree pass.

    Preserve the existing capacity semantics: live managed processes count even when
    their durable record is transiently stale, while durable RUNNING records not
    represented in `_RUNNING` are counted only when their PID is alive. Global job
    IDs are deduplicated independently from per-project counts.
    """
    managed_alive: set[str] = set()
    with _RUNNING_LOCK:
        for job_id, proc in list(_RUNNING.items()):
            if proc.poll() is None:
                managed_alive.add(job_id)

    global_seen: set[str] = set(managed_alive)
    per_project_seen: dict[str, set[str]] = {}
    per_project: dict[str, int] = {}
    total = len(global_seen)

    for path in _iter_job_files(None):
        job, _ = _load_job_file(path)
        if not job:
            continue
        job_id = str(job.job_id or "")
        if not job_id:
            continue
        managed = job_id in managed_alive
        durable_alive = job.status == JOB_STATUS_RUNNING and _pid_alive(job.pid)
        if not managed and not durable_alive:
            continue

        if job_id not in global_seen:
            global_seen.add(job_id)
            total += 1

        project_key = str(job.project_id or "")
        if not project_key:
            continue
        seen = per_project_seen.setdefault(project_key, set())
        if job_id in seen:
            continue
        seen.add(job_id)
        per_project[project_key] = per_project.get(project_key, 0) + 1

    return total, per_project


def _queued_job_candidates(project_id: str | None = None) -> list[tuple[str, str, str]]:
    """Discover queued jobs without holding the global admission lock."""
    queued: list[tuple[str, str, str]] = []
    for path in _iter_job_files(project_id):
        job, _ = _load_job_file(path)
        if not job or job.status != JOB_STATUS_QUEUED:
            continue
        queued.append((str(job.submitted_at or ""), str(job.project_id or ""), str(job.job_id or "")))
    queued.sort(key=lambda item: item)
    return queued


def _drain_queue_locked(
    project_id: str | None = None, *, limit: int | None = EXECUTION_DRAIN_BATCH,
    candidates: list[tuple[str, str, str]] | None = None,
) -> list[str]:
    # Candidate discovery is intentionally outside the admission critical section when
    # callers can provide a snapshot. Capacity itself must be established while the
    # admission lock is held, but one census is enough for the entire drain pass.
    queued_jobs = candidates if candidates is not None else _queued_job_candidates(project_id)
    started: list[str] = []
    running_global, running_per_project = _running_census()
    global_limit = EXECUTION_GLOBAL_CONCURRENCY
    project_limit = EXECUTION_PROJECT_CONCURRENCY

    for _, pid, job_id in queued_jobs:
        if limit is not None and len(started) >= limit:
            break
        if global_limit is not None and running_global >= global_limit:
            break
        if not pid or not job_id:
            continue
        if project_limit is not None and running_per_project.get(pid, 0) >= project_limit:
            continue
        try:
            job = _read_job(pid, job_id)
        except FileNotFoundError:
            continue
        if job.status != JOB_STATUS_QUEUED:
            continue
        try:
            job = _spawn_job(job)
            _write_job(pid, job.job_id, job)
            started.append(job.job_id)
            running_global += 1
            running_per_project[pid] = running_per_project.get(pid, 0) + 1
        except (OSError, RuntimeError, ValueError, TypeError) as e:
            _set_job_status(job, JOB_STATUS_FAILED, "spawn")
            job.finished_at = utc_now()
            job.failure_digest = _failure_digest(
                job, "SPAWN_FAILURE", retryable=False, stderr_excerpt=str(e), stdout_excerpt=""
            )
            _write_job(pid, job.job_id, job)
    return started


def _drain_queue(
    project_id: str | None = None, *, limit: int | None = EXECUTION_DRAIN_BATCH
) -> list[str]:
    candidates = _queued_job_candidates(project_id)
    with _ADMISSION_LOCK:
        return _drain_queue_locked(project_id, limit=limit, candidates=candidates)


def _mark_job_unsupervised(
    project_id: str, job_id: str, job: ExecutionJobRecord
) -> ExecutionJobRecord:
    job.supervision_state = "unsupervised"
    job.stage = "runtime_unsupervised"
    _write_job(project_id, job_id, job)
    return job


def _job_failure_excerpt(job: ExecutionJobRecord) -> tuple[str, str]:
    stderr_excerpt, _ = _tail_text(Path(job.stderr_path), 2048)
    stdout_excerpt, _ = _tail_text(Path(job.stdout_path), 2048)
    return stderr_excerpt, stdout_excerpt


def _mark_supervision_lost(
    project_id: str, job_id: str, job: ExecutionJobRecord
) -> ExecutionJobRecord:
    _set_job_status(job, JOB_STATUS_FAILED, "supervision_lost")
    job.finished_at = job.finished_at or utc_now()
    job.duration_ms = _compute_duration_ms(job)
    stderr_excerpt, stdout_excerpt = _job_failure_excerpt(job)
    job.failure_digest = _failure_digest(
        job,
        "SUPERVISION_LOST",
        retryable=True,
        stderr_excerpt=stderr_excerpt,
        stdout_excerpt=stdout_excerpt,
    )
    _write_job(project_id, job_id, job)
    return job


def _mark_timeout_failure(
    project_id: str, job_id: str, job: ExecutionJobRecord, proc: ManagedProcess
) -> ExecutionJobRecord:
    proc.kill()
    _set_job_status(job, JOB_STATUS_FAILED, "timeout")
    job.return_code = -9
    job.finished_at = utc_now()
    job.duration_ms = _compute_duration_ms(job)
    job.failure_digest = _failure_digest(job, "TIMEOUT", retryable=True)
    _write_job(project_id, job_id, job)
    _scheduler_stat_inc("jobs_timed_out")
    _scheduler_stat_inc("jobs_failed")
    with _RUNNING_LOCK:
        _RUNNING.pop(job_id, None)
    started_after = _drain_queue_locked(project_id)
    if started_after:
        _scheduler_stat_inc("jobs_started", len(started_after))
    return job


def _record_completion_journal(project_id: str, job: ExecutionJobRecord) -> None:
    if job.journal_on_complete and job.return_code == 0:
        _append_job_journal(
            project_id, f"execution complete {job.job_id}", f"Command: {' '.join(job.command)}"
        )
    if job.journal_on_failure and job.return_code != 0:
        failure_payload = (
            job.failure_digest.to_dict()
            if isinstance(job.failure_digest, ExecutionFailureDigest)
            else job.failure_digest or {}
        )
        _append_job_journal(
            project_id, f"execution failed {job.job_id}", safe_json_dumps(failure_payload)
        )


def _apply_worker_completion(
    project_id: str, job_id: str, job: ExecutionJobRecord, receipt: JsonObject
) -> ExecutionJobRecord:
    state = str(receipt.get("state") or "").upper()
    return_code = int(receipt.get("return_code", -1))
    job.worker_pid = int(receipt.get("worker_pid")) if receipt.get("worker_pid") is not None else job.worker_pid
    job.pid = int(receipt.get("child_pid")) if receipt.get("child_pid") is not None else job.pid
    job.finished_at = str(receipt.get("finished_at") or utc_now())
    job.duration_ms = _compute_duration_ms(job)
    if state == "COMPLETED" and return_code == 0:
        _set_job_status(job, JOB_STATUS_COMPLETED, "complete")
        job.return_code = 0
        job.supervision_state = "worker_receipt_complete"
    elif state == "TERMINATED":
        _set_job_status(job, JOB_STATUS_TERMINATED, "terminated")
        job.return_code = return_code
        job.supervision_state = "worker_receipt_terminated"
        job.failure_digest = _failure_digest(job, "HOST_PREEMPT", retryable=True)
    elif state == "TIMED_OUT":
        _set_job_status(job, JOB_STATUS_FAILED, "timeout")
        job.return_code = return_code
        job.supervision_state = "worker_receipt_timeout"
        job.failure_digest = _failure_digest(job, "TIMEOUT", retryable=True)
        _scheduler_stat_inc("jobs_timed_out")
    else:
        _set_job_status(job, JOB_STATUS_FAILED, "complete")
        job.return_code = return_code
        job.supervision_state = "worker_receipt_failed"
        stderr_excerpt, stdout_excerpt = _job_failure_excerpt(job)
        job.failure_digest = _failure_digest(
            job,
            "NONZERO_EXIT" if state == "FAILED" else "WORKER_FAILURE",
            retryable=(state == "WORKER_FAILED"),
            stderr_excerpt=stderr_excerpt,
            stdout_excerpt=stdout_excerpt,
            worker_reason=receipt.get("reason"),
        )
    _record_completion_journal(project_id, job)
    _write_job(project_id, job_id, job)
    _scheduler_stat_inc("jobs_completed" if job.status == JOB_STATUS_COMPLETED else "jobs_failed")
    with _RUNNING_LOCK:
        _RUNNING.pop(job_id, None)
    return job


def _finalize_worker_job(project_id: str, job_id: str, job: ExecutionJobRecord) -> ExecutionJobRecord:
    completion = _load_worker_receipt(job, job.worker_completion_path)
    if completion is not None:
        result = _apply_worker_completion(project_id, job_id, job, completion)
        started_after = _drain_queue(project_id)
        if started_after:
            _scheduler_stat_inc("jobs_started", len(started_after))
        return result

    heartbeat = _load_worker_receipt(job, job.worker_heartbeat_path)
    if heartbeat is not None:
        job.worker_pid = int(heartbeat.get("worker_pid")) if heartbeat.get("worker_pid") is not None else job.worker_pid
        job.pid = int(heartbeat.get("child_pid")) if heartbeat.get("child_pid") is not None else job.pid
        state = str(heartbeat.get("state") or "").upper()
        if state in {"WORKER_STARTING", "RUNNING"} and _heartbeat_fresh(heartbeat):
            job.supervision_state = "worker_heartbeat"
            if job.status == JOB_STATUS_TERMINATING:
                job.stage = "cancel_requested"
            else:
                _set_job_status(job, JOB_STATUS_RUNNING, "runtime")
            _write_job(project_id, job_id, job)
            return job

    worker_alive = _pid_alive(job.worker_pid)
    if worker_alive:
        job.supervision_state = "worker_alive_heartbeat_stale"
        job.stage = "worker_heartbeat_stale"
        _write_job(project_id, job_id, job)
        return job

    _set_job_status(job, JOB_STATUS_HOST_PREEMPTED, "worker_lost")
    job.finished_at = utc_now()
    job.duration_ms = _compute_duration_ms(job)
    job.supervision_state = "worker_lost"
    job.failure_digest = _failure_digest(job, "HOST_PREEMPT", retryable=True)
    _write_job(project_id, job_id, job)
    _scheduler_stat_inc("jobs_failed")
    _scheduler_stat_inc("jobs_reconciled")
    with _RUNNING_LOCK:
        _RUNNING.pop(job_id, None)
    started_after = _drain_queue(project_id)
    if started_after:
        _scheduler_stat_inc("jobs_started", len(started_after))
    return job


def _mark_process_completion(
    project_id: str, job_id: str, job: ExecutionJobRecord, return_code: int
) -> ExecutionJobRecord:
    _set_job_status(
        job, JOB_STATUS_COMPLETED if return_code == 0 else JOB_STATUS_FAILED, "complete"
    )
    job.return_code = int(return_code)
    job.finished_at = utc_now()
    job.duration_ms = _compute_duration_ms(job)
    if return_code != 0:
        stderr_excerpt, stdout_excerpt = _job_failure_excerpt(job)
        job.failure_digest = _failure_digest(
            job,
            "NONZERO_EXIT",
            retryable=False,
            stderr_excerpt=stderr_excerpt,
            stdout_excerpt=stdout_excerpt,
        )
    _record_completion_journal(project_id, job)
    _write_job(project_id, job_id, job)
    _scheduler_stat_inc("jobs_completed" if return_code == 0 else "jobs_failed")
    with _RUNNING_LOCK:
        _RUNNING.pop(job_id, None)
    started_after = _drain_queue_locked(project_id)
    if started_after:
        _scheduler_stat_inc("jobs_started", len(started_after))
    return job


def _finalize_without_process(
    project_id: str, job_id: str, job: ExecutionJobRecord
) -> ExecutionJobRecord:
    if job.status == JOB_STATUS_QUEUED:
        _drain_queue_locked(project_id)
        return _read_job(project_id, job_id)
    if job.status != JOB_STATUS_RUNNING:
        return job
    if _pid_alive(job.pid):
        return _mark_job_unsupervised(project_id, job_id, job)
    return _mark_supervision_lost(project_id, job_id, job)


def _finalize_running_process(
    project_id: str, job_id: str, job: ExecutionJobRecord, proc: ManagedProcess
) -> ExecutionJobRecord:
    ret = proc.poll()
    now = time.time()
    if ret is None:
        if job.deadline_epoch and now > job.deadline_epoch:
            return _mark_timeout_failure(project_id, job_id, job, proc)
        return job
    return _mark_process_completion(project_id, job_id, job, ret)


def _finalize(project_id: str, job_id: str, job: ExecutionJobRecord) -> ExecutionJobRecord:
    if job.worker_token:
        with _ADMISSION_LOCK:
            return _finalize_worker_job(project_id, job_id, job)
    with _ADMISSION_LOCK:
        proc = _RUNNING.get(job_id)
        if proc is None:
            return _finalize_without_process(project_id, job_id, job)
        return _finalize_running_process(project_id, job_id, job, proc)


def _reconcile_job_locked(job: ExecutionJobRecord) -> None:
    project_id = str(job.project_id).strip()
    job_id = str(job.job_id).strip()
    if not project_id or not job_id:
        return
    if job.worker_token:
        if job.status in JOB_ACTIVE_STATUSES:
            _finalize_worker_job(project_id, job_id, job)
        return
    proc = _RUNNING.get(job_id)
    if proc is not None:
        _finalize(project_id, job_id, job)
        return
    if job.status != JOB_STATUS_RUNNING:
        return
    if _pid_alive(job.pid):
        if job.supervision_state != "unsupervised":
            _mark_job_unsupervised(project_id, job_id, job)
        return
    _mark_supervision_lost(project_id, job_id, job)
    _scheduler_stat_inc("jobs_failed")
    _scheduler_stat_inc("jobs_reconciled")


def _scheduler_tick() -> None:
    # Whole-tree discovery and file reads must never monopolize admission for every project.
    paths = list(_iter_job_files(None))
    for path in paths:
        job, _error = _load_job_file(path)
        if not job:
            continue
        with _ADMISSION_LOCK:
            _reconcile_job_locked(job)
    started = _drain_queue(None)
    if started:
        _scheduler_stat_inc("jobs_started", len(started))


def _scheduler_loop() -> None:
    while not _SCHEDULER_STOP.is_set():
        _scheduler_stat_inc("iterations")
        _scheduler_stat_set("last_tick_at", utc_now())
        try:
            _scheduler_stat_set("last_error", None)
            _scheduler_tick()
        except (OSError, RuntimeError, ValueError, TypeError, KeyError) as exc:
            _scheduler_stat_set("last_error", f"{type(exc).__name__}: {exc}")
        _SCHEDULER_STOP.wait(EXECUTION_SCHEDULER_INTERVAL_SECONDS)


def _shutdown_scheduler() -> None:
    _SCHEDULER_STOP.set()
    thread = _SCHEDULER_THREAD
    if thread and thread.is_alive():
        thread.join(timeout=1.0)


atexit.register(_shutdown_scheduler)


def _ensure_scheduler_started() -> None:
    global _SCHEDULER_THREAD
    if _SCHEDULER_THREAD and _SCHEDULER_THREAD.is_alive():
        return
    _SCHEDULER_STOP.clear()
    _SCHEDULER_THREAD = threading.Thread(
        target=_scheduler_loop,
        name="pcmmad-execution-scheduler",
        daemon=True,
    )
    _SCHEDULER_THREAD.start()
    _scheduler_stat_inc("scheduler_startups")


@execution_bp.post("/submit")
def submit_execution() -> object:
    ae = _auth()
    if ae:
        return ae
    try:
        request_payload = request.get_json(silent=False, force=True)
        job = submit_execution_job(request_payload)
        return jsonify(ExecutionStatusResponse(ok=True, job=job).to_dict())
    except ExecutionRequestError as e:
        return _error(e.error_code, e.message, e.status, **e.extra)
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as e:
        return _error("EXECUTION_SUBMIT_FAILED", str(e), 500)


def _status_payload(status_request: ExecutionStatusRequest) -> JsonObject:
    job = _finalize(
        status_request.project_id,
        status_request.job_id,
        _read_job(status_request.project_id, status_request.job_id),
    )
    return ExecutionStatusResponse(ok=True, job=job).to_dict()


def _output_window_request(
    output_request: ExecutionOutputRequest,
) -> tuple[int | None, int | None, int | None, str]:
    max_bytes = _request_optional_positive_int(
        output_request.max_bytes, 32768, minimum=1024, maximum=MAX_OUTPUT_BYTES
    )
    offset_bytes = _request_optional_positive_int(
        output_request.offset_bytes, None, minimum=0, maximum=MAX_OUTPUT_BYTES
    )
    length_bytes = _request_optional_positive_int(
        output_request.length_bytes, max_bytes, minimum=1, maximum=MAX_OUTPUT_BYTES
    )
    return max_bytes, offset_bytes, length_bytes, output_request.mode


def _job_output_windows(
    job: ExecutionJobRecord, output_request: ExecutionOutputRequest
) -> tuple[str, str, bool, bool, TextWindow, TextWindow, int | None]:
    max_bytes, offset_bytes, length_bytes, mode = _output_window_request(output_request)
    stdout_text, stdout_truncated, stdout_window = _read_text_window(
        Path(job.stdout_path),
        max_bytes=max_bytes,
        mode=mode,
        offset_bytes=offset_bytes,
        length_bytes=length_bytes,
    )
    stderr_text, stderr_truncated, stderr_window = _read_text_window(
        Path(job.stderr_path),
        max_bytes=max_bytes,
        mode=mode,
        offset_bytes=offset_bytes,
        length_bytes=length_bytes,
    )
    return (
        stdout_text,
        stderr_text,
        stdout_truncated,
        stderr_truncated,
        stdout_window,
        stderr_window,
        max_bytes,
    )


def _finalized_output_job(output_request: ExecutionOutputRequest) -> ExecutionJobRecord:
    job = _read_job(output_request.project_id, output_request.job_id)
    return _finalize(output_request.project_id, output_request.job_id, job)


def _output_response(
    output_request: ExecutionOutputRequest,
    job: ExecutionJobRecord,
    windows: tuple[str, str, bool, bool, JsonObject, JsonObject, int | None],
) -> ExecutionOutputResponse:
    stdout_text, stderr_text, stdout_truncated, stderr_truncated = windows[:4]
    stdout_window, stderr_window, max_bytes = windows[4:]
    return ExecutionOutputResponse(
        ok=True,
        project_id=output_request.project_id,
        job_id=output_request.job_id,
        status=str(job.status),
        stdout=stdout_text,
        stderr=stderr_text,
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
        bytes_returned=len(stdout_text.encode("utf-8")) + len(stderr_text.encode("utf-8")),
        max_bytes=_limit_for_wire(max_bytes),
        stdout_window=stdout_window,
        stderr_window=stderr_window,
        stdout_path=str(job.stdout_path),
        stderr_path=str(job.stderr_path),
        last_update_time=utc_now(),
    )


def _output_payload(output_request: ExecutionOutputRequest) -> JsonObject:
    job = _finalized_output_job(output_request)
    windows = _job_output_windows(job, output_request)
    return _output_response(output_request, job, windows).to_dict()


def _list_payload(list_request: ExecutionListRequest) -> JsonObject:
    project_id = list_request.project_id
    limit = _request_optional_positive_int(list_request.limit, DEFAULT_LIST_LIMIT, minimum=1)
    _drain_queue(project_id)
    jobs: list[ExecutionJobRecord] = []
    corrupt_job_files: list[CorruptJobFileRecord] = []
    job_files = sorted(
        _jobs_dir(project_id).glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True
    )
    for path in job_files[:limit] if limit is not None else job_files:
        job, error = _load_job_file(path)
        if error:
            corrupt_job_files.append(CorruptJobFileRecord(path=str(path), error=error))
            continue
        if job:
            jobs.append(_finalize(project_id, job.job_id, job) if job.job_id else job)
    return ExecutionListResponse(
        ok=True,
        project_id=project_id,
        count=len(jobs),
        jobs=jobs,
        capacity=_capacity_snapshot(project_id),
        corrupt_job_files=corrupt_job_files,
    ).to_dict()


def _terminate_running_job(
    project_id: str, job_id: str, job: ExecutionJobRecord
) -> ExecutionJobRecord:
    proc = _RUNNING.get(job_id)
    if proc and proc.poll() is None:
        proc.kill()
        _set_job_status(job, JOB_STATUS_TERMINATED, "terminated")
        job.return_code = -9
        job.finished_at = utc_now()
        job.duration_ms = _compute_duration_ms(job)
        job.failure_digest = _failure_digest(job, "HOST_PREEMPT", retryable=True)
        _write_job(project_id, job_id, job)
        with _RUNNING_LOCK:
            _RUNNING.pop(job_id, None)
        _drain_queue(project_id)
    return job


def terminate_execution_job(project_id: str, job_id: str) -> ExecutionJobRecord:
    """Request canonical termination; worker-capsule jobs use durable cancellation receipts."""
    with _ADMISSION_LOCK:
        job = _read_job(project_id, job_id)
        if job.worker_token and job.status in {JOB_STATUS_RUNNING, JOB_STATUS_TERMINATING}:
            if not job.worker_cancel_path:
                raise ExecutionRequestError("WORKER_CONTROL_MISSING", "worker cancel path missing", 500)
            save_json_atomic(
                Path(job.worker_cancel_path),
                {"job_id": job.job_id, "worker_token": job.worker_token, "requested_at": utc_now()},
            )
            _set_job_status(job, JOB_STATUS_TERMINATING, "cancel_requested")
            job.supervision_state = "worker_cancel_requested"
            _write_job(project_id, job_id, job)
            return job
        job = _terminate_running_job(project_id, job_id, job)
        if job.status == JOB_STATUS_QUEUED:
            _set_job_status(job, JOB_STATUS_TERMINATED, "terminated_while_queued")
            job.finished_at = utc_now()
            job.failure_digest = _failure_digest(job, "HOST_PREEMPT", retryable=True)
            _write_job(project_id, job_id, job)
            _drain_queue_locked(project_id)
        return job


def _terminate_payload(terminate_request: ExecutionTerminateRequest) -> JsonObject:
    job = terminate_execution_job(terminate_request.project_id, terminate_request.job_id)
    return ExecutionStatusResponse(ok=True, job=job).to_dict()


@execution_bp.post("/status")
def execution_status() -> object:
    ae = _auth()
    if ae:
        return ae
    try:
        return jsonify(
            _status_payload(
                ExecutionStatusRequest.from_json(request.get_json(silent=False, force=True))
            )
        )
    except FileNotFoundError:
        return _error("NOT_FOUND", "job not found", 404)
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as e:
        return _error("EXECUTION_STATUS_FAILED", str(e), 500)


@execution_bp.post("/output")
def execution_output() -> object:
    ae = _auth()
    if ae:
        return ae
    try:
        return jsonify(
            _output_payload(
                ExecutionOutputRequest.from_json(request.get_json(silent=False, force=True))
            )
        )
    except FileNotFoundError:
        return _error("NOT_FOUND", "job not found", 404)
    except (
        OSError,
        RuntimeError,
        ValueError,
        TypeError,
        KeyError,
        UnicodeError,
        json.JSONDecodeError,
    ) as e:
        return _error("EXECUTION_OUTPUT_FAILED", str(e), 500)


@execution_bp.post("/list")
def execution_list() -> object:
    ae = _auth()
    if ae:
        return ae
    try:
        return jsonify(
            _list_payload(
                ExecutionListRequest.from_json(request.get_json(silent=False, force=True))
            )
        )
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as e:
        return _error("EXECUTION_LIST_FAILED", str(e), 500)


@execution_bp.post("/terminate")
def execution_terminate() -> object:
    ae = _auth()
    if ae:
        return ae
    try:
        return jsonify(
            _terminate_payload(
                ExecutionTerminateRequest.from_json(request.get_json(silent=False, force=True))
            )
        )
    except FileNotFoundError:
        return _error("NOT_FOUND", "job not found", 404)
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as e:
        return _error("TERMINATION_FAILED", str(e), 500)


def _resolve_registration_source(project_id: str, source_path: str) -> tuple[Path, Path]:
    root = get_project_root(project_id)
    src = (
        (root / source_path).resolve()
        if not Path(source_path).is_absolute()
        else Path(source_path).resolve()
    )
    if root.resolve() not in [src, *src.parents]:
        raise ValueError("source_path escapes project root")
    if not src.exists() or not src.is_file():
        raise FileNotFoundError("source artifact not found")
    return root, src


def _validate_registration_target(spec: RegistrationTargetSpec) -> Path:
    target = resolve_target(spec.project_id, spec.artifact_class, spec.logical_name)
    if target.exists() and spec.operation == "create":
        raise FileExistsError("target already exists")
    if (not target.exists()) and spec.operation == "update":
        raise FileNotFoundError("target does not exist")
    if target.exists() and spec.expected_previous_sha256:
        cur = sha256_file(target)
        if cur != spec.expected_previous_sha256:
            raise RuntimeError(f"HASH_MISMATCH:{cur}")
    return target


def _registration_record(spec: RegistrationRecordBuildSpec) -> ExecutionRegistrationRecord:
    return ExecutionRegistrationRecord(
        project_id=spec.request_model.project_id,
        session_id=spec.request_model.session_id,
        commit_id=spec.commit_id,
        idempotency_key=spec.request_model.idempotency_key,
        artifact_class=spec.request_model.artifact_class,
        logical_name=spec.request_model.logical_name,
        operation=spec.request_model.operation,
        path=str(spec.target.relative_to(spec.root)),
        sha256=spec.sha,
        bytes=spec.target.stat().st_size,
        time=utc_now(),
    )


def _register_payload(request_model: ExecutionRegisterRequest) -> JsonObject:
    root, src = _resolve_registration_source(request_model.project_id, request_model.source_path)
    target = _validate_registration_target(
        RegistrationTargetSpec(
            request_model.project_id,
            request_model.artifact_class,
            request_model.logical_name,
            request_model.operation,
            request_model.expected_previous_sha256,
        )
    )
    ensure_parent(target)
    shutil.copy2(src, target)
    sha = sha256_file(target)
    _update_manifest_entry(request_model.project_id, target, request_model.artifact_class)
    commit_id = request_model.commit_id or f"execution-register-{uuid.uuid4().hex[:8]}"
    record = _registration_record(
        RegistrationRecordBuildSpec(request_model, root, target, sha, commit_id)
    )
    _record_commit(request_model.project_id, record.to_dict())
    if request_model.job_id:
        job = _read_job(request_model.project_id, request_model.job_id)
        job.registered_artifacts.append(record.to_dict())
        job.artifact_registration_status = "registered"
        _write_job(request_model.project_id, request_model.job_id, job)
    return ExecutionRegisterResponse(
        ok=True, registration_commit_id=commit_id, **record.to_dict()
    ).to_dict()


def _default_replay_key(project_id: str, prior_job_id: str, payload: JsonObject) -> str:
    return hashlib.sha256(
        safe_json_dumps(
            {
                "project_id": project_id,
                "prior_job_id": prior_job_id,
                "timeout_seconds": payload["timeout_seconds"],
                "stdout_max_bytes": payload["stdout_max_bytes"],
                "stderr_max_bytes": payload["stderr_max_bytes"],
                "env_allowlist": payload["env_allowlist"],
                "result_artifact_targets": payload["result_artifact_targets"],
            }
        ).encode("utf-8")
    ).hexdigest()


def _replay_payload(replay_request: ExecutionReplayRequest) -> JsonObject:
    prior = _read_job(replay_request.project_id, replay_request.job_id)
    payload = _build_replay_submission_data(prior, replay_request, replay_request.project_id)
    job = submit_execution_job(
        payload,
        execution_mode_override="replay",
        replay_of=replay_request.job_id,
        default_idempotency_key=_default_replay_key(
            replay_request.project_id, replay_request.job_id, payload
        ),
    )
    return ExecutionStatusResponse(ok=True, job=job).to_dict()


@execution_bp.post("/register")
def execution_register() -> object:
    ae = _auth()
    if ae:
        return ae
    try:
        return jsonify(
            _register_payload(
                ExecutionRegisterRequest.from_json(request.get_json(silent=False, force=True))
            )
        )
    except FileExistsError as e:
        return _error("BAD_OPERATION", str(e), 409)
    except FileNotFoundError as e:
        return _error("NOT_FOUND", str(e), 404)
    except RuntimeError as e:
        if str(e).startswith("HASH_MISMATCH:"):
            return _error(
                "HASH_MISMATCH",
                "expected_previous_sha256 did not match existing file",
                409,
                current_sha256=str(e).split(":", 1)[1],
            )
        return _error("RESULT_REGISTRATION_FAILED", str(e), 500)
    except (OSError, ValueError, TypeError, KeyError, shutil.Error) as e:
        return _error("RESULT_REGISTRATION_FAILED", str(e), 500)


@execution_bp.post("/replay")
def execution_replay() -> object:
    ae = _auth()
    if ae:
        return ae
    try:
        return jsonify(
            _replay_payload(
                ExecutionReplayRequest.from_json(request.get_json(silent=False, force=True))
            )
        )
    except FileNotFoundError:
        return _error("NOT_FOUND", "job not found", 404)
    except ExecutionRequestError as e:
        return _error(e.error_code, e.message, e.status, **e.extra)
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as e:
        return _error("SPAWN_FAILURE", str(e), 500)
