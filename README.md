# PCMMAD Receiver V29 — Native Protocol Release Candidate

PCMMAD Receiver is the authenticated local authority, persistence, execution, research, continuity, and verification plane for the PCMMAD lab protocol. The Custom GPT mediates; the receiver preserves machine truth.

## Preserved and expanded surface

- 49 Flask routes retained
- 75 V28 server-native tools retained
- 12 PCMMAD-native protocol tools added, for at least 87 total
- exactly 30 Custom GPT operations retained
- project, continuity, journal, checkpoint, research, execution, archive, filesystem, browser, Git, SOP, CSC, doctrine, semantic, session, approval, mount, and result-handle capabilities retained

The two-layer architecture remains intentional: stable first-class routes for durable contracts, and `/lab/tools` + `/lab/dispatch` + `/lab/batch` for capability growth without repeated GPT schema surgery.

## Native protocol plane

Each initialized project can maintain an append-only hash-chained protocol ledger containing typed mode, rigor, objective, constraint, continuity, claim, evidence, artifact, promotion, and waiver state. The derived snapshot is rebuildable and never outranks the ledger.

The mode gate is compatibility-aware:

- `PCMMAD_PROTOCOL_POLICY_MODE=off`
- `PCMMAD_PROTOCOL_POLICY_MODE=advisory` (default)
- `PCMMAD_PROTOCOL_POLICY_MODE=strict`

Existing projects remain usable until they initialize protocol state.

## One command surface on Windows

```powershell
.\PCMMAD.ps1 -Action Setup
.\PCMMAD.ps1 -Action Verify
.\PCMMAD.ps1 -Action Start
.\PCMMAD.ps1 -Action Status
.\PCMMAD.ps1 -Action BrowserStart
.\PCMMAD.ps1 -Action Stop
```

`GITHOME_API_KEY` is read from the User environment. Secrets are never stored in this package.

## Recovery installation

1. Extract the ZIP to a stable location, such as `C:\Users\<you>\Desktop\PCMMAD_receiver`.
2. Keep surviving D:/E: project data in place and mount it through environment variables.
3. Run `.\PCMMAD.ps1 -Action Setup`.
4. Run `.\PCMMAD.ps1 -Action Verify`.
5. Start locally with `.\PCMMAD.ps1 -Action Start -NoNgrok`.
6. Confirm local health, then start with ngrok enabled.
7. Import the generated `pcmmad_lab_action_schema_ACTIVE.json` into the Custom GPT.

Read `docs/pcmmad_doctrine/`, `docs/protocol/`, `docs/architecture/INVARIANTS.md`, and `docs/verification/RELEASE_CONTRACT.md` before machine promotion.
