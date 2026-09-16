# V30 Adaptive Mutation Guard and Async Admission — 2026-09-10

Status: **REBASED CURRENT-MAIN CANDIDATE QUALIFIED / GITHUB PUBLICATION PENDING**

Original base: `f38c564c486b03278ba9f10dbc87aa4b1c9c07d1`. Candidate rebased conflict-free onto current GitHub parent `e1b2b8eddd92e8ad9159a548f9e6d6b2beb895f4` (hosted clean-box repairs + project-aware access logging).

## Problem reproduced

The Runtime had a 12-worker async scheduler but arbitrary project execution carried a project mutation binding and the worker held the single project-wide consequence guard for the **entire subprocess lifetime**. Same-project contenders therefore waited on the same file lock and could fail after a fixed 5-second timeout as `PROJECT_MUTATION_GUARD_BUSY` even though the scheduler had free worker capacity.

Additionally, `execution.submit` itself was marked `project_mutation_fenced`, causing the request thread to acquire the long project consequence guard **before it could even enqueue** the durable job.

Observed historical jobs confirm compatibility/no-lease long-running executions were the practical blocker class.

## Laws

- `ASYNC_JOB != PROJECT_WIDE_EXCLUSION`
- `LEASE_LIFETIME != CONSEQUENCE_LOCK_LIFETIME`
- `LONG_COMPUTE != LONG_MUTATION_CRITICAL_SECTION`
- `SCHEDULER_CAPACITY != MUTATION_CONCURRENCY`
- `WAITED_FOR_LOCK != STILL_CURRENT_AUTHORITY`
- `CONSEQUENCE_HEARTBEAT != MUTATION_AUTHORITY`
- `UNKNOWN_EFFECT_EXECUTION_REMAINS_PROJECT_EXCLUSIVE`

## 1. Adaptive consequence-holder coordination

The OS cross-process file lock remains the **authoritative exclusion primitive**.

While the project consequence guard is held, Runtime now publishes a bounded non-authoritative sidecar containing:
- project id;
- opaque holder token;
- holder PID/thread id;
- acquire timestamp;
- heartbeat timestamp/sequence;
- `authority_effect = NONE`;
- law `CONSEQUENCE_HEARTBEAT != MUTATION_AUTHORITY`.

The heartbeat is refreshed only while the guard is actually held and is removed on release. Idle projects therefore have no heartbeat thread or periodic write.

Waiters acquire in short slices with exponential bounded backoff. A **fresh** holder heartbeat may extend a short base wait up to a bounded healthy-holder ceiling instead of returning an immediate false `PROJECT_MUTATION_GUARD_BUSY`. Stale/missing holder metadata never extends the wait.

Default/configurable timing:
- heartbeat interval: 0.50s (`PCMMAD_PROJECT_MUTATION_HEARTBEAT_SECONDS`);
- freshness window: 2.50s (`PCMMAD_PROJECT_MUTATION_HEARTBEAT_FRESH_SECONDS`);
- healthy wait ceiling: 30s, configurable up to 900s (`PCMMAD_PROJECT_MUTATION_HEALTHY_WAIT_MAX_SECONDS`);
- acquire slice: 0.20s (`PCMMAD_PROJECT_MUTATION_ACQUIRE_SLICE_SECONDS`).

`project.mutation.inspect` remains observational/non-reconciling and now reports the consequence-holder snapshot so HUD/clients can distinguish healthy occupancy from stale contention.

## 2. Scheduler-level project-exclusive admission

Durable execution records with a project mutation binding are explicitly marked:
- `execution_project_exclusive = true`;
- `execution_exclusivity_reason = project_mutation_binding`.

Backward compatibility treats older durable jobs carrying a mutation binding as exclusive even if the explicit flag is absent.

The scheduler derives project-exclusive occupancy during the **same durable running census** already used for capacity accounting. No extra active-tree scan is added to queue drain.

