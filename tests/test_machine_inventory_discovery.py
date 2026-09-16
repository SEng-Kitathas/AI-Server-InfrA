from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "baseline" / "pcmmad_receiver"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

import lab_tools
import lab_tools_machine


def _dispatch(name: str, payload: dict, rows: object):
    fake = {"ok": True, "stdout": json.dumps(rows), "stderr": ""}
    with patch.object(lab_tools_machine, "run_subprocess_envelope", return_value=fake):
        envelope = lab_tools.dispatch_tool(name, payload)
    assert envelope["ok"] is True
    return envelope["result"]


def test_machine_processes_list_normalizes_identity_and_filters():
    rows = [
        {"ProcessId": 10, "ParentProcessId": 1, "Name": "python.exe", "ExecutablePath": "C:/Python/python.exe", "CommandLine": "python worker.py", "CreationDate": "20260915120000.000000-240"},
        {"ProcessId": 20, "ParentProcessId": 1, "Name": "other.exe", "ExecutablePath": "C:/other.exe", "CommandLine": "other", "CreationDate": "20260915120100.000000-240"},
    ]
    result = _dispatch("machine.processes.list", {"name_filter": "python", "limit": 10}, rows)
    assert result["scope"] == "operator_machine_read"
    assert result["mutation_authority"] is False
    assert result["count"] == 1
    row = result["processes"][0]
    assert row["pid"] == 10 and row["parent_pid"] == 1
    assert row["creation_identity"] == "20260915120000.000000-240"
    assert row["executable_path"] == "C:/Python/python.exe"


def test_machine_services_list_is_bounded_and_preserves_process_binding():
    rows = [
        {"Name": "SvcA", "DisplayName": "Service A", "State": "Running", "StartMode": "Auto", "ProcessId": 42, "PathName": "C:/svc.exe"},
        {"Name": "SvcB", "DisplayName": "Service B", "State": "Stopped", "StartMode": "Manual", "ProcessId": 0, "PathName": "C:/b.exe"},
    ]
    result = _dispatch("machine.services.list", {"limit": 1}, rows)
    assert result["count"] == 1 and result["matched_count"] == 2 and result["truncated"] is True
    assert result["services"][0]["process_id"] == 42
    assert result["mutation_authority"] is False


def test_machine_scheduled_tasks_list_filters_identity_without_actions():
    rows = [
        {"TaskPath": "\\", "TaskName": "PCMMAD_V30_Receiver", "State": "Ready"},
        {"TaskPath": "\\Microsoft\\", "TaskName": "Other", "State": "Ready"},
    ]
    result = _dispatch("machine.scheduled_tasks.list", {"name_filter": "PCMMAD", "limit": 10}, rows)
    assert result["count"] == 1
    assert result["scheduled_tasks"][0]["task_name"] == "PCMMAD_V30_Receiver"
    assert result["mutation_authority"] is False


def test_machine_inventory_capabilities_are_read_only_operator_scope():
    for name in ("machine.processes.list", "machine.services.list", "machine.scheduled_tasks.list"):
        spec = lab_tools._TOOL_REGISTRY[name]
        assert spec.category == "machine"
        assert spec.approval_required is False
        assert spec.mutating is False
        assert spec.side_effect_class == "read"
        traits = set(spec.effect_traits or [])
        assert {"operator_scope", "bounded_results", "identity_metadata", "does_not_grant_mutation_authority"} <= traits


def test_machine_inventory_rejects_unbounded_limit_before_subprocess():
    with patch.object(lab_tools_machine, "run_subprocess_envelope") as runner:
        try:
            lab_tools.dispatch_tool("machine.processes.list", {"limit": 501})
        except lab_tools.LabToolError as exc:
            assert exc.error_code == "BAD_REQUEST"
        else:
            raise AssertionError("unbounded limit unexpectedly accepted")
        runner.assert_not_called()


def test_machine_process_inspect_binds_creation_identity_and_rejects_stale_pid():
    rows = [{"ProcessId": 10, "ParentProcessId": 1, "Name": "python.exe", "ExecutablePath": "C:/Python/python.exe", "CommandLine": "python worker.py", "CreationDate": "20260915120000.000000-240"}]
    result = _dispatch("machine.process.inspect", {"pid": 10, "expected_creation_identity": "20260915120000.000000-240"}, rows)
    assert result["identity_current"] is True
    assert result["process"]["pid"] == 10
    assert result["mutation_authority"] is False
    fake = {"ok": True, "stdout": json.dumps(rows), "stderr": ""}
    with patch.object(lab_tools_machine, "run_subprocess_envelope", return_value=fake):
        try:
            lab_tools.dispatch_tool("machine.process.inspect", {"pid": 10, "expected_creation_identity": "stale"})
        except lab_tools.LabToolError as exc:
            assert exc.error_code == "PROCESS_IDENTITY_MISMATCH"
            assert exc.extra["observed_creation_identity"] == "20260915120000.000000-240"
        else:
            raise AssertionError("stale PID identity unexpectedly accepted")


def test_machine_service_inspect_requires_exact_service_name():
    rows = [{"Name": "SvcA", "DisplayName": "Service A", "State": "Running", "StartMode": "Auto", "ProcessId": 42, "PathName": "C:/svc.exe"}]
    result = _dispatch("machine.service.inspect", {"name": "svca"}, rows)
    assert result["identity_current"] is True
    assert result["service"]["name"] == "SvcA"
    assert result["service"]["process_id"] == 42


def test_machine_scheduled_task_inspect_requires_path_when_name_is_ambiguous():
    rows = [
        {"TaskPath": "\\", "TaskName": "Worker", "State": "Ready"},
        {"TaskPath": "\\Other\\", "TaskName": "Worker", "State": "Ready"},
    ]
    fake = {"ok": True, "stdout": json.dumps(rows), "stderr": ""}
    with patch.object(lab_tools_machine, "run_subprocess_envelope", return_value=fake):
        try:
            lab_tools.dispatch_tool("machine.scheduled_task.inspect", {"task_name": "Worker"})
        except lab_tools.LabToolError as exc:
            assert exc.error_code == "AMBIGUOUS_IDENTITY"
            assert "machine.scheduled_tasks.list" in exc.extra["lawful_next"]
        else:
            raise AssertionError("ambiguous task identity unexpectedly accepted")
    result = _dispatch("machine.scheduled_task.inspect", {"task_name": "Worker", "task_path": "\\Other\\"}, rows)
    assert result["scheduled_task"]["task_path"] == "\\Other\\"
    assert result["identity_current"] is True


def test_machine_inspect_capabilities_are_read_only_currentness_checks():
    for name in ("machine.process.inspect", "machine.service.inspect", "machine.scheduled_task.inspect"):
        spec = lab_tools._TOOL_REGISTRY[name]
        assert spec.approval_required is False
        assert spec.mutating is False
        assert spec.side_effect_class == "read"
        traits = set(spec.effect_traits or [])
        assert {"operator_scope", "exact_identity_required", "currentness_check", "identity_metadata", "does_not_grant_mutation_authority"} <= traits
