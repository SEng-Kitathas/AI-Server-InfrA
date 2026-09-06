param(
    [ValidateSet("Restart", "Start", "Stop", "Status")]
    [string]$Action = "Restart",
    [int]$Port = 5000,
    [int]$DelaySeconds = 2,
    [int]$PreDelaySeconds = 0,
    [string]$HostAddress = "127.0.0.1",
    [string]$ApiKey = "",
    [switch]$NoNgrok,
    [string]$ReceiptPath = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Runtime = Join-Path $Root "baseline\pcmmad_receiver"
$ServerPy = Join-Path $Runtime "server.py"
$VenvPython = Join-Path $Runtime ".venv\Scripts\python.exe"
$SchemaTemplate = Join-Path $Runtime "pcmmad_lab_action_schema_v10_3_pcmmad_native_protocol_compact_30_router.json"
$ActiveSchema = Join-Path $Runtime "pcmmad_lab_action_schema_ACTIVE.json"
$ReceiptRoot = Join-Path $env:TEMP "pcmmad_restart_receipts"
if ([string]::IsNullOrWhiteSpace($ReceiptPath)) {
    New-Item -ItemType Directory -Force -Path $ReceiptRoot | Out-Null
    $ReceiptPath = Join-Path $ReceiptRoot ("restart_" + (Get-Date -Format "yyyyMMdd_HHmmss_fff") + ".json")
}
$Script:Receipt = [ordered]@{
    ok = $false
    action = $Action
    stage = "init"
    started_at = (Get-Date).ToUniversalTime().ToString("o")
    finished_at = $null
    root = $Root
    runtime = $Runtime
    port = $Port
    stopped_receiver_pids = @()
    stopped_ngrok_pids = @()
    stopped_wrapper_pids = @()
    receiver_listener_pid = $null
    receiver_process_pids = @()
    ngrok_pids = @()
    public_url = $null
    error = $null
}

function Save-Receipt {
    param([string]$Stage, [bool]$Ok = $false, [string]$ErrorText = "")
    $Script:Receipt.stage = $Stage
    $Script:Receipt.ok = $Ok
    if (-not [string]::IsNullOrWhiteSpace($ErrorText)) { $Script:Receipt.error = $ErrorText }
    if ($Ok -or $Stage -eq "failed" -or $Stage -eq "stopped" -or $Stage -eq "status") {
        $Script:Receipt.finished_at = (Get-Date).ToUniversalTime().ToString("o")
    }
    $dir = Split-Path -Parent $ReceiptPath
    if ($dir) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    $tmp = $ReceiptPath + ".tmp"
    $Script:Receipt | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $tmp -Encoding UTF8
    Move-Item -LiteralPath $tmp -Destination $ReceiptPath -Force
}

function Write-Stage([string]$Message) {
    Write-Host ""
    Write-Host "=== $Message ==="
    Save-Receipt -Stage $Message
}

function Import-UserEnvironment {
    $names = @(
        "PCMMAD_ROOT", "PCMMAD_PROJECTS_ROOT", "PCMMAD_SYSTEM_ROOT",
        "PCMMAD_SANDBOX_ROOT", "PCMMAD_TEMP_ROOT", "PCMMAD_MOUNTS_JSON",
        "PCMMAD_BROWSER_BRIDGE_URL", "PCMMAD_BROWSER_SCREENSHOT_DIR",
        "PCMMAD_BIND_HOST", "PCMMAD_BIND_PORT", "PCMMAD_PROTOCOL_POLICY_MODE"
    )
    foreach ($name in $names) {
        # Restart is a canonical rehydration boundary: prefer persisted User-level
        # configuration over stale/poisoned values inherited from the dying server.
        $value = [Environment]::GetEnvironmentVariable($name, "User")
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            Set-Item -Path "Env:$name" -Value $value
        }
    }
}

