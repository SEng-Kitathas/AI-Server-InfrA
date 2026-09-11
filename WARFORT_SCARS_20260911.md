# WARFORT SCARS — 2026-09-11

Preserved before sacrificial cleanup. These are historical scars, not current authority.

## Sacrificial worktrees
```text
worktree C:/Users/ancal/Desktop/PCMMAD_LABORATORY_RUNTIME_V30_RC1/PCMMAD_receiver
HEAD ce54b4a28df14c4aa9b10a2ac3c9db08e4c1243e
branch refs/heads/main

worktree E:/new pc/AI_Pushes_Sandbox/projects/PCMMAD_RECEIVER_LAB/.warfort_live_20260911/source_current
HEAD 6c2ef7086c103f3062cb5964b629a07f992822b4
detached

worktree E:/new pc/AI_Pushes_Sandbox/projects/PCMMAD_RECEIVER_LAB/.warfort_live_20260911/source_main_d9b3
HEAD 6c2ef7086c103f3062cb5964b629a07f992822b4
detached

worktree E:/new pc/AI_Pushes_Sandbox/projects/PCMMAD_RECEIVER_LAB/.warfort_live_20260911/source_patch
HEAD 7e5b65c672069af64655aeafd0e3b459572ade64
detached

worktree E:/new pc/AI_Pushes_Sandbox/projects/PCMMAD_RECEIVER_LAB/.warfort_live_20260911/transfer_patch
HEAD ce54b4a28df14c4aa9b10a2ac3c9db08e4c1243e
detached

```

## One-shot / warfort scheduled tasks before cleanup
- PCMMAD_V30_ReloadOnce — state=Ready, last_result=0, next=2026-09-11T23:59:00.0000000-04:00
- PCMMAD_V30_ReloadTransferFixOnce — state=Ready, last_result=0, next=2026-09-11T23:59:00.0000000-04:00
- PCMMAD_V30_Reload_6c2ef70 — state=Ready, last_result=0, next=2026-09-11T23:59:00.0000000-04:00
- PCMMAD_Warfort_Promote_6c2ef70 — state=Ready, last_result=1, next=
- PCMMAD_Warfort_RestartMidJob — state=Ready, last_result=3221225786, next=2026-09-11T23:59:00.0000000-04:00
- PCMMAD_Warfort_RestartMidJob2 — state=Ready, last_result=0, next=2026-09-11T23:59:00.0000000-04:00

## Known failure scars
- PCMMAD_Warfort_Promote_6c2ef70 last result = 1.
- PCMMAD_Warfort_RestartMidJob last result = 3221225786.
- Receiver restart during live control traffic severed its own ngrok/tool readback with ERR_NGROK_3004; recovery required post-restart reconstruction.
- HUD watchdog had died while orphan HUD child processes survived; current-source watchdog replacement was subsequently live-verified.
- Browser bridge is intentionally optional and was not supervised/running during this checkpoint; HUD now distinguishes unavailable from zero sessions.
- Result-handle identity target remains sha256 3c3794917ce8abbd29ecf04eb8b311ed4bb1b66037dde87f213fd22e20384cc4, 29237 bytes; original handle still pending exact recovery.
