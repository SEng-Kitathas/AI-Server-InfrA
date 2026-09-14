param(
 [Parameter(Mandatory=$true)][string]$BundleRoot,
 [Parameter(Mandatory=$true)][string]$TargetRoot,
 [switch]$VerifyOnly
)
$ErrorActionPreference='Stop'
function Sha256([string]$p){(Get-FileHash -Algorithm SHA256 -LiteralPath $p).Hash.ToLowerInvariant()}
$manifestPath=Join-Path $BundleRoot 'bundle_manifest.json'
if(-not(Test-Path $manifestPath)){throw 'BREAKGLASS_MANIFEST_MISSING'}
$m=Get-Content -Raw -LiteralPath $manifestPath|ConvertFrom-Json
foreach($a in $m.artifacts){$p=Join-Path $BundleRoot $a.path;if(-not(Test-Path $p)){throw "BREAKGLASS_ARTIFACT_MISSING:$($a.path)"};if((Sha256 $p)-ne $a.sha256){throw "BREAKGLASS_HASH_MISMATCH:$($a.path)"}}
if($VerifyOnly){Write-Output 'BREAKGLASS_BUNDLE_VERIFIED';exit 0}
New-Item -ItemType Directory -Force -Path $TargetRoot|Out-Null
$src=Join-Path $BundleRoot 'known_good_receiver.zip';$runtimeZip=Join-Path $BundleRoot 'recovery_python.zip'
$sourceOut=Join-Path $TargetRoot 'receiver';$runtimeOut=Join-Path $TargetRoot 'runtime'
if(Test-Path $sourceOut){Remove-Item -Recurse -Force $sourceOut};if(Test-Path $runtimeOut){Remove-Item -Recurse -Force $runtimeOut}
New-Item -ItemType Directory -Force -Path $sourceOut,$runtimeOut|Out-Null
& tar.exe -xf $src -C $sourceOut;if($LASTEXITCODE -ne 0){throw 'SOURCE_EXTRACT_FAILED'}
& tar.exe -xf $runtimeZip -C $runtimeOut;if($LASTEXITCODE -ne 0){throw 'RUNTIME_EXTRACT_FAILED'}
$py=Join-Path $runtimeOut 'Python312\\python.exe';if(-not(Test-Path $py)){throw 'RECOVERY_RUNTIME_NOT_RESTORED'}
$baseline=Join-Path $sourceOut 'baseline';$probe="import sys;sys.path.insert(0,r'$baseline');import pcmmad_receiver.lab_tools as l;c=l.list_tools();assert len(c)>=100;print('RECOVERY_RECEIVER_IMPORT_OK',len(c))"
& $py -I -c $probe
if($LASTEXITCODE -ne 0){throw "RECOVERY_RECEIVER_FUNCTIONAL_PROBE_FAILED:$LASTEXITCODE"}
Write-Output "BREAKGLASS_RESTORE_OK TARGET=$TargetRoot"

