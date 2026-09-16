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


def _process_inspect(payload: JsonObject, error_cls: type[Exception]) -> JsonObject:
    try:
        pid = int(payload.get("pid") or 0)
    except (TypeError, ValueError) as exc:
        raise error_cls("BAD_REQUEST", "pid must be a positive integer", 400) from exc
    if pid <= 0:
        raise error_cls("BAD_REQUEST", "pid must be a positive integer", 400)
    rows = _rows_from_powershell(
        "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine,CreationDate | ConvertTo-Json -Compress -Depth 3",
        error_cls,
    )
    match = next((row for row in rows if int(row.get("ProcessId") or 0) == pid), None)
    if match is None:
        raise error_cls("NOT_FOUND", "process not found", 404, pid=pid)
    current_creation = str(match.get("CreationDate") or "") or None
    expected = str(payload.get("expected_creation_identity") or "").strip() or None
    if expected is not None and current_creation != expected:
        raise error_cls(
            "PROCESS_IDENTITY_MISMATCH",
            "process creation identity does not match current PID occupant",
            409,
            pid=pid,
            expected_creation_identity=expected,
            observed_creation_identity=current_creation,
        )
    return {
        "ok": True,
        "scope": "operator_machine_read",
        "platform": "windows",
        "process": {
            "pid": pid,
            "parent_pid": int(match.get("ParentProcessId") or 0) or None,
            "name": str(match.get("Name") or ""),
            "executable_path": str(match.get("ExecutablePath") or "") or None,
            "command_line": str(match.get("CommandLine") or "") or None,
            "creation_identity": current_creation,
        },
        "identity_current": True,
        "mutation_authority": False,
    }


def _service_inspect(payload: JsonObject, error_cls: type[Exception]) -> JsonObject:
    name = str(payload.get("name") or "").strip()
    if not name:
        raise error_cls("BAD_REQUEST", "name is required", 400)
    rows = _rows_from_powershell(
        "Get-CimInstance Win32_Service | Select-Object Name,DisplayName,State,StartMode,ProcessId,PathName | ConvertTo-Json -Compress -Depth 3",
        error_cls,
    )
    matches = [row for row in rows if str(row.get("Name") or "").casefold() == name.casefold()]
    if not matches:
        raise error_cls("NOT_FOUND", "service not found", 404, name=name)
    if len(matches) != 1:
        raise error_cls("AMBIGUOUS_IDENTITY", "service name resolved to multiple rows", 409, name=name, count=len(matches))
    row = matches[0]
    return {
        "ok": True,
        "scope": "operator_machine_read",
        "platform": "windows",
        "service": {
            "name": str(row.get("Name") or ""),
            "display_name": str(row.get("DisplayName") or ""),
            "state": str(row.get("State") or ""),
            "start_mode": str(row.get("StartMode") or ""),
            "process_id": int(row.get("ProcessId") or 0) or None,
            "path_name": str(row.get("PathName") or "") or None,
        },
        "identity_current": True,
        "mutation_authority": False,
    }


def _scheduled_task_inspect(payload: JsonObject, error_cls: type[Exception]) -> JsonObject:
    task_name = str(payload.get("task_name") or "").strip()
    task_path = str(payload.get("task_path") or "").strip() or None
    if not task_name:
        raise error_cls("BAD_REQUEST", "task_name is required", 400)
    rows = _rows_from_powershell(
        "Get-ScheduledTask | Select-Object TaskPath,TaskName,State | ConvertTo-Json -Compress -Depth 3",
        error_cls,
    )
    matches = [row for row in rows if str(row.get("TaskName") or "").casefold() == task_name.casefold()]
    if task_path is not None:
        matches = [row for row in matches if str(row.get("TaskPath") or "").casefold() == task_path.casefold()]
    if not matches:
        raise error_cls("NOT_FOUND", "scheduled task not found", 404, task_name=task_name, task_path=task_path)
    if len(matches) != 1:
        raise error_cls(
            "AMBIGUOUS_IDENTITY",
            "scheduled task name is ambiguous; provide task_path",
            409,
            task_name=task_name,
            count=len(matches),
            lawful_next=["machine.scheduled_tasks.list"],
        )
    row = matches[0]
    return {
        "ok": True,
        "scope": "operator_machine_read",
        "platform": "windows",
        "scheduled_task": {
            "task_path": str(row.get("TaskPath") or ""),
            "task_name": str(row.get("TaskName") or ""),
            "state": str(row.get("State") or ""),
        },
        "identity_current": True,
        "mutation_authority": False,
    }


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

    inspect_traits = ["operator_scope", "exact_identity_required", "currentness_check", "identity_metadata", "does_not_grant_mutation_authority"]

    @register_tool(
        "machine.process.inspect",
        "Inspect one current process identity by PID and optionally verify its creation identity.",
        "low", category="machine", approval_required=False, mutating=False, side_effect_class="read",
        effect_traits=inspect_traits,
        input_schema={
            "type": "object",
            "properties": {"pid": {"type": "integer", "minimum": 1}, "expected_creation_identity": {"type": "string", "minLength": 1}},
            "required": ["pid"],
            "additionalProperties": False,
        },
    )
    def tool_machine_process_inspect(payload: JsonObject) -> JsonObject:
        return _process_inspect(payload, error_cls)

    @register_tool(
        "machine.service.inspect",
        "Inspect one Windows service by exact service name.",
        "low", category="machine", approval_required=False, mutating=False, side_effect_class="read",
        effect_traits=inspect_traits,
        input_schema={"type": "object", "properties": {"name": {"type": "string", "minLength": 1}}, "required": ["name"], "additionalProperties": False},
    )
    def tool_machine_service_inspect(payload: JsonObject) -> JsonObject:
        return _service_inspect(payload, error_cls)

    @register_tool(
        "machine.scheduled_task.inspect",
        "Inspect one Windows scheduled task by exact name and optional path.",
        "low", category="machine", approval_required=False, mutating=False, side_effect_class="read",
        effect_traits=inspect_traits,
        input_schema={
            "type": "object",
            "properties": {"task_name": {"type": "string", "minLength": 1}, "task_path": {"type": "string", "minLength": 1}},
            "required": ["task_name"],
            "additionalProperties": False,
        },
    )
    def tool_machine_scheduled_task_inspect(payload: JsonObject) -> JsonObject:
        return _scheduled_task_inspect(payload, error_cls)
