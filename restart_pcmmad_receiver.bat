@echo off
setlocal EnableExtensions
set "PCMMAD_INSTALL_ROOT=%USERPROFILE%\Desktop\PCMMAD_RECEIVER_V29_NATIVE_PROTOCOL_RC1\PCMMAD_receiver"
set "RESTART_PS1=%PCMMAD_INSTALL_ROOT%\RESTART_RECEIVER_AND_NGROK.ps1"
set "ACTION=Restart"
set "DO_PAUSE=1"

for %%A in (%*) do (
  if /I "%%~A"=="--status" set "ACTION=Status"
  if /I "%%~A"=="--no-pause" set "DO_PAUSE=0"
)

if not exist "%RESTART_PS1%" (
  echo ERROR: Restart controller not found:
  echo   %RESTART_PS1%
  if "%DO_PAUSE%"=="1" pause
  exit /b 2
)

echo ============================================================
if /I "%ACTION%"=="Status" (
  echo PCMMAD Receiver - status probe
) else (
  echo PCMMAD Receiver - clean convergent restart
)
echo ============================================================

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%RESTART_PS1%" -Action %ACTION% -DelaySeconds 2
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo PCMMAD %ACTION% FAILED with exit code %RC%.
) else (
  echo PCMMAD %ACTION% completed successfully.
)
if "%DO_PAUSE%"=="1" pause
exit /b %RC%
