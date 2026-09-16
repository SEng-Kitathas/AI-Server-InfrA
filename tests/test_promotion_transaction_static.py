from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
INSTALL=(ROOT/'supervisor'/'install_unattended_recovery.ps1').read_text(encoding='utf-8')
ROLLBACK=(ROOT/'supervisor'/'rollback_unattended_recovery.ps1').read_text(encoding='utf-8')

def test_installer_uses_program_transaction_and_task_definition_rollback():
    assert 'recovery_program_tx.py' in INSTALL
    assert ' stage --bundle-source ' in INSTALL
    assert 'Export-ScheduledTask -TaskName $taskName' in INSTALL
    assert 'Unregister-ScheduledTask -TaskName $taskName' in INSTALL
    assert 'Register-ScheduledTask -TaskName $taskName -Xml $xml -Force' in INSTALL
    assert ' rollback --tx $programTx --install-root $InstallRoot' in INSTALL

def test_handoff_activation_is_after_tasks_and_promotion_backup_archive():
    task_pos=INSTALL.index("Register-ScheduledTask -TaskName 'PCMMAD_V30_NgrokSupervisor_SYSTEM'")
    archive_pos=INSTALL.index(' commit --tx $programTx --archive-root $promotionBackupRoot')
    publish_pos=INSTALL.index('-m mvf_resident.project_handoff --source $sourceHandoff')
    assert task_pos < archive_pos < publish_pos

def test_explicit_handoff_source_and_host_singleton_are_bound():
    assert '[string]$HandoffSource=""' in INSTALL
    assert '[IO.Path]::GetFullPath($HandoffSource)' in INSTALL
    entry=INSTALL.split("$daemonEntry=@'",1)[1].split("'@;Set-Content",1)[0]
    assert '--handoff-root' in entry and "project/'handoff'" in entry
    assert '--host-lock' in entry and "daemon_identity.lock" in entry
    assert "live/'handoff'/'current'" not in entry

def test_rollback_preserves_daemon_memory_generations_budgets_and_receipts_by_not_deleting_them():
    assert "Join-Path $DaemonProjectRoot 'daemon'" not in ROLLBACK.split('# Restore immutable program generation')[0]
    assert 'Remove-Item -Recurse -Force $DaemonProjectRoot' not in ROLLBACK
    assert 'restart_events' not in ROLLBACK
    assert 'receipt.json' not in ROLLBACK
    assert "Remove-Item -Force $current" in ROLLBACK  # only pointer may be removed when prior state was absent
    assert "generations" in ROLLBACK

def test_rollback_requires_quiescence_and_restores_task_xml_and_prior_pointer():
    assert 'ROLLBACK_REQUIRES_MANAGED_TASKS_STOPPED' in ROLLBACK
    assert 'ROLLBACK_REQUIRES_RUNTIME_LISTENERS_STOPPED' in ROLLBACK
    assert 'Register-ScheduledTask -TaskName $taskName -Xml' in ROLLBACK
    assert 'OLD_HANDOFF_POINTER_SCHEMA_MISMATCH' in ROLLBACK
    assert 'OLD_HANDOFF_MANIFEST_MISMATCH' in ROLLBACK
