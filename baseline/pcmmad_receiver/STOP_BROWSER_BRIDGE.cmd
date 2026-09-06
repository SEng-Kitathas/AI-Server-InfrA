@echo off

powershell -NoProfile -ExecutionPolicy Bypass -Command "$c=Get-NetTCPConnection -LocalPort 4471 -State Listen -ErrorAction SilentlyContinue; if (-not $c) { Write-Host 'No browser bridge listener found on port 4471'; exit 0 }; $c | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Write-Host ('Stopping PID ' + $_); Stop-Process -Id $_ -Force }"

pause

