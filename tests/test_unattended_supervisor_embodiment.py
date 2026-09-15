from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_unattended_recovery_embodies_authenticated_system_supervisor():
    s=(ROOT/"supervisor/install_unattended_recovery.ps1").read_text(encoding="utf-8")
    assert "receiver_supervisor.py') $InstallRoot" in s
    assert "start_supervisor_system.ps1" in s
    assert "PCMMAD_V30_Supervisor_SYSTEM" in s
    assert "PCMMAD_V30_Receiver_SYSTEM" in s
    assert "Unprotect-PCMMADRecoverySecret (Join-Path $root 'githome_api.dpapi')" in s
    assert "UriBuilder" in s and "lab/health" in s
    assert "--stop-file" in s and "--lock-file" in s
    assert "New-ScheduledTaskPrincipal -UserId 'SYSTEM'" in s

def test_standalone_system_supervisor_installer_fails_closed():
    s=(ROOT/"supervisor/install_receiver_supervisor_task.ps1").read_text(encoding="utf-8")
    assert "STANDALONE_SYSTEM_SUPERVISOR_INSTALL_DISABLED_USE_INSTALL_UNATTENDED_RECOVERY" in s


def test_unattended_installer_local_dependencies_exist():
    sup=ROOT/"supervisor"
    for name in ["RecoverySecret.psm1","breakglass_restore.ps1","receiver_supervisor.py"]:
        assert (sup/name).is_file(), name
