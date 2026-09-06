# V30 P0 Async Execution Hostile Audit

Status: ACTIVE / partially verified

## Governing decision
The canonical `execution_routes.py` scheduler/lifecycle is the authoritative async execution engine. The smaller `lab_tools_execution.py` direct-Popen lifecycle is a duplicate semantic surface and is demoted to an adapter. No competing async lifecycle is permitted.

## P0-001 — duplicate async lifecycle
### Probe
V29 exposed two materially different async paths:
- canonical `/project/execution/*`: durable queue, idempotency, reconciliation, scheduler, replay, artifact-registration state
- server-native `execution.submit/terminate`: direct `Popen`, in-memory ownership, bypassing canonical admission/recovery semantics

### Embodiment
- `lab_tools_execution.execution.submit` now delegates to canonical `submit_execution_job`
- `lab_tools_execution.execution.terminate` now delegates to canonical `terminate_execution_job`
- status/output/wait already read canonical job state and remain there
- regression forbids reintroduction of adapter-owned background process lifecycle

### Verification
- targeted async-unification tests: 3/3 PASS
- full preserved suite after patch: PASS

## P0-002 — cross-project global-lock contention
### Probe
`_ADMISSION_LOCK` was one global RLock covering readiness scans, all-project scheduler reconciliation, submit, finalize, queue drain, and terminate. Capacity helpers recursively scanned durable job JSON across all projects.

A hostile concurrency regression held an all-project reconciliation scan open while an unrelated project attempted admission. The V29-style implementation deterministically blocked the unrelated project.

This matches the operator's observed multi-project-tab symptom class: one project can make unrelated assistant/server actions feel serialized or hung even without CPU/GPU saturation or a formal deadlock.

### Embodiment
- readiness whole-tree scans moved outside the global admission critical section
- scheduler whole-tree discovery/file reads moved outside the critical section; lock is acquired per reconciled mutation
- queued-job candidate discovery moved outside the critical section
- critical section retained around check-and-mutate operations that can affect global capacity correctness

### Verification
- hostile cross-project isolation regression: FAIL before patch, PASS after patch
- async-unification + cross-project targeted guards: 4/4 PASS
- full preserved V30 suite after both patches: 44/44 PASS

## P0-003 — restart supervision gap (OPEN)
### Verified seam
Canonical jobs currently store PID + job state, while live process control is held in in-memory `_RUNNING: dict[job_id, Popen]`.
After receiver restart, a still-alive child PID can be detected and marked `unsupervised`, but the receiver no longer owns a poll/kill handle. Timeout and terminate semantics therefore cease to be fully enforceable while status may still say RUNNING.

### Intended repair direction
Preserve the big scheduler as control-plane authority. Introduce a durable per-job worker capsule/actuator that executes one already-admitted canonical job and writes heartbeat/completion/cancellation receipts. It SHALL NOT own admission, queueing, idempotency, replay, or promotion. The scheduler reconciles durable worker receipts so receiver restart does not destroy execution truth.

## Claim ceiling
P0-001 and the first layer of P0-002 are verified in the V30 lab copy only. They are not yet promoted to the live receiver. P0-003 remains open and must pass restart/cancel/timeout/race tests before promotion.

## P0-003 update — restart-safe ownership composition integrated in V30 working tree

Status: WORKING / integrated / not live-promoted

### Additional scars isolated
1. Worker startup stale cleanup erased a fresh scheduler cancel request. Cleanup ownership was moved back to scheduler pre-spawn only.
2. Windows atomic heartbeat replace could transiently fail while scheduler read the destination; this telemetry collision was incorrectly promoted to `WORKER_FAILED`. Atomic replace now uses bounded retry/backoff on `PermissionError` while preserving atomicity.
3. Venv launcher PID was not the actual long-lived worker PID. Observed process tree: venv `python.exe` launcher -> base Python worker. Both inherit Job Object membership. Runtime model now distinguishes `worker_launcher_pid` from actual heartbeat `worker_pid` and records worker creation time.
4. A named Job Object alone does NOT survive last-handle closure on this host. This falsified design is retained as a negative-contract regression.