function Resolve-ApiKey([string]$ExplicitKey) {
    if (-not [string]::IsNullOrWhiteSpace($ExplicitKey)) { return $ExplicitKey }
    if (-not [string]::IsNullOrWhiteSpace($env:GITHOME_API_KEY)) { return $env:GITHOME_API_KEY }
    $saved = [Environment]::GetEnvironmentVariable("GITHOME_API_KEY", "User")
    if (-not [string]::IsNullOrWhiteSpace($saved)) { return $saved }
    throw "GITHOME_API_KEY is not configured as a User environment variable."
}

function Get-AllProcesses { @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue) }

function Test-IsReceiverServerProcess($Process) {
    if (-not $Process -or -not $Process.CommandLine) { return $false }
    if ($Process.Name -notin @("python.exe", "pythonw.exe")) { return $false }
    $cmd = [string]$Process.CommandLine
    $exact = [regex]::Escape($ServerPy)
    if ($cmd -match $exact) { return $true }
    # Legacy receiver installs are eligible; unrelated projects that merely reuse the venv are not.
    return ($cmd -match '(?i)\\PCMMAD_receiver\\baseline\\pcmmad_receiver\\server\.py(?:[\"\s]|$)')
}

function Get-ReceiverServerProcesses { @(Get-AllProcesses | Where-Object { Test-IsReceiverServerProcess $_ }) }
function Get-NgrokProcesses { @(Get-CimInstance Win32_Process -Filter "Name='ngrok.exe'" -ErrorAction SilentlyContinue) }

function Test-IsReceiverWrapper($Process) {
    if (-not $Process -or -not $Process.CommandLine) { return $false }
    if ($Process.Name -notin @("powershell.exe", "pwsh.exe", "cmd.exe")) { return $false }
    $cmd = [string]$Process.CommandLine
    return ($cmd -match [regex]::Escape($ServerPy))
}

function Test-IsNgrokWrapper($Process) {
    if (-not $Process -or -not $Process.CommandLine) { return $false }
    if ($Process.Name -notin @("powershell.exe", "pwsh.exe", "cmd.exe")) { return $false }
    return ([string]$Process.CommandLine -match '(?i)ngrok(?:\.exe)?\s+http\b')
}

function Stop-ProcessSet([object[]]$Processes, [string]$Kind) {
    foreach ($proc in @($Processes | Sort-Object ProcessId -Unique)) {
        if (-not $proc) { continue }
        Write-Host "Stopping $Kind PID $($proc.ProcessId): $($proc.CommandLine)"
        try { Stop-Process -Id ([int]$proc.ProcessId) -Force -ErrorAction Stop } catch {
            if (Get-Process -Id ([int]$proc.ProcessId) -ErrorAction SilentlyContinue) { throw }
        }
        if ($Kind -eq "receiver") { $Script:Receipt.stopped_receiver_pids += [int]$proc.ProcessId }
        elseif ($Kind -eq "ngrok") { $Script:Receipt.stopped_ngrok_pids += [int]$proc.ProcessId }
        else { $Script:Receipt.stopped_wrapper_pids += [int]$proc.ProcessId }
    }
}

function Get-PortOwner([int]$TargetPort) {
    $connection = Get-NetTCPConnection -LocalPort $TargetPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $connection) { return $null }
    return Get-CimInstance Win32_Process -Filter "ProcessId=$($connection.OwningProcess)" -ErrorAction SilentlyContinue
}

function Wait-ForStop([int]$TimeoutSeconds = 15) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        $receiver = @(Get-ReceiverServerProcesses)
        $ngrok = @(Get-NgrokProcesses)
        $owner = Get-PortOwner $Port
        if ($receiver.Count -eq 0 -and $ngrok.Count -eq 0 -and -not $owner) { return $true }
        Start-Sleep -Milliseconds 250
    } while ((Get-Date) -lt $deadline)
    return $false
}

