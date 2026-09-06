@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0PCMMAD.ps1" -Action BrowserStop
set "RC=%ERRORLEVEL%"
pause
exit /b %RC%
