Add-Type -AssemblyName System.Security
$script:Entropy=[Text.Encoding]::UTF8.GetBytes('PCMMAD_RECOVERY_SECRET_V1')
function Protect-PCMMADRecoverySecret([string]$Secret,[string]$Path){
 if([string]::IsNullOrEmpty($Secret)){throw 'SECRET_REQUIRED'}
 $plain=[Text.Encoding]::UTF8.GetBytes($Secret)
 try{$cipher=[Security.Cryptography.ProtectedData]::Protect($plain,$script:Entropy,[Security.Cryptography.DataProtectionScope]::LocalMachine)}finally{[Array]::Clear($plain,0,$plain.Length)}
 $dir=Split-Path -Parent $Path;New-Item -ItemType Directory -Force $dir|Out-Null;[IO.File]::WriteAllBytes($Path,$cipher)
 & icacls.exe $Path /inheritance:r /grant:r 'SYSTEM:(F)' 'Administrators:(F)' | Out-Null
 return $cipher.Length
}
function Unprotect-PCMMADRecoverySecret([string]$Path){
 $cipher=[IO.File]::ReadAllBytes($Path);$plain=[Security.Cryptography.ProtectedData]::Unprotect($cipher,$script:Entropy,[Security.Cryptography.DataProtectionScope]::LocalMachine)
 try{return [Text.Encoding]::UTF8.GetString($plain)}finally{[Array]::Clear($plain,0,$plain.Length)}
}
Export-ModuleMember -Function Protect-PCMMADRecoverySecret,Unprotect-PCMMADRecoverySecret