### Integrated composition
- canonical `execution_routes.py` scheduler remains sole lifecycle authority
- durable one-job runner writes heartbeat/completion/cancel receipts
- one named Windows Job Object per canonical job provides process-tree containment
- scheduler creates Job Object + KILL_ON_JOB_CLOSE, spawns launcher, assigns launcher before any user child can start
- actual worker opens and holds the named Job Object as an ownership anchor
- runner reports `OWNERSHIP_READY`
- scheduler verifies actual worker PID is a member of the Job Object and records creation time
- scheduler writes a token/job-bound ownership-release receipt
- only then may worker spawn user command
- scheduler closes its creator handle after release; runner remains ownership anchor
- if receiver restarts, runner remains durable and Job Object remains reopenable while runner owns a handle
- if receiver is absent and runner dies, final Job Object handle closure kills surviving descendants

### Negative contracts now verified
- forced scheduler handshake failure cannot start user command
- wrong-token ownership release cannot start user command
- cancel-before-release produces TERMINATED receipt without user command start
- duplicate named Job Object creation is rejected rather than hijacking existing object
- last-handle closure makes unanchored named Job Object non-reopenable
- anchored Job Object survives receiver-side handle loss and can be reopened/queried/terminated
- runner death with receiver handle absent kills runner-created descendants

### Verification
- 20 repeated lost-Popen completion runs passed after atomic receipt fix
- 10 repeated restart-survival triples passed after Job Object integration
- restart-survival / ownership / Job Object hostile cluster: 10/10 PASS
- full V30 pytest suite: PASS after integration

### Exact current hashes
- execution_routes.py: `c38c595b21fc4fe158d85e24781d7804c8d685ca659e4d6b3c0e8e607042eb98`
- execution_worker.py: `d80cd344dbb21a6bde851c538845c6224e8dcf7cfe50f2beab54403ecfc90412`
- control_plane_models.py: `199d6febdeca6ce56ad12f8d37d9e243e31bfd552bddaf6e5d748b52c09daf8b`
- windows_job_object.py: `304be97a0e523a0aef85445a9bf3f1f2bb3bf2511ba7aa5a7ecd04f95f617e5c`

### Claim ceiling
This is a verified integrated V30 working-tree mechanism. It has NOT been promoted to the live receiver and has not yet completed full V30 release qualification, full-plane audit, malformed-state replay matrix, or clean-package install verification.


## A-033 — saturation-time admission read amplification under the global lock

Status: **FIXED / QUALIFIED IN V30 WORKING TREE / PENDING THIS STEP GIT PUBLICATION**

### External hostile evidence
A user-supplied execution teardown reported that `_drain_queue_locked()` called `_can_start_now()` per queued candidate; `_can_start_now()` called `_capacity_snapshot()`, and `_capacity_snapshot()` performed four full durable job-tree scans. With `EXECUTION_DRAIN_BATCH=None` and saturation using `continue`, one drain repeatedly re-read the lifetime job tree while starting nothing.

Exact external attachment identities and campaign split are preserved in:
`reports/hostile_inputs/EXECUTION_PLANE_TEARDOWN_2026-09-05_RECEIPT.md`.

### Current-V30 reproduction before mutation
Synthetic current-module store:
- 40 terminal history records
- 8 RUNNING records (global limit saturated)
- 12 QUEUED records

One `_drain_queue('p1')`:
- started: 0
- `_capacity_snapshot` calls: 12
- `_can_start_now` calls: 12
- job-tree walks: **49** = 1 candidate discovery + (4 × 12) capacity walks
- job-file loads: **2,940** = 49 × 60 records
- elapsed on operator Windows host: **0.554 s**, already > configured 0.25 s scheduler interval.

