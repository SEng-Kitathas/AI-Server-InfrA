@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RESTART_RECEIVER_AND_NGROK.ps1" -DelaySeconds 3 -NoNgrok
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" echo PCMMAD command failed with code %RC%.
pause
exit /b %RC%
