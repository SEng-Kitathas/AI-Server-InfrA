"""Typed API wire models for power routes, journals, file trees, and checkpoints."""

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
    _as_str_list,
)

JsonObject = MutableMapping[str, Any]


def _as_str_map(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items()}


@dataclass
class SyncExecRequest:
    project_id: str
    command: list[str]
    args: list[str] = field(default_factory=list)
    cwd: str | None = None
    timeout_seconds: int | None = None
    stdout_max_bytes: int | None = None
    stderr_max_bytes: int | None = None
    env: dict[str, str] = field(default_factory=dict)
    session_id: str = ""
    mutation_authority: dict[str, Any] | None = None

    @classmethod
    def from_json(cls, data: JsonObject) -> "SyncExecRequest":
        data = _require_object(data)
        command = _as_str_list(data.get("command"))
        if not command or any(not x for x in command):
            raise ValueError("command must be a non-empty string array")
        args = _as_str_list(data.get("args"))
        return cls(
            project_id=_as_str(data.get("project_id", "")),
            command=command,
            args=args,
            cwd=data.get("cwd"),
            timeout_seconds=data.get("timeout_seconds"),
            stdout_max_bytes=data.get("stdout_max_bytes"),
            stderr_max_bytes=data.get("stderr_max_bytes"),
            env=_as_str_map(data.get("env") or data.get("env_allowlist")),
            session_id=_as_str(data.get("session_id", "")).strip(),
            mutation_authority=(dict(data["mutation_authority"]) if isinstance(data.get("mutation_authority"), dict) else None),
        )


@dataclass
class PythonExecRequest:
    project_id: str
    code: str
    cwd: str | None = None
    timeout_seconds: int | None = None
    stdout_max_bytes: int | None = None
    stderr_max_bytes: int | None = None
    env: dict[str, str] = field(default_factory=dict)
    session_id: str = ""
    mutation_authority: dict[str, Any] | None = None

    @classmethod
    def from_json(cls, data: JsonObject) -> "PythonExecRequest":
        data = _require_object(data)
        return cls(
            project_id=_as_str(data.get("project_id", "")),
            code=_as_str(data.get("code", "")),
            cwd=data.get("cwd"),
            timeout_seconds=data.get("timeout_seconds"),
            stdout_max_bytes=data.get("stdout_max_bytes"),
            stderr_max_bytes=data.get("stderr_max_bytes"),
            env=_as_str_map(data.get("env") or data.get("env_allowlist")),
            session_id=_as_str(data.get("session_id", "")).strip(),
            mutation_authority=(dict(data["mutation_authority"]) if isinstance(data.get("mutation_authority"), dict) else None),
        )


@dataclass
class ReadManyRequest:
    project_id: str
    paths: list[str]
    max_bytes_each: int | None = None

    @classmethod
    def from_json(cls, data: JsonObject) -> "ReadManyRequest":
        data = _require_object(data)
        paths = _as_str_list(data.get("paths"))
        if not paths:
            raise ValueError("paths must be a non-empty array")
        return cls(
            project_id=_as_str(data.get("project_id", "")),
            paths=paths,
            max_bytes_each=data.get("max_bytes_each"),
        )


@dataclass
class WriteFileRequest:
    project_id: str
    path: str
    content: str
    mode: str = "overwrite"
    encoding: str = "utf-8"
    session_id: str = ""
    mutation_authority: dict[str, Any] | None = None

    @classmethod
    def from_json(cls, data: JsonObject) -> "WriteFileRequest":
        data = _require_object(data)
        return cls(
            project_id=_as_str(data.get("project_id", "")),
            path=_as_str(data.get("path", "")).strip(),
            content=_as_str(data.get("content", "")),
            mode=_as_str(data.get("mode", "overwrite"), "overwrite"),
            encoding=_as_str(data.get("encoding", "utf-8"), "utf-8"),
            session_id=_as_str(data.get("session_id", "")).strip(),
            mutation_authority=(dict(data["mutation_authority"]) if isinstance(data.get("mutation_authority"), dict) else None),
        )


@dataclass
class ZipReadRequest:
    zip_path: str
    project_id: str = ""
    entries: list[str] = field(default_factory=list)
    max_entry_bytes: int | None = 65536

    @classmethod
    def from_json(cls, data: JsonObject) -> "ZipReadRequest":
        data = _require_object(data)
        return cls(
            zip_path=_as_str(data.get("zip_path", "")).strip(),
            project_id=_as_str(data.get("project_id", "")),
            entries=_as_str_list(data.get("entries")),
            max_entry_bytes=data.get("max_entry_bytes", 65536),
        )


