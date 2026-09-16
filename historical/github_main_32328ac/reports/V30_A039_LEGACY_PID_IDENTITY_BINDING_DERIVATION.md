# V30 A-039 — Legacy Non-Worker PID Identity Binding

Date: 2026-09-06
Status: **TECHNICALLY EARNED / PENDING GIT PUBLICATION**

## Trigger
A-038 deterministic lifecycle simulation produced a replayable current witness: a legacy non-worker RUNNING record could survive PID reuse because legacy reconciliation treated `PID_ALIVE` as equivalent to `SAME_PROCESS`.

Worker-capsule ownership already carried `worker_creation_time_100ns`; the open seam was specifically historical/legacy non-worker RUNNING records with `job.pid` and no worker token.

## Baseline defect
Legacy paths used bare PID liveness in:
- effective running/capacity accounting;
- running census;
- readiness;
- finalization without a local ManagedProcess;
- scheduler reconciliation.

On Windows a recycled PID can therefore keep a stale job apparently alive indefinitely and consume execution capacity.

A-038 seed0 supplied a deterministic schedule-level witness. A-039 adds a smaller fixed PID-reuse probe for exact vulnerable/current comparison.

## Derivation
Identity law:

`PID_ALIVE != SAME_PROCESS`

Legacy non-worker identity state is classified as:
- `same_process`
- `dead`
- `creation_time_mismatch`
- `identity_unverifiable`.

Windows process creation time reuses the already-existing `windows_job_object.process_creation_time_100ns()` helper rather than inventing a second process-identity API.

`ExecutionJobRecord` now carries optional `pid_creation_time_100ns` for legacy identity witness compatibility.

### Authority vs capacity split
A focused A-033 regression exposed an important policy collision: treating an alive-but-unverifiable historical legacy record as absent from capacity can over-admit before scheduler reconciliation.

Therefore A-039 separates **identity authority** from **capacity safety**:

- `same_process` -> identity is accepted; record may remain RUNNING/unsupervised; consumes capacity;
- `creation_time_mismatch` -> not the same process; does not consume capacity; reconciles to supervision-lost terminal failure;
- `dead` -> does not consume capacity; reconciles terminal;
- `identity_unverifiable` -> SHALL NOT be promoted to SAME_PROCESS or TOFU-adopt the observed PID identity; however an alive PID consumes capacity conservatively until reconciliation explicitly resolves the record.

This preserves A-033's anti-overadmission guarantee while satisfying A-039's authority rule.

`UNVERIFIABLE_IDENTITY != SAME_PROCESS`

and

`IDENTITY_AUTHORITY != CONSERVATIVE_CAPACITY_ACCOUNTING`.

## Worker-capsule claim ceiling
Current production `_spawn_job()` always creates a worker token and uses worker-capsule/Job Object ownership. It records `worker_pid` and, on Windows, `worker_creation_time_100ns`; `job.pid` is deliberately cleared before returning.

A-039 therefore does **not** change current worker-capsule ownership semantics. `pid_creation_time_100ns` is a legacy/recovery field, not a replacement for worker identity.

Current-host migration census across persisted project execution records found:
- legacy non-worker `RUNNING + pid + no worker_token`: **0**.

So the current rollout does not demote any actually-running legacy process on this host.

## Embodiment
### `control_plane_models.py`
- added optional `pid_creation_time_100ns` to `ExecutionJobRecord` parsing/serialization.

### `execution_routes.py`
- added process creation-time wrapper around existing Windows helper;
- added `_legacy_process_identity_state()`;
- added conservative `_durable_running_consumes_capacity()`;
- effective running count/running census use identity-aware capacity accounting;
- readiness flags mismatched/unverifiable legacy identities;
- legacy finalization/reconciliation bind to identity state rather than bare PID liveness;
- supervision-loss failure digest carries:
  - `legacy_process_identity_state`
  - `expected_creation_time_100ns`
  - `observed_creation_time_100ns`.

Historical records/test doubles lacking the new witness field are treated as `identity_unverifiable`, not as parser errors.

### Deterministic simulator
`tools/hostile/execution_lifecycle_sim.py` now supports:
- `legacy_identity_variant=current`
- `legacy_identity_variant=pid_only` vulnerable specimen;
- virtual process creation-time queries;
- creation-time witness on simulated spawned legacy records;
- identity-aware concurrency invariant;
- clean-tick invariant that dead/recycled/unverifiable legacy RUNNING records cannot survive reconciliation;
- fixed `run_pid_reuse_probe()` for vulnerable/current comparison.