This reproduces the mechanism independently of the donor patch and proves O(queued × lifetime_jobs) read amplification on current V30.

### Derivation / embodiment
The supplied donor diff was not applied wholesale because it also contained poison-record isolation (a separate failure class reserved for A-034).

Current-V30 A-033 repair:
- added `_running_census()`;
- snapshots live `_RUNNING` managed process IDs under `_RUNNING_LOCK` so existing managed-process capacity semantics are preserved;
- performs one durable global job-tree pass;
- globally deduplicates job IDs while maintaining independent per-project seen sets/counts;
- durable RUNNING records not represented by a live managed process count only when `_pid_alive(job.pid)` succeeds;
- `_drain_queue_locked()` establishes global/per-project capacity once under `_ADMISSION_LOCK`;
- successful starts increment local global/project budgets;
- global capacity exhaustion uses `break` because no later candidate can be admitted in that pass;
- project capacity exhaustion still uses `continue` so other projects can make progress;
- `_capacity_snapshot()` / `_can_start_now()` remain intact for observational/other callers.

No queue/lifecycle/authority semantics were intentionally changed.

### Hostile regression
Added:
`tests/test_execution_admission_hotpath.py`

It proves:
1. same 60-record saturated drain performs exactly 2 tree walks / 120 loads and never calls `_can_start_now` or `_capacity_snapshot` per candidate;
2. saturation breaks before queued-record reads;
3. one remaining global slot starts exactly one job and local capacity prevents over-admission without re-census;
4. a full project is skipped while another project may still start;
5. live managed `_RUNNING` process semantics survive even if durable status is transiently stale.

### Post-fix reproduction
Same 60-record case:
- started: 0
- tree walks: **2**
- file loads: **120**
- `_can_start_now` calls: 0
- `_capacity_snapshot` calls: 0
- queued `_read_job` calls at global saturation: 0
- elapsed: **0.231 s**.

500 terminal + 8 RUNNING + 50 QUEUED Windows case with candidate discovery separated from lock:
- candidate discovery: **2.226 s** (outside `_ADMISSION_LOCK`)
- admission-lock hold: **0.049 s**
- jobs started: 0.

The remaining 2.226 s discovery cost is not claimed fixed. It is direct current-host evidence for A-035 active/terminal partitioning: lifetime history still dominates flat-tree scans even after admission serialization is repaired.

### Verification
- current execution focused cluster: **19/19 PASS**
- complete V30 suite: **264 collected tests GREEN**, existing conditional Windows symlink-privilege skip only.

Current identities:
- `execution_routes.py` SHA-256 `2cea76cd1b24291f1ef5d929fedbf02f6102b3bc0e2927cedc5db2a367d0a02e`
- A-033 test SHA-256 `fd2ed0b73c413d88dc8083797d623504da5bca435b7a0063c9d1d8b1ba56efb8`.

### Claim ceiling
A-033 fixes repeated capacity rescans under admission. It does **not** fix:
- one lifetime-tree candidate discovery scan;
- one lifetime-tree running census scan;
- scheduler whole-tree reconciliation;
- poison-record isolation;
- retention;
- process-global-only admission ownership;
- legacy bare-PID identity;
- WSGI serving model.

Those remain separately pressure-tested seams.


## A-034 — poison execution record can abort every scheduler tick before queue drain

Status: **FIXED / QUALIFIED IN V30 WORKING TREE / PENDING THIS STEP GIT PUBLICATION**

### Current-V30 reproduction before mutation
A real temp-store poison record was created with:
- status `RUNNING`;
- dead PID;
- empty `stdout_path` / `stderr_path`;
- three healthy `QUEUED` records behind it.

`_drain_queue` was replaced with a no-op sentinel to avoid launching user work during the hostile repro.

