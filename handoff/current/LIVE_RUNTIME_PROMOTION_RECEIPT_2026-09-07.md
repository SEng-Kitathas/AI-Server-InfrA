# LIVE RUNTIME PROMOTION RECEIPT — 2026-09-07

Status: **LIVE PROMOTION COMPLETE / REMOTE-RESTARTED / ASYNC VERIFIED / ROLLBACK AVAILABLE**

## Source authority
- Git/remote `main`: `4163606459324feaa31252b3c2a6d58d73aaff46`
- tree: `4b2836e1add4d218748e45b929189d2d72ed839b`
- subject: `Record completion journal inside worker fence`
- worktree: clean / `main...origin/main`
- current source suite: `370 collected / 369 passed / 0 failed / 1 conditional skip`

## Rollback surfaces
- Full pre-promotion live snapshot: `C:\Users\ancal\Desktop\PCMMAD_LIVE_ROLLBACKS\20260907_195134_pre_b8b6ca69`
- Full snapshot archive SHA-256: `0b4b59a8891899b402bee3aac36de553b432e4588098f7f4b90eadd4a81a01b2`
- Full snapshot manifest SHA-256: `d1ea91f68e74462b54e6f181ee1aea76354117c2d5fa01e9cb60105fc0385774`
- Restore script: `C:\Users\ancal\Desktop\PCMMAD_LIVE_ROLLBACKS\20260907_195134_pre_b8b6ca69\RESTORE_LIVE_CODE.ps1`
- Incremental rollback for `e34bf05` authority module retained under `pre_e34bf05_incremental`.
- Incremental rollback for final execution modules retained under `pre_4163606_incremental`; deploy receipt SHA-256 `9b0c6f4970c4106c57148943de62d8d1f0297fdfb95d4beb9e4bce80074db0c9`.

## Live deployment proof
- 70 curated Runtime files deployed; live-only assets and existing `.venv` preserved.
- Final 70-file parity check against current Git worktree: `0 mismatches`.
- Canonical receiver+ngrok restart executed through bound approval policy.
- Final restart request: `db9d766b17044cddbeb57474e76518ca`.
- Final restart receipt: `stage=ready`, `ok=true`.
- Receiver PIDs after final restart: `8792`, `15256`.
- ngrok PID after final restart: `41744`.
- Public URL restored: `https://touchy-deanna-unspeakingly.ngrok-free.dev`.

## Async proof
- Public compact action `submitProjectExecution` now works without an explicit fenced lease when no governed lease is active, using `compatibility_no_lease` worker binding.
- Active governed lease still requires explicit fenced authority; a lease appearing before worker consequence fails closed.
- Final live smoke job: `job-4fbdd90dd2f3`.
- Job completed `return_code=0` with expected stdout and empty stderr.
- Identical same-key resubmission returned the same job with `replayed=true`; no duplicate child consequence.
- Final terminal readback: `completion_journal_status=recorded`.
- Completion journaling is now performed by the worker inside its already-held project consequence fence before terminal receipt publication, eliminating the prior `PROJECT_MUTATION_GUARD_BUSY` race.

## Live health
- Runtime health: online.
- Server-native tool count: 107.
- Scheduler alive; watcher active.
- Aggregate `lab.health`: responsive and `degraded` only because optional browser bridge is unavailable (`BROWSER_BRIDGE_UNAVAILABLE` / local connection refused).
- Mount health was repaired before promotion: bounded, concurrent, subprocess-isolated, non-mutating probes; real nine-mount probe reduced from >20–35s hang to ~124ms in qualification and ~187–199ms aggregate health in installed sidecar verification.

## Claim ceiling / next frontier
- `LIVE_PROMOTION_COMPLETE != FINAL_SCHEMA_READY`.
- OBE/Skills 11-Skill interface remains unfrozen pending dogfood against the live promoted Runtime.
- Browser bridge degradation remains a residual, not a core execution failure.
- Commander ordering remains: Windows Job Object resource envelope -> remaining cross-domain raids -> whole-runtime convergence -> final schema redesign LAST, only after explicit user `hells yeah, ready`.
