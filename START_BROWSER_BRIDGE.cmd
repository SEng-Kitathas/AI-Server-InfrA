@echo off
setlocal
set "ROOT=%~dp0"
set "RUNTIME=%ROOT%baseline\pcmmad_receiver"
set "PYTHON=%RUNTIME%\.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
  echo ERROR: PCMMAD virtual environment is missing. Run SETUP_PCMMAD_RUNTIME.ps1 first.
  pause
  exit /b 2
)
if "%PCMMAD_BROWSER_BRIDGE_URL%"=="" set "PCMMAD_BROWSER_BRIDGE_URL=http://127.0.0.1:4471"
if "%PCMMAD_BROWSER_SCREENSHOT_DIR%"=="" set "PCMMAD_BROWSER_SCREENSHOT_DIR=%ROOT%browser_screenshots"
cd /d "%RUNTIME%"
echo Starting PCMMAD browser bridge with %PYTHON%
"%PYTHON%" browser_bridge_service.py --host 127.0.0.1 --port 4471
set "RC=%ERRORLEVEL%"
pause
exit /b %RC%
