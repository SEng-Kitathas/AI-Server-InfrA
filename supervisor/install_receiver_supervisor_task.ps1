param(
  [string]$Python = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
  [string]$TaskName = "PCMMAD_V30_Supervisor",
  [string]$ReceiverTaskName = "PCMMAD_V30_Receiver",
  [string]$HealthUrl = "http://127.0.0.1:5000/health",
  [string]$Receipt = "$PSScriptRoot\..\.live\receiver_supervisor_receipt.json",
  [string]$StopFile = "$PSScriptRoot\..\.live\receiver_supervisor.maintenance_hold",
  [int]$IntervalSeconds = 10,
  [string]$LockFile = "$PSScriptRoot\..\.live\receiver_supervisor.lock",
  [string]$ExpectedSchemaFamily = "11."
)
$ErrorActionPreference='Stop'
$script = (Resolve-Path (Join-Path $PSScriptRoot 'receiver_supervisor.py')).Path
if(-not (Test-Path $Python)){ throw "Python not found: $Python" }
$arg = '"' + $script + '" --daemon --health-url "' + $HealthUrl + '" --task-name "' + $ReceiverTaskName + '" --receipt "' + $Receipt + '" --stop-file "' + $StopFile + '" --interval-seconds ' + $IntervalSeconds
$action = New-ScheduledTaskAction -Execute $Python -Argument $arg
# Boot trigger is primary: survives Windows Update/reboot and does not require an interactive login.
$boot = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -StartWhenAvailable
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $boot -Principal $principal -Settings $settings -Force | Out-Null
# Start it now as well; installation should converge immediately, not wait for next reboot.
Start-ScheduledTask -TaskName $TaskName
Write-Output "INSTALLED=$TaskName MODE=AT_STARTUP SYSTEM HIGHEST DAEMON=TRUE SCRIPT=$script"
