# V30 Async 12-Worker Capacity + Orphaned SUBMITTED Recovery — 2026-09-09

Status: **ENGINEERING QUALIFIED / LIVE PROCESS NOT RESTARTED**

## Trigger
Operator reported repeated async failures and, for the first time, a concrete reason surface: the full grounded-language campaign had two orphaned `SUBMITTED` records that never acquired workers, so the work was bypassed through synchronous execution. Operator also stated a practical requirement of at least 10 simultaneous jobs.

The referenced external production seal prefix `5e2b55f4...` is not present in this local repository and is therefore treated as external evidence, not locally verified Git identity.

## Verified local Runtime diagnosis

Current server control-surface capacity readback before this patch:
- `global_limit = 8`
- `project_limit = unbounded`
- global/project queue limits = unbounded (`0` on wire represents `None`)

Source default before patch:
- `PCMMAD_EXECUTION_GLOBAL_CONCURRENCY` fallback = 8

Host headroom at diagnosis:
- 16 physical cores / 32 logical CPUs
- ~31.2 GiB total RAM
- ~18.2 GiB available RAM

### Capacity finding
The existing default of 8 is below the operator's >=10 simultaneous-job requirement. A default of 12 was selected to provide the requested 10-job floor plus two slots of concurrency slack without jumping to host-wide oversubscription.

### Orphaned SUBMITTED finding
`SUBMITTED` is a durable reservation state written before spawn/queue consequence. It does **not** consume running capacity: running census counts live `RUNNING` jobs, and queue census counts only `QUEUED` jobs.

However, the scheduler reconciliation path ignored bare `SUBMITTED` records. A process interruption after durable reservation but before `_spawn_or_queue_job()` therefore left a permanent orphan unless an idempotent client retried the identical submission.

The spawn ordering makes scheduler recovery safe:
1. bare `SUBMITTED` reservation exists before consequence;
2. `_write_worker_request()` assigns durable worker token/request;
3. job is persisted as `STARTING` with stage `worker_request_durable`;
4. only then is the worker process launched.

Therefore a durable record still at `SUBMITTED` with no worker token cannot represent a legitimately launched worker under the normal consequence ordering.

## Engineering changes

### 1. Default async global worker limit 8 -> 12
`runtime_config.py`:
- `ExecutionRuntimeConfig.global_concurrency` default = 12
- environment fallback for `PCMMAD_EXECUTION_GLOBAL_CONCURRENCY` = 12
- explicit environment override remains supported, including unbounded semantics where already allowed

Per-project concurrency remains unbounded unless explicitly configured.

### 2. Scheduler recovery for bare SUBMITTED reservations
`_reconcile_job_locked()` now recognizes:
- `status == SUBMITTED`
- no `worker_token`

and performs the already-existing spawn-or-queue transition without requiring client retry.

Outcomes:
- capacity available -> `STARTING/RUNNING`
- capacity unavailable + queue available -> `QUEUED`
- queue full -> durable `SUBMITTED` reservation remains retryable on later scheduler passes
- real spawn failure -> existing spawn path persists terminal failure; scheduler records failure/reconciliation telemetry

No duplicate scheduler or second execution truth plane was introduced.

## Qualification

### Focused tests
Runtime config + idempotency response-loss + scheduler poison isolation + admission hotpath:
- **28/28 PASS**

New regressions include:
- default global concurrency is 12
- project concurrency remains unbounded by default
- scheduler recovers an orphaned bare `SUBMITTED` reservation without client retry
- queue-full case leaves the durable reservation retryable rather than losing it

### Real 12-worker isolated integration
Patched Runtime imported in an isolated execution root and submitted 12 six-second jobs rapidly.

Observed:
- configured global limit: **12**
- jobs submitted: **12**
- maximum simultaneous running: **12**
- maximum queued: **0**
- final status: **12/12 COMPLETED**

### Real orphan-reservation recovery integration
A job was manually persisted in the exact pre-consequence state:
- initial status: `SUBMITTED`
- `worker_token = None`

No client retry was issued. Scheduler wake/reconciliation produced:
`SUBMITTED -> STARTING -> RUNNING -> COMPLETED`

Final supervision state: `worker_receipt_complete`.

Integration result file generated locally:
`.pcmmad_concurrency12_integration_result.json`

### Full Runtime
- collected: **446**
- passed: **445**
- failed: **0**
- conditional skip: **1**

## Claim ceiling / operational boundary

This patch proves the source Runtime can admit and execute 12 simultaneous jobs and can autonomously recover the observed orphaned-reservation class.

The **currently running server process still reports global limit 8** because the process has not been restarted/reloaded after the source change. This report does not claim live embodiment.

Live restart/promotion remains a separate operator-controlled boundary.