function Stop-PcmmadStack {
    # Kill service executables first; wrappers second. Never use interpreter identity as service identity.
    Stop-ProcessSet -Processes (Get-ReceiverServerProcesses) -Kind "receiver"
    Stop-ProcessSet -Processes (Get-NgrokProcesses) -Kind "ngrok"
    Start-Sleep -Milliseconds 300
    $wrappers = @(Get-AllProcesses | Where-Object { (Test-IsReceiverWrapper $_) -or (Test-IsNgrokWrapper $_) })
    Stop-ProcessSet -Processes $wrappers -Kind "wrapper"

    if (-not (Wait-ForStop -TimeoutSeconds 15)) {
        $remainingReceiver = @(Get-ReceiverServerProcesses)
        $remainingNgrok = @(Get-NgrokProcesses)
        $owner = Get-PortOwner $Port
        $detail = "receiver=$($remainingReceiver.Count) ngrok=$($remainingNgrok.Count) portOwner=" + $(if($owner){$owner.ProcessId}else{'none'})
        throw "Shutdown convergence failed: $detail"
    }
}

function Resolve-NgrokExe {
    $cmd = Get-Command ngrok.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cmd) { return $cmd.Source }
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links\ngrok.exe'),
        (Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\ngrok.exe'),
        (Join-Path $env:USERPROFILE 'scoop\shims\ngrok.exe'),
        (Join-Path $env:ProgramData 'chocolatey\bin\ngrok.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\ngrok\ngrok.exe'),
        (Join-Path $env:USERPROFILE 'ngrok\ngrok.exe')
    )
    foreach ($candidate in $candidates) { if ($candidate -and (Test-Path -LiteralPath $candidate)) { return $candidate } }
    throw "A working ngrok.exe could not be found."
}

function Start-Receiver {
    $env:PCMMAD_RECEIVER_INSTANCE = "desktop_canonical"
    $env:PCMMAD_BIND_HOST = $HostAddress
    $env:PCMMAD_BIND_PORT = [string]$Port
    $proc = Start-Process -FilePath $VenvPython -ArgumentList @($ServerPy) -WorkingDirectory $Runtime -PassThru
    Write-Host "Receiver launcher PID: $($proc.Id)"
}

function Wait-ReceiverHealth([string]$Url, [string]$Key, [int]$TimeoutSeconds = 30) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $headers = @{ "X-GitHome-Key" = $Key }
    do {
        try {
            $response = Invoke-RestMethod -Method Get -Uri $Url -Headers $headers -TimeoutSec 3
            if ($response.ok -eq $true) { return $response }
        } catch { }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)
    throw "Receiver did not become healthy at $Url within $TimeoutSeconds seconds."
}

function Start-Ngrok([string]$TargetUrl) {
    $exe = Resolve-NgrokExe
    try { & $exe version *> $null } catch { throw "ngrok failed version preflight: $exe" }
    if ($LASTEXITCODE -ne 0) { throw "ngrok failed version preflight: $exe" }
    $proc = Start-Process -FilePath $exe -ArgumentList @("http", $TargetUrl) -PassThru
    Write-Host "ngrok PID: $($proc.Id)"
}

function Get-NgrokPublicUrl([int]$TimeoutSeconds = 20) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $state = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 3
            $urls = @($state.tunnels | Where-Object { $_.public_url -like "https://*" } | Select-Object -ExpandProperty public_url)
            if ($urls.Count -eq 1) { return [string]$urls[0] }
            if ($urls.Count -gt 1) { throw "More than one ngrok HTTPS tunnel exists after clean start." }
        } catch { if ($_.Exception.Message -like '*More than one*') { throw } }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)
    throw "ngrok public HTTPS URL was not available from the local API."
}

function Write-ActiveSchema([string]$PublicUrl) {
    if (-not (Test-Path $SchemaTemplate)) { return }
    $schema = Get-Content -Raw -LiteralPath $SchemaTemplate | ConvertFrom-Json
    $schema.servers[0].url = $PublicUrl.TrimEnd('/')
    $schema | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $ActiveSchema -Encoding UTF8
}

function Refresh-ObservedState {
    $owner = Get-PortOwner $Port
    $Script:Receipt.receiver_listener_pid = $(if($owner){[int]$owner.ProcessId}else{$null})
    $Script:Receipt.receiver_process_pids = @((Get-ReceiverServerProcesses) | ForEach-Object {[int]$_.ProcessId})
    $Script:Receipt.ngrok_pids = @((Get-NgrokProcesses) | ForEach-Object {[int]$_.ProcessId})
}