## Fixed deterministic discriminator
Same fixed schedule:
1. queue one legacy job;
2. scheduler starts it;
3. recycle its PID by changing simulated process generation;
4. run a clean scheduler tick.

Vulnerable `pid_only` result:
- target remains active `RUNNING`;
- target absent from terminal store;
- target present in `pid_alias_jobs`.

Current A-039 result:
- target absent from active store;
- target terminal `FAILED`;
- no alias remains.

Both vulnerable and current probes replay byte-identically across repeated runs.

## Randomized deterministic campaign
Current identity semantics:
- seeds: 0..99
- steps: 40 per seed
- result: **100/100 PASS**
- total PID recycle actions observed: **203**.

Some random schedules end immediately after a recycle and before another level-triggered tick:
- endpoint alias observations across campaign: 34.

This is not claimed as an A-039 failure. A-039 is level-triggered, not an instantaneous watcher.

After one explicit clean final scheduler tick across the same 100 seeds:
- aliases remaining: **0**.

Claim ceiling:
`PID_RECYCLE_EDGE != INSTANTANEOUS_RECONCILIATION`.

The later informer/watch raid may reduce detection latency, but correctness remains backed by the level-triggered scheduler.

## Hostile regressions
Added `tests/test_execution_legacy_pid_identity.py`.

It proves:
1. `pid_creation_time_100ns` record round-trip;
2. same/mismatch/dead/unverifiable classifier states;
3. recycled PID moves real durable active record to terminal FAILED with exact identity receipt;
4. missing historical witness fails safe without TOFU adoption;
5. capacity excludes mismatched identity but conservatively counts alive unverifiable history until reconciliation;
6. same-process legacy record stays RUNNING and becomes `unsupervised` rather than falsely failed;
7. readiness flags mismatch/unverifiable records but not same-process identity;
8. deterministic vulnerable/current fixed PID-reuse probe.

## Evaluator / derivation scars
A-039 qualification deliberately preserved several failures rather than weakening Runtime:

1. Existing A-033 mock records lacked `worker_token` and `pid_creation_time_100ns`. Migration-compatible identity helpers were hardened with `getattr(..., None)` instead of rewriting historical tests.
2. A-038 simulator originally counted any `RUNNING + PID alive` as owned capacity. Seed 8 demonstrated that a recycled foreign PID can remain textually RUNNING after an injected reconciliation fault while no longer being the owned process. The invariant was corrected to count identity-valid ownership, while alias state remains separately observable.
3. The first new readiness regression patched `_iter_all_job_files`; current readiness actually scans `_iter_job_files(None)`. The test harness was corrected; Runtime was unchanged.
4. A new test initially expected witness-less alive legacy records not to consume capacity. A-033 exposed the over-admission hazard; the model was corrected to separate identity authority from conservative capacity accounting.

## Verification
Focused A-039/execution/simulation cluster:
- **29 / 29 PASS**.

Complete V30 suite:
- **297 collected tests GREEN**;
- existing conditional Windows symlink-privilege skip only.

Current file identities:
- `baseline/pcmmad_receiver/control_plane_models.py`
  - SHA-256 `d70e890854965f73b4fbeaa61bd8a25b7a414ca386683fee10af0457083bd2ee`
- `baseline/pcmmad_receiver/execution_routes.py`
  - SHA-256 `1f19988d2d86ce1dedeef51578a46a6d6b17405e689b8285b09be2464d62c15b`
- `tools/hostile/execution_lifecycle_sim.py`
  - SHA-256 `d13b8288b1f734ed868198605c2e87ed315b308e0b3d9c834c2b9a7200d39834`
- `tests/test_execution_legacy_pid_identity.py`
  - SHA-256 `4346fa6c67dfbabe651fd17518cd6dcf8f441f2f27fa09c3298248e815a0106e`.

## Claim ceiling / next raid
A-039 closes the specific legacy PID-reuse identity seam in current V30 source scope.

It does not:
- make PID/process identity cryptographically strong;
- add executable/command/service/node fingerprints;
- change worker-capsule/Job Object authority;
- provide instantaneous process-exit/PID-reuse notification;
- implement informer/watch;
- implement Job Object memory/process-count limits;
- solve multi-receiver process-local admission ownership.

After A-039 Git publication, raid order resumes with informer/watch + slow resync unless a stronger correctness discriminator appears first.
