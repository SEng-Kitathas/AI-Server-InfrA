from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_launcher_exposes_explicit_force_restart_without_changing_default():
    launcher = (ROOT / "PCMMAD.ps1").read_text(encoding="utf-8")
    assert "[switch]$ForceRestart" in launcher
    assert "-ForceRestart:$ForceRestart" in launcher
    assert launcher.count("-ForceRestart:$ForceRestart") == 2
    assert '[string]$Action = "Status"' in launcher

def test_repo_manual_helper_uses_launcher_force_instead_of_deleting_intensity_state():
    helper = (ROOT / "restart_pcmmad_receiver.bat").read_text(encoding="utf-8")
    folded = helper.casefold()
    assert "%~dp0" in helper
    assert "PCMMAD.ps1" in helper
    assert "-Action Restart -ForceRestart" in helper
    assert "restart_intensity_state" not in folded
    assert "remove-item" not in folded

def test_autonomous_restart_adapter_remains_intensity_governed_by_default():
    adapter = (ROOT / "baseline" / "pcmmad_receiver" / "restart_control.py").read_text(encoding="utf-8")
    assert '"-Action", "Restart"' in adapter
    assert "ForceRestart" not in adapter
