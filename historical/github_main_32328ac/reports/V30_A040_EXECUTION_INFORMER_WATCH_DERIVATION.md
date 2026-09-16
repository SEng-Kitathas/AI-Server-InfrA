# V30 A-040 — Execution Event Wake + Slow Level-Triggered Resync

Date: 2026-09-06
Status: **TECHNICALLY EARNED / PENDING GIT PUBLICATION**

## Trigger
The cross-domain Kubernetes-informer raid proposed preserving level-triggered reconciliation as correctness authority while moving steady-state change detection to an edge-triggered mechanism with periodic resync.

A-035 already partitioned execution metadata into `active/` and `terminal/`, but the scheduler still called `_scheduler_tick()` every 0.25 seconds regardless of whether any active work existed.

## Current-host baseline before A-040
Current project root contained:
- **59 execution-store roots**;
- **0 active job records** at measurement time.

Instrumented 100 idle scheduler ticks on post-A039 bytes:
- project execution-root traversals: **300**;
- `_iter_job_files` calls: **300**;
- active job loads: 0;
- total elapsed: **6791.506 ms**;
- mean tick: **67.915 ms**;
- configured cadence: 250 ms;
- idle duty attributable to scheduler tick work: **27.166%**.

The scheduler was doing substantial filesystem discovery work precisely when there was nothing to schedule.

## Donor pressure and rejection of naive implementation
A direct `ReadDirectoryChangesW + 60s resync` transplant would have weakened current Runtime behavior:
- scheduler reconciliation also handles stale worker heartbeat/process-loss recovery;
- worker heartbeat freshness grace is 3 seconds;
- a blind 60-second active resync would delay crash/liveness cleanup materially.

A second naive design was rejected because it would create a feedback oscillator:
- worker heartbeat is written every **0.20 seconds**;
- fresh-heartbeat reconciliation rewrites active job metadata;
- waking on every heartbeat or `active/*.json` rename would recreate 4–5 Hz scheduler work as event-driven work.

A-040 therefore uses a narrower edge contract.

## Native Windows watcher
Added:
`baseline/pcmmad_receiver/windows_directory_watch.py`.

Properties:
- dependency-free `ctypes` wrapper over `CreateFileW` + synchronous recursive `ReadDirectoryChangesW`;
- watches filename/directory-name changes only, not file-content writes;
- 64 KiB notification buffer;
- parses `FILE_NOTIFY_INFORMATION` into bounded `DirectoryChangeEvent` rows;
- zero-byte successful read is treated as overflow/unknown edge completeness;
- parse failures cause error + overflow/resync signal;
- `CancelIoEx` + handle close support clean shutdown;
- watcher owns no job/execution semantics.

Real Windows smoke test:
- atomic temp-file -> JSON replacement produced expected add/rename events;
- watcher stopped cleanly;
- 0 overflow;
- 0 errors.

## Event contract
A-040 deliberately does **not** wake on:
- `worker_heartbeat.json`;
- `active/*.json` metadata rewrites;
- unrelated project filename changes.

A-040 wakes on the one-shot durable edge:
- `*/system/logs/execution/<job_id>/worker_completion.json`.

Why this edge:
- worker completion/timeout/cancel/failure all materialize a completion receipt;
- completion frees capacity and is the highest-value prompt scheduler transition;
- submissions already run admission/drain synchronously and now also set the scheduler wake event explicitly;
- missing/stale worker heartbeat is a time-based negative signal and remains a resync responsibility.

Multiple completion events coalesce through one process-local `threading.Event`.

## Resync policy
New typed Runtime configuration:
- `PCMMAD_EXECUTION_SCHEDULER_ACTIVE_RESYNC_SECONDS`
  - default: **2.0 s**
  - minimum: 0.25 s
- `PCMMAD_EXECUTION_SCHEDULER_IDLE_RESYNC_SECONDS`
  - default: **60.0 s**
  - minimum: 1.0 s

Historical fallback:
- `PCMMAD_EXECUTION_SCHEDULER_INTERVAL_SECONDS`
  - current default: **0.25 s**.

Scheduler wait policy:
- healthy watcher + active records -> `watch_active`, 2-second periodic backstop;
- healthy watcher + no active records -> `watch_idle`, 60-second periodic backstop;
- watcher unavailable/failed -> `poll_fallback`, historical 250 ms cadence.

On any watcher overflow:
- edge completeness is treated as unknown;
- scheduler wake is forced;
- next scheduler tick performs authoritative full active-store reconciliation.

On watcher error:
- watcher accelerator is disabled for the process lifetime;
- bounded error telemetry is recorded;
- scheduler is immediately woken and falls back to historical polling.