Five consecutive `_scheduler_tick()` calls on the operator Windows host:
- **5/5 aborted**;
- exception: `PermissionError: [Errno 13] Permission denied: '.'`;
- drain reached: **0/5**;
- poison durable status remained `RUNNING`;
- all healthy records remained `QUEUED`.

This independently reproduces the external Linux `IsADirectoryError` mechanism with the Windows-specific exception type.

### Root cause
Legacy non-worker RUNNING reconciliation followed:
`_scheduler_tick -> _reconcile_job_locked -> _mark_supervision_lost -> _job_failure_excerpt -> _tail_text(Path(""))`.

`Path("")` resolves to `.`. `_mark_supervision_lost` changed the in-memory job to FAILED but attempted arbitrary log reads **before** `_write_job`, so the exception prevented the terminal transition from becoming durable. The scheduler loop caught the outer exception and retried the same poison record next tick, suppressing `_drain_queue` indefinitely.

### Derivation / embodiment
A scheduler reconciliation transition must not depend on arbitrary operator-controlled output filesystem paths.

A-034 therefore makes two narrow changes:
1. `_mark_supervision_lost` persists a deterministic `SUPERVISION_LOST` failure digest without opening stdout/stderr. It carries empty excerpt fields plus `excerpt_capture="deferred_to_output_read"`. The existing bounded `/project/execution/output` path remains the explicit read surface for output windows/ranges.
2. `_scheduler_tick` isolates reconciliation exceptions per record, records bounded typed telemetry, continues reconciling later records, and **always reaches queue drain**.

Typed `SchedulerTelemetry` additions:
- `jobs_reconcile_errors`
- `last_tick_reconcile_errors`
- `last_reconcile_error`
- `last_reconcile_error_at`.

Readiness degrades when the **current tick** has reconcile errors. Historical `last_reconcile_error` remains visible for diagnosis without leaving readiness permanently degraded after later clean ticks.

No record is described as quarantined because A-034 does not move it to a separate store.

Backups:
- `baseline/pcmmad_receiver/_v30_backups/AUDIT_A034_POISON_ISOLATION/execution_routes.py`
- `baseline/pcmmad_receiver/_v30_backups/AUDIT_A034_POISON_ISOLATION/control_plane_models.py`.

### Hostile regression
Added:
`tests/test_execution_scheduler_poison_isolation.py`.

It proves:
1. a real empty-log-path poison record transitions to durable FAILED and does not suppress drain;
2. `_mark_supervision_lost` cannot invoke `_job_failure_excerpt`;
3. an arbitrary first-record reconciliation exception does not suppress a healthy second record or queue drain;
4. telemetry records cumulative + current-tick reconcile error state and bounded last error;
5. a later clean tick resets current error count while retaining historical diagnostics;
6. readiness degrades on current-tick reconcile errors and recovers when a later tick is clean.

### Hostile evaluator scar
The first focused run was 23/24 PASS. The failing integration fixture wrote `aaa_poison.json` containing `job_id="poison"`; Runtime correctly persisted the canonical terminal record to `poison.json`, while the test reread the stale alias filename and incorrectly concluded status remained RUNNING.

The fixture identity was corrected. Runtime code was not weakened.

### Post-fix exact poison repro
Five consecutive ticks:
- **5/5 completed cleanly**;
- drain reached **5/5**;
- poison durable status `FAILED`;
- stage `supervision_lost`;
- failure digest `excerpt_capture=deferred_to_output_read`;
- current-tick reconcile errors 0 for this now-valid transition.

Queued records remained QUEUED only because the hostile repro intentionally used a no-op drain sentinel; the invariant under test is that drain is reached.

### Verification
- current execution cluster: **24/24 PASS**;
- complete V30 suite: **269 collected tests GREEN**, existing conditional Windows symlink-privilege skip only.

