from __future__ import annotations
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
INSTALL=(ROOT/'supervisor'/'install_unattended_recovery.ps1').read_text(encoding='utf-8')
SUP=(ROOT/'supervisor'/'receiver_supervisor.py').read_text(encoding='utf-8')
SETUP=(ROOT/'SETUP_PCMMAD_RUNTIME.ps1').read_text(encoding='utf-8')
REQ=(ROOT/'baseline'/'pcmmad_receiver'/'requirements.txt').read_text(encoding='utf-8').lower()
PYPROJECT=(ROOT/'pyproject.toml').read_text(encoding='utf-8').lower()

def test_browser_bridge_is_managed_boot_workload_with_independent_supervisor():
    for token in ('PCMMAD_V30_BrowserBridge_SYSTEM','PCMMAD_V30_BrowserBridgeSupervisor_SYSTEM','start_browser_bridge_system.ps1','start_browser_bridge_supervisor_system.ps1','http://127.0.0.1:4471/health','browser_bridge_supervisor.failure_state.json','browser_bridge_supervisor.maintenance_hold'):
        assert token in INSTALL
    assert "@('PCMMAD_V30_BrowserBridge_SYSTEM','start_browser_bridge_system.ps1')" in INSTALL
    assert "--expected-health-service','pcmmad_browser_bridge'" in INSTALL

def test_browser_preflight_occurs_before_program_transaction_and_is_not_fake_health():
    pre=INSTALL.index('BROWSER_BRIDGE_RUNTIME_MISSING_RUN_SETUP_PCMMAD_RUNTIME');tx=INSTALL.index('recovery_program_tx.py');assert pre<tx
    assert 'import flask,playwright' in INSTALL
    assert 'BROWSER_BRIDGE_SUPPORTED_SYSTEM_BROWSER_MISSING' in INSTALL
    assert 'PCMMAD_BROWSER_DEFAULT_CHANNEL' in INSTALL
    assert '--expected-health-service' in SUP

def test_runtime_setup_declares_and_verifies_playwright():
    assert 'playwright>=1,<2' in REQ
    assert 'playwright>=1,<2' in PYPROJECT
    assert 'import flask, requests, bs4, playwright' in SETUP

def test_gate_file_and_security_mode_are_bound_into_installed_workload():
    assert 'PCMMAD_BROWSER_BRIDGE_GATE_FILE' in INSTALL
    assert "browser_bridge_gate.json" in INSTALL
    assert "PCMMAD_BROWSER_DEFAULT_CHANNEL" in INSTALL
