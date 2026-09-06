@echo off
rem Optional non-secret local overrides. GITHOME_API_KEY is stored as a User environment variable.
set "PCMMAD_BIND_HOST=127.0.0.1"
set "PCMMAD_BIND_PORT=5000"
set "PCMMAD_BROWSER_BRIDGE_URL=http://127.0.0.1:4471"
set "PCMMAD_BROWSER_SCREENSHOT_DIR=%~dp0browser_screenshots"