Current identities:
- `execution_routes.py` SHA-256 `6c3dda46a004ca88f24839b6ad769c12e235b1f679ae0654c1ba9ae5c95c058c`
- `control_plane_models.py` SHA-256 `1ac32417682c6638728c1a9c5523f0781a81256c13cc55810a68b7af0ebded0e`
- A-034 test SHA-256 `ced3b110ad52c56b2f58ea611cd79230440d5e0d2fc7eeadd7945950ff144484`.

### Claim ceiling
A-034 fixes poison-record starvation and removes supervision-loss output reads from scheduler reconciliation. It does **not** fix:
- lifetime-tree scan cost;
- active/terminal durable layout;
- retention;
- drain batch default;
- legacy PID reuse;
- process-local multi-receiver admission ownership;
- public serving model.

A-035 active/terminal partition remains the next structural discriminator after A-034 Git publication.


## A-035 — flat lifetime execution history remained on the scheduler hot path

Status: **FIXED / QUALIFIED IN V30 WORKING TREE / GIT PUBLICATION PENDING**

A-033 removed repeated capacity rescans under `_ADMISSION_LOCK`, but Windows measurement still showed ~2.226 s queued-candidate discovery with 500 terminal history records. A-035 separated hot active metadata from terminal history.

Earned layout:
- `execution/active/<job>.json` for active lifecycle records;
- `execution/terminal/<job>.json` for terminal durable history;
- legacy flat `<job>.json` remains direct-read/migration fallback;
- `idempotency.json` remains at execution root;
- per-job stdout/stderr/worker-control directories remain unchanged.

Hot iterator now scans active only. All-history list merges active + terminal + remaining legacy. Direct identity resolves active -> terminal -> legacy.

Terminal transition persists the terminal payload at its current source then uses same-filesystem `os.replace(source, terminal_path)`. Startup repair handles a crash-stranded terminal-status record in active.

Legacy migration is explicit scheduler-start mutation, conflict-refusing, corruption-visible, and readiness is tracked per execution-store root so later-mounted projects can be normalized without rescanning ready histories.

Structural discriminator with constant 58 active jobs:
- 0 terminal: queued/running scans load 58 / 58 records;
- 500 terminal: 58 / 58;
- 5,000 terminal: 58 / 58.

Post-warm Windows timings were ~7–8 ms per hot scan independent of terminal history.

### Test-isolation hostile scar
Initial full-suite qualification inherited the operator's real `PCMMAD_PROJECTS_ROOT` and startup migration moved 1,158 real terminal records into test-created partition directories. A-035 was immediately blocked from promotion.

Recovery manifest SHA:
`fafb83d8674be0d37c5625d8dd1a863368b49a7bde20bce6e5bd4cf471e313a7`

Recovery result:
- 1,158 / 1,158 records restored to original flat paths;
- 94 / 94 test-created active/terminal directories removed;
- 0 conflicts;
- 0 source remnants;
- 0 target hash failures.

Suite-wide pre-import isolation was added in `tests/conftest.py`, assigning temporary PCMMAD project/system/sandbox/temp roots. Real ambient partition directories were verified **0 before -> 0 after** isolated focused + full suites.

Detailed qualification:
`reports/V30_A035_ACTIVE_TERMINAL_PARTITION.md`.

Verification:
- execution/partition cluster: **34/34 PASS**;
- complete isolated V30 suite: **279 collected tests GREEN**;
- existing conditional Windows symlink-privilege skip only.

Current identities:
- execution_routes.py `11d888186db1f365ca76aada5512f9fcef420c93c2ec0b0976e9dcfd8c8e2a40`
- A-035 test `28b3b667a7332690bb251d01f0a73e7344a434e3d41870dfdf82dc0980be01c7`
- A-034 currentness test `673b5b227584d5da3552f2b34249fbe9756ef3da2f36fce67b01c8736e67e272`
- pytest isolation `43d8b6b940b19a88932197f54d13fa2b677642eaa46ca28c20381cb342714ab7`.

Claim ceiling: no retention/deletion, no multi-receiver admission fix, no legacy PID fix, no WSGI serving change, no live V30 promotion.
