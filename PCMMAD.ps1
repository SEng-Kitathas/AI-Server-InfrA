param(
    [ValidateSet("Setup", "Start", "Restart", "Stop", "Status", "Verify", "BrowserStart", "BrowserStop")]
    [string]$Action = "Status",
    [switch]$NoNgrok,
    [int]$Port = 5000,
    [string]$HostAddress = "127.0.0.1"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Runtime = Join-Path $Root "baseline\pcmmad_receiver"
$Python = Join-Path $Runtime ".venv\Scripts\python.exe"
$RestartScript = Join-Path $Root "RESTART_RECEIVER_AND_NGROK.ps1"
$SetupScript = Join-Path $Root "SETUP_PCMMAD_RUNTIME.ps1"

function Get-ApiKey {
    $value = $env:GITHOME_API_KEY
    if ([string]::IsNullOrWhiteSpace($value)) {
        $value = [Environment]::GetEnvironmentVariable("GITHOME_API_KEY", "User")
    }
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "GITHOME_API_KEY is not configured as a User environment variable."
    }
    return $value
}

function Get-PcmmadProcesses {
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -and (
            $_.CommandLine -match "server\.py" -or
            $_.CommandLine -match "browser_bridge_service\.py"
        ) -and $_.CommandLine -like "*$Runtime*"
    }
}

function Stop-PcmmadProcesses {
    foreach ($process in @(Get-PcmmadProcesses)) {
        Write-Host "Stopping PCMMAD PID $($process.ProcessId): $($process.CommandLine)"
        Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
    }
    foreach ($process in @(Get-CimInstance Win32_Process -Filter "Name='ngrok.exe'" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -and $_.CommandLine -match "\bhttp\b"
    })) {
        Write-Host "Stopping ngrok PID $($process.ProcessId)"
        Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Invoke-Verify {
    if (-not (Test-Path $Python)) {
        throw "PCMMAD virtual environment is missing. Run: .\PCMMAD.ps1 -Action Setup"
    }
    Push-Location $Root
    try {
        & $Python -m compileall -q "baseline\pcmmad_receiver" "tests" "tools\csc_native" "system"
        if ($LASTEXITCODE -ne 0) { throw "compileall verification failed" }
        & $Python -m unittest discover -s tests -p "test_*.py"
        if ($LASTEXITCODE -ne 0) { throw "regression tests failed" }
        $gates = @(
            "receiver_baseline_selftest_gate.py",
            "receiver_schema_authority_gate.py",
            "semantic_footgun_dataflow_gate.py",
            "receiver_full_route_trace_gate.py",
            "receiver_resilience_gate_suite.py",
            "receiver_package_integrity_gate.py",
            "receiver_launcher_script_audit_gate.py"
        )
        foreach ($gate in $gates) {
            Write-Host "Running $gate"
            & $Python (Join-Path $Root "tools\csc_native\$gate")
            if ($LASTEXITCODE -ne 0) { throw "$gate failed" }
        }
        & $Python (Join-Path $Root "tools\verify_release.py")
        if ($LASTEXITCODE -ne 0) { throw "aggregate release verification failed" }
        Write-Host "PCMMAD verification contract: CLEAN"
    }
    finally {
        Pop-Location
    }
}

function Start-BrowserBridge {
    if (-not (Test-Path $Python)) {
        throw "PCMMAD virtual environment is missing. Run Setup first."
    }
    $bridgeUrl = [Environment]::GetEnvironmentVariable("PCMMAD_BROWSER_BRIDGE_URL", "User")
    if ([string]::IsNullOrWhiteSpace($bridgeUrl)) { $bridgeUrl = "http://127.0.0.1:4471" }
    $uri = [Uri]$bridgeUrl
    $screenshotDir = Join-Path $Root "browser_screenshots"
    $env:PCMMAD_BROWSER_BRIDGE_URL = $bridgeUrl.TrimEnd('/')
    $env:PCMMAD_BROWSER_SCREENSHOT_DIR = $screenshotDir
    Start-Process -FilePath "powershell.exe" -WorkingDirectory $Runtime -ArgumentList @(
        "-NoExit", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
        "& '$Python' '$(Join-Path $Runtime 'browser_bridge_service.py')' --host '$($uri.Host)' --port $($uri.Port)"
    ) | Out-Null
    Write-Host "Browser bridge starting at $bridgeUrl"
}

switch ($Action) {
    "Setup" {
        & $SetupScript
        exit $LASTEXITCODE
    }
    "Start" {
        & $RestartScript -Port $Port -HostAddress $HostAddress -DelaySeconds 1 -NoNgrok:$NoNgrok
        exit $LASTEXITCODE
    }
    "Restart" {
        & $RestartScript -Port $Port -HostAddress $HostAddress -DelaySeconds 3 -NoNgrok:$NoNgrok
        exit $LASTEXITCODE
    }
    "Stop" {
        Stop-PcmmadProcesses
        exit 0
    }
    "Status" {
        $key = Get-ApiKey
        $url = "http://$HostAddress`:$Port/lab/health"
        try {
            $health = Invoke-RestMethod -Uri $url -Headers @{ "X-GitHome-Key" = $key } -TimeoutSec 5
            $health | ConvertTo-Json -Depth 20
            exit 0
        }
        catch {
            Write-Host "PCMMAD is not healthy at $url"
            Write-Host $_.Exception.Message
            exit 1
        }
    }
    "Verify" {
        Invoke-Verify
        exit 0
    }
    "BrowserStart" {
        Start-BrowserBridge
        exit 0
    }
    "BrowserStop" {
        foreach ($process in @(Get-PcmmadProcesses | Where-Object { $_.CommandLine -match "browser_bridge_service\.py" })) {
            Write-Host "Stopping browser bridge PID $($process.ProcessId)"
            Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
        }
        exit 0
    }
}
