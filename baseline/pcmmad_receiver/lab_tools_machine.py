"""Read-only operator/machine discovery capabilities."""
from __future__ import annotations

import json
import os
from collections.abc import Callable, MutableMapping
from pathlib import Path
from typing import Any

from server_hardening import run_subprocess_envelope

JsonObject = MutableMapping[str, Any]
Registrar = Callable[..., Any]


def _rows_from_powershell(script: str, error_cls: type[Exception]) -> list[dict[str, Any]]:
    if os.name != "nt":
        raise error_cls("PLATFORM_UNSUPPORTED", "machine discovery currently requires Windows", 501, platform=os.name)
    stable_cwd = Path(os.environ.get("SystemRoot") or os.getcwd()).resolve()
    result = run_subprocess_envelope(
        ["powershell.exe", "-NoProfile", "-Command", script],
        cwd=stable_cwd,
        timeout_seconds=15, stdout_max_bytes=524288, stderr_max_bytes=65536,
    )
    if not result.get("ok"):
        raise error_cls("MACHINE_DISCOVERY_FAILED", str(result.get("stderr") or result.get("stdout") or result.get("error") or "machine discovery failed"), 503, result=result)
    raw = str(result.get("stdout") or "").strip()
    if not raw:
        return []
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise error_cls("MACHINE_DISCOVERY_DECODE_FAILED", "machine discovery returned invalid JSON", 502) from exc
    if isinstance(decoded, dict):
        return [decoded]
    if isinstance(decoded, list):
        return [row for row in decoded if isinstance(row, dict)]
    raise error_cls("MACHINE_DISCOVERY_DECODE_FAILED", "machine discovery JSON must be an object or array", 502)


def _limit_filter(payload: JsonObject) -> tuple[str, int]:
    needle = str(payload.get("name_filter") or "").strip().casefold()
    limit = int(payload.get("limit", 100))
    if limit < 1 or limit > 500:
        raise ValueError("limit must be between 1 and 500")
    return needle, limit


def _bounded(rows: list[dict[str, Any]], needle: str, limit: int, fields: tuple[str, ...]) -> tuple[list[dict[str, Any]], int, bool]:
    if needle:
        rows = [row for row in rows if any(needle in str(row.get(field) or "").casefold() for field in fields)]
    matched = len(rows)
    return rows[:limit], matched, matched > limit


def _processes(payload: JsonObject, error_cls: type[Exception]) -> JsonObject:
    try:
        needle, limit = _limit_filter(payload)
    except ValueError as exc:
        raise error_cls("BAD_REQUEST", str(exc), 400) from exc
    rows = _rows_from_powershell(
        "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine,CreationDate | ConvertTo-Json -Compress -Depth 3",
        error_cls,
    )
    normalized = [{
        "pid": int(row.get("ProcessId") or 0),
        "parent_pid": int(row.get("ParentProcessId") or 0) or None,
        "name": str(row.get("Name") or ""),
        "executable_path": str(row.get("ExecutablePath") or "") or None,
        "command_line": str(row.get("CommandLine") or "") or None,
        "creation_identity": str(row.get("CreationDate") or "") or None,
    } for row in rows if int(row.get("ProcessId") or 0) > 0]
    selected, matched, truncated = _bounded(normalized, needle, limit, ("name", "executable_path", "command_line"))
    return {"ok": True, "scope": "operator_machine_read", "platform": "windows", "processes": selected, "count": len(selected), "matched_count": matched, "limit": limit, "truncated": truncated, "mutation_authority": False}


def _services(payload: JsonObject, error_cls: type[Exception]) -> JsonObject:
    try:
        needle, limit = _limit_filter(payload)
    except ValueError as exc:
        raise error_cls("BAD_REQUEST", str(exc), 400) from exc
    rows = _rows_from_powershell(
        "Get-CimInstance Win32_Service | Select-Object Name,DisplayName,State,StartMode,ProcessId,PathName | ConvertTo-Json -Compress -Depth 3",
        error_cls,
    )
    normalized = [{
        "name": str(row.get("Name") or ""),
        "display_name": str(row.get("DisplayName") or ""),
        "state": str(row.get("State") or ""),
        "start_mode": str(row.get("StartMode") or ""),
        "process_id": int(row.get("ProcessId") or 0) or None,
        "path_name": str(row.get("PathName") or "") or None,
    } for row in rows]
    selected, matched, truncated = _bounded(normalized, needle, limit, ("name", "display_name", "path_name"))
    return {"ok": True, "scope": "operator_machine_read", "platform": "windows", "services": selected, "count": len(selected), "matched_count": matched, "limit": limit, "truncated": truncated, "mutation_authority": False}


def _scheduled_tasks(payload: JsonObject, error_cls: type[Exception]) -> JsonObject:
    try:
        needle, limit = _limit_filter(payload)
    except ValueError as exc:
        raise error_cls("BAD_REQUEST", str(exc), 400) from exc
    rows = _rows_from_powershell(
        "Get-ScheduledTask | Select-Object TaskPath,TaskName,State | ConvertTo-Json -Compress -Depth 3",
        error_cls,
    )
    normalized = [{
        "task_path": str(row.get("TaskPath") or ""),
        "task_name": str(row.get("TaskName") or ""),
        "state": str(row.get("State") or ""),
    } for row in rows]
    selected, matched, truncated = _bounded(normalized, needle, limit, ("task_path", "task_name"))
    return {"ok": True, "scope": "operator_machine_read", "platform": "windows", "scheduled_tasks": selected, "count": len(selected), "matched_count": matched, "limit": limit, "truncated": truncated, "mutation_authority": False}


def register_machine_tools(register_tool: Registrar, *, error_cls: type[Exception]) -> None:
    common = {
        "danger_tier": "low", "category": "machine", "approval_required": False, "mutating": False, "side_effect_class": "read",
        "effect_traits": ["operator_scope", "bounded_results", "identity_metadata", "does_not_grant_mutation_authority"],
        "input_schema": {"type": "object", "properties": {"name_filter": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 500}}, "additionalProperties": False},
    }

    @register_tool("machine.processes.list", "List bounded Windows process identity metadata.", **common)
    def tool_machine_processes_list(payload: JsonObject) -> JsonObject:
        return _processes(payload, error_cls)

    @register_tool("machine.services.list", "List bounded Windows service identity/state metadata.", **common)
    def tool_machine_services_list(payload: JsonObject) -> JsonObject:
        return _services(payload, error_cls)

    @register_tool("machine.scheduled_tasks.list", "List bounded Windows scheduled-task identity/state metadata.", **common)
    def tool_machine_scheduled_tasks_list(payload: JsonObject) -> JsonObject:
        return _scheduled_tasks(payload, error_cls)
