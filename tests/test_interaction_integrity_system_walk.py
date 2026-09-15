from __future__ import annotations

import importlib.util
import json
import tempfile
from types import SimpleNamespace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def _text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")

def test_bound_hitl_exactness_does_not_become_universal_gate():
    approval = _text("tests/test_bound_approval_dispatch.py")
    memory = _text("baseline/pcmmad_receiver/lab_tools_memory.py")
    assert "test_exact_challenge_executes_once_and_reports_bound_mode" in approval
    start = memory.index('name="memory.profiles.list"')
    block = memory[start:start + 1400]
    assert "approval_required=False" in block
    assert "mutating=False" in block

def test_project_scope_guard_has_lawful_broader_filesystem_route():
    project = _text("baseline/pcmmad_receiver/lab_tools_project.py")
    filesystem = _text("baseline/pcmmad_receiver/lab_tools_filesystem.py")
    assert "path escapes project root" in project
    assert "allow_absolute=True" in filesystem
    for name in ("fs.read", "fs.glob", "fs.grep", "fs.tree"):
        assert name in filesystem

def test_maintenance_hold_is_bounded_not_a_global_availability_deadlock():
    path = ROOT / "supervisor/receiver_supervisor.py"
    spec = importlib.util.spec_from_file_location("interaction_supervisor", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    with tempfile.TemporaryDirectory() as td:
        hold = Path(td) / "hold.json"
        hold.write_text(json.dumps({"desired_state": "STOPPED", "expires_at_epoch": 99, "operator_id": "op", "reason": "maintenance"}), encoding="utf-8")
        expired = mod.hold_state(hold, now_epoch=100)
        assert expired["hold"] is False
        hold.write_text("not-json", encoding="utf-8")
        malformed = mod.hold_state(hold, now_epoch=100)
        assert malformed["hold"] is False
        hold.write_text(json.dumps({"desired_state": "STOPPED", "expires_at_epoch": 150, "operator_id": "op", "reason": "maintenance"}), encoding="utf-8")
        active = mod.hold_state(hold, now_epoch=100)
        assert active["hold"] is True

def test_profile_discovery_is_ingress_edge_not_dead_end():
    memory = _text("baseline/pcmmad_receiver/lab_tools_memory.py")
    assert 'name="memory.profiles.list"' in memory
    assert '"memory.read"' in memory
    assert '"memory.search"' in memory
    assert '"hydration"' in memory
    assert '"source_currentness_check"' in memory


def test_project_scope_mismatch_points_to_lawful_filesystem_recovery():
    import sys
    runtime = ROOT / "baseline" / "pcmmad_receiver"
    if str(runtime) not in sys.path:
        sys.path.insert(0, str(runtime))
    import lab_tools_project as project

    class E(Exception):
        def __init__(self, code, message, status=400, **extra):
            super().__init__(message)
            self.code, self.status, self.extra = code, status, extra

    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        dep = SimpleNamespace(
            error_cls=E,
            ensure_project_layout=lambda payload: "p",
            get_project_root=lambda project_id: root,
            ensure_parent=lambda path: None,
        )
        try:
            project._project_write_payload({"project_id": "p", "path": "../outside.txt", "content": "x"}, dep)
        except E as exc:
            assert exc.code == "PROJECT_SCOPE_MISMATCH"
            assert exc.extra["scope"] == "project"
            assert "fs.write" in exc.extra["lawful_next"]
            assert "fs.write" in exc.extra["recovery"]
        else:
            raise AssertionError("project escape unexpectedly succeeded")
