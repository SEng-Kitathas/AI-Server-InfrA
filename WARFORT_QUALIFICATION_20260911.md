# WARFORT QUALIFICATION RECEIPT — 2026-09-11

## Candidate lineage
- Baseline HEAD before this candidate: `ce54b4a28df14c4aa9b10a2ac3c9db08e4c1243e`
- Branch: `main`
- Origin baseline: `origin/main` at `ce54b4a` before publish.

## Verified repairs
- Idempotency error projection: repaired and live verified before this continuation.
- Approval/lease consumption ordering: repaired and live verified before this continuation.
- Transfer safety failure projection: repaired and live verified before this continuation.
- Malformed v11 HTTP boundary: hostile green before this continuation.
- Standing authority / ALLOW_ALL: fresh high-danger `execution.run` executed with `approval_mode=standing_authority`, no manual challenge.
- Exact challenge HUD approval path remains functional for HITL mode.
- HUD current-source supervision: watchdog replacement live verified; final v5 replacement PID changed after deliberate kill.
- HUD live activity: now merges durable HUD journal with live receiver telemetry pulses.
- HUD session truth: browser bridge unavailable is no longer rendered as false `0` sessions.
- Browser bridge lifecycle: intentionally optional per `BROWSER_BRIDGE_README.md`; no forced always-on daemon added.
- Desktop FULL Liquid-Aero blur restored to 24px; lower tiers remain the performance fallback.

## Qualification
- Focused HUD/approval/standing-authority tests: `29/29 PASS`.
- Full pytest suite: `100%`, zero failures, two skips.
- Python compile: PASS.
- Node syntax: PASS.
- `git diff --check`: PASS.
- 12-way HUD/read pressure: 120/120 successful requests, 0 failures.
- Pressure latency: p50 ~2.813s, p95 ~7.253s, max ~7.669s. Fresh-status path remains a performance seam, not a correctness failure.
- Post-pressure drain: queued=0, running=0, unsupervised_jobs=0, corrupt_job_files=0.
- Scheduler/watcher: alive, watcher_errors=0, reconcile_errors=0, last errors null.
- Post-pressure RSS/thread/handle counts ended below pre-pressure snapshot.
- One-shot reload/warfort scheduled tasks removed.
- Sacrificial `.warfort_live_20260911` worktrees removed; only live `main` remains.

## Residual seam — NOT silently promoted
- Original persisted result identity target: 29,237 bytes, SHA-256 `3c3794917ce8abbd29ecf04eb8b311ed4bb1b66037dde87f213fd22e20384cc4`.
- Earlier boundary tests for forged/wrong-project/EOF/range limits were hostile green.
- Exact original result handle could not be recovered cleanly from persisted project search wrappers in this continuation, so the requested final byte-count/SHA reread of that exact object remains unverified.

## Scars
See `WARFORT_SCARS_20260911.md` for preserved failed harness, restart-coupling, watchdog, stale-worktree, and task evidence captured before cleanup.