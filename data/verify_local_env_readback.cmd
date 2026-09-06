@echo off
cd /d "%~dp0.."
call PCMMAD_LOCAL_ENV.cmd
"C:\Program Files\Python312\python.exe" "%~dp0verify_local_env_readback.py"
