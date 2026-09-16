# GLOBAL INTERACTION WAR CAMPAIGN — CLOSEOUT — 2026-09-15

## Scope
Parent campaign: fully embodied pre-live Receiver + Daemon + out-of-process HA + persistence/continuity/promotion system. Goal was to find local-optimum/global-interaction failures before live promotion. Inference/conversation and HUD redesign were intentionally deferred except where current HUD/security contracts were directly implicated.

## Campaign verdict
**CLONE GLOBAL-INTERACTION QUALIFICATION: PASS to live-promotion boundary.**
This is not live promotion. No Daemon root/SYSTEM topology/promotion package was installed into live by this campaign.

## Highest-value defects actually earned and fixed
- read-only Daemon status mutated disk; fixed read/persist separation.
- unchanged polling grew evidence/biography/timeline linearly; fixed transition-only evidence/biography and bounded event timeline.
- duplicate Daemon services could share a plane; added lifetime service lease.
- recovery/migration could race live Daemon state; fenced by service/plane ownership.
- existing plane could reopen under wrong daemon/project identity; fail closed.
- bootstrap/audit SQLite read-only opens created WAL/SHM sidecars; immutable reads after clean shutdown.
- Daemon health startup semantics could create restart storms; explicit starting/currentness contract.
- generic supervisor accepted missing/foreign Daemon schema/identity; bound schema + daemon_id + project_id + authority shape.
- duty read-only authority was descriptive only; native tool spec enforcement now blocks mutating/effectful tools.
- machine process filter self-contamination could 'prove' ngrok by command-line text; exact observation requirements added.
- Daemon depended on live Receiver Python/tool tree; recovery Python preferred and Receiver tool bridge degrades to UNKNOWN/reconnects.
- Daemon/task wrapper stop could strand child process; direct Daemon ownership plus cooperative Receiver/ngrok/supervisor child ownership proven.
- Task Scheduler workload auto-restart could bypass supervisor crash-loop budgets; workload/supervisor policies separated.
- supervisor restart budget disappeared across watchdog restart; durable failure state added.
- corrupt restart-budget state silently could reset safety; conservative bounded CORRUPT_HOLD.
- structured maintenance hold helper was not used by loop; loop now validates hold and rechecks immediately before trigger.
- ngrok lacked independent OOP supervision; exact public URL/upstream supervisor added.
- concurrent triple workload failure recovered independently once each without live movement.
- Daemon status/timeline disk failure could trigger pointless cognition restart; observability degradation separated from cognition health.
- partial evidence/biography commit before state materialization could duplicate life events on restart due tuple/list shape; canonical replay equality fixed.
- unresolved epistemic deficits disappeared from in-memory registry after restart; deficit rehydration added.
- wall-clock jumps could distort health freshness; monotonic health currentness.
- stale live-runtime handoff would omit Commander Intent; authoritative project-control immutable handoff generations + atomic pointer added.
- racing/older handoff publication could roll intent backward; serialized publish + monotonic source/currentness guards.
- copied Daemon roots could create same-identity split brain; production host-level identity lock.
- recovery installer overlaid program bytes and mixed mutable state; immutable-program transaction with manifest/rollback added.
- rollback during incomplete backup could delete still-authoritative old program; phase-aware rollback fixed.
- task registration failure could leave mixed task/program generation; task XML/absence rollback added.
- successful promotion lacked later rollback; archived promotion backup + explicit rollback command restores prior program/tasks/handoff pointer while preserving Daemon memory/evidence/secrets/budgets.
- Windows Defender Severe detection actually interfered with a PCMMAD soak harness; native Windows/Defender telemetry added and security evidence kept distinct from causation.
- continuity surfaces could be current but unused; intelligent relevance planner + handoff/rehydrate gate added, explicitly bounded by no-ritual doctrine.
- synchronous live `execution.run` whole-corpus testing correlated with Receiver loss; Windows child process groups were not isolated. CREATE_NEW_PROCESS_GROUP added.
- execution worker capsule launched through venv redirector and all restart-recovery scenarios generated KeyboardInterrupt even under OS task; worker capsule now uses base Python on Windows.
- kernel Job Object tests used venv redirector, causing false process-creation failure; kernel-level tests use base Python.

## Security/telemetry evidence
Defender 1116 record 2680 at 18:43:42 EDT detected Severe `Trojan:Win32/ClickFix.DAD!MTB` on the exact soak-harness PowerShell command; 1117 record 2681 at 18:43:55 recorded remediation; `Get-MpThreatDetection` reported ActionSuccess true. This is verified campaign interference, not established cause of later Receiver outages. No new matching Defender event was observed for the second outage window.

## Qualification receipts
- real Daemon independent recovery and maintenance-hold recovery: earned earlier in campaign.
- fake ngrok independent OOP recovery/hold: earned.
- correlated fake Receiver + fake ngrok + real Daemon simultaneous kill: all three independently recovered exactly once; live Receiver/ngrok unchanged.
- workhorse soak: 150 unchanged cognitive cycles, evidence remained 4, biography digest stable, 25 reopen/close cycles, 2,169 concurrent HTTP reads with zero reader errors, bounded event memory/timeline.
- promotion rollback synthetic v1 -> v2 -> rollback: prior program bytes, generated config, task XML/absence and handoff pointer restored; secret and Daemon memory sentinel preserved.
- execution resource envelope: 6/6 PASS under OS-owned task after base-interpreter correction; live unchanged.
- execution worker restart/recovery: 3/3 PASS under OS-owned task after worker-capsule base-interpreter correction; live unchanged.
- focused Receiver/Daemon supervisor identity + unattended supervisor + HUD continuation contract: 17/17 PASS.
- continuity + conditional telemetry + Windows telemetry + Daemon service: 16/16 PASS.
- program transaction / promotion static suite: 37/37 PASS before final global run.
- **final entire corpus:** rc 0, duration 63.0367s, Receiver PID 22968 -> 22968, 121 TCP liveness samples, 0 down samples, ngrok PID19772 stable.
- install and rollback PowerShell parse: 0 errors.
- Python compile of load-bearing new/modified modules: rc 0.
- all PCMMAD_HEAT temporary Scheduled Tasks removed; temp listener set empty at cleanup boundary.

## Remaining boundaries / reopen conditions
- Live promotion has NOT occurred. Promotion requires explicit safe-window review/readback and must use the qualified handoff source, rollback archive, host singleton, OOP HA topology and live identity checks.
- External ChatGPT approval bridge remains unproven where previously noted.
- Inference/conversation remains explicitly deferred.
- HUD cockpit/instrument-panel redesign is the next separate campaign; current visual dashboard is not accepted as cockpit-grade information architecture.
- Any change to Windows/Python/Task Scheduler/Defender behavior, execution-worker control semantics, supervisor topology, handoff generation schema or promotion transaction reopens relevant qualification.


## Final exact-tree confirmation
After the last continuity campaign-identity normalization change, the entire corpus was rerun under the OS-owned envelope against the exact tree intended for commit: rc0, 62.2664s, Receiver PID22968 start/end unchanged, ngrok PID19772 unchanged, 120 TCP liveness samples / 0 down. This supersedes the earlier 121-sample pass as the final commit-tree qualification receipt.


## Post-newline-hygiene byte-level confirmation
After restoring original CRLF conventions in 10 pre-existing files, the entire corpus was rerun under the OS-owned envelope: rc0, 60.8588s, Receiver PID22968 unchanged start/end, ngrok PID19772 unchanged, 117/117 TCP liveness samples up. No code semantics changed during newline hygiene.
