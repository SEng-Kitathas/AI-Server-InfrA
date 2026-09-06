param(
    [string]$PythonVersion = "3.12"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Runtime = Join-Path $Root "baseline\pcmmad_receiver"
$VenvPython = Join-Path $Runtime ".venv\Scripts\python.exe"
$Requirements = Join-Path $Runtime "requirements.txt"

Write-Host "PCMMAD root: $Root"
Write-Host "Runtime:     $Runtime"

if (-not (Test-Path (Join-Path $Runtime "server.py"))) {
    throw "server.py not found at $Runtime"
}
if (-not (Test-Path $Requirements)) {
    throw "requirements.txt not found at $Requirements"
}

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating Python $PythonVersion virtual environment..."
    & py "-$PythonVersion" -m venv (Join-Path $Runtime ".venv")
    if ($LASTEXITCODE -ne 0) { throw "Virtual environment creation failed." }
}

Write-Host "Installing exact receiver dependency ranges..."
& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }
& $VenvPython -m pip install -r $Requirements
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }

& $VenvPython -c "import flask, requests, bs4; print('PCMMAD Python dependencies OK')"
if ($LASTEXITCODE -ne 0) { throw "Dependency import verification failed." }

$key = [Environment]::GetEnvironmentVariable("GITHOME_API_KEY", "User")
Write-Host "Saved GITHOME_API_KEY present: $(-not [string]::IsNullOrWhiteSpace($key))"

$ngrok = Get-Command ngrok -ErrorAction SilentlyContinue
if ($ngrok) { & ngrok version } else { Write-Warning "ngrok is not on PATH." }

Write-Host "Setup verification completed."
