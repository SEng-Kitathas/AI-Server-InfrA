"""Primitive payload parsing helpers shared by lab tool registration surfaces."""

from __future__ import annotations
from typing import Any
from collections.abc import MutableMapping

from typing import Mapping

ToolPayload = Mapping[str, Any]
ToolResult = MutableMapping[str, Any]
JsonObject = MutableMapping[str, Any]


def payload_value(payload: ToolPayload, key: str, default: object | None = None) -> object | None:
    return payload.get(key, default)


def payload_str(payload: ToolPayload, key: str, default: str = "") -> str:
    value = payload_value(payload, key, default)
    return default if value is None else str(value)


def payload_optional_str(payload: ToolPayload, key: str) -> str | None:
    value = payload_value(payload, key)
    return None if value is None else str(value)


def payload_bool(payload: ToolPayload, key: str, default: bool = False) -> bool:
    value = payload_value(payload, key, default)
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return bool(value)


def payload_optional_int(payload: ToolPayload, key: str) -> int | None:
    value = payload_value(payload, key)
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return None


def payload_list_of_str(payload: ToolPayload, key: str) -> list[str]:
    value = payload_value(payload, key)
    return [str(item) for item in value] if isinstance(value, list) else []


def payload_mapping(payload: ToolPayload, key: str) -> JsonObject:
    value = payload_value(payload, key)
    return {str(key): item for key, item in value.items()} if isinstance(value, dict) else {}
