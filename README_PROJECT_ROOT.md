
# PCMMAD Receiver project root

The canonical runtime is `baseline\pcmmad_receiver`. All supported Windows operations route through the project-local PowerShell command surface:

```powershell
.\PCMMAD.ps1 -Action Setup
.\PCMMAD.ps1 -Action Verify
.\PCMMAD.ps1 -Action Start -NoNgrok
.\PCMMAD.ps1 -Action Start
.\PCMMAD.ps1 -Action Status
.\PCMMAD.ps1 -Action BrowserStart
.\PCMMAD.ps1 -Action BrowserStop
.\PCMMAD.ps1 -Action Stop
```

Compatibility `.cmd` launchers remain, but they use the same canonical runtime and `.venv` interpreter.

## Project surfaces

- `baseline\pcmmad_receiver` — live server
- `tools\csc_native` — route, security, resilience, schema, package, and doctrine gates
- `system\constraint_pipeline` — claim/finalizer pipeline
- `tests` — regression contracts
- `docs` and `spec` — doctrine, invariants, setup, and promotion rules
- `reports` and `data\csc_v28` — mutable verification evidence

Do not run `server.py` with global PATH Python. Do not store credentials in this tree.
