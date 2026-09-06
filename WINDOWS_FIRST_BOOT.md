# Windows first boot — PCMMAD Receiver V29

This procedure performs machine-bound deployment verification. It does not alter surviving D:/E: project folders unless you explicitly configure those paths as writable mounts.

## 1. Extract beside older recovery folders

Use a stable path such as:

```text
C:\Users\<you>\Desktop\PCMMAD_receiver
```

Do not extract over the surviving recovery ZIP or your older receiver folder.

## 2. Open PowerShell in the extracted root

```powershell
Set-Location "$env:USERPROFILE\Desktop\PCMMAD_receiver"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

The execution-policy change applies only to the current PowerShell process.

## 3. Confirm the existing API key without displaying it

```powershell
$key = [Environment]::GetEnvironmentVariable("GITHOME_API_KEY", "User")
"GITHOME_API_KEY configured: $(-not [string]::IsNullOrWhiteSpace($key))"
```

The result must be `True`.

## 4. Configure storage deliberately

Inspect surviving drives and choose exact paths before setting variables:

```powershell
Get-PSDrive -PSProvider FileSystem | Select-Object Name, Root
Get-ChildItem D:\ -Directory -ErrorAction SilentlyContinue
Get-ChildItem E:\ -Directory -ErrorAction SilentlyContinue
```

Example only—replace every path with a real surviving location:

```powershell
[Environment]::SetEnvironmentVariable("PCMMAD_ROOT", "D:\PCMMAD", "User")
[Environment]::SetEnvironmentVariable("PCMMAD_PROJECTS_ROOT", "D:\Projects", "User")
[Environment]::SetEnvironmentVariable("PCMMAD_SYSTEM_ROOT", "D:\PCMMAD\system", "User")
[Environment]::SetEnvironmentVariable("PCMMAD_SANDBOX_ROOT", "D:\PCMMAD\sandbox", "User")
[Environment]::SetEnvironmentVariable("PCMMAD_TEMP_ROOT", "D:\PCMMAD\temp", "User")
[Environment]::SetEnvironmentVariable("PCMMAD_PROTOCOL_POLICY_MODE", "advisory", "User")
```

When multiple roots are needed, set `PCMMAD_MOUNTS_JSON` as compact JSON. Do not copy the example until its paths match reality.

## 5. Build the Python 3.12 environment

```powershell
.\PCMMAD.ps1 -Action Setup
```

This creates `baseline\pcmmad_receiver\.venv`, installs `requirements.txt`, verifies Flask/Requests/BeautifulSoup imports, and checks whether ngrok is on PATH.

## 6. Run the complete local verification contract

```powershell
.\PCMMAD.ps1 -Action Verify
```

Promotion requires the aggregate result:

```text
PCMMAD verification contract: CLEAN
```

## 7. Start locally before exposing a tunnel

```powershell
.\PCMMAD.ps1 -Action Start -NoNgrok
.\PCMMAD.ps1 -Action Status
```

Do not continue until local health is clean.

## 8. Verify surviving mounts

Use the authenticated `/lab/mounts` response or the Custom GPT only after confirming every returned path points to the intended D:/E: location. Treat unexpected roots as a deployment blocker.

## 9. Start ngrok and generate the active schema

```powershell
.\PCMMAD.ps1 -Action Restart
```

The launcher waits for local health, starts ngrok, reads the current HTTPS URL from ngrok's local API, and writes:

```text
baseline\pcmmad_receiver\pcmmad_lab_action_schema_ACTIVE.json
```

## 10. Configure the Custom GPT

Import only the generated `pcmmad_lab_action_schema_ACTIVE.json`.

Authentication:

- Type: API key
- Header: `X-GitHome-Key`
- Value: the same secret stored as the User-level `GITHOME_API_KEY`

Historical schemas under `reports\lineage\schemas` are evidence only and must not be imported.

## 11. Adopt the protocol plane safely

Leave `PCMMAD_PROTOCOL_POLICY_MODE=advisory` while existing projects establish explicit protocol state and valid mode transitions. Move to `strict` only after the relevant project workflows pass in advisory mode.

## Remaining machine-promotion gates

- PowerShell execution on the target Windows installation
- actual D:/E: mount parity
- ngrok tunnel health
- real Custom GPT authenticated callback

The sandbox release does not claim these host-bound gates are complete.
