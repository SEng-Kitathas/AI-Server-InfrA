param(
 [Parameter(Mandatory=$true)][string]$PromotionBackup,
 [string]$InstallRoot="$env:ProgramData\PCMMAD\Recovery",
 [string]$DaemonProjectRoot="",
 [int]$ReceiverPort=5000,
 [int]$NgrokApiPort=4040,
 [int]$DaemonPort=5015
)
$ErrorActionPreference='Stop'
function Resolve-UnderRoot([string]$Root,[string]$Relative){$rootFull=[IO.Path]::GetFullPath($Root).TrimEnd('\')+'\';$candidate=[IO.Path]::GetFullPath((Join-Path $Root $Relative));if(-not $candidate.StartsWith($rootFull,[StringComparison]::OrdinalIgnoreCase)){throw ('PROMOTION_BACKUP_PATH_ESCAPE:'+$Relative)};return $candidate}
$PromotionBackup=[IO.Path]::GetFullPath($PromotionBackup);if(-not(Test-Path $PromotionBackup)){throw 'PROMOTION_BACKUP_MISSING'}
$promotionDir=Join-Path $PromotionBackup 'promotion';$metaPath=Join-Path $promotionDir 'promotion_metadata.json';if(-not(Test-Path $metaPath)){throw 'PROMOTION_METADATA_MISSING'}
$meta=Get-Content -Raw $metaPath|ConvertFrom-Json;if([string]$meta.schema -ne 'pcmmad.promotion-backup.v1'){throw 'PROMOTION_METADATA_SCHEMA_MISMATCH'}
$storedProject=[IO.Path]::GetFullPath([string]$meta.daemon_project_root);if([string]::IsNullOrWhiteSpace($DaemonProjectRoot)){$DaemonProjectRoot=$storedProject}elseif(-not([IO.Path]::GetFullPath($DaemonProjectRoot).Equals($storedProject,[StringComparison]::OrdinalIgnoreCase))){throw 'ROLLBACK_DAEMON_PROJECT_ROOT_MISMATCH'}
$taskNames=@($meta.task_names|ForEach-Object {[string]$_});$running=@(Get-ScheduledTask -ErrorAction SilentlyContinue|Where-Object {$_.TaskName -in $taskNames -and $_.State -eq 'Running'});if($running.Count -gt 0){throw ('ROLLBACK_REQUIRES_MANAGED_TASKS_STOPPED:'+($running.TaskName -join ','))}
foreach($port in @($ReceiverPort,$NgrokApiPort,$DaemonPort)){if($port -gt 0 -and (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue)){throw ('ROLLBACK_REQUIRES_RUNTIME_LISTENERS_STOPPED:'+([string]$port))}}
$programPython=Join-Path $InstallRoot 'runtime\Python312\python.exe';if(-not(Test-Path $programPython)){$programPython=(Get-Command python.exe -ErrorAction SilentlyContinue|Select-Object -First 1 -ExpandProperty Source)};if([string]::IsNullOrWhiteSpace($programPython)){throw 'ROLLBACK_PYTHON_MISSING'}
$txHelper=Join-Path $InstallRoot 'recovery_program_tx.py';if(-not(Test-Path $txHelper)){$txHelper=Join-Path $PSScriptRoot 'recovery_program_tx.py'};if(-not(Test-Path $txHelper)){throw 'ROLLBACK_TX_HELPER_MISSING'}
# Stop/unregister current promoted definitions; prior XML is restored below and left stopped.
foreach($taskName in $taskNames){Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue;Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue}
# Restore generated config/secret/startup files from promotion metadata.
$fileStatePath=Join-Path $promotionDir 'file_state.json';if(-not(Test-Path $fileStatePath)){throw 'PROMOTION_FILE_STATE_MISSING'};$state=Get-Content -Raw $fileStatePath|ConvertFrom-Json;$fileBackup=Join-Path $promotionDir 'files'
foreach($prop in $state.psobject.Properties){$rel=[string]$prop.Name;$dst=Resolve-UnderRoot $InstallRoot $rel;if([string]$prop.Value -eq 'PRESENT'){$src=Resolve-UnderRoot $fileBackup $rel;if(-not(Test-Path $src)){throw ('PROMOTION_FILE_BACKUP_MISSING:'+ $rel)};Copy-Item -LiteralPath $src -Destination $dst -Force}else{Remove-Item -LiteralPath $dst -Force -ErrorAction SilentlyContinue}}
# Restore immutable program generation from archived transaction. Durable state not in program manifest is untouched.
& $programPython $txHelper rollback --tx $PromotionBackup --install-root $InstallRoot|Out-Null;if($LASTEXITCODE -ne 0){throw ('PROGRAM_ROLLBACK_FAILED:'+([string]$LASTEXITCODE))}
# Restore prior task definitions exactly; absent markers remain absent.
$taskMetaDir=Join-Path $promotionDir 'tasks'
foreach($taskName in $taskNames){$safe=$taskName.Replace('\','_').Replace('/','_');$xmlPath=Join-Path $taskMetaDir ($safe+'.xml');$absent=Join-Path $taskMetaDir ($safe+'.absent');if(Test-Path $xmlPath){Register-ScheduledTask -TaskName $taskName -Xml (Get-Content -Raw $xmlPath) -Force|Out-Null}elseif(-not(Test-Path $absent)){throw ('PROMOTION_TASK_BACKUP_MISSING:'+ $taskName)}}
# Restore prior handoff pointer only; generations and Daemon memory/evidence remain preserved.
$handoffRoot=Join-Path $DaemonProjectRoot 'handoff';New-Item -ItemType Directory -Force $handoffRoot|Out-Null;$current=Join-Path $handoffRoot 'current.json';$oldPointer=Join-Path $promotionDir 'old_handoff_pointer.json';$oldAbsent=Join-Path $promotionDir 'old_handoff_pointer.absent'
if(Test-Path $oldPointer){$obj=Get-Content -Raw $oldPointer|ConvertFrom-Json;if([string]$obj.schema -ne 'pcmmad.project-handoff-pointer.v1'){throw 'OLD_HANDOFF_POINTER_SCHEMA_MISMATCH'};$rel=[string]$obj.relative_path;if(-not $rel.StartsWith('generations/',[StringComparison]::Ordinal)){throw 'OLD_HANDOFF_POINTER_PATH_INVALID'};$gen=Resolve-UnderRoot $handoffRoot $rel;if(-not(Test-Path $gen)){throw 'OLD_HANDOFF_GENERATION_MISSING'};$manifest=Join-Path $gen 'SNAPSHOT_MANIFEST_SHA256.json';if(-not(Test-Path $manifest)){throw 'OLD_HANDOFF_MANIFEST_MISSING'};$sha=(Get-FileHash $manifest -Algorithm SHA256).Hash.ToLowerInvariant();if($sha -ne ([string]$obj.manifest_sha256).ToLowerInvariant()){throw 'OLD_HANDOFF_MANIFEST_MISMATCH'};$tmp=$current+'.rollback.tmp';Get-Content -Raw $oldPointer|Set-Content -Encoding UTF8 $tmp;if(Test-Path $current){$bak=$current+'.rollback.bak';Remove-Item -Force $bak -ErrorAction SilentlyContinue;[IO.File]::Replace($tmp,$current,$bak);Remove-Item -Force $bak -ErrorAction SilentlyContinue}else{Move-Item -Force $tmp $current}}
elseif(Test-Path $oldAbsent){Remove-Item -Force $current -ErrorAction SilentlyContinue}else{throw 'OLD_HANDOFF_POINTER_BACKUP_MISSING'}
Write-Output ("UNATTENDED_RECOVERY_ROLLED_BACK BACKUP=$PromotionBackup DAEMON_MEMORY_PRESERVED="+(Test-Path (Join-Path $DaemonProjectRoot 'daemon')))
