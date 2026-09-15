from __future__ import annotations
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=(ROOT/'supervisor'/'install_unattended_recovery.ps1').read_text(encoding='utf-8')

def test_daemon_runtime_is_copied_as_independent_bundle():
    assert 'MVF_DAEMON_SOURCE_MISSING' in SCRIPT
    assert "daemon_runtime" in SCRIPT
    assert "mvf_resident" in SCRIPT

def test_daemon_has_independent_system_task_and_supervisor_task():
    assert 'PCMMAD_V30_Daemon_SYSTEM' in SCRIPT
    assert 'PCMMAD_V30_DaemonSupervisor_SYSTEM' in SCRIPT
    assert 'start_daemon_system.ps1' in SCRIPT
    assert 'start_daemon_supervisor_system.ps1' in SCRIPT

def test_daemon_supervisor_has_separate_lock_hold_receipt_and_schema_family():
    assert 'daemon_supervisor_receipt.json' in SCRIPT
    assert 'daemon_supervisor.maintenance_hold' in SCRIPT
    assert 'daemon_supervisor.lock' in SCRIPT
    assert "--expected-schema-family 'mvf.daemon-health.'" in SCRIPT

def test_existing_receiver_ngrok_supervisor_tasks_remain_present():
    for name in ['PCMMAD_V30_Receiver_SYSTEM','PCMMAD_V30_Ngrok_SYSTEM','PCMMAD_V30_Supervisor_SYSTEM']:
        assert name in SCRIPT

def test_daemon_project_root_is_explicit_and_not_coopted_from_state_or_continuity():
    assert 'DAEMON_PROJECT_ROOT' in SCRIPT
    assert "Join-Path $daemonProject 'daemon'" in SCRIPT
    assert "Join-Path $daemonProject 'state'" not in SCRIPT
    assert "Join-Path $daemonProject 'continuity'" not in SCRIPT

def test_daemon_workload_does_not_receive_recovery_secret_as_cognitive_authority():
    daemon_block=SCRIPT.split("$daemon=@'",1)[1].split("'@;Set-Content",1)[0]
    assert 'GITHOME_API_KEY' not in daemon_block
    assert 'ngrok_authtoken' not in daemon_block
    assert 'RecoverySecret' not in daemon_block


def test_daemon_url_is_exported_to_receiver_environment():
    assert "PCMMAD_DAEMON_URL" in SCRIPT
    assert "http://127.0.0.1:" in SCRIPT
