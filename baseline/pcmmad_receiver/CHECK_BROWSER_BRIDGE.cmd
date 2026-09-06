@echo off
setlocal
if "%PCMMAD_BROWSER_BRIDGE_URL%"=="" set "PCMMAD_BROWSER_BRIDGE_URL=http://127.0.0.1:4471"
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { (Invoke-WebRequest -UseBasicParsing -Uri ($env:PCMMAD_BROWSER_BRIDGE_URL + '/health') -TimeoutSec 5).Content; exit 0 } catch { Write-Host ('PCMMAD browser bridge is not responding at ' + $env:PCMMAD_BROWSER_BRIDGE_URL + '/health'); Write-Host $_.Exception.Message; exit 1 }"
pause
