from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "baseline" / "pcmmad_receiver"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

import lab_tools
import shared_core


def test_machine_roots_list_is_read_only_operator_scope():
    spec = lab_tools._TOOL_REGISTRY["machine.roots.list"]
    assert spec.category == "machine"
    assert spec.approval_required is False
    assert spec.mutating is False
    assert spec.side_effect_class == "read"
    traits = set(spec.effect_traits or [])
    assert {"operator_scope", "non_recursive", "bounded_results", "does_not_grant_mutation_authority"} <= traits


def test_machine_roots_list_reports_configured_mounts_without_recursion():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        mount_a = base / "a"; mount_b = base / "b"
        mount_a.mkdir(); mount_b.mkdir()
        with patch.object(shared_core, "MOUNT_TABLE", {"alpha": mount_a, "beta": mount_b}):
            envelope = lab_tools.dispatch_tool("machine.roots.list", {"include_drives": False})
        assert envelope["ok"] is True
        result = envelope["result"]
        assert result["ok"] is True
        assert result["scope"] == "operator_machine_read"
        assert result["recursive"] is False
        assert result["mutation_authority"] is False
        roots = result["roots"]
        assert [(x["name"], x["path"], x["allowed_root"]) for x in roots] == [
            ("alpha", str(mount_a), True), ("beta", str(mount_b), True)
        ]


def test_machine_roots_discovery_does_not_relax_project_scope_guard():
    project_source = (RUNTIME / "lab_tools_project.py").read_text(encoding="utf-8")
    assert "PROJECT_SCOPE_MISMATCH" in project_source
    assert "path escapes project root" in project_source
    machine_spec = lab_tools._TOOL_REGISTRY["machine.roots.list"]
    assert "operator_scope" in set(machine_spec.effect_traits or [])
    assert "project_scope_enforced" not in set(machine_spec.effect_traits or [])
