param(
 [Parameter(Mandatory=$true)][string]$BundleSource,
 [string]$InstallRoot = "$env:ProgramData\PCMMAD\Recovery",
 [string]$TaskName = "PCMMAD_BreakGlass_Recovery",
 [string]$ReceiverHealth = "http://127.0.0.1:5000/health"
)
$ErrorActionPreference='Stop'
function Sha256([string]$p){(Get-FileHash -Algorithm SHA256 -LiteralPath $p).Hash.ToLowerInvariant()}
$src=(Resolve-Path $BundleSource).Path;$manifest=Join-Path $src 'bundle_manifest.json';if(-not(Test-Path $manifest)){throw 'SOURCE_MANIFEST_MISSING'}
$m=Get-Content -Raw $manifest|ConvertFrom-Json;foreach($a in $m.artifacts){$p=Join-Path $src $a.path;if(-not(Test-Path $p)){throw "SOURCE_ARTIFACT_MISSING:$($a.path)"};if((Sha256 $p)-ne $a.sha256){throw "SOURCE_ARTIFACT_HASH_MISMATCH:$($a.path)"}}
$manifestSha=Sha256 $manifest
New-Item -ItemType Directory -Force -Path $InstallRoot|Out-Null
Copy-Item -LiteralPath (Join-Path $src '*') -Destination $InstallRoot -Recurse -Force
$installedManifest=Join-Path $InstallRoot 'bundle_manifest.json';if((Sha256 $installedManifest)-ne $manifestSha){throw 'INSTALLED_MANIFEST_HASH_MISMATCH'}
$bootstrap=Join-Path $InstallRoot 'bootstrap.ps1';@"
`$ErrorActionPreference='Stop'
function Sha256([string]`$p){(Get-FileHash -Algorithm SHA256 -LiteralPath `$p).Hash.ToLowerInvariant()}
`$root='$InstallRoot';`$expected='$manifestSha';`$manifest=Join-Path `$root 'bundle_manifest.json'
if(-not(Test-Path `$manifest) -or (Sha256 `$manifest)-ne `$expected){throw 'BREAKGLASS_MANIFEST_ANCHOR_MISMATCH'}
try{`$r=Invoke-WebRequest -UseBasicParsing -Uri '$ReceiverHealth' -TimeoutSec 3;if(`$r.StatusCode -ge 200 -and `$r.StatusCode -lt 300){exit 0}}catch{}
# Availability root only restores material. Normal receiver startup remains canonical and separately supervised.
`$target=Join-Path `$env:ProgramData 'PCMMAD\RecoveredMinimum'
& (Join-Path `$root 'breakglass_restore.ps1') -BundleRoot `$root -TargetRoot `$target
if(`$LASTEXITCODE -ne 0){exit `$LASTEXITCODE}
"@|Set-Content -Encoding UTF8 $bootstrap
$action=New-ScheduledTaskAction -Execute 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -Argument ('-NoProfile -ExecutionPolicy Bypass -File "'+$bootstrap+'"')
$trigger=New-ScheduledTaskTrigger -AtStartup;$principal=New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest;$settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Minutes 15)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force|Out-Null
Write-Output "BREAKGLASS_INSTALLED ROOT=$InstallRoot MANIFEST_SHA256=$manifestSha TASK=$TaskName"
