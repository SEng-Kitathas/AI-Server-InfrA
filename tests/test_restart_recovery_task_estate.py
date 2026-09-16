from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TEXT=(ROOT/"RESTART_RECEIVER_AND_NGROK.ps1").read_text(encoding="utf-8-sig")

def test_restart_prefers_recovery_system_task_estate_and_fixed_tunnel():
    assert 'machine_config.json' in TEXT
    assert 'PCMMAD_V30_Receiver_SYSTEM' in TEXT
    assert 'PCMMAD_V30_Ngrok_SYSTEM' in TEXT
    assert 'PCMMAD_V30_Supervisor_SYSTEM' in TEXT
    assert 'PCMMAD_V30_NgrokSupervisor_SYSTEM' in TEXT
    assert 'Stop-RecoveryTaskEstate' in TEXT
    assert TEXT.index('Stop-RecoveryTaskEstate') < TEXT.index('Stop-PcmmadStack', TEXT.index('Write-Stage "stopping"'))
    assert 'Start-ScheduledTask -TaskName $ReceiverTaskName' in TEXT
    assert 'Start-ScheduledTask -TaskName $NgrokTaskName' in TEXT
    assert '@("--url", $env:PCMMAD_NGROK_URL)' in TEXT
    assert 'ngrok public URL mismatch' in TEXT
    assert 'Start-RecoverySupervisors' in TEXT
    block=TEXT[TEXT.index('function Test-IsRecoverySupervisorProcess'):TEXT.index('function Stop-RecoveryTaskEstate')]
    assert 'PCMMAD_V30_Receiver_SYSTEM' in block
    assert 'PCMMAD_V30_Ngrok_SYSTEM' in block
    assert 'PCMMAD_V30_Daemon_SYSTEM' not in block
    assert 'PCMMAD_V30_BrowserBridge_SYSTEM' not in block

def test_reservation_only_exits_before_machine_state_hydration():
    reserve=TEXT.index('if ($RestartIntensityReservationOnly)')
    hydrate=TEXT.index('Import-RecoveryMachineConfig', reserve)
    assert reserve < hydrate