## Authority model
A-040 does **not** create a watcher-owned execution cache or second state plane.

Authority remains:
- durable execution metadata;
- worker receipts;
- existing admission/reconciliation semantics.

The watcher supplies only a wake hint.

Laws:
`WATCHER_EVENT != AUTHORITATIVE_STATE`

`EDGE_ACCELERATION != LOSS_OF_LEVEL_TRIGGERED_RECOVERY`

`WATCHER_FAILURE -> POLL_FALLBACK`, not task failure.

## Integrated actual-host measurement
Using the same real 59 execution-root tree and no active jobs:
- watcher startup: PASS;
- observation window: 2.001 seconds;
- scheduler iterations: **1**;
- mode: `watch_idle`;
- watcher events accepted: 0;
- scheduler wakeups: 0;
- periodic resyncs during window: 0;
- watcher errors: 0;
- scheduler thread/watcher shut down cleanly.

The old 250 ms design would continue scanning ~4 times per second. The new healthy idle path reconciles once then waits for a completion/submission edge or the 60-second backstop.

Using the pre-A040 measured 67.915 ms reconciliation cost as a conservative reference, one 60-second idle resync corresponds to roughly **0.113%** duty instead of 27.166%, before accounting for lightweight watcher parsing of ignored filename edges. This is an extrapolated duty estimate, not a direct 60-second CPU measurement.

## Observable control surface
`SchedulerTelemetry` now reports:
- `watcher_started`
- `watcher_alive`
- `watcher_events`
- `watcher_overflows`
- `watcher_errors`
- `last_watcher_event_at`
- `last_watcher_error`
- `scheduler_wakeups`
- `periodic_resyncs`
- `last_resync_at`
- `last_active_records`
- `scheduler_wait_mode`.

Execution capabilities now separately report policy/support:
- scheduler historical fallback interval;
- active resync interval;
- idle resync interval;
- watcher supported;
- watcher active.

This keeps **capability/policy** distinct from **live telemetry/currentness**.

## Hostile regression
Added:
`tests/test_execution_informer_watch.py`.

It proves:
1. heartbeat and active-metadata paths are ignored;
2. completion paths are accepted;
3. multiple completion edges coalesce to one wake;
4. overflow forces wake/resync without claiming event completeness;
5. healthy watcher selects idle/active resync policy;
6. dead watcher selects historical polling fallback;
7. watcher error disables accelerator and wakes fallback;
8. capabilities expose policy while telemetry exposes live wait mode;
9. real Windows watcher observes atomic completion receipt and stops cleanly;
10. real scheduler thread remains at one idle tick across >250 ms, then wakes promptly on a completion receipt.

`test_runtime_config.py` also proves typed environment overrides and minimum clamping for resync intervals.

## Verification
Focused A-040 + adjacent execution/config cluster:
- **37 / 37 PASS**.

Complete V30 suite:
- **306 collected tests GREEN**;
- existing conditional Windows symlink-privilege skip only.

Current identities:
- `runtime_config.py`
  - SHA-256 `9c47876b409bfd6fc5fd9bc091ab8a40fbc6bad9bc9b2aa3834e6b792c592be8`
- `control_plane_models.py`
  - SHA-256 `d89caf8ba08618b6a82e383231b9d164999e57d68b15256d9f18590701727049`
- `execution_routes.py`
  - SHA-256 `20756e443265f1bff80bc6c8178f9dc7811856ecf6e1ec9c6080a5b2d77ece66`
- `windows_directory_watch.py`
  - SHA-256 `faad367cd9675be7138ab4a54084ccb3b3d0a5fc4bfe0d2a45f5680c57e7903b`
- A-040 regression
  - SHA-256 `90996775b0d8f3475ba9239efaf438ec2ff80ca6682287c942cb4a6c91a87ecd`
- runtime config regression
  - SHA-256 `0903fb206881ce054a687f889374e8054dd68cc71ad4b72962ff02dce0373434`.

## Claim ceiling
A-040 changes scheduler wake frequency and fallback behavior, not execution truth semantics.

It does not:
- maintain a Kubernetes-style indexed job cache;
- make each wake O(number-of-changed-jobs); each scheduler tick still performs authoritative active-store reconciliation;
- eliminate broad `PROJECTS_ROOT` filename notification traffic inside the Windows kernel watcher;
- guarantee zero notification overflow;
- replace level-triggered repair;
- replace worker timeout/heartbeat authority;
- solve multi-receiver admission ownership;
- implement CT/Merkle receipts;
- implement idempotency expansion;
- implement Job Object resource caps.

A future informer-cache refinement is justified only if active-change workloads show the remaining per-wake active scan is material. A-040 earns the high-value frequency reduction first without creating a new truth plane.