@dataclass
class WaitExecutionRequest:
    project_id: str
    job_id: str
    timeout_seconds: int | None = None
    max_bytes: int | None = None

    @classmethod
    def from_json(cls, data: JsonObject) -> "WaitExecutionRequest":
        data = _require_object(data)
        return cls(
            project_id=_as_str(data.get("project_id", "")),
            job_id=_as_str(data.get("job_id", "")),
            timeout_seconds=data.get("timeout_seconds"),
            max_bytes=data.get("max_bytes"),
        )


@dataclass
class JournalAppendRequest:
    project_id: str
    entry_type: str
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    session_id: str | None = None

    @classmethod
    def from_json(cls, data: JsonObject) -> "JournalAppendRequest":
        data = _require_object(data)
        return cls(
            project_id=_as_str(data.get("project_id", "")),
            entry_type=_as_str(data.get("entry_type", "note"), "note"),
            title=_as_str(data.get("title", "")),
            content=_as_str(data.get("content", "")),
            tags=_as_str_list(data.get("tags")),
            session_id=data.get("session_id"),
        )


@dataclass
class JournalReadRequest:
    project_id: str
    limit: int = 50

    @classmethod
    def from_json(cls, data: JsonObject) -> "JournalReadRequest":
        data = _require_object(data)
        return cls(project_id=_as_str(data.get("project_id", "")), limit=int(data.get("limit", 50)))


@dataclass
class CheckpointCreateRequest:
    project_id: str
    checkpoint_name: str | None = None

    @classmethod
    def from_json(cls, data: JsonObject) -> "CheckpointCreateRequest":
        data = _require_object(data)
        name = data.get("checkpoint_name")
        return cls(
            project_id=_as_str(data.get("project_id", "")),
            checkpoint_name=_as_str(name).strip() if name is not None else None,
        )


@dataclass
class SyncExecResponse:
    ok: bool
    status: str
    return_code: int
    stdout: str
    stderr: str
    stdout_truncated: bool
    stderr_truncated: bool
    stdout_bytes: int
    stderr_bytes: int
    stdout_path: str
    stderr_path: str
    stdout_window: JsonObject
    stderr_window: JsonObject
    duration_ms: int

    def to_dict(self) -> JsonObject:
        return asdict(self)


@dataclass
class ReadManyFileResult:
    content: str = ""
    size_bytes: int = 0
    truncated: bool = False
    error: str | None = None

    def to_dict(self) -> JsonObject:
        data = asdict(self)
        if self.error is None:
            data.pop("error", None)
        return data


@dataclass
class ReadManyResponse:
    ok: bool
    files: dict[str, JsonObject]
    read_count: int
    error_count: int

    def to_dict(self) -> JsonObject:
        return asdict(self)


@dataclass
class WriteFileResponse:
    ok: bool
    project_id: str
    path: str
    absolute_path: str
    bytes_written: int
    created: bool

    def to_dict(self) -> JsonObject:
        return asdict(self)


@dataclass
class ZipReadResponse:
    ok: bool
    zip_path: str
    listing: list[JsonObject]
    contents: dict[str, JsonObject]

    def to_dict(self) -> JsonObject:
        return asdict(self)


@dataclass
class WaitExecutionResponse:
    ok: bool
    job_id: str
    status: str
    timed_out: bool
    stdout: str
    stderr: str
    return_code: int | None
    duration_ms: int | None
    stdout_truncated: bool
    max_bytes: int | None

    def to_dict(self) -> JsonObject:
        return asdict(self)


@dataclass
class JournalEntry:
    time: str
    entry_type: str
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    session_id: str | None = None

    def to_dict(self) -> JsonObject:
        data = asdict(self)
        if self.session_id is None:
            data.pop("session_id", None)
        return data


@dataclass
class JournalAppendResponse:
    ok: bool
    project_id: str
    entry: JsonObject
    path: str

    def to_dict(self) -> JsonObject:
        return asdict(self)


@dataclass
class JournalReadResponse:
    ok: bool
    project_id: str
    count: int
    entries: list[JsonObject]

    def to_dict(self) -> JsonObject:
        return asdict(self)


@dataclass
class CheckpointCreateResponse:
    ok: bool
    project_id: str
    checkpoint_name: str
    path: str
    bytes: int
    time: str

    def to_dict(self) -> JsonObject:
        return asdict(self)
