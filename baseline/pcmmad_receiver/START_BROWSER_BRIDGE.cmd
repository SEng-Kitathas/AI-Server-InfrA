@echo off
setlocal
set "TASK=PCMMAD_V30_BrowserBridge_SYSTEM"
set "URL=http://127.0.0.1:4471"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$t=Get-ScheduledTask -TaskName '%TASK%' -ErrorAction SilentlyContinue; if($t){ Start-ScheduledTask -TaskName '%TASK%' -ErrorAction Stop; $deadline=(Get-Date).AddSeconds(20); do { Start-Sleep -Milliseconds 250; try { $b=Invoke-RestMethod '%URL%/health' -TimeoutSec 2; if($b.ok -eq $true -and [string]$b.service -eq 'pcmmad_browser_bridge'){ Write-Host 'PCMMAD browser bridge managed task is healthy at %URL%'; exit 0 } } catch {} } while((Get-Date)-lt $deadline); Write-Error 'Managed browser bridge task did not become healthy'; exit 3 } else { exit 44 }"
if %ERRORLEVEL% EQU 0 exit /b 0
if not %ERRORLEVEL% EQU 44 exit /b %ERRORLEVEL%
rem Development fallback when unattended-recovery task is not installed.
set "ROOT=%~dp0"
set "RUNTIME=%ROOT%baseline\pcmmad_receiver"
set "PYTHON=%RUNTIME%\.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=%ROOT%.heat_runtime\venv\Scripts\python.exe"
if not exist "%PYTHON%" (
  echo ERROR: No qualified PCMMAD Python runtime found. Run SETUP_PCMMAD_RUNTIME.ps1 first.
  exit /b 2
)
"%PYTHON%" -c "import flask,playwright" >nul 2>&1
if errorlevel 1 (
  echo ERROR: Browser bridge runtime is missing Flask or Playwright. Run SETUP_PCMMAD_RUNTIME.ps1.
  exit /b 3
)
if "%PCMMAD_BROWSER_BRIDGE_URL%"=="" set "PCMMAD_BROWSER_BRIDGE_URL=%URL%"
if "%PCMMAD_BROWSER_SCREENSHOT_DIR%"=="" set "PCMMAD_BROWSER_SCREENSHOT_DIR=%ROOT%browser_screenshots"
if "%PCMMAD_BROWSER_BRIDGE_GATE_FILE%"=="" set "PCMMAD_BROWSER_BRIDGE_GATE_FILE=%ROOT%.heat_runtime\browser_bridge_gate.json"
if "%PCMMAD_BROWSER_DEFAULT_CHANNEL%"=="" set "PCMMAD_BROWSER_DEFAULT_CHANNEL=msedge"
cd /d "%RUNTIME%"
echo Starting unmanaged development browser bridge at %PCMMAD_BROWSER_BRIDGE_URL%
"%PYTHON%" browser_bridge_service.py --host 127.0.0.1 --port 4471
exit /b %ERRORLEVEL%
