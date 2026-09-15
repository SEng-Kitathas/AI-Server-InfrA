param([Parameter(Mandatory=$true)][ValidateSet('Protect','Unprotect')][string]$Mode,[Parameter(Mandatory=$true)][string]$Path)
$ErrorActionPreference='Stop';Import-Module (Join-Path $PSScriptRoot 'RecoverySecret.psm1') -Force
if($Mode -eq 'Protect'){$s=[Console]::In.ReadToEnd();$n=Protect-PCMMADRecoverySecret -Secret $s -Path $Path;Write-Output ('PROTECTED bytes='+$n);exit 0}
[Console]::Out.Write((Unprotect-PCMMADRecoverySecret -Path $Path))
