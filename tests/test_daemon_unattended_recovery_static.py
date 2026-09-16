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


def test_daemon_supervisor_binds_expected_daemon_and_project_identity():
    assert "--expected-daemon-id 'pcmmad-daemon'" in SCRIPT
    assert "--expected-project-id 'RECEIVER-LAB'" in SCRIPT


def test_daemon_runtime_reinstall_is_transactional_and_requires_managed_quiescence():
    assert "recovery_program_tx.py" in SCRIPT
    assert "RECOVERY_INSTALL_REQUIRES_MANAGED_TASKS_STOPPED" in SCRIPT
    assert "RECOVERY_INSTALL_REQUIRES_RUNTIME_LISTENERS_STOPPED" in SCRIPT
    assert "PCMMAD_V30_Daemon_SYSTEM" in SCRIPT


def test_daemon_tasks_are_direct_python_owned_not_powershell_child_wrappers():
    assert "daemon_task_entry.py" in SCRIPT
    assert "$daemonAction=New-ScheduledTaskAction -Execute $daemonPython" in SCRIPT
    assert "$daemonSupervisorAction=New-ScheduledTaskAction -Execute $daemonPython" in SCRIPT
    assert "Register-ScheduledTask -TaskName 'PCMMAD_V30_Daemon_SYSTEM' -Action $daemonAction" in SCRIPT
    assert "Register-ScheduledTask -TaskName 'PCMMAD_V30_DaemonSupervisor_SYSTEM' -Action $daemonSupervisorAction" in SCRIPT

def test_daemon_entry_requires_existing_project_root_and_only_loads_nonsecret_machine_config():
    assert "DAEMON_PROJECT_ROOT_DOES_NOT_EXIST" in SCRIPT
    entry=SCRIPT.split("$daemonEntry=@'",1)[1].split("'@;Set-Content",1)[0]
    assert "RecoverySecret" not in entry
    assert "githome_api.dpapi" not in entry
    assert "ngrok_authtoken.dpapi" not in entry


def test_daemon_and_daemon_supervisor_prefer_recovery_bundled_python_over_live_receiver_venv():
    expected="$daemonPython=Join-Path $InstallRoot 'runtime\\Python312\\python.exe';if(-not(Test-Path $daemonPython)){$daemonPython=Join-Path $LiveReceiverRoot 'baseline\\pcmmad_receiver\\.venv\\Scripts\\python.exe'}"
    assert expected in SCRIPT


def test_workload_and_supervisor_task_restart_policies_are_separated():
    assert "$workloadSettings=New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit" in SCRIPT
    assert "$supervisorSettings=New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 999" in SCRIPT
    assert "PCMMAD_V30_Daemon_SYSTEM' -Action $daemonAction" in SCRIPT and "-Settings $workloadSettings" in SCRIPT
    assert "PCMMAD_V30_DaemonSupervisor_SYSTEM' -Action $daemonSupervisorAction" in SCRIPT and "-Settings $supervisorSettings" in SCRIPT


def test_ngrok_has_independent_health_supervisor_and_persistent_failure_budget():
    assert "ngrok_supervisor.py" in SCRIPT
    assert "PCMMAD_V30_NgrokSupervisor_SYSTEM" in SCRIPT
    assert "ngrok_supervisor.failure_state.json" in SCRIPT
    assert "daemon_supervisor.failure_state.json" in SCRIPT
    assert "receiver_supervisor.failure_state.json" in SCRIPT


def test_recovery_reinstall_delegates_manifest_validation_to_transaction_helper_and_preserves_mutable_state():
    assert "RECOVERY_INSTALL_REQUIRES_MANAGED_TASKS_STOPPED" in SCRIPT
    assert "RECOVERY_INSTALL_REQUIRES_RUNTIME_LISTENERS_STOPPED" in SCRIPT
    assert "recovery_program_tx.py" in SCRIPT
    helper=(ROOT/'supervisor'/'recovery_program_tx.py').read_text(encoding='utf-8')
    assert "INSTALLED_PROGRAM_MANIFEST_CORRUPT" in helper
    assert "PROGRAM_PATH_ESCAPE" in helper
    assert "Remove-Item -Recurse -Force $InstallRoot" not in SCRIPT



def test_receiver_and_ngrok_wrappers_cooperatively_reap_children_when_task_leaves_running_state():
    assert "Start-Process -FilePath $py" in SCRIPT
    assert "Get-ScheduledTask -TaskName 'PCMMAD_V30_Receiver_SYSTEM'" in SCRIPT
    assert "Get-ScheduledTask -TaskName 'PCMMAD_V30_Ngrok_SYSTEM'" in SCRIPT
    assert "Stop-Process -Id $child.Id -Force" in SCRIPT
    assert "job_wrapper.py" not in SCRIPT


def test_receiver_supervisor_wrapper_cooperatively_reaps_child_when_task_stops():
    assert "Get-ScheduledTask -TaskName 'PCMMAD_V30_Supervisor_SYSTEM'" in SCRIPT
    assert "receiver_supervisor.py" in SCRIPT and "Stop-Process -Id $child.Id -Force" in SCRIPT


def test_daemon_project_root_cannot_escape_receiver_lab_project_root():
    assert "DAEMON_PROJECT_ROOT_MUST_MATCH_RECEIVER_LAB" in SCRIPT
    assert "$expectedDaemonProject=[IO.Path]::GetFullPath((Join-Path $projects 'RECEIVER-LAB'))" in SCRIPT


def test_fresh_first_install_can_stage_while_live_is_up_but_existing_install_upgrade_requires_quiescence():
    assert "$requiresQuiescence=(Test-Path $programManifest)" in SCRIPT
    assert "if($requiresQuiescence)" in SCRIPT
    assert "RECOVERY_INSTALL_REQUIRES_MANAGED_TASKS_STOPPED" in SCRIPT
    assert "RECOVERY_INSTALL_REQUIRES_RUNTIME_LISTENERS_STOPPED" in SCRIPT


def test_daemon_uses_authoritative_project_handoff_generation_not_live_runtime_handoff():
    assert "SOURCE_HANDOFF_MISSING_AT_INSTALL" in SCRIPT
    assert "-m mvf_resident.project_handoff --source $sourceHandoff --project-root $DaemonProjectRoot" in SCRIPT
    entry=SCRIPT.split("$daemonEntry=@'",1)[1].split("'@;Set-Content",1)[0]
    assert "--handoff-root" in entry
    assert "project/'handoff'" in entry
    assert "live/'handoff'/'current'" not in entry
