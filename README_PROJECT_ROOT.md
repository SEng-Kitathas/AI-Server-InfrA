# AI-Server-InfrA project root

The canonical Runtime source is `baseline\pcmmad_receiver`. This repository is the V30 engineering/evaluation surface; the older V29 release metadata identifies the last packaged release and must not be mistaken for current Git source capability.

External evaluators should begin with [`README.md`](README.md) and [`docs/EXTERNAL_EVALUATION.md`](docs/EXTERNAL_EVALUATION.md).

## Supported Windows command surface

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

Compatibility `.cmd` launchers remain, but they route to the same canonical Runtime and project virtual environment.

## Repository surfaces

- `baseline\pcmmad_receiver` — canonical Runtime source
- `tests` — regression, hostile, authority, boundedness, and integration contracts
- `operator_hud` — operator presentation/HUD projection
- `tools\csc_native` — route, security, resilience, schema, package, and doctrine gates
- `system\constraint_pipeline` — claim/finalizer constraint pipeline
- `docs` — architecture, doctrine, protocol, setup, and external evaluation guidance
- `reports` — engineering evidence, derivations, audits, and historical lineage
- `handoff\current` — Git-contained recovery mirror; not Runtime truth authority
- `design_donors` — donor/reference material; donor provenance does not grant authority

## Identity boundary

```text
Git main                 current V30 engineering source
VERSION / RELEASE.json   last packaged V29 release identity
running Desktop Runtime  separate deployment state; verify independently
```

Do not run `server.py` with global PATH Python. Do not store credentials in this tree.
