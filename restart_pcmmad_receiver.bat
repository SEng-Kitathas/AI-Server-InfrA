@echo off
setlocal EnableExtensions
set "PCMMAD_INSTALL_ROOT=%~dp0"
set "PCMMAD_LAUNCHER=%PCMMAD_INSTALL_ROOT%PCMMAD.ps1"
set "ACTION=Restart"
set "DO_PAUSE=1"

for %%A in (%*) do (
  if /I "%%~A"=="--status" set "ACTION=Status"
  if /I "%%~A"=="--no-pause" set "DO_PAUSE=0"
)

if not exist "%PCMMAD_LAUNCHER%" (
  echo ERROR: Canonical launcher not found:
  echo   %PCMMAD_LAUNCHER%
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

if /I "%ACTION%"=="Restart" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PCMMAD_LAUNCHER%" -Action Restart -ForceRestart
) else (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PCMMAD_LAUNCHER%" -Action Status
)
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo PCMMAD %ACTION% FAILED with exit code %RC%.
) else (
  echo PCMMAD %ACTION% completed successfully.
)
if "%DO_PAUSE%"=="1" pause
exit /b %RC%
