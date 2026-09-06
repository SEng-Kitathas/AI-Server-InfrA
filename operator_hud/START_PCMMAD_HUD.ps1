$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = 'C:\Users\ancal\Desktop\PCMMAD_RECEIVER_V29_NATIVE_PROTOCOL_RC1\PCMMAD_receiver\baseline\pcmmad_receiver\.venv\Scripts\python.exe'
$HudUrl = 'http://127.0.0.1:5090/'

if (-not $env:GITHOME_API_KEY) {
    throw 'GITHOME_API_KEY is not present in this PowerShell environment.'
}

Write-Host 'Starting PCMMAD HUD...'
Write-Host "HUD: $HudUrl"
Write-Host 'Receiver: http://127.0.0.1:5000'
Write-Host 'Browser bridge: http://127.0.0.1:4471'
Write-Host 'API key remains server-side; it is not delivered to the browser.'

Start-Process powershell.exe -ArgumentList @(
    '-NoExit',
    '-NoProfile',
    '-Command',
    "Set-Location -LiteralPath '$Here'; & '$Python' '$Here\server.py'"
)

$deadline = (Get-Date).AddSeconds(15)
while ((Get-Date) -lt $deadline) {
    try {
        $r = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:5090/api/meta' -TimeoutSec 2
        if ($r.StatusCode -eq 200) { break }
    } catch { Start-Sleep -Milliseconds 350 }
}

Start-Process $HudUrl
Write-Host 'HUD launch requested.'