try {
    if (-not (Test-Path -LiteralPath $ServerPy)) { throw "server.py not found: $ServerPy" }
    if (-not (Test-Path -LiteralPath $VenvPython)) { throw "Virtual environment missing: $VenvPython" }
    Import-UserEnvironment
    if (-not [string]::IsNullOrWhiteSpace($env:PCMMAD_BIND_HOST)) { $HostAddress = $env:PCMMAD_BIND_HOST }
    if (-not [string]::IsNullOrWhiteSpace($env:PCMMAD_BIND_PORT)) { $Port = [int]$env:PCMMAD_BIND_PORT }
    $LocalBase = "http://$HostAddress`:$Port"
    $ResolvedApiKey = Resolve-ApiKey -ExplicitKey $ApiKey
    $env:GITHOME_API_KEY = $ResolvedApiKey

    if ($Action -eq "Status") {
        Refresh-ObservedState
        try { $null = Wait-ReceiverHealth -Url "$LocalBase/health" -Key $ResolvedApiKey -TimeoutSeconds 2 } catch { }
        Save-Receipt -Stage "status" -Ok $true
        $Script:Receipt | ConvertTo-Json -Depth 10
        exit 0
    }

    if ($Action -in @("Restart", "Stop")) {
        if ($PreDelaySeconds -gt 0) {
            Save-Receipt -Stage "scheduled"
            Start-Sleep -Seconds ([Math]::Min($PreDelaySeconds, 30))
        }
        Write-Stage "stopping"
        Stop-PcmmadStack
        Refresh-ObservedState
        if ($Action -eq "Stop") {
            Save-Receipt -Stage "stopped" -Ok $true
            Write-Host "PCMMAD stack stopped cleanly. Receipt: $ReceiptPath"
            exit 0
        }
        if ($DelaySeconds -gt 0) { Start-Sleep -Seconds $DelaySeconds }
    }

    if ($Action -in @("Restart", "Start")) {
        $owner = Get-PortOwner $Port
        if ($owner) { throw "Refusing start: port $Port is already owned by PID $($owner.ProcessId): $($owner.CommandLine)" }
        if ((Get-ReceiverServerProcesses).Count -gt 0) { throw "Refusing start: receiver process already exists." }
        if (-not $NoNgrok -and (Get-NgrokProcesses).Count -gt 0) { throw "Refusing start: ngrok process already exists." }

        Write-Stage "starting_receiver"
        Start-Receiver
        $health = Wait-ReceiverHealth -Url "$LocalBase/health" -Key $ResolvedApiKey -TimeoutSeconds 30
        Write-Host "Receiver health: OK"

        if (-not $NoNgrok) {
            Write-Stage "starting_ngrok"
            Start-Ngrok -TargetUrl $LocalBase
            $PublicUrl = Get-NgrokPublicUrl -TimeoutSeconds 20
            $Script:Receipt.public_url = $PublicUrl
            Write-ActiveSchema -PublicUrl $PublicUrl
            Write-Host "Public URL: $PublicUrl"
        }

        Refresh-ObservedState
        if (-not $Script:Receipt.receiver_listener_pid) { throw "Post-start verification failed: no listener owns port $Port." }
        if ($Script:Receipt.receiver_process_pids.Count -lt 1) { throw "Post-start verification failed: no canonical receiver process found." }
        if (-not $NoNgrok -and $Script:Receipt.ngrok_pids.Count -ne 1) { throw "Post-start verification failed: expected exactly one ngrok process, found $($Script:Receipt.ngrok_pids.Count)." }

        Save-Receipt -Stage "ready" -Ok $true
        Write-Host "PCMMAD restart converged successfully."
        Write-Host "Receipt: $ReceiptPath"
        exit 0
    }
}
catch {
    Refresh-ObservedState
    Save-Receipt -Stage "failed" -Ok $false -ErrorText $_.Exception.Message
    Write-Error $_.Exception.Message
    Write-Host "Failure receipt: $ReceiptPath"
    exit 1
}
