param(
 [Parameter(Mandatory=$true)][string]$BundleSource,
 [string]$InstallRoot="$env:ProgramData\PCMMAD\Recovery",
 [string]$LiveReceiverRoot="C:\Users\ancal\Desktop\PCMMAD_LABORATORY_RUNTIME_V30_RC1\PCMMAD_receiver",
 [string]$DaemonProjectRoot="",
 [int]$DaemonPort=5015
)
$ErrorActionPreference='Stop'
$id=[Security.Principal.WindowsIdentity]::GetCurrent();$wp=New-Object Security.Principal.WindowsPrincipal($id)
if(-not $wp.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'ELEVATED_ADMIN_REQUIRED_FOR_ONE_TIME_RECOVERY_INSTALL'}
New-Item -ItemType Directory -Force $InstallRoot|Out-Null
Copy-Item -Recurse -Force (Join-Path $BundleSource '*') $InstallRoot
Copy-Item -Force (Join-Path $PSScriptRoot 'RecoverySecret.psm1') $InstallRoot
Copy-Item -Force (Join-Path $PSScriptRoot 'breakglass_restore.ps1') $InstallRoot
Copy-Item -Force (Join-Path $PSScriptRoot 'receiver_supervisor.py') $InstallRoot
$daemonSource=Join-Path (Split-Path -Parent $PSScriptRoot) 'mvf_resident';if(-not(Test-Path $daemonSource)){throw 'MVF_DAEMON_SOURCE_MISSING'};$daemonRuntime=Join-Path $InstallRoot 'daemon_runtime';New-Item -ItemType Directory -Force $daemonRuntime|Out-Null;Copy-Item -Recurse -Force $daemonSource (Join-Path $daemonRuntime 'mvf_resident')
Import-Module (Join-Path $InstallRoot 'RecoverySecret.psm1') -Force
$api=[Environment]::GetEnvironmentVariable('GITHOME_API_KEY','User');if([string]::IsNullOrWhiteSpace($api)){throw 'USER_API_KEY_MISSING_AT_INSTALL'}
[void](Protect-PCMMADRecoverySecret -Secret $api -Path (Join-Path $InstallRoot 'githome_api.dpapi'))
$cfgPath=Join-Path $env:LOCALAPPDATA 'ngrok\ngrok.yml';if(-not(Test-Path $cfgPath)){throw 'NGROK_USER_CONFIG_MISSING_AT_INSTALL'}
$cfg=Get-Content -Raw $cfgPath;$match=[regex]::Match($cfg,'(?m)^\s*authtoken:\s*(.+?)\s*$');if(-not $match.Success){throw 'NGROK_AUTHTOKEN_MISSING_AT_INSTALL'}
[void](Protect-PCMMADRecoverySecret -Secret $match.Groups[1].Value.Trim() -Path (Join-Path $InstallRoot 'ngrok_authtoken.dpapi'))
$ng=(Get-Process ngrok -ErrorAction SilentlyContinue|Select-Object -First 1 -ExpandProperty Path);if([string]::IsNullOrWhiteSpace($ng)){throw 'RUNNING_NGROK_REAL_BINARY_NOT_FOUND'}
Copy-Item -Force $ng (Join-Path $InstallRoot 'ngrok.exe')
$nonsecret=@{};foreach($k in @('PCMMAD_ROOT','PCMMAD_PROJECTS_ROOT','PCMMAD_SYSTEM_ROOT','PCMMAD_SANDBOX_ROOT','PCMMAD_TEMP_ROOT','PCMMAD_MOUNTS_JSON','PCMMAD_PROTOCOL_POLICY_MODE','PCMMAD_BIND_HOST','PCMMAD_BIND_PORT','PCMMAD_LOCAL_PORT','PCMMAD_RECEIVER_INSTANCE','PCMMAD_HUD_HOST','PCMMAD_HUD_PORT','PCMMAD_RECEIVER_BASE','PCMMAD_NGROK_URL')){$v=[Environment]::GetEnvironmentVariable($k,'User');if(-not[string]::IsNullOrWhiteSpace($v)){$nonsecret[$k]=$v}}
$nonsecret['LIVE_RECEIVER_ROOT']=$LiveReceiverRoot;if([string]::IsNullOrWhiteSpace($DaemonProjectRoot)){$projects=[string]$nonsecret['PCMMAD_PROJECTS_ROOT'];if([string]::IsNullOrWhiteSpace($projects)){throw 'DAEMON_PROJECT_ROOT_REQUIRED'};$DaemonProjectRoot=Join-Path $projects 'RECEIVER-LAB'};$nonsecret['DAEMON_PROJECT_ROOT']=$DaemonProjectRoot;$nonsecret['DAEMON_PORT']=[string]$DaemonPort;$nonsecret['PCMMAD_DAEMON_URL']='http://127.0.0.1:'+([string]$DaemonPort);$nonsecret|ConvertTo-Json|Set-Content -Encoding UTF8 (Join-Path $InstallRoot 'machine_config.json')
$receiver=@'
$ErrorActionPreference='Stop';$root=Split-Path -Parent $MyInvocation.MyCommand.Path;Import-Module (Join-Path $root 'RecoverySecret.psm1') -Force
$c=Get-Content -Raw (Join-Path $root 'machine_config.json')|ConvertFrom-Json;$c.psobject.Properties|ForEach-Object {if($_.Name -ne 'LIVE_RECEIVER_ROOT'){Set-Item ('Env:'+ $_.Name) ([string]$_.Value)}}
$env:GITHOME_API_KEY=Unprotect-PCMMADRecoverySecret (Join-Path $root 'githome_api.dpapi')
$live=[string]$c.LIVE_RECEIVER_ROOT;$runtime=Join-Path $live 'baseline\pcmmad_receiver';$py=Join-Path $runtime '.venv\Scripts\python.exe'
if(-not(Test-Path $py) -or -not(Test-Path (Join-Path $runtime 'server.py'))){$target=Join-Path $env:ProgramData 'PCMMAD\RecoveredMinimum';& (Join-Path $root 'breakglass_restore.ps1') -BundleRoot $root -TargetRoot $target;$runtime=Join-Path $target 'receiver\baseline\pcmmad_receiver';$py=Join-Path $target 'runtime\Python312\python.exe'}
Set-Location $runtime;& $py (Join-Path $runtime 'server.py');exit $LASTEXITCODE
'@;Set-Content -Encoding UTF8 (Join-Path $InstallRoot 'start_receiver_system.ps1') $receiver
$tunnel=@'
$ErrorActionPreference='Stop';$root=Split-Path -Parent $MyInvocation.MyCommand.Path;Import-Module (Join-Path $root 'RecoverySecret.psm1') -Force
$c=Get-Content -Raw (Join-Path $root 'machine_config.json')|ConvertFrom-Json;$url=[string]$c.PCMMAD_NGROK_URL;if([string]::IsNullOrWhiteSpace($url)){throw 'RECOVERY_NGROK_URL_MISSING'}
$token=Unprotect-PCMMADRecoverySecret (Join-Path $root 'ngrok_authtoken.dpapi');$tmp=Join-Path $root ('ngrok-runtime-'+$PID+'.yml')
try{@("version: 3","agent:","  authtoken: $token")|Set-Content -Encoding ASCII $tmp;& icacls.exe $tmp /inheritance:r /grant:r 'SYSTEM:(F)' 'Administrators:(F)'|Out-Null;& (Join-Path $root 'ngrok.exe') http http://127.0.0.1:5000 --url $url --config $tmp;exit $LASTEXITCODE}finally{Remove-Item -Force $tmp -ErrorAction SilentlyContinue;$token=$null}
'@;Set-Content -Encoding UTF8 (Join-Path $InstallRoot 'start_ngrok_system.ps1') $tunnel
$supervisor=@'
$ErrorActionPreference='Stop';$root=Split-Path -Parent $MyInvocation.MyCommand.Path;Import-Module (Join-Path $root 'RecoverySecret.psm1') -Force
$c=Get-Content -Raw (Join-Path $root 'machine_config.json')|ConvertFrom-Json;$c.psobject.Properties|ForEach-Object {if($_.Name -ne 'LIVE_RECEIVER_ROOT'){Set-Item ('Env:'+ $_.Name) ([string]$_.Value)}}
$env:GITHOME_API_KEY=Unprotect-PCMMADRecoverySecret (Join-Path $root 'githome_api.dpapi')
$live=[string]$c.LIVE_RECEIVER_ROOT;$py=Join-Path $live 'baseline\pcmmad_receiver\.venv\Scripts\python.exe';$bindHost=[string]$c.PCMMAD_BIND_HOST;if([string]::IsNullOrWhiteSpace($bindHost)){$bindHost='127.0.0.1'};$port=[string]$c.PCMMAD_BIND_PORT;if([string]::IsNullOrWhiteSpace($port)){$port=[string]$c.PCMMAD_LOCAL_PORT};if([string]::IsNullOrWhiteSpace($port)){$port='5000'};$url=([UriBuilder]::new('http',$bindHost,[int]$port,'lab/health')).Uri.AbsoluteUri
if(-not(Test-Path $py)){$py=Join-Path $root 'runtime\Python312\python.exe'};if(-not(Test-Path $py)){throw 'SUPERVISOR_PYTHON_MISSING'}
& $py (Join-Path $root 'receiver_supervisor.py') --daemon --health-url $url --task-name 'PCMMAD_V30_Receiver_SYSTEM' --receipt (Join-Path $root 'receiver_supervisor_receipt.json') --stop-file (Join-Path $root 'receiver_supervisor.maintenance_hold') --lock-file (Join-Path $root 'receiver_supervisor.lock');exit $LASTEXITCODE
'@;Set-Content -Encoding UTF8 (Join-Path $InstallRoot 'start_supervisor_system.ps1') $supervisor
$daemon=@'
$ErrorActionPreference='Stop';$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$c=Get-Content -Raw (Join-Path $root 'machine_config.json')|ConvertFrom-Json;$c.psobject.Properties|ForEach-Object {if($_.Name -ne 'LIVE_RECEIVER_ROOT'){Set-Item ('Env:'+ $_.Name) ([string]$_.Value)}}
$live=[string]$c.LIVE_RECEIVER_ROOT;$py=Join-Path $live 'baseline\pcmmad_receiver\.venv\Scripts\python.exe';if(-not(Test-Path $py)){$py=Join-Path $root 'runtime\Python312\python.exe'};if(-not(Test-Path $py)){throw 'DAEMON_PYTHON_MISSING'}
$daemonProject=[string]$c.DAEMON_PROJECT_ROOT;if([string]::IsNullOrWhiteSpace($daemonProject)){throw 'DAEMON_PROJECT_ROOT_MISSING'};$daemonRoot=Join-Path $daemonProject 'daemon';$handoff=Join-Path $live 'handoff\current';$runtime=Join-Path $root 'daemon_runtime';$port=[int]$c.DAEMON_PORT
Set-Location $runtime;& $py -m mvf_resident.daemon_service --daemon-root $daemonRoot --handoff-dir $handoff --project-id 'RECEIVER-LAB' --daemon-id 'pcmmad-daemon' --receiver-root $live --host '127.0.0.1' --port $port --interval-seconds 15;exit $LASTEXITCODE
'@;Set-Content -Encoding UTF8 (Join-Path $InstallRoot 'start_daemon_system.ps1') $daemon
$daemonSupervisor=@'
$ErrorActionPreference='Stop';$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$c=Get-Content -Raw (Join-Path $root 'machine_config.json')|ConvertFrom-Json;$live=[string]$c.LIVE_RECEIVER_ROOT;$py=Join-Path $live 'baseline\pcmmad_receiver\.venv\Scripts\python.exe';if(-not(Test-Path $py)){$py=Join-Path $root 'runtime\Python312\python.exe'};if(-not(Test-Path $py)){throw 'DAEMON_SUPERVISOR_PYTHON_MISSING'};$port=[int]$c.DAEMON_PORT;$url=('http://127.0.0.1:'+ $port +'/health')
& $py (Join-Path $root 'receiver_supervisor.py') --daemon --health-url $url --task-name 'PCMMAD_V30_Daemon_SYSTEM' --receipt (Join-Path $root 'daemon_supervisor_receipt.json') --stop-file (Join-Path $root 'daemon_supervisor.maintenance_hold') --lock-file (Join-Path $root 'daemon_supervisor.lock') --expected-schema-family 'mvf.daemon-health.';exit $LASTEXITCODE
'@;Set-Content -Encoding UTF8 (Join-Path $InstallRoot 'start_daemon_supervisor_system.ps1') $daemonSupervisor
$principal=New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest;$settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
foreach($spec in @(@('PCMMAD_V30_Receiver_SYSTEM','start_receiver_system.ps1'),@('PCMMAD_V30_Ngrok_SYSTEM','start_ngrok_system.ps1'),@('PCMMAD_V30_Supervisor_SYSTEM','start_supervisor_system.ps1'),@('PCMMAD_V30_Daemon_SYSTEM','start_daemon_system.ps1'),@('PCMMAD_V30_DaemonSupervisor_SYSTEM','start_daemon_supervisor_system.ps1'))){$action=New-ScheduledTaskAction -Execute 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -Argument ('-NoProfile -ExecutionPolicy Bypass -File "'+(Join-Path $InstallRoot $spec[1])+'"');Register-ScheduledTask -TaskName $spec[0] -Action $action -Trigger (New-ScheduledTaskTrigger -AtStartup) -Principal $principal -Settings $settings -Force|Out-Null}
Write-Output "UNATTENDED_RECOVERY_INSTALLED ROOT=$InstallRoot"
