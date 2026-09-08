"""Typed control-plane models for manifests, batches, telemetry, and persistence records."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any
from collections.abc import MutableMapping, Callable

JsonObject = MutableMapping[str, Any]


class DictSerializable:
    def to_dict(self) -> JsonObject:
        return asdict(self)


def _as_str(value: Any, default: str = "") -> str:
    return default if value is None else str(value)


def _as_optional_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value if value is not None else default)
    except (TypeError, ValueError, OverflowError):
        return default


def _as_list_of_str(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _as_mapping(value: Any) -> JsonObject:
    return value if isinstance(value, dict) else {}


def _as_str_dict(value: Any) -> JsonObject:
    return {str(key): item for key, item in _as_mapping(value).items()}


def _record_list(value: Any, record_cls: type[Any]) -> list[Any]:
    return (
        [record_cls.from_dict(item) for item in value if isinstance(item, dict)]
        if isinstance(value, list)
        else []
    )


def _record_or_none(value: Any, record_cls: type[Any]) -> Any | None:
    return record_cls.from_dict(value) if isinstance(value, dict) else None


def _extra_fields(mapped: JsonObject, core_keys: set[str]) -> JsonObject:
    return {str(key): item for key, item in mapped.items() if key not in core_keys}


def _failure_digest_or_none(value: Any) -> "ExecutionFailureDigest | None":
    return ExecutionFailureDigest.from_dict(value) if isinstance(value, dict) else None


def _as_float(value: Any, default: float | None = None) -> float | None:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError, OverflowError):
        return default


def _as_optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return None


def _as_optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError, OverflowError):
        return None


def _as_optional_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return bool(value)


@dataclass
class SchedulerTelemetry(DictSerializable):
    iterations: int = 0
    last_tick_at: str | None = None
    last_error: str | None = None
    jobs_started: int = 0
    jobs_completed: int = 0
    jobs_failed: int = 0
    jobs_timed_out: int = 0
    jobs_reconciled: int = 0
    jobs_reconcile_errors: int = 0
    last_tick_reconcile_errors: int = 0
    last_reconcile_error: str | None = None
    last_reconcile_error_at: str | None = None
    scheduler_startups: int = 0
    watcher_started: bool = False
    watcher_alive: bool = False
    watcher_events: int = 0
    watcher_overflows: int = 0
    watcher_errors: int = 0
    last_watcher_event_at: str | None = None
    last_watcher_error: str | None = None
    scheduler_wakeups: int = 0
    periodic_resyncs: int = 0
    last_resync_at: str | None = None
    last_active_records: int = 0
    scheduler_wait_mode: str = "poll"

    def inc(self, name: str, amount: int = 1) -> None:
        setattr(self, name, int(getattr(self, name, 0)) + amount)

    def set(self, name: str, value: Any) -> None:
        setattr(self, name, value)


@dataclass
class BatchExecutorTelemetry(DictSerializable):
    foreground_parallel_dispatches: int = 0
    background_batches_completed: int = 0
    background_batches_failed: int = 0
    background_batches_active: int = 0
    last_background_error: str | None = None

    def inc(self, name: str, amount: int = 1) -> None:
        setattr(self, name, int(getattr(self, name, 0)) + amount)

    def set(self, name: str, value: Any) -> None:
        setattr(self, name, value)


def _failure_digest_core_keys() -> set[str]:
    return {
        "job_id",
        "project_id",
        "failure_kind",
        "execution_state",
        "stage",
        "host_preempted",
        "exit_code",
        "signal",
        "artifact_registration_status",
        "time_started",
        "time_ended",
        "duration_ms",
        "retryable",
    }


def _failure_digest_args(mapped: JsonObject) -> JsonObject:
    return {
        "job_id": _as_str(mapped.get("job_id")),
        "project_id": _as_str(mapped.get("project_id")),
        "failure_kind": _as_str(mapped.get("failure_kind")),
        "execution_state": _as_str(mapped.get("execution_state")),
        "stage": _as_str(mapped.get("stage")),
        "host_preempted": bool(mapped.get("host_preempted", False)),
        "exit_code": _as_optional_int(mapped.get("exit_code")),
        "signal": _as_optional_str(mapped.get("signal")),
        "artifact_registration_status": _as_str(
            mapped.get("artifact_registration_status"), "not_attempted"
        ),
        "time_started": _as_optional_str(mapped.get("time_started")),
        "time_ended": _as_optional_str(mapped.get("time_ended")),
        "duration_ms": _as_optional_int(mapped.get("duration_ms")),
        "retryable": bool(mapped.get("retryable", False)),
    }


@dataclass(frozen=True)
class ExecutionFailureDigest:
    job_id: str
    project_id: str
    failure_kind: str
    execution_state: str
    stage: str
    host_preempted: bool
    exit_code: int | None = None
    signal: str | None = None
    artifact_registration_status: str = "not_attempted"
    time_started: str | None = None
    time_ended: str | None = None
    duration_ms: int | None = None
    retryable: bool = False
    extra: JsonObject = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: JsonObject) -> "ExecutionFailureDigest":
        mapped = _as_mapping(data)
        return cls(
            **_failure_digest_args(mapped),
            extra=_extra_fields(mapped, _failure_digest_core_keys()),
        )

    def to_dict(self) -> JsonObject:
        data = asdict(self)
        extra = data.pop("extra", {})
        data.update(extra)
        return data


@dataclass(frozen=True)
class CapacitySnapshot:
    running_global: int
    running_project: int
    global_limit: int | None
    project_limit: int | None
    queued_global: int
    queued_project: int
    global_queue_limit: int | None
    project_queue_limit: int | None

    def to_dict(self) -> JsonObject:
        return asdict(self)


@dataclass(frozen=True)
class GlobalExecutionSnapshot:
    running: int
    queued: int
    global_limit: int
    global_queue_limit: int
    oldest_queued_age_seconds: float | None

    def to_dict(self) -> JsonObject:
        return asdict(self)


@dataclass(frozen=True)
class CorruptJobFileRecord:
    path: str
    error: str


@dataclass(frozen=True)
class ExecutionReadinessEnvelope:
    status: str
    global_snapshot: GlobalExecutionSnapshot
    per_project: dict[str, CapacitySnapshot]
    corrupt_job_files: list[str]
    unsupervised_jobs: list[str]
    drain_batch: int
    scheduler_thread_alive: bool
    scheduler_telemetry: SchedulerTelemetry

    def to_dict(self) -> JsonObject:
        return {
            "status": self.status,
            "global": self.global_snapshot.to_dict(),
            "per_project": {
                project_key: stats.to_dict() for project_key, stats in self.per_project.items()
            },
            "corrupt_job_files": self.corrupt_job_files,
            "unsupervised_jobs": self.unsupervised_jobs,
            "drain_batch": self.drain_batch,
            "scheduler_thread_alive": self.scheduler_thread_alive,
            "scheduler_telemetry": self.scheduler_telemetry.to_dict(),
        }


@dataclass(frozen=True)
class ExecutionCapabilitiesEnvelope:
    execution_enabled: bool
    execution_modes: list[str]
    max_timeout_seconds: int
    default_timeout_seconds: int
    max_stdout_bytes: int
    max_stderr_bytes: int
    artifact_registration_enabled: bool
    termination_enabled: bool
    global_concurrency_limit: int
    per_project_concurrency_limit: int
    global_queue_limit: int
    per_project_queue_limit: int
    scheduler_interval_seconds: float
    scheduler_active_resync_seconds: float
    scheduler_idle_resync_seconds: float
    watcher_supported: bool
    watcher_active: bool
    background_scheduler: bool
    scheduler_alive: bool
    resource_envelope_supported: bool = False
    resource_envelope_backend: str = "none"
    resource_budget_fields: list[str] = field(default_factory=list)

    def to_dict(self) -> JsonObject:
        return asdict(self)


@dataclass
class TextWindow:
    mode: str
    file_size: int
    requested_bytes: int | None
    returned_bytes: int
    offset_bytes: int | None = None


@dataclass
class BackgroundResultEnvelope:
    project_id: str
    handle: str
    label: str
    tool_name: str
    created_at: str
    payload: object


def _job_record_known_keys(cls: type) -> set[str]:
    return {field.name for field in cls.__dataclass_fields__.values() if field.name != "extra"}


def _result_artifact_targets(mapped: JsonObject) -> list[JsonObject]:
    value = mapped.get("result_artifact_targets")
    return value if isinstance(value, list) else []


def _env_allowlist(mapped: JsonObject) -> dict[str, str]:
    value = mapped.get("env_allowlist", {})
    if not isinstance(value, dict):
        return {}
    return {str(env_key): str(env_value) for env_key, env_value in value.items()}


def _resource_component(mapped: JsonObject, key: str) -> JsonObject:
    value = mapped.get(key, {})
    if not isinstance(value, dict):
        return {}
    return dict(value)


def _normalized_failure_digest(mapped: JsonObject) -> JsonObject | ExecutionFailureDigest | None:
    failure_digest = _failure_digest_or_none(mapped.get("failure_digest"))
    if isinstance(failure_digest, (dict, ExecutionFailureDigest)) or failure_digest is None:
        return failure_digest
    return None


def _job_record_identity_args(mapped: JsonObject) -> JsonObject:
    return {
        "project_id": _as_str(mapped.get("project_id")),
        "job_id": _as_str(mapped.get("job_id")),
        "status": _as_str(mapped.get("status")),
        "stage": _as_str(mapped.get("stage")),
        "execution_mode": _as_str(mapped.get("execution_mode")),
        "replay_of": _as_optional_str(mapped.get("replay_of")),
        "command": _as_list_of_str(mapped.get("command")),
        "cwd": _as_str(mapped.get("cwd")),
        "cwd_rel": _as_str(mapped.get("cwd_rel"), "."),
    }


def _job_record_runtime_args(mapped: JsonObject) -> JsonObject:
    return {
        "submitted_at": _as_str(mapped.get("submitted_at")),
        "started_at": _as_optional_str(mapped.get("started_at")),
        "deadline_epoch": _as_optional_float(mapped.get("deadline_epoch")),
        "timeout_seconds": _as_optional_int(mapped.get("timeout_seconds")),
        "stdout_path": _as_str(mapped.get("stdout_path")),
        "stderr_path": _as_str(mapped.get("stderr_path")),
        "stdout_max_bytes": _as_optional_int(mapped.get("stdout_max_bytes")),
        "stderr_max_bytes": _as_optional_int(mapped.get("stderr_max_bytes")),
        "resource_budget": _resource_component(mapped, "resource_budget"),
        "applied_resource_envelope": _resource_component(mapped, "applied_resource_envelope"),
        "result_artifact_targets": _result_artifact_targets(mapped),
        "artifact_registration_status": _as_str(
            mapped.get("artifact_registration_status"), "not_attempted"
        ),
    }


def _job_record_gate_args(mapped: JsonObject) -> JsonObject:
    return {
        "truth_gate": _as_str(mapped.get("truth_gate"), "not_evaluated"),
        "resource_gate": _as_str(mapped.get("resource_gate"), "not_evaluated"),
        "feasibility_gate": _as_str(mapped.get("feasibility_gate"), "not_evaluated"),
        "journal_on_submit": bool(mapped.get("journal_on_submit", True)),
        "journal_on_complete": bool(mapped.get("journal_on_complete", False)),
        "journal_on_failure": bool(mapped.get("journal_on_failure", True)),
        "checkpoint_on_complete": bool(mapped.get("checkpoint_on_complete", False)),
    }


def _job_record_tail_args(mapped: JsonObject) -> JsonObject:
    return {
        "local_model_id": _as_optional_str(mapped.get("local_model_id")),
        "agent_role": _as_optional_str(mapped.get("agent_role")),
        "idempotency_key": _as_str(mapped.get("idempotency_key")),
        "submission_fingerprint": _as_str(mapped.get("submission_fingerprint")),
        "env_allowlist": _env_allowlist(mapped),
        "queue_position": _as_optional_int(mapped.get("queue_position")),
        "pid": _as_optional_int(mapped.get("pid")),
        "pid_creation_time_100ns": _as_optional_int(mapped.get("pid_creation_time_100ns")),
        "worker_pid": _as_optional_int(mapped.get("worker_pid")),
        "worker_launcher_pid": _as_optional_int(mapped.get("worker_launcher_pid")),
        "worker_token": _as_optional_str(mapped.get("worker_token")),
        "worker_request_path": _as_optional_str(mapped.get("worker_request_path")),
        "worker_heartbeat_path": _as_optional_str(mapped.get("worker_heartbeat_path")),
        "worker_completion_path": _as_optional_str(mapped.get("worker_completion_path")),
        "worker_cancel_path": _as_optional_str(mapped.get("worker_cancel_path")),
        "worker_ownership_release_path": _as_optional_str(mapped.get("worker_ownership_release_path")),
        "job_object_name": _as_optional_str(mapped.get("job_object_name")),
        "worker_creation_time_100ns": _as_optional_int(mapped.get("worker_creation_time_100ns")),
        "child_creation_time_100ns": _as_optional_int(mapped.get("child_creation_time_100ns")),
        "finished_at": _as_optional_str(mapped.get("finished_at")),
        "duration_ms": _as_optional_int(mapped.get("duration_ms")),
        "return_code": _as_optional_int(mapped.get("return_code")),
        "failure_digest": _normalized_failure_digest(mapped),
        "supervision_state": _as_optional_str(mapped.get("supervision_state")),
        "replayed": _as_optional_bool(mapped.get("replayed")),
    }


def _job_record_args(mapped: JsonObject) -> JsonObject:
    args: JsonObject = {}
    args.update(_job_record_identity_args(mapped))
    args.update(_job_record_runtime_args(mapped))
    args.update(_job_record_gate_args(mapped))
    args.update(_job_record_tail_args(mapped))
    return args


@dataclass
class ExecutionJobRecord:
    project_id: str
    job_id: str
    status: str
    stage: str
    execution_mode: str
    replay_of: str | None
    command: list[str]
    cwd: str
    cwd_rel: str
    submitted_at: str
    started_at: str | None = None
    deadline_epoch: float | None = None
    timeout_seconds: int | None = None
    stdout_path: str = ""
    stderr_path: str = ""
    stdout_max_bytes: int | None = None
    stderr_max_bytes: int | None = None
    resource_budget: JsonObject = field(default_factory=dict)
    applied_resource_envelope: JsonObject = field(default_factory=dict)
    result_artifact_targets: list[object] = field(default_factory=list)
    artifact_registration_status: str = "not_attempted"
    truth_gate: str = "not_evaluated"
    resource_gate: str = "not_evaluated"
    feasibility_gate: str = "not_evaluated"
    journal_on_submit: bool = True
    journal_on_complete: bool = False
    journal_on_failure: bool = True
    checkpoint_on_complete: bool = False
    local_model_id: str | None = None
    agent_role: str | None = None
    idempotency_key: str = ""
    submission_fingerprint: str = ""
    env_allowlist: dict[str, str] = field(default_factory=dict)
    queue_position: int | None = None
    pid: int | None = None
    pid_creation_time_100ns: int | None = None
    worker_pid: int | None = None
    worker_launcher_pid: int | None = None
    worker_token: str | None = None
    worker_request_path: str | None = None
    worker_heartbeat_path: str | None = None
    worker_completion_path: str | None = None
    worker_cancel_path: str | None = None
    worker_ownership_release_path: str | None = None
    job_object_name: str | None = None
    worker_creation_time_100ns: int | None = None
    child_creation_time_100ns: int | None = None
    finished_at: str | None = None
    duration_ms: int | None = None
    return_code: int | None = None
    failure_digest: JsonObject | ExecutionFailureDigest | None = None
    supervision_state: str | None = None
    replayed: bool | None = None
    extra: JsonObject = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: JsonObject) -> "ExecutionJobRecord":
        mapped = _as_mapping(data)
        rec = cls(**_job_record_args(mapped))
        rec.extra = _extra_fields(mapped, _job_record_known_keys(cls))
        return rec

    def to_dict(self) -> JsonObject:
        record = asdict(self)
        if isinstance(self.failure_digest, ExecutionFailureDigest):
            record["failure_digest"] = self.failure_digest.to_dict()
        extra = record.pop("extra", {})
        record.update(extra)
        return record

    # compatibility helpers so the rest of the file can be migrated incrementally
    def get(self, key: str, default: Any = None) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        return self.extra.get(key, default)

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        return self.extra[key]

    def __setitem__(self, key: str, value: Any) -> None:
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            self.extra[key] = value

    def setdefault(self, key: str, default: Any) -> Any:
        current = self.get(key, None)
        if current is None:
            self[key] = default
            return default
        return current


@dataclass(frozen=True)
class ExecutionSubmitPayload(DictSerializable):
    project_id: str
    execution_mode: str
    command: list[str]
    cwd: str
    cwd_rel: str
    timeout_seconds: int | None
    stdout_max_bytes: int | None
    stderr_max_bytes: int | None
    resource_budget: JsonObject = field(default_factory=dict)
    env_allowlist: dict[str, str] = field(default_factory=dict)
    result_artifact_targets: list[object] = field(default_factory=list)
    local_model_id: str | None = None
    agent_role: str | None = None
    journal_on_submit: bool = True
    journal_on_complete: bool = False
    journal_on_failure: bool = True
    checkpoint_on_complete: bool = False
    idempotency_key: str = ""
    replay_of: str | None = None
    submission_fingerprint: str = ""


@dataclass(frozen=True)
class ExecutionIdempotencyRecord(DictSerializable):
    job_id: str
    submission_fingerprint: str
    recorded_at: str

    @classmethod
    def from_dict(cls, raw: JsonObject) -> "ExecutionIdempotencyRecord":
        data = _as_mapping(raw)
        return cls(
            job_id=str(data.get("job_id", "")),
            submission_fingerprint=str(data.get("submission_fingerprint", "")),
            recorded_at=str(data.get("recorded_at", "")),
        )


@dataclass
class ExecutionIdempotencyLedger:
    keys: dict[str, ExecutionIdempotencyRecord] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: JsonObject) -> "ExecutionIdempotencyLedger":
        raw = _as_mapping(data).get("keys", {})
        keys: dict[str, ExecutionIdempotencyRecord] = {}
        if isinstance(raw, dict):
            for key, value in raw.items():
                if isinstance(key, str):
                    record = _record_or_none(value, ExecutionIdempotencyRecord)
                    if record is not None:
                        keys[key] = record
        return cls(keys=keys)

    def to_dict(self) -> JsonObject:
        return {"keys": {key: value.to_dict() for key, value in self.keys.items()}}


@dataclass(frozen=True)
class ExecutionRegistrationRecord(DictSerializable):
    project_id: str
    session_id: str | None
    commit_id: str
    idempotency_key: str
    artifact_class: str
    logical_name: str
    operation: str
    path: str
    sha256: str
    bytes: int
    time: str


@dataclass(frozen=True)
class PluginLoadRecord(DictSerializable):
    module: str
    path: str
    sha256: str | None = None


@dataclass(frozen=True)
class BlueprintLoadResult(DictSerializable):
    module: str
    blueprint: str
    error: str | None = None


@dataclass(frozen=True)
class BlueprintFailureSpec:
    module: str
    blueprint: str
    error: str
    required: bool


@dataclass
class BootReport:
    loaded: list[BlueprintLoadResult] = field(default_factory=list)
    required_failed: list[BlueprintLoadResult] = field(default_factory=list)
    optional_failed: list[BlueprintLoadResult] = field(default_factory=list)

    def record_loaded(self, *, module: str, blueprint: str) -> None:
        self.loaded.append(BlueprintLoadResult(module=module, blueprint=blueprint))

    def record_failure(self, spec: BlueprintFailureSpec) -> None:
        item = BlueprintLoadResult(module=spec.module, blueprint=spec.blueprint, error=spec.error)
        if spec.required:
            self.required_failed.append(item)
        else:
            self.optional_failed.append(item)

    def degraded(self) -> bool:
        return bool(self.optional_failed or self.required_failed)

    def to_dict(self) -> JsonObject:
        return {
            "loaded": [item.to_dict() for item in self.loaded],
            "required_failed": [item.to_dict() for item in self.required_failed],
            "optional_failed": [item.to_dict() for item in self.optional_failed],
        }


@dataclass
class BootRuntimeStatus(DictSerializable):
    execution_started: bool = False
    lab_executor_started: bool = False
    execution_error: str | None = None
    lab_executor_error: str | None = None

    def degraded(self) -> bool:
        return bool(self.execution_error or self.lab_executor_error)


def _stable_contract_hash(payload: JsonObject) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    danger_tier: str = "medium"
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    approval_required: bool = False
    mutating: bool = False
    input_schema: JsonObject = field(default_factory=lambda: {"type": "object"})
    output_schema: JsonObject = field(default_factory=lambda: {"type": "object"})
    capability_version: str = "1"
    schema_version: str = "1"
    side_effect_class: str = ""
    effect_traits: list[str] = field(default_factory=list)
    idempotency_semantics: str = ""
    availability_mode: str = "resident"
    availability_scope: str = "handler"
    availability_provider_id: str = ""
    availability_provider: Callable[[], JsonObject] | None = None
    handler: Callable[[JsonObject], JsonObject] | None = None

    @property
    def effective_approval_required(self) -> bool:
        return bool(
            self.approval_required
            or str(self.danger_tier).lower() in {"high", "critical"}
            or self.mutating
        )

    @property
    def effective_side_effect_class(self) -> str:
        explicit = str(self.side_effect_class or "").strip().lower()
        if explicit:
            return explicit
        if self.mutating:
            return "mutation"
        # `mutating=False` historically meant only "not declared mutating".  Do
        # not launder that absence into a read-only guarantee.
        return "unknown"

    @property
    def effective_idempotency_semantics(self) -> str:
        explicit = str(self.idempotency_semantics or "").strip().lower()
        if explicit:
            return explicit
        traits = set(self.effect_traits or [])
        if self.effective_side_effect_class == "read":
            return "safe_repeat"
        if "idempotent_replay_while_unacked" in traits:
            return "state_bound_replay"
        if {"exact_offset_required", "requires_chunk_hash"}.issubset(traits):
            return "position_bound_replay"
        # Conservative default: absence of an earned replay mechanism is not idempotency.
        return "unsafe_retry"

    @property
    def availability_contract(self) -> JsonObject:
        mode = str(self.availability_mode or "resident").strip().lower()
        if mode not in {"resident", "dynamic"}:
            mode = "dynamic"
        dynamic = mode == "dynamic"
        return {
            "registered": self.handler is not None,
            "mode": mode,
            "scope": str(self.availability_scope or "handler"),
            "status": "unknown" if dynamic else "available",
            "available": None if dynamic else bool(self.handler is not None),
            "probe_supported": bool(self.availability_provider),
            "provider_id": str(self.availability_provider_id or "") or None,
            "basis": "explicit_probe_required" if dynamic else "registered_handler",
        }

    @property
    def schema_hash(self) -> str:
        return _stable_contract_hash(
            {
                "schema_version": str(self.schema_version),
                "input_schema": self.input_schema,
                "output_schema": self.output_schema,
            }
        )

    @property
    def contract_digest(self) -> str:
        return _stable_contract_hash(
            {
                "name": self.name,
                "capability_version": str(self.capability_version),
                "schema_version": str(self.schema_version),
                "schema_hash": self.schema_hash,
                "danger_tier": self.danger_tier,
                "effective_approval_required": self.effective_approval_required,
                "side_effect_class": self.effective_side_effect_class,
                "effect_traits": sorted(set(self.effect_traits)),
                "idempotency_semantics": self.effective_idempotency_semantics,
                "availability_mode": str(self.availability_mode or "resident").strip().lower(),
                "availability_scope": str(self.availability_scope or "handler"),
                "availability_provider_id": str(self.availability_provider_id or ""),
                "availability_probe_supported": bool(self.availability_provider),
            }
        )

    def to_card(self) -> JsonObject:
        return {
            "name": self.name,
            "description": self.description,
            "danger_tier": self.danger_tier,
            "category": self.category,
            "tags": list(self.tags),
            # Historical field retained as the declaration authored at registration.
            "approval_required": self.approval_required,
            "effective_approval_required": self.effective_approval_required,
            "mutating": self.mutating,
            "side_effect_class": self.effective_side_effect_class,
            "effect_traits": sorted(set(self.effect_traits or (["durable_mutation"] if self.mutating else []))),
            "idempotency_semantics": self.effective_idempotency_semantics,
            "capability_version": str(self.capability_version),
            "schema_version": str(self.schema_version),
            "schema_hash": self.schema_hash,
            "contract_digest": self.contract_digest,
            "availability": self.availability_contract,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
        }


@dataclass(frozen=True)
class CapabilityFamilyCard(DictSerializable):
    name: str
    tool_count: int
    mutating_tools: int
    approval_required_tools: int
    effective_approval_required_tools: int = 0
    danger_tiers: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CompactControlSurfaceDescriptor(DictSerializable):
    operation_budget: int
    action_count: int
    purpose: str
    note: str


@dataclass(frozen=True)
class ServerCapabilityRouterDescriptor:
    dispatch_entrypoint: str
    batch_entrypoint: str
    result_handle_entrypoint: str
    larger_server_native_capability_set: bool
    families: list[CapabilityFamilyCard] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> JsonObject:
        data = asdict(self)
        data["families"] = [f.to_dict() for f in self.families]
        return data


@dataclass(frozen=True)
class ToolRouterValidationState:
    api_valid: bool
    connected: bool
    validation_mode: str
    checked_at: str
    reason: str | None = None

    def to_dict(self) -> JsonObject:
        data = asdict(self)
        if self.reason is None:
            data.pop("reason", None)
        return data


@dataclass(frozen=True)
class ToolCatalogResponse:
    ok: bool
    count: int
    tools: list[JsonObject]
    compact_control_surface: CompactControlSurfaceDescriptor
    server_native_router: ServerCapabilityRouterDescriptor
    validation: ToolRouterValidationState

    def to_dict(self) -> JsonObject:
        return {
            "ok": self.ok,
            "count": self.count,
            "tools": list(self.tools),
            "compact_control_surface": self.compact_control_surface.to_dict(),
            "server_native_router": self.server_native_router.to_dict(),
            "validation": self.validation.to_dict(),
        }


@dataclass(frozen=True)
class CompactCapabilitiesEnvelope:
    ok: bool
    time: str
    capabilities: JsonObject
    limits: JsonObject
    compact_control_surface: CompactControlSurfaceDescriptor
    server_native_router: ServerCapabilityRouterDescriptor

    def to_dict(self) -> JsonObject:
        return {
            "ok": self.ok,
            "time": self.time,
            "capabilities": dict(self.capabilities),
            "limits": dict(self.limits),
            "compact_control_surface": self.compact_control_surface.to_dict(),
            "server_native_router": self.server_native_router.to_dict(),
        }


@dataclass(frozen=True)
class ToolResultEnvelope:
    ok: bool
    tool: str
    danger_tier: str
    policy_mode: str
    approved: bool
    time: str
    result: JsonObject
    warning: str | None = None
    approval_mode: str | None = None
    approval_handle: str | None = None

    def to_dict(self) -> JsonObject:
        data = asdict(self)
        if self.warning is None:
            data.pop("warning", None)
        if self.approval_mode is None:
            data.pop("approval_mode", None)
        if self.approval_handle is None:
            data.pop("approval_handle", None)
        return data


@dataclass(frozen=True)
class ManifestEntryRecord(DictSerializable):
    artifact_class: str
    sha256: str
    bytes: int
    updated_at: str

    @classmethod
    def from_dict(cls, raw: JsonObject) -> "ManifestEntryRecord":
        data = _as_mapping(raw)
        return cls(
            artifact_class=_as_str(data.get("artifact_class")),
            sha256=_as_str(data.get("sha256")),
            bytes=_as_int(data.get("bytes")),
            updated_at=_as_str(data.get("updated_at")),
        )


@dataclass
class ManifestDocument:
    updated_at: str | None = None
    files: dict[str, ManifestEntryRecord] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: JsonObject | None) -> "ManifestDocument":
        data = _as_mapping(raw)
        files_raw = data.get("files", {})
        files: dict[str, ManifestEntryRecord] = {}
        if isinstance(files_raw, dict):
            for rel, entry in files_raw.items():
                if isinstance(rel, str):
                    record = _record_or_none(entry, ManifestEntryRecord)
                    if record is not None:
                        files[rel] = record
        updated = data.get("updated_at")
        return cls(updated_at=_as_optional_str(updated), files=files)

    def to_dict(self) -> JsonObject:
        return {
            "updated_at": self.updated_at,
            "files": {rel: entry.to_dict() for rel, entry in self.files.items()},
        }


@dataclass(frozen=True)
class CommitLedgerRecord(DictSerializable):
    project_id: str
    session_id: str
    commit_id: str
    idempotency_key: str
    artifact_class: str
    logical_name: str
    operation: str
    path: str
    sha256: str
    bytes: int
    time: str

    @classmethod
    def from_dict(cls, raw: JsonObject) -> "CommitLedgerRecord":
        data = _as_mapping(raw)
        return cls(
            project_id=_as_str(data.get("project_id")),
            session_id=_as_str(data.get("session_id")),
            commit_id=_as_str(data.get("commit_id")),
            idempotency_key=_as_str(data.get("idempotency_key")),
            artifact_class=_as_str(data.get("artifact_class")),
            logical_name=_as_str(data.get("logical_name")),
            operation=_as_str(data.get("operation")),
            path=_as_str(data.get("path")),
            sha256=_as_str(data.get("sha256")),
            bytes=_as_int(data.get("bytes")),
            time=_as_str(data.get("time")),
        )


@dataclass(frozen=True)
class SessionNoteRecord(DictSerializable):
    time: str
    type: str
    note: str

    @classmethod
    def from_dict(cls, raw: JsonObject) -> "SessionNoteRecord":
        data = _as_mapping(raw)
        return cls(
            time=_as_str(data.get("time")),
            type=_as_str(data.get("type"), "note"),
            note=_as_str(data.get("note")),
        )


@dataclass(frozen=True)
class ReflexionRecord(DictSerializable):
    time: str
    session_id: str | None = None
    title: str = ""
    content: str = ""
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: JsonObject) -> "ReflexionRecord":
        data = _as_mapping(raw)
        return cls(
            time=_as_str(data.get("time")),
            session_id=_as_optional_str(data.get("session_id")),
            title=_as_str(data.get("title")),
            content=_as_str(data.get("content")),
            tags=_as_list_of_str(data.get("tags")),
        )


@dataclass(frozen=True)
class AndonEventRecord(DictSerializable):
    time: str
    session_id: str | None = None
    reason: str = ""
    details: str = ""

    @classmethod
    def from_dict(cls, raw: JsonObject) -> "AndonEventRecord":
        data = _as_mapping(raw)
        return cls(
            time=_as_str(data.get("time")),
            session_id=_as_optional_str(data.get("session_id")),
            reason=_as_str(data.get("reason")),
            details=_as_str(data.get("details")),
        )


@dataclass
class LabSessionRecord:
    project_id: str
    session_id: str
    title: str = ""
    status: str = "active"
    created_at: str = ""
    updated_at: str = ""
    meta: JsonObject = field(default_factory=dict)
    notes: list[SessionNoteRecord] = field(default_factory=list)
    andon_events: list[AndonEventRecord] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: JsonObject) -> "LabSessionRecord":
        data = _as_mapping(raw)
        return cls(
            project_id=_as_str(data.get("project_id")),
            session_id=_as_str(data.get("session_id")),
            title=_as_str(data.get("title")),
            status=_as_str(data.get("status"), "active"),
            created_at=_as_str(data.get("created_at")),
            updated_at=_as_str(data.get("updated_at")),
            meta=_as_str_dict(data.get("meta", {})),
            notes=_record_list(data.get("notes"), SessionNoteRecord),
            andon_events=_record_list(data.get("andon_events"), AndonEventRecord),
        )

    def to_dict(self) -> JsonObject:
        return {
            "project_id": self.project_id,
            "session_id": self.session_id,
            "title": self.title,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "meta": dict(self.meta),
            "notes": [note.to_dict() for note in self.notes],
            "andon_events": [event.to_dict() for event in self.andon_events],
        }
