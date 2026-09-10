"""Shared API wire helpers for envelopes, warnings, and typed response primitives."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from collections.abc import MutableMapping

from .control_plane_models import (
    CapacitySnapshot,
    CompactControlSurfaceDescriptor,
    CorruptJobFileRecord,
    ExecutionJobRecord,
    ServerCapabilityRouterDescriptor,
    TextWindow,
)

JsonObject = MutableMapping[str, Any]


def _require_object(data: Any) -> JsonObject:
    if not isinstance(data, dict):
        raise ValueError("JSON request body must be an object")
    return data


def _as_str(value: Any, default: str = "") -> str:
    return str(value if value is not None else default)


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized_value = value.strip().lower()
        if normalized_value in {"1", "true", "yes", "on"}:
            return True
        if normalized_value in {"0", "false", "no", "off"}:
            return False
    return bool(value)


def _as_int(value: Any, default: int | None = None) -> int | None:
    if value is None or value == "":
        return default
    return int(value)


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _as_str_map(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items()}


@dataclass
class ErrorEnvelope:
    ok: bool
    error_code: str
    message: str
    time: str | None = None
    extra: JsonObject = field(default_factory=dict)

    def to_dict(self) -> JsonObject:
        data = {"ok": self.ok, "error_code": self.error_code, "message": self.message}
        if self.time is not None:
            data["time"] = self.time
        data.update(self.extra)
        return data


@dataclass
class WarningItem:
    kind: str
    message: str
    path: str | None = None

    def to_dict(self) -> JsonObject:
        data = {"kind": self.kind, "message": self.message}
        if self.path is not None:
            data["path"] = self.path
        return data


@dataclass
class IndexCacheStats:
    entries: int
    bytes: int
    max_bytes: int
    ttl_seconds: int
    source_currentness: str = "ttl_only"

    def to_dict(self) -> JsonObject:
        return asdict(self)