Admission rules:
- if no exclusive execution is running for project P, the next exclusive job for P may start;
- while an exclusive job for P is live, another exclusive P job remains durably queued;
- an exclusive job for unrelated project Q may still start if global/project capacity allows;
- queue stage is `queued_project_exclusive` with `queue_reason = project_exclusive_execution`, rather than spawning a worker that races/fails on the project guard.

Thus same-project unknown-effect arbitrary code remains conservatively serialized, but it no longer wastes worker slots or fails transiently at the guard boundary.

## 3. Submission authority split

`execution.submit` no longer uses the generic long `project_mutation_fenced` dispatch behavior.

Instead `submission_mutation_binding(...)`:
1. validates current governed authority under the **short lease-state guard** (or confirms compatibility/no-active-lease mode);
2. derives the same non-secret durable worker binding used historically: project/generation/owner/session only;
3. never persists the bearer `lease_id`;
4. never enters the project-wide consequence guard;
5. enqueues the durable job;
6. requires the worker to revalidate the binding again before the real arbitrary-code consequence.

This is used by both native `execution.submit` and direct `/project/execution/submit`.

Synchronous `execution.run` and `python.run` remain conservatively project-consequence fenced because they execute arbitrary code inline rather than through the durable scheduler.

## 4. Authority restraint

Automatic governed-lease renewal was **not** added. Durable worker bindings intentionally exclude the bearer lease token, and converting that non-secret binding into renewable authority would violate the authority model.

The adaptive heartbeat refreshes **coordination/current occupancy evidence**, not mutation authority.

If future product requirements need server-owned lease renewal, that must be an explicit delegated authority contract rather than an emergent side effect of scheduler liveness.

## 5. Schema/effect-profile consequence

Changing `execution.submit` from `project_mutation_fenced` to `mutation_authority_validated_before_enqueue` changes its capability contract digest. The v11 scheduler effect profile correctly failed closed as stale.

The profile was regenerated against the new 158-capability catalog. Scheduler authority remains conservative:
- effect-truth verified: **0**;
- parallel verified: **0**;
- resume-replay verified: **0**.

New profile digest: `c9aa7e5aa24f0abd54543d9bcb926b1184652704f93fa93d4582a72ecb59c28e`.
New catalog digest: `8696add7f622e1fc886de856d17ae75fe15bd560c7c903bed611a1b8dcae6fe5`.

## Detached qualification

Focused authority/admission/hot-path suite: **41/41 PASS**.

Combined schema/profile/package/guard focused gate: **PASS**.

Full serial source suite: **PASS** after one unrelated transient UCM cross-process test failure; that exact UCM test then passed twice in isolation and the complete serial suite passed on immediate rerun.

F821: **0**.
Compile-all: **PASS**.

## Claim ceiling

Earned:
- healthy long consequence occupancy is observable and adaptively waited;
- heartbeat goes dormant on release;
- stale holder metadata does not extend wait indefinitely;
- same-project bound async execution is serialized in the durable scheduler before worker spawn;
- cross-project execution remains independently admissible;
- enqueue validates authority without holding the long consequence guard;
- durable worker binding remains non-secret and is revalidated by the worker;
- scheduler-effect authority remains zero-witness conservative after catalog rebind.

Not yet earned at this stage:
- rebase/qualification on latest GitHub main;
- hosted Windows/Ubuntu CI;
- live Runtime promotion.

## Rebased combined qualification

Rebased feature commit parent: `e1b2b8eddd92e8ad9159a548f9e6d6b2beb895f4`.

Combined current-main candidate:
- F821: **0**;
- compile-all: **PASS**;
- focused access-log + mutation/admission + schema/profile/package + observability/transfer gate: **PASS**;
- serial: **1012 JUnit cases / 0 failures / 0 errors / 2 skips**;
- four-worker loadscope: **1012 / 0 / 0 / 2**;
- four-worker worksteal: **1012 / 0 / 0 / 2**.

The scheduler effect profile remains zero-witness conservative after rebind: no automatic parallel/effect/replay authority was earned by this feature.
