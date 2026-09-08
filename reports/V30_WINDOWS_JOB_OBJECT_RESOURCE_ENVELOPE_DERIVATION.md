# V30 WINDOWS JOB OBJECT RESOURCE ENVELOPE DERIVATION

Date: 2026-09-07
Status: QUALIFIED ENGINEERING CANDIDATE / PUBLICATION PENDING
Live promotion: NOT PART OF THIS CAMPAIGN

## Quarry

Cross-domain raid R7 identified that the Windows process-ownership primitive already used a named Job Object and `KILL_ON_JOB_CLOSE`, while the same native structure exposed process/memory limits that the Runtime did not model or enforce.

The execution scheduler already owned durable Job lifecycle, worker ownership handshake, restart-safe named-Job-Object anchoring, termination, and idempotency. The missing component was a Runtime-owned resource budget attached to that canonical Job.

## Derived laws

- `RESOURCE_LIMIT_DECLARATION != RESOURCE_ENFORCEMENT`.
- `RESOURCE_ENVELOPE_CURRENTNESS_REQUIRES_KERNEL_READBACK`.
- `IDEMPOTENCY_KEY_BINDS_RESOURCE_BUDGET`.
- `JOB_OBJECT_RESOURCE_LIMITS_INCLUDE_PCMMAD_CONTROL_MEMBERS`.
- `KILL_ON_JOB_CLOSE_IS_ONE_LIMIT_FLAG_NOT_THE_WHOLE_LIMIT_STRUCTURE`.
- `TRANSPORT_RESOURCE_FIELDS != RESOURCE_POLICY_AUTHORITY`; the Runtime normalizes, persists, applies, and reads back the budget.

## Embodiment

### Windows primitive

`windows_job_object.py` now supports an OS-native resource envelope:

- per-process memory limit;
- aggregate Job memory limit;
- active Job-member process limit;
- CPU hard-cap percentage;
- kill-on-close containment preserved.

`configure_resource_envelope()` applies native limits and immediately calls `query_resource_envelope()` so durable execution state records what the kernel reports, not merely what the caller requested.

`set_kill_on_close()` now preserves already-applied memory/process flags instead of replacing the full ExtendedLimitInformation structure with a zeroed one.

### Durable execution component

Each `ExecutionJobRecord` now carries:

- `resource_budget`: normalized caller request;
- `applied_resource_envelope`: kernel readback;
- existing `resource_gate`, promoted to `pass` only after successful native application/readback and to `fail` on application failure.

The budget is applied before the worker request is released into user execution. The worker request carries the requested/applied component for exact recovery traceability.

### Idempotency/currentness

`resource_budget` is part of `submission_fingerprint`. Reusing an idempotency key with a different budget therefore conflicts instead of replaying a job under silently changed resource policy.

### Adapter projection

The compact 30-operation OpenAPI 3.0.3 schema remains 30 operations and adds only parity fields:

- `ExecutionResourceBudget` on `ExecutionSubmitRequest.resource_budget`;
- `ExecutionResourceBudget` and `ExecutionResourceEnvelope` on `ExecutionJob` readback.

This is adapter parity, not the final schema redesign.

## Exact resource semantics

The Windows Job Object contains the PCMMAD worker/control members plus the user process tree. `active_process_limit` therefore counts all Job members, not only user descendants. Async validation requires a minimum of 3 so the current control/worker/user composition has room to start.

Resource budgets remain optional for legacy callers. A non-empty resource budget fails closed on a Runtime without Windows Job Object support.

## Direct hostile evidence

`tests/test_execution_resource_envelope.py` proves:

1. kernel round-trip for 256 MiB per-process memory, 512 MiB aggregate Job memory, 8 active members, and 50% CPU hard cap;
2. active-process limit behavior: a Job capped at one active member blocks an assigned parent from creating a descendant;
3. toggling kill-on-close does not erase the other resource limits;
4. budget validation and idempotency fingerprint sensitivity;
5. canonical scheduler applies and persists kernel readback before user execution, and a fresh named Job Object reopen reports the same envelope;
6. execution capabilities and compact action schema expose the exact Runtime fields without increasing operation count.

Existing idempotency spawn-order tests were updated to model the new resource-envelope call while preserving the original write-before-launch invariant.

## Qualification

- Resource/Job Object/ownership focused cluster: PASS.
- Compact schema/resource parity cluster: PASS.
- Full suite: **376 collected / 375 passed / 0 failed / 1 skipped**.
- Changed/new Python compile: PASS.
- CRLF-aware `git diff --check`: PASS.

## Claim ceiling

Direct behavioral enforcement is proven for active-process count. Memory and CPU controls are proven as successful Windows Job Object configuration plus kernel readback; this campaign does not claim long-duration memory-pressure or CPU-throttling soak behavior.

No live Runtime promotion is included. The live Runtime remains on the previously promoted engineering feature until the remaining server campaigns converge.

## Next

After engineering publication, continue the remaining cross-domain raids. OBE/Skills may dogfood the live promoted Runtime independently. Final schema redesign remains LAST and untriggered pending whole-runtime convergence plus explicit user `hells yeah, ready`.
