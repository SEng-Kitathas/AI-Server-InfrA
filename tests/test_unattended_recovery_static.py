from __future__ import annotations
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_install_requires_elevation_and_system_tasks():
 s=(ROOT/'supervisor/install_unattended_recovery.ps1').read_text();assert 'ELEVATED_ADMIN_REQUIRED' in s;assert "-UserId 'SYSTEM'" in s;assert '-AtStartup' in s;assert 'ServiceAccount' in s
def test_runtime_launchers_do_not_read_user_environment():
 s=(ROOT/'supervisor/install_unattended_recovery.ps1').read_text();generated=s[s.index("$receiver=@'"):];assert 'GetEnvironmentVariable(' not in generated;assert "machine_config.json" in generated
def test_secrets_are_dpapi_localmachine_and_acl_restricted():
 s=(ROOT/'supervisor/RecoverySecret.psm1').read_text();assert 'DataProtectionScope]::LocalMachine' in s;assert "'SYSTEM:(F)'" in s and "'Administrators:(F)'" in s and '/inheritance:r' in s
def test_secret_cli_does_not_accept_secret_argument():
 s=(ROOT/'supervisor/recovery_secret.ps1').read_text();assert '[Console]::In.ReadToEnd()' in s;assert '[string]$Secret' not in s
def test_receiver_and_tunnel_are_independent_tasks():
 s=(ROOT/'supervisor/install_unattended_recovery.ps1').read_text();assert 'PCMMAD_V30_Receiver_SYSTEM' in s and 'PCMMAD_V30_Ngrok_SYSTEM' in s;assert 'start_receiver_system.ps1' in s and 'start_ngrok_system.ps1' in s
def test_tunnel_failure_cannot_restart_receiver_from_tunnel_launcher():
 s=(ROOT/'supervisor/install_unattended_recovery.ps1').read_text();t=s[s.index("$tunnel=@'"):s.index("'@;Set-Content",s.index("$tunnel=@'"))]
 assert '127.0.0.1:5000' in t.lower()
 assert 'Restart-PCMMAD' not in t and 'PCMMAD_V30_Receiver_SYSTEM' not in t and 'server.py' not in t
 if 'Stop-Process' in t: assert 'Stop-Process -Id $child.Id' in t
def test_ngrok_secret_materialized_only_in_acl_temp_and_deleted():
 s=(ROOT/'supervisor/install_unattended_recovery.ps1').read_text();t=s[s.index("$tunnel=@'"):s.index("'@;Set-Content",s.index("$tunnel=@'"))]
 assert 'ngrok-runtime-' in t and "'SYSTEM:(F)'" in t
 assert 'finally{' in t and 'Remove-Item -Force $tmp -ErrorAction SilentlyContinue' in t and '$token=$null' in t
