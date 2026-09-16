@echo off
setlocal
set "ROOT=%~dp0"
set "DEFAULT_GATE=%ROOT%.heat_runtime\browser_bridge_gate.json"
set "INSTALL_GATE=%ProgramData%\PCMMAD\recovery\browser_bridge_gate.json"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$managed=Get-ScheduledTask -TaskName 'PCMMAD_V30_BrowserBridge_SYSTEM' -ErrorAction SilentlyContinue;$path=if($managed){'%INSTALL_GATE%'}else{'%DEFAULT_GATE%'};$dir=Split-Path -Parent $path;New-Item -ItemType Directory -Force $dir|Out-Null;$obj=[ordered]@{schema='pcmmad.browser-bridge-gate.v1';state='BLOCKED';changed_at=(Get-Date).ToUniversalTime().ToString('o');provenance='EXPLICIT_OPERATOR_TOGGLE'};$tmp=$path+'.tmp';$obj|ConvertTo-Json|Set-Content -Encoding UTF8 $tmp;Move-Item -Force $tmp $path;Write-Host ('Browser bridge BLOCKED via '+$path)"
exit /b %ERRORLEVEL%
