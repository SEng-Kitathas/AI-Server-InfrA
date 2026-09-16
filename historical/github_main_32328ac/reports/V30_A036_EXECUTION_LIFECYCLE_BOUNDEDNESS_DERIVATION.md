# V30 A-036 — Execution Lifecycle Boundedness Re-Derivation

Date: 2026-09-06
Status: **DERIVED / NO EXECUTION-CODE MUTATION EARNED / ONE DEFECT HANDED FORWARD**

## Why A-036 was re-derived
A-033 removed repeated capacity rescans under the admission lock. A-035 partitioned execution metadata into active/terminal stores so scheduler/capacity hot scans no longer scale with terminal lifetime history. Therefore the earlier teardown's retention/drain assumptions could not be inherited unchanged.

A-036 re-tested three separate questions against current post-A-035 reality:
1. Is terminal retention still required for scheduler health/performance?
2. Is `EXECUTION_DRAIN_BATCH=None` materially unbounded under current admission semantics?
3. Does `/execution/list(limit=N)` perform bounded work or merely return a bounded response?

## 1. Terminal retention
Current A-035 hot paths operate on active metadata. Terminal history is excluded from scheduler/capacity scans.

Disposition: **DEFER retention as a performance fix.**

Deleting/compressing terminal history may later be justified by:
- storage pressure;
- privacy/data-lifecycle policy;
- explicit operator retention requirements.

It is no longer justified merely to keep scheduler hot paths healthy. Deletion would trade lineage for no demonstrated scheduler performance gain.

`RETENTION_POLICY != HOT_PATH_PERFORMANCE_FIX_AFTER_PARTITION`.

## 2. Drain boundedness
Current defaults:
- global concurrency: 8;
- per-project concurrency: unlimited unless configured;
- drain batch: unlimited (`None`).

Synthetic candidate pressure with no filesystem I/O:

| queued candidates | running global | starts | job reads | drain-loop ms |
|---:|---:|---:|---:|---:|
| 100 | 0 | 8 | 8 | 0.159 |
| 1,000 | 0 | 8 | 8 | 0.115 |
| 10,000 | 0 | 8 | 8 | 0.116 |
| 100 | 8 | 0 | 0 | 0.009 |
| 1,000 | 8 | 0 | 0 | 0.007 |
| 10,000 | 8 | 0 | 0 | 0.009 |

Under the actual finite default global concurrency, start work is already bounded by available capacity independent of candidate count. `drain_batch=None` does not create unbounded starts in the default configuration.

Per-project-limit discriminator: with project limit 1, project p1 already full, and one p2 job after N p1 candidates:

| skipped p1 candidates | starts | job reads | traversal ms |
|---:|---:|---:|---:|
| 100 | 1 | 1 | 0.034 |
| 1,000 | 1 | 1 | 0.098 |
| 10,000 | 1 | 1 | 0.776 |

The loop may traverse a large in-memory candidate list to find a runnable project, but it does not read each full project's job record. Current measured cost is not enough to justify a bespoke fairness/index patch before the informer/cache raid.

Disposition: **NO A-036 DRAIN CODE CHANGE.**

Explicit unlimited global concurrency remains an operator choice and is not silently reinterpreted as finite.

## 3. `/execution/list(limit=N)` boundedness
Current implementation:
```text
job_files = sorted(_iter_all_job_files(...), key=path.stat().st_mtime, reverse=True)
for path in job_files[:limit]: ...
```

So `limit` bounds loaded/returned records but not history enumeration/stat/sort.

Instrumented `limit=20`:

| history candidates | `stat()` calls | loaded records |
|---:|---:|---:|
| 100 | 100 | 20 |
| 1,000 | 1,000 | 20 |
| 10,000 | 10,000 | 20 |

Disposition: **REAL DEFECT / HAND FORWARD TO INCREMENTAL-DERIVED-STATE RAID.**

This violates the existing project law:
`BOUNDED_RESPONSE_SHALL_IMPLY_BOUNDED_EXECUTION_OR_MATERIALIZATION`.

A one-off `heapq.nlargest(limit, ...)` would reduce memory but still scan/stat O(history), so it would not solve the actual cost model. The right family of solution is maintained/indexed recent state or a cache with recovery rebuild, aligning with the newly promoted `DERIVED_STATE_IS_A_FOLD_NOT_A_REBUILD` scar.

## Cross-domain raid impact
The user-supplied `CROSS DOMAIN RAIDS.md` was read in full and preserved as a controlled-evidence receipt at:
`reports/hostile_inputs/CROSS_DOMAIN_RAIDS_2026-09-06_RECEIPT.md`.

Independent protocol-store reproduction confirms the same steady-state rebuild disease in a second subsystem. This is enough to promote the scar as an active audit lens while retaining full rebuild/verification as recovery backstop.

## A-036 conclusion
- retention: **DEFER / policy-only**;
- default drain boundedness: **NO DEFECT EARNED**;
- per-project skipped-candidate traversal: **OBSERVED / NOT MATERIAL ENOUGH YET**;
- all-history list bounded materialization: **DEFECT CONFIRMED / DEFER TO INCREMENTAL-STATE RAID**;
- no execution Runtime code change is justified in A-036.

## Next
A-037 shall begin the cross-domain raid campaign with current-V30 `protocol_store` incremental fold/checkpoint derivation because that defect has already been independently reproduced on the operator's Windows host.

Later raid candidates remain evidence-ranked rather than source-ranked:
- deterministic simulation/state-machine on-ramp;
- informer watch/cache + slow resync;
- Certificate Transparency-style Merkle receipts;
- lab/protocol idempotency;
- Windows Job Object resource limits;
- remaining supervision/lease/queue/schema/cursor/version-vector/peer-auth mechanisms.
