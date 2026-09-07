"""Typed API wire models for execution job lifecycle and output responses."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from collections.abc import MutableMapping

from control_plane_models import (
    CapacitySnapshot,
    CompactControlSurfaceDescriptor,
    CorruptJobFileRecord,
    ExecutionJobRecord,
    ServerCapabilityRouterDescriptor,
    TextWindow,
)
from api_wire_common import (
    ErrorEnvelope,
    WarningItem,
    IndexCacheStats,
    _require_object,
    _as_str,
    _as_bool,
    _as_int,
    _as_str_map,
)

JsonObject = MutableMapping[str, Any]


@dataclass
class ExecutionStatusRequest:
    project_id: str
    job_id: str

    @classmethod
    def from_json(cls, data: JsonObject) -> "ExecutionStatusRequest":
        data = _require_object(data)
        return cls(
            project_id=_as_str(data.get("project_id", "")).strip(),
            job_id=_as_str(data.get("job_id", "")).strip(),
        )


@dataclass
class ExecutionOutputRequest:
    project_id: str
    job_id: str
    max_bytes: int | None = None
    mode: str = "tail"
    offset_bytes: int | None = None
    length_bytes: int | None = None

    @classmethod
    def from_json(cls, data: JsonObject) -> "ExecutionOutputRequest":
        data = _require_object(data)
        return cls(
            project_id=_as_str(data.get("project_id", "")).strip(),
            job_id=_as_str(data.get("job_id", "")).strip(),
            max_bytes=data.get("max_bytes"),
            mode=_as_str(data.get("mode", "tail")).strip().lower() or "tail",
            offset_bytes=data.get("offset_bytes"),
            length_bytes=data.get("length_bytes"),
        )


@dataclass
class ExecutionListRequest:
    project_id: str
    limit: int | None = 20

    @classmethod
    def from_json(cls, data: JsonObject) -> "ExecutionListRequest":
        data = _require_object(data)
        return cls(
            project_id=_as_str(data.get("project_id", "")).strip(), limit=data.get("limit", 20)
        )


@dataclass
class ExecutionTerminateRequest:
    project_id: str
    job_id: str

    @classmethod
    def from_json(cls, data: JsonObject) -> "ExecutionTerminateRequest":
        data = _require_object(data)
        return cls(
            project_id=_as_str(data.get("project_id", "")).strip(),
            job_id=_as_str(data.get("job_id", "")).strip(),
        )


@dataclass
class ExecutionRegisterRequest:
    project_id: str
    source_path: str
    artifact_class: str
    logical_name: str
    operation: str = "create"
    job_id: str | None = None
    expected_previous_sha256: str | None = None
    session_id: str = "execution"
    commit_id: str | None = None
    idempotency_key: str = ""
    mutation_authority: dict[str, Any] | None = None

    @classmethod
    def from_json(cls, data: JsonObject) -> "ExecutionRegisterRequest":
        data = _require_object(data)
        return cls(
            project_id=_as_str(data.get("project_id", "")).strip(),
            source_path=_as_str(data.get("source_path", "")).strip(),
            artifact_class=_as_str(data.get("artifact_class", "")).strip(),
            logical_name=_as_str(data.get("logical_name", "")).strip(),
            operation=_as_str(data.get("operation", "create")).strip() or "create",
            job_id=(_as_str(data.get("job_id", "")).strip() or None),
            expected_previous_sha256=(
                _as_str(data.get("expected_previous_sha256", "")).strip() or None
            ),
            session_id=_as_str(data.get("session_id", "execution")).strip() or "execution",
            commit_id=(_as_str(data.get("commit_id", "")).strip() or None),
            idempotency_key=_as_str(data.get("idempotency_key", "")).strip(),
            mutation_authority=(dict(data["mutation_authority"]) if isinstance(data.get("mutation_authority"), dict) else None),
        )


@dataclass
class ExecutionReplayRequest:
    project_id: str
    job_id: str
    timeout_seconds: int | None = None
    stdout_max_bytes: int | None = None
    stderr_max_bytes: int | None = None
    env_allowlist: dict[str, str] = field(default_factory=dict)
    result_artifact_targets: list[JsonObject] = field(default_factory=list)
    journal_on_submit: bool = False
    journal_on_complete: bool = False
    journal_on_failure: bool = True
    local_model_id: str | None = None
    agent_role: str | None = None
    idempotency_key: str | None = None
    mutation_authority: dict[str, Any] | None = None

    @classmethod
    def from_json(cls, data: JsonObject) -> "ExecutionReplayRequest":
        data = _require_object(data)
        rat = data.get("result_artifact_targets") or []
        if not isinstance(rat, list):
            raise ValueError("result_artifact_targets must be an array")
        return cls(
            project_id=_as_str(data.get("project_id", "")).strip(),
            job_id=_as_str(data.get("job_id", "")).strip(),
            timeout_seconds=data.get("timeout_seconds"),
            stdout_max_bytes=data.get("stdout_max_bytes"),
            stderr_max_bytes=data.get("stderr_max_bytes"),
            env_allowlist=_as_str_map(data.get("env_allowlist")),
            result_artifact_targets=[item for item in rat if isinstance(item, dict)],
            journal_on_submit=_as_bool(data.get("journal_on_submit", False), False),
            journal_on_complete=_as_bool(data.get("journal_on_complete", False), False),
            journal_on_failure=_as_bool(data.get("journal_on_failure", True), True),
            local_model_id=(_as_str(data.get("local_model_id", "")).strip() or None),
            agent_role=(_as_str(data.get("agent_role", "")).strip() or None),
            idempotency_key=(_as_str(data.get("idempotency_key", "")).strip() or None),
            mutation_authority=(
                dict(data["mutation_authority"])
                if isinstance(data.get("mutation_authority"), dict)
                else None
            ),
        )


@dataclass
class ExecutionStatusResponse:
    ok: bool
    job: ExecutionJobRecord

    def to_dict(self) -> JsonObject:
        return {"ok": self.ok, **self.job.to_dict()}


@dataclass
class ExecutionOutputResponse:
    ok: bool
    project_id: str
    job_id: str
    status: str
    stdout: str
    stderr: str
    stdout_truncated: bool
    stderr_truncated: bool
    bytes_returned: int
    max_bytes: int
    stdout_window: TextWindow
    stderr_window: TextWindow
    stdout_path: str
    stderr_path: str
    last_update_time: str

    def to_dict(self) -> JsonObject:
        return {
            "ok": self.ok,
            "project_id": self.project_id,
            "job_id": self.job_id,
            "status": self.status,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "stdout_truncated": self.stdout_truncated,
            "stderr_truncated": self.stderr_truncated,
            "bytes_returned": self.bytes_returned,
            "max_bytes": self.max_bytes,
            "stdout_window": self.stdout_window.to_dict(),
            "stderr_window": self.stderr_window.to_dict(),
            "stdout_path": self.stdout_path,
            "stderr_path": self.stderr_path,
            "last_update_time": self.last_update_time,
        }


@dataclass
class ExecutionListResponse:
    ok: bool
    project_id: str
    count: int
    jobs: list[ExecutionJobRecord]
    capacity: CapacitySnapshot
    corrupt_job_files: list[CorruptJobFileRecord] = field(default_factory=list)

    def to_dict(self) -> JsonObject:
        return {
            "ok": self.ok,
            "project_id": self.project_id,
            "count": self.count,
            "jobs": [{"ok": True, **job.to_dict()} for job in self.jobs],
            "capacity": self.capacity.to_dict(),
            "corrupt_job_files": [item.to_dict() for item in self.corrupt_job_files],
        }


@dataclass
class ExecutionRegisterResponse:
    ok: bool
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
    registration_commit_id: str

    def to_dict(self) -> JsonObject:
        return asdict(self)


@dataclass
class CompactCapabilitiesResponse:
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
