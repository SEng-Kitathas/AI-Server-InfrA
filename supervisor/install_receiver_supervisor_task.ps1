param(
  [string]$Python = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
  [string]$TaskName = "PCMMAD_V30_Supervisor",
  [string]$ReceiverTaskName = "PCMMAD_V30_Receiver",
  [string]$HealthUrl = "http://127.0.0.1:5090/api/health",
  [string]$Receipt = "$PSScriptRoot\..\.live\receiver_supervisor_receipt.json"
)
$script = Join-Path $PSScriptRoot 'receiver_supervisor.py'
$arg = '"' + $script + '" --health-url "' + $HealthUrl + '" --task-name "' + $ReceiverTaskName + '" --receipt "' + $Receipt + '"'
$action = New-ScheduledTaskAction -Execute $Python -Argument $arg
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 1)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Write-Output "INSTALLED=$TaskName SCRIPT=$script"
