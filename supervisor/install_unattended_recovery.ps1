param(
 [Parameter(Mandatory=$true)][string]$BundleSource,
 [string]$InstallRoot="$env:ProgramData\PCMMAD\Recovery",
 [string]$LiveReceiverRoot="C:\Users\ancal\Desktop\PCMMAD_LABORATORY_RUNTIME_V30_RC1\PCMMAD_receiver",
 [string]$DaemonProjectRoot="",
 [int]$DaemonPort=5015,
 [string]$HandoffSource=""
)
$ErrorActionPreference='Stop'
$id=[Security.Principal.WindowsIdentity]::GetCurrent();$wp=New-Object Security.Principal.WindowsPrincipal($id)
if(-not $wp.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'ELEVATED_ADMIN_REQUIRED_FOR_ONE_TIME_RECOVERY_INSTALL'}
$managedTaskNames=@('PCMMAD_V30_Receiver_SYSTEM','PCMMAD_V30_Ngrok_SYSTEM','PCMMAD_V30_BrowserBridge_SYSTEM','PCMMAD_V30_Supervisor_SYSTEM','PCMMAD_V30_Daemon_SYSTEM','PCMMAD_V30_DaemonSupervisor_SYSTEM','PCMMAD_V30_NgrokSupervisor_SYSTEM','PCMMAD_V30_BrowserBridgeSupervisor_SYSTEM')
$existingManaged=@(Get-ScheduledTask -ErrorAction SilentlyContinue|Where-Object {$_.TaskName -in $managedTaskNames})
$programManifest=Join-Path $InstallRoot 'installed_program_manifest.json'
$existingInstallContent=if(Test-Path $InstallRoot){@(Get-ChildItem -Force $InstallRoot -ErrorAction SilentlyContinue).Count}else{0}
$requiresQuiescence=(Test-Path $programManifest) -or ($existingManaged.Count -gt 0) -or ($existingInstallContent -gt 0)
if($requiresQuiescence){
  $runningManaged=@($existingManaged|Where-Object {$_.State -eq 'Running'})
  if($runningManaged.Count -gt 0){throw ('RECOVERY_INSTALL_REQUIRES_MANAGED_TASKS_STOPPED:'+($runningManaged.TaskName -join ','))}
  foreach($port in @(5000,4040,4471,$DaemonPort)){if(Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue){throw ('RECOVERY_INSTALL_REQUIRES_RUNTIME_LISTENERS_STOPPED:'+([string]$port))}}
}
New-Item -ItemType Directory -Force $InstallRoot|Out-Null
$browserPython=Join-Path $LiveReceiverRoot 'baseline\pcmmad_receiver\.venv\Scripts\python.exe';if(-not(Test-Path $browserPython)){throw 'BROWSER_BRIDGE_RUNTIME_MISSING_RUN_SETUP_PCMMAD_RUNTIME'}
& $browserPython -c "import flask,playwright"|Out-Null;if($LASTEXITCODE -ne 0){throw 'BROWSER_BRIDGE_RUNTIME_DEPENDENCIES_MISSING'}
$browserChannel=$null;if(Test-Path 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'){$browserChannel='msedge'}elseif(Test-Path 'C:\Program Files\Microsoft\Edge\Application\msedge.exe'){$browserChannel='msedge'}elseif(Test-Path 'C:\Program Files\Google\Chrome\Application\chrome.exe'){$browserChannel='chrome'}elseif(Test-Path 'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'){$browserChannel='chrome'}else{throw 'BROWSER_BRIDGE_SUPPORTED_SYSTEM_BROWSER_MISSING'}
$programPython=Join-Path $BundleSource 'runtime\Python312\python.exe';if(-not(Test-Path $programPython)){$programPython=Join-Path $LiveReceiverRoot 'baseline\pcmmad_receiver\.venv\Scripts\python.exe'};if(-not(Test-Path $programPython)){throw 'RECOVERY_PROGRAM_TRANSACTION_PYTHON_MISSING'}
$txHelper=Join-Path $PSScriptRoot 'recovery_program_tx.py';if(-not(Test-Path $txHelper)){throw 'RECOVERY_PROGRAM_TRANSACTION_HELPER_MISSING'}
$daemonSource=Join-Path (Split-Path -Parent $PSScriptRoot) 'mvf_resident';if(-not(Test-Path $daemonSource)){throw 'MVF_DAEMON_SOURCE_MISSING'}
$programTxOut=& $programPython $txHelper stage --bundle-source $BundleSource --support-root $PSScriptRoot --daemon-source $daemonSource --install-root $InstallRoot
if($LASTEXITCODE -ne 0){throw ('RECOVERY_PROGRAM_TRANSACTION_STAGE_FAILED:'+([string]$LASTEXITCODE))}
$programTx=[string](@($programTxOut)[-1]);if([string]::IsNullOrWhiteSpace($programTx) -or -not(Test-Path $programTx)){throw 'RECOVERY_PROGRAM_TRANSACTION_TOKEN_MISSING'}
$promotionMetaDir=Join-Path $programTx 'promotion';$fileMetaDir=Join-Path $promotionMetaDir 'files';New-Item -ItemType Directory -Force $fileMetaDir|Out-Null
$rollbackFiles=@('githome_api.dpapi','ngrok_authtoken.dpapi','machine_config.json','start_receiver_system.ps1','start_ngrok_system.ps1','start_browser_bridge_system.ps1','start_supervisor_system.ps1','start_daemon_system.ps1','start_daemon_supervisor_system.ps1','start_browser_bridge_supervisor_system.ps1','daemon_task_entry.py')
$rollbackFileState=@{}
foreach($rel in $rollbackFiles){$src=Join-Path $InstallRoot $rel;if(Test-Path -LiteralPath $src){Copy-Item -LiteralPath $src -Destination (Join-Path $fileMetaDir $rel) -Force;$rollbackFileState[$rel]='PRESENT'}else{$rollbackFileState[$rel]='ABSENT'}}
$rollbackFileState|ConvertTo-Json -Depth 3|Set-Content -Encoding UTF8 (Join-Path $promotionMetaDir 'file_state.json')
$taskBackups=@{};$registeredManaged=New-Object System.Collections.Generic.List[string];$promotionBackup=$null
try{
Import-Module (Join-Path $InstallRoot 'RecoverySecret.psm1') -Force
$api=[Environment]::GetEnvironmentVariable('GITHOME_API_KEY','User');if([string]::IsNullOrWhiteSpace($api)){throw 'USER_API_KEY_MISSING_AT_INSTALL'}
[void](Protect-PCMMADRecoverySecret -Secret $api -Path (Join-Path $InstallRoot 'githome_api.dpapi'))
$cfgPath=Join-Path $env:LOCALAPPDATA 'ngrok\ngrok.yml';if(-not(Test-Path $cfgPath)){throw 'NGROK_USER_CONFIG_MISSING_AT_INSTALL'}
$cfg=Get-Content -Raw $cfgPath;$match=[regex]::Match($cfg,'(?m)^\s*authtoken:\s*(.+?)\s*$');if(-not $match.Success){throw 'NGROK_AUTHTOKEN_MISSING_AT_INSTALL'}
[void](Protect-PCMMADRecoverySecret -Secret $match.Groups[1].Value.Trim() -Path (Join-Path $InstallRoot 'ngrok_authtoken.dpapi'))
$ng=(Get-Process ngrok -ErrorAction SilentlyContinue|Select-Object -First 1 -ExpandProperty Path);if([string]::IsNullOrWhiteSpace($ng)){throw 'RUNNING_NGROK_REAL_BINARY_NOT_FOUND'}
Copy-Item -Force $ng (Join-Path $InstallRoot 'ngrok.exe')
$nonsecret=@{};foreach($k in @('PCMMAD_ROOT','PCMMAD_PROJECTS_ROOT','PCMMAD_SYSTEM_ROOT','PCMMAD_SANDBOX_ROOT','PCMMAD_TEMP_ROOT','PCMMAD_MOUNTS_JSON','PCMMAD_PROTOCOL_POLICY_MODE','PCMMAD_BIND_HOST','PCMMAD_BIND_PORT','PCMMAD_LOCAL_PORT','PCMMAD_RECEIVER_INSTANCE','PCMMAD_HUD_HOST','PCMMAD_HUD_PORT','PCMMAD_RECEIVER_BASE','PCMMAD_NGROK_URL','PCMMAD_BROWSER_BRIDGE_URL')){$v=[Environment]::GetEnvironmentVariable($k,'User');if(-not[string]::IsNullOrWhiteSpace($v)){$nonsecret[$k]=$v}}
$nonsecret['LIVE_RECEIVER_ROOT']=$LiveReceiverRoot;$projects=[string]$nonsecret['PCMMAD_PROJECTS_ROOT'];if([string]::IsNullOrWhiteSpace($projects)){throw 'DAEMON_PROJECT_ROOT_REQUIRED'};$expectedDaemonProject=[IO.Path]::GetFullPath((Join-Path $projects 'RECEIVER-LAB'));if([string]::IsNullOrWhiteSpace($DaemonProjectRoot)){$DaemonProjectRoot=$expectedDaemonProject}else{$candidateDaemonProject=[IO.Path]::GetFullPath($DaemonProjectRoot);if(-not $candidateDaemonProject.Equals($expectedDaemonProject,[StringComparison]::OrdinalIgnoreCase)){throw 'DAEMON_PROJECT_ROOT_MUST_MATCH_RECEIVER_LAB'}};$reservedPorts=@();foreach($k in @('PCMMAD_BIND_PORT','PCMMAD_LOCAL_PORT','PCMMAD_HUD_PORT')){$v=[string]$nonsecret[$k];if(-not[string]::IsNullOrWhiteSpace($v)){$reservedPorts+=[int]$v}};if($DaemonPort -lt 1 -or $DaemonPort -gt 65535 -or $reservedPorts -contains $DaemonPort){throw 'DAEMON_PORT_COLLIDES_WITH_RECEIVER_OR_HUD'};$nonsecret['DAEMON_PROJECT_ROOT']=$DaemonProjectRoot;$nonsecret['DAEMON_PORT']=[string]$DaemonPort;$nonsecret['PCMMAD_DAEMON_URL']='http://127.0.0.1:'+([string]$DaemonPort);$nonsecret['PCMMAD_DAEMON_ID']='pcmmad-daemon';$nonsecret['PCMMAD_DAEMON_PROJECT_ID']='RECEIVER-LAB';if([string]::IsNullOrWhiteSpace([string]$nonsecret['PCMMAD_BROWSER_BRIDGE_URL'])){$nonsecret['PCMMAD_BROWSER_BRIDGE_URL']='http://127.0.0.1:4471'};$nonsecret['PCMMAD_BROWSER_DEFAULT_CHANNEL']=$browserChannel;$nonsecret|ConvertTo-Json|Set-Content -Encoding UTF8 (Join-Path $InstallRoot 'machine_config.json')
$daemonRuntime=Join-Path $InstallRoot 'daemon_runtime'
$daemonPython=Join-Path $InstallRoot 'runtime\Python312\python.exe';if(-not(Test-Path $daemonPython)){$daemonPython=Join-Path $LiveReceiverRoot 'baseline\pcmmad_receiver\.venv\Scripts\python.exe'};if(-not(Test-Path $daemonPython)){throw 'DAEMON_PYTHON_MISSING_AT_INSTALL'}

$receiver=@'
$ErrorActionPreference='Stop';$root=Split-Path -Parent $MyInvocation.MyCommand.Path;Import-Module (Join-Path $root 'RecoverySecret.psm1') -Force
$c=Get-Content -Raw (Join-Path $root 'machine_config.json')|ConvertFrom-Json;$c.psobject.Properties|ForEach-Object {if($_.Name -ne 'LIVE_RECEIVER_ROOT'){Set-Item ('Env:'+ $_.Name) ([string]$_.Value)}}
$env:GITHOME_API_KEY=Unprotect-PCMMADRecoverySecret (Join-Path $root 'githome_api.dpapi')
$live=[string]$c.LIVE_RECEIVER_ROOT;$runtime=Join-Path $live 'baseline\pcmmad_receiver';$py=Join-Path $runtime '.venv\Scripts\python.exe'
if(-not(Test-Path $py) -or -not(Test-Path (Join-Path $runtime 'server.py'))){$target=Join-Path $env:ProgramData 'PCMMAD\RecoveredMinimum';& (Join-Path $root 'breakglass_restore.ps1') -BundleRoot $root -TargetRoot $target;$runtime=Join-Path $target 'receiver\baseline\pcmmad_receiver';$py=Join-Path $target 'runtime\Python312\python.exe'}
$child=Start-Process -FilePath $py -ArgumentList @((Join-Path $runtime 'server.py')) -WorkingDirectory $runtime -PassThru
try{while(-not $child.HasExited){$state=(Get-ScheduledTask -TaskName 'PCMMAD_V30_Receiver_SYSTEM' -ErrorAction SilentlyContinue).State;if($null -eq $state -or $state -ne 'Running'){Stop-Process -Id $child.Id -Force -ErrorAction SilentlyContinue;break};Start-Sleep -Milliseconds 500;$child.Refresh()};if($child.HasExited){exit $child.ExitCode}}finally{if(-not $child.HasExited){Stop-Process -Id $child.Id -Force -ErrorAction SilentlyContinue}}
'@;Set-Content -Encoding UTF8 (Join-Path $InstallRoot 'start_receiver_system.ps1') $receiver
$tunnel=@'
$ErrorActionPreference='Stop';$root=Split-Path -Parent $MyInvocation.MyCommand.Path;Import-Module (Join-Path $root 'RecoverySecret.psm1') -Force
$c=Get-Content -Raw (Join-Path $root 'machine_config.json')|ConvertFrom-Json;$url=[string]$c.PCMMAD_NGROK_URL;if([string]::IsNullOrWhiteSpace($url)){throw 'RECOVERY_NGROK_URL_MISSING'}
$token=Unprotect-PCMMADRecoverySecret (Join-Path $root 'ngrok_authtoken.dpapi');$tmp=Join-Path $root ('ngrok-runtime-'+$PID+'.yml')
try{@("version: 3","agent:","  authtoken: $token")|Set-Content -Encoding ASCII $tmp;& icacls.exe $tmp /inheritance:r /grant:r 'SYSTEM:(F)' 'Administrators:(F)'|Out-Null;$child=Start-Process -FilePath (Join-Path $root 'ngrok.exe') -ArgumentList @('http','http://127.0.0.1:5000','--url',$url,'--config',$tmp) -WorkingDirectory $root -PassThru;while(-not $child.HasExited){$state=(Get-ScheduledTask -TaskName 'PCMMAD_V30_Ngrok_SYSTEM' -ErrorAction SilentlyContinue).State;if($null -eq $state -or $state -ne 'Running'){Stop-Process -Id $child.Id -Force -ErrorAction SilentlyContinue;break};Start-Sleep -Milliseconds 500;$child.Refresh()};if($child.HasExited){exit $child.ExitCode}}finally{if($child -and -not $child.HasExited){Stop-Process -Id $child.Id -Force -ErrorAction SilentlyContinue};Remove-Item -Force $tmp -ErrorAction SilentlyContinue;$token=$null}
'@;Set-Content -Encoding UTF8 (Join-Path $InstallRoot 'start_ngrok_system.ps1') $tunnel
$browserBridge=@'
$ErrorActionPreference='Stop';$root=Split-Path -Parent $MyInvocation.MyCommand.Path;$cfg=Get-Content -Raw (Join-Path $root 'machine_config.json')|ConvertFrom-Json;$live=[string]$cfg.LIVE_RECEIVER_ROOT;$py=Join-Path $live 'baseline\pcmmad_receiver\.venv\Scripts\python.exe';$svc=Join-Path $live 'baseline\pcmmad_receiver\browser_bridge_service.py';if(-not(Test-Path $py)){throw 'BROWSER_BRIDGE_PYTHON_MISSING'};if(-not(Test-Path $svc)){throw 'BROWSER_BRIDGE_SERVICE_MISSING'};$env:PCMMAD_BROWSER_BRIDGE_URL=[string]$cfg.PCMMAD_BROWSER_BRIDGE_URL;$env:PCMMAD_BROWSER_SCREENSHOT_DIR=Join-Path $live 'browser_screenshots';$env:PCMMAD_BROWSER_BRIDGE_GATE_FILE=Join-Path $root 'browser_bridge_gate.json';$env:PCMMAD_BROWSER_DEFAULT_CHANNEL=[string]$cfg.PCMMAD_BROWSER_DEFAULT_CHANNEL;& $py $svc --host 127.0.0.1 --port 4471;exit $LASTEXITCODE
'@;Set-Content -Encoding UTF8 (Join-Path $InstallRoot 'start_browser_bridge_system.ps1') $browserBridge
$supervisor=@'
$ErrorActionPreference='Stop';$root=Split-Path -Parent $MyInvocation.MyCommand.Path;Import-Module (Join-Path $root 'RecoverySecret.psm1') -Force
$c=Get-Content -Raw (Join-Path $root 'machine_config.json')|ConvertFrom-Json;$c.psobject.Properties|ForEach-Object {if($_.Name -ne 'LIVE_RECEIVER_ROOT'){Set-Item ('Env:'+ $_.Name) ([string]$_.Value)}}
$env:GITHOME_API_KEY=Unprotect-PCMMADRecoverySecret (Join-Path $root 'githome_api.dpapi')
$live=[string]$c.LIVE_RECEIVER_ROOT;$py=Join-Path $live 'baseline\pcmmad_receiver\.venv\Scripts\python.exe';$bindHost=[string]$c.PCMMAD_BIND_HOST;if([string]::IsNullOrWhiteSpace($bindHost)){$bindHost='127.0.0.1'};$port=[string]$c.PCMMAD_BIND_PORT;if([string]::IsNullOrWhiteSpace($port)){$port=[string]$c.PCMMAD_LOCAL_PORT};if([string]::IsNullOrWhiteSpace($port)){$port='5000'};$url=([UriBuilder]::new('http',$bindHost,[int]$port,'lab/health')).Uri.AbsoluteUri
if(-not(Test-Path $py)){$py=Join-Path $root 'runtime\Python312\python.exe'};if(-not(Test-Path $py)){throw 'SUPERVISOR_PYTHON_MISSING'}
$args=@((Join-Path $root 'receiver_supervisor.py'),'--daemon','--health-url',$url,'--task-name','PCMMAD_V30_Receiver_SYSTEM','--receipt',(Join-Path $root 'receiver_supervisor_receipt.json'),'--stop-file',(Join-Path $root 'receiver_supervisor.maintenance_hold'),'--lock-file',(Join-Path $root 'receiver_supervisor.lock'),'--failure-state-file',(Join-Path $root 'receiver_supervisor.failure_state.json'));$child=Start-Process -FilePath $py -ArgumentList $args -WorkingDirectory $root -PassThru;try{while(-not $child.HasExited){$state=(Get-ScheduledTask -TaskName 'PCMMAD_V30_Supervisor_SYSTEM' -ErrorAction SilentlyContinue).State;if($null -eq $state -or $state -ne 'Running'){Stop-Process -Id $child.Id -Force -ErrorAction SilentlyContinue;break};Start-Sleep -Milliseconds 500;$child.Refresh()};if($child.HasExited){exit $child.ExitCode}}finally{if(-not $child.HasExited){Stop-Process -Id $child.Id -Force -ErrorAction SilentlyContinue}}
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
& $py (Join-Path $root 'receiver_supervisor.py') --daemon --health-url $url --task-name 'PCMMAD_V30_Daemon_SYSTEM' --receipt (Join-Path $root 'daemon_supervisor_receipt.json') --stop-file (Join-Path $root 'daemon_supervisor.maintenance_hold') --lock-file (Join-Path $root 'daemon_supervisor.lock') --expected-schema-family 'mvf.daemon-health.' --expected-daemon-id 'pcmmad-daemon' --expected-project-id 'RECEIVER-LAB';exit $LASTEXITCODE
'@;Set-Content -Encoding UTF8 (Join-Path $InstallRoot 'start_daemon_supervisor_system.ps1') $daemonSupervisor
$browserBridgeSupervisor=@'
$ErrorActionPreference='Stop';$root=Split-Path -Parent $MyInvocation.MyCommand.Path;$py=Join-Path $root 'runtime\Python312\python.exe';if(-not(Test-Path $py)){$py=(Get-Command python.exe -ErrorAction Stop).Source};$args=@((Join-Path $root 'receiver_supervisor.py'),'--daemon','--health-url','http://127.0.0.1:4471/health','--task-name','PCMMAD_V30_BrowserBridge_SYSTEM','--receipt',(Join-Path $root 'browser_bridge_supervisor_receipt.json'),'--stop-file',(Join-Path $root 'browser_bridge_supervisor.maintenance_hold'),'--lock-file',(Join-Path $root 'browser_bridge_supervisor.lock'),'--failure-state-file',(Join-Path $root 'browser_bridge_supervisor.failure_state.json'),'--expected-schema-family','','--expected-health-service','pcmmad_browser_bridge','--receipt-action','TRIGGER_CANONICAL_BROWSER_BRIDGE_TASK');$child=Start-Process -FilePath $py -ArgumentList $args -WorkingDirectory $root -PassThru;try{while(-not $child.HasExited){$state=(Get-ScheduledTask -TaskName 'PCMMAD_V30_BrowserBridgeSupervisor_SYSTEM' -ErrorAction SilentlyContinue).State;if($null -eq $state -or $state -ne 'Running'){Stop-Process -Id $child.Id -Force -ErrorAction SilentlyContinue;break};Start-Sleep -Milliseconds 500;$child.Refresh()};if($child.HasExited){exit $child.ExitCode}}finally{if(-not $child.HasExited){Stop-Process -Id $child.Id -Force -ErrorAction SilentlyContinue}}
'@;Set-Content -Encoding UTF8 (Join-Path $InstallRoot 'start_browser_bridge_supervisor_system.ps1') $browserBridgeSupervisor
$daemonEntry=@'
from __future__ import annotations
import json,os,sys
from pathlib import Path
root=Path(__file__).resolve().parent
cfg=json.loads((root/'machine_config.json').read_text(encoding='utf-8-sig'))
for k,v in cfg.items():
    if k!='LIVE_RECEIVER_ROOT' and v is not None: os.environ[str(k)]=str(v)
live=Path(str(cfg['LIVE_RECEIVER_ROOT'])).resolve();project=Path(str(cfg['DAEMON_PROJECT_ROOT'])).resolve()
if not project.exists(): raise SystemExit('DAEMON_PROJECT_ROOT_DOES_NOT_EXIST')
runtime=root/'daemon_runtime';sys.path.insert(0,str(runtime))
from mvf_resident.daemon_service import main
raise SystemExit(main(['--daemon-root',str(project/'daemon'),'--handoff-root',str(project/'handoff'),'--project-id','RECEIVER-LAB','--daemon-id','pcmmad-daemon','--receiver-root',str(live),'--host-lock',str(root/'daemon_identity.lock'),'--host','127.0.0.1','--port',str(cfg['DAEMON_PORT']),'--interval-seconds','15']))
'@;Set-Content -Encoding UTF8 (Join-Path $InstallRoot 'daemon_task_entry.py') $daemonEntry

foreach($taskName in $managedTaskNames){$existing=Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue;if($existing){$taskBackups[$taskName]=Export-ScheduledTask -TaskName $taskName}else{$taskBackups[$taskName]=$null}}
$principal=New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$workloadSettings=New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero)
$supervisorSettings=New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
foreach($spec in @(@('PCMMAD_V30_Receiver_SYSTEM','start_receiver_system.ps1'),@('PCMMAD_V30_Ngrok_SYSTEM','start_ngrok_system.ps1'),@('PCMMAD_V30_BrowserBridge_SYSTEM','start_browser_bridge_system.ps1'))){
  $action=New-ScheduledTaskAction -Execute 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -Argument ('-NoProfile -ExecutionPolicy Bypass -File "'+(Join-Path $InstallRoot $spec[1])+'"')
  Register-ScheduledTask -TaskName $spec[0] -Action $action -Trigger (New-ScheduledTaskTrigger -AtStartup) -Principal $principal -Settings $workloadSettings -Force|Out-Null;$registeredManaged.Add([string]$spec[0])|Out-Null
}
$receiverSupervisorAction=New-ScheduledTaskAction -Execute 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -Argument ('-NoProfile -ExecutionPolicy Bypass -File "'+(Join-Path $InstallRoot 'start_supervisor_system.ps1')+'"')
Register-ScheduledTask -TaskName 'PCMMAD_V30_Supervisor_SYSTEM' -Action $receiverSupervisorAction -Trigger (New-ScheduledTaskTrigger -AtStartup) -Principal $principal -Settings $supervisorSettings -Force|Out-Null;$registeredManaged.Add('PCMMAD_V30_Supervisor_SYSTEM')|Out-Null
$daemonAction=New-ScheduledTaskAction -Execute $daemonPython -Argument ('"'+(Join-Path $InstallRoot 'daemon_task_entry.py')+'"') -WorkingDirectory $InstallRoot
Register-ScheduledTask -TaskName 'PCMMAD_V30_Daemon_SYSTEM' -Action $daemonAction -Trigger (New-ScheduledTaskTrigger -AtStartup) -Principal $principal -Settings $workloadSettings -Force|Out-Null;$registeredManaged.Add('PCMMAD_V30_Daemon_SYSTEM')|Out-Null
$daemonSupervisorArgs='"'+(Join-Path $InstallRoot 'receiver_supervisor.py')+'" --daemon --health-url http://127.0.0.1:'+$DaemonPort+'/health --task-name PCMMAD_V30_Daemon_SYSTEM --receipt "'+(Join-Path $InstallRoot 'daemon_supervisor_receipt.json')+'" --stop-file "'+(Join-Path $InstallRoot 'daemon_supervisor.maintenance_hold')+'" --lock-file "'+(Join-Path $InstallRoot 'daemon_supervisor.lock')+'" --expected-schema-family mvf.daemon-health. --expected-daemon-id pcmmad-daemon --expected-project-id RECEIVER-LAB --failure-state-file "'+(Join-Path $InstallRoot 'daemon_supervisor.failure_state.json')+'" --receipt-action TRIGGER_CANONICAL_DAEMON_TASK'
$daemonSupervisorAction=New-ScheduledTaskAction -Execute $daemonPython -Argument $daemonSupervisorArgs -WorkingDirectory $InstallRoot
Register-ScheduledTask -TaskName 'PCMMAD_V30_DaemonSupervisor_SYSTEM' -Action $daemonSupervisorAction -Trigger (New-ScheduledTaskTrigger -AtStartup) -Principal $principal -Settings $supervisorSettings -Force|Out-Null;$registeredManaged.Add('PCMMAD_V30_DaemonSupervisor_SYSTEM')|Out-Null
$ngrokSupervisorArgs='"'+(Join-Path $InstallRoot 'ngrok_supervisor.py')+'" --health-url http://127.0.0.1:4040/api/tunnels --expected-public-url "'+([string]$nonsecret['PCMMAD_NGROK_URL'])+'" --expected-upstream http://127.0.0.1:5000 --task-name PCMMAD_V30_Ngrok_SYSTEM --receipt "'+(Join-Path $InstallRoot 'ngrok_supervisor_receipt.json')+'" --stop-file "'+(Join-Path $InstallRoot 'ngrok_supervisor.maintenance_hold')+'" --lock-file "'+(Join-Path $InstallRoot 'ngrok_supervisor.lock')+'" --failure-state-file "'+(Join-Path $InstallRoot 'ngrok_supervisor.failure_state.json')+'" --receipt-action TRIGGER_CANONICAL_NGROK_TASK'
$ngrokSupervisorAction=New-ScheduledTaskAction -Execute $daemonPython -Argument $ngrokSupervisorArgs -WorkingDirectory $InstallRoot
Register-ScheduledTask -TaskName 'PCMMAD_V30_NgrokSupervisor_SYSTEM' -Action $ngrokSupervisorAction -Trigger (New-ScheduledTaskTrigger -AtStartup) -Principal $principal -Settings $supervisorSettings -Force|Out-Null;$registeredManaged.Add('PCMMAD_V30_NgrokSupervisor_SYSTEM')|Out-Null
$browserBridgeSupervisorAction=New-ScheduledTaskAction -Execute 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -Argument ('-NoProfile -ExecutionPolicy Bypass -File "'+(Join-Path $InstallRoot 'start_browser_bridge_supervisor_system.ps1')+'"')
Register-ScheduledTask -TaskName 'PCMMAD_V30_BrowserBridgeSupervisor_SYSTEM' -Action $browserBridgeSupervisorAction -Trigger (New-ScheduledTaskTrigger -AtStartup) -Principal $principal -Settings $supervisorSettings -Force|Out-Null;$registeredManaged.Add('PCMMAD_V30_BrowserBridgeSupervisor_SYSTEM')|Out-Null
$taskMetaDir=Join-Path $promotionMetaDir 'tasks';New-Item -ItemType Directory -Force $taskMetaDir|Out-Null
foreach($taskName in $managedTaskNames){$safeName=$taskName.Replace('\\','_').Replace('/','_');$xml=$taskBackups[$taskName];if($null -eq $xml){Set-Content -Encoding ASCII (Join-Path $taskMetaDir ($safeName+'.absent')) 'ABSENT'}else{Set-Content -Encoding UTF8 (Join-Path $taskMetaDir ($safeName+'.xml')) $xml}}
$handoffPointer=Join-Path (Join-Path $DaemonProjectRoot 'handoff') 'current.json';if(Test-Path $handoffPointer){Get-Content -Raw $handoffPointer|Set-Content -Encoding UTF8 (Join-Path $promotionMetaDir 'old_handoff_pointer.json')}else{Set-Content -Encoding ASCII (Join-Path $promotionMetaDir 'old_handoff_pointer.absent') 'ABSENT'}
@{schema='pcmmad.promotion-backup.v1';daemon_project_root=[IO.Path]::GetFullPath($DaemonProjectRoot);task_names=$managedTaskNames;created_at=(Get-Date).ToUniversalTime().ToString('o')}|ConvertTo-Json -Depth 4|Set-Content -Encoding UTF8 (Join-Path $promotionMetaDir 'promotion_metadata.json')
$promotionBackupRoot=Join-Path $InstallRoot 'promotion_backups';$commitOut=& $programPython $txHelper commit --tx $programTx --archive-root $promotionBackupRoot
if($LASTEXITCODE -ne 0){throw ('RECOVERY_PROGRAM_TRANSACTION_ARCHIVE_FAILED:'+([string]$LASTEXITCODE))}
$promotionBackup=[string](@($commitOut)[-1]);if([string]::IsNullOrWhiteSpace($promotionBackup)-or -not(Test-Path $promotionBackup)){throw 'PROMOTION_BACKUP_TOKEN_MISSING'};$programTx=$null
$sourceHandoff=if([string]::IsNullOrWhiteSpace($HandoffSource)){Join-Path (Split-Path -Parent $PSScriptRoot) 'handoff\current'}else{[IO.Path]::GetFullPath($HandoffSource)};if(-not(Test-Path $sourceHandoff)){throw 'SOURCE_HANDOFF_MISSING_AT_INSTALL'}
$oldPythonPath=$env:PYTHONPATH;try{$env:PYTHONPATH=$daemonRuntime;& $programPython -m mvf_resident.project_handoff --source $sourceHandoff --project-root $DaemonProjectRoot;if($LASTEXITCODE -ne 0){throw ('DAEMON_HANDOFF_PUBLISH_FAILED:'+([string]$LASTEXITCODE))}}finally{$env:PYTHONPATH=$oldPythonPath}
Get-ChildItem $promotionBackupRoot -Directory -ErrorAction SilentlyContinue|Sort-Object LastWriteTimeUtc -Descending|Select-Object -Skip 8|Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Write-Output ("UNATTENDED_RECOVERY_INSTALLED ROOT=$InstallRoot PROMOTION_BACKUP="+$promotionBackup)
}catch{
  $installError=$_
  foreach($taskName in @($registeredManaged)){Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue;Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue}
  foreach($taskName in $managedTaskNames){$xml=$taskBackups[$taskName];if($null -ne $xml){Register-ScheduledTask -TaskName $taskName -Xml $xml -Force|Out-Null}}
  if($promotionMetaDir -and (Test-Path (Join-Path $promotionMetaDir 'file_state.json'))){$state=Get-Content -Raw (Join-Path $promotionMetaDir 'file_state.json')|ConvertFrom-Json;foreach($prop in $state.psobject.Properties){$rel=[string]$prop.Name;$dst=Join-Path $InstallRoot $rel;if([string]$prop.Value -eq 'PRESENT'){$src=Join-Path $fileMetaDir $rel;if(Test-Path $src){Copy-Item -LiteralPath $src -Destination $dst -Force}}else{Remove-Item -LiteralPath $dst -Force -ErrorAction SilentlyContinue}}}
  if($programTx -and (Test-Path $programTx)){& $programPython $txHelper rollback --tx $programTx --install-root $InstallRoot|Out-Null}elseif($promotionBackup -and (Test-Path $promotionBackup)){& $programPython $txHelper rollback --tx $promotionBackup --install-root $InstallRoot|Out-Null}
  throw $installError
}
