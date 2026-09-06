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
