@echo off

setlocal

cd /d "%~dp0"

set "PCMMAD_BROWSER_BRIDGE_URL=http://127.0.0.1:4471"

set "PCMMAD_BROWSER_SCREENSHOT_DIR=%~dp0browser_screenshots"

echo Starting PCMMAD browser bridge at %PCMMAD_BROWSER_BRIDGE_URL%

echo Screenshots: %PCMMAD_BROWSER_SCREENSHOT_DIR%

python browser_bridge_service.py --host 127.0.0.1 --port 4471

pause

