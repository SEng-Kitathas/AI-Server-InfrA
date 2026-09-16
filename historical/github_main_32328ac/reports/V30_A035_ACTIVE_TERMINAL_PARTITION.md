# V30 A-035 — Active / Terminal Execution-Store Partition

Status: **EARNED IN V30 WORKING TREE / GIT PUBLICATION PENDING**
Date: 2026-09-06

## Intended outcome

Make scheduler/admission hot scans scale with **active work**, not lifetime execution history, while preserving durable terminal history, direct status/output/replay/register access, restart recovery, legacy-flat compatibility, and byte-/identity-exact lineage.

Core law:

**HOT STATE AND HISTORICAL STATE MAY SHARE IDENTITY BUT NEED NOT SHARE ENUMERATION COST.**

A-035 does **not** introduce retention/deletion. Retention is deferred to A-036.

## Pre-A-035 evidence

After A-033 removed repeated capacity rescans under `_ADMISSION_LOCK`, the same Windows host still showed a 500-history / 50-queued candidate-discovery cost of ~2.226 s outside the lock. This isolated the structural problem from admission serialization: flat durable execution storage made hot scans proportional to lifetime job count.

## Access-surface census

Current execution-store access classified as:

- **HOT-ACTIVE enumeration** — scheduler reconciliation, queued-candidate discovery, running/queue capacity, readiness.
- **ALL-HISTORY enumeration** — `/execution/list`.
- **DIRECT-IDENTITY** — status, output, terminate/cancel, replay, registration-by-job, idempotency replay lookup.
- **LIFECYCLE MUTATION** — centralized `_write_job`.

This allowed the storage change to be expressed beneath stable identity APIs instead of spreading physical-path logic across callers.

## Earned storage contract

Per project:

```text
system/logs/execution/
  active/
    <job_id>.json
  terminal/
    <job_id>.json
  <job_id>.json          # legacy-flat compatibility only
  idempotency.json       # remains at root; never migrated
  <job_id>/              # stdout/stderr + worker-control payload directory unchanged
```

### Direct identity

`_read_job(project_id, job_id)` resolves:

1. `active/<job>.json`
2. `terminal/<job>.json`
3. legacy flat `<job>.json`

Ordinary direct reads do not perform migration.

### Hot enumeration

`_iter_job_files()` now enumerates **active records only**.

Therefore scheduler reconciliation, queued discovery, running census, queue counts, and readiness no longer enumerate terminal history after layout qualification.

### History enumeration

`_iter_all_job_files(project_id)` merges active + terminal + any still-unmigrated legacy record, excludes `idempotency.json`, and deduplicates by canonical filename.

`/execution/list` uses the history iterator so terminal records remain visible.

### Lifecycle writes

`_write_job` routes records by status using the existing `JOB_ACTIVE_STATUSES` / `JOB_TERMINAL_STATUSES` model.

For active -> terminal transition:

1. persist the terminal payload at the current active/legacy source path with `save_json_atomic`;
2. perform `os.replace(source, terminal_path)` on the same filesystem.

This gives an atomic namespace transition without copy/delete split-brain.

If a crash occurs after the terminal payload is written but before the move, startup repair sees a terminal-status record stranded under `active/` and moves it to `terminal/`.

### Legacy migration

Migration is explicit startup mutation owned by execution scheduler initialization, not ordinary reads.

Rules:

- valid legacy terminal record -> `terminal/` via `os.replace`;
- valid legacy nonterminal/unknown-active record -> `active/`;
- corrupt/unclassifiable legacy record -> `active/`, keeping corruption visible to hot readiness rather than hiding it in history;
- `idempotency.json` stays at execution root;
- conflicting legacy + partition record with different bytes -> migration **fails** rather than guessing;
- byte-identical duplicate -> redundant source may be removed safely;
- partition repair moves terminal-status records stranded in `active/` and active-status records stranded in `terminal/`.

Migration readiness is tracked **per execution-store root**, not once for the whole `PROJECTS_ROOT`, so later-mounted legacy projects are normalized on a subsequent pre-admission scheduler-start check without rescanning already-ready histories.

`submit_execution_job()` ensures scheduler/layout startup **before** acquiring `_ADMISSION_LOCK`, preventing migration from becoming an admission-lock critical section.

## Hostile tests

Added:

`tests/test_execution_active_terminal_partition.py`

It verifies:

1. legacy active/terminal migration and idempotency-root preservation;
2. corrupt legacy record remains hot-visible;
3. active -> terminal transition uses `os.replace` and direct identity still resolves;
4. crash-stranded terminal record in active is repaired at startup;
5. conflicting legacy/canonical record is refused rather than guessed;
6. hot iterator excludes terminal history while all-history iterator includes it;
7. direct terminal read remains replay-compatible;
8. 500 terminal + 58 active hot scans load only the 58 active records;
9. history iterator excludes idempotency ledger;
10. a later-mounted legacy project is migrated on the next layout check.

A-034 poison isolation tests were advanced from deprecated physical flat-path assertions to the direct identity contract.

## Structural performance discriminator

Windows host, constant active set:

- 8 RUNNING
- 50 QUEUED
- 58 active total

Terminal history varied independently.

| terminal history | active | queued-discovery loads | running-census loads | queued scan time | running scan time |
|---:|---:|---:|---:|---:|---:|
| 0 | 58 | 58 | 58 | 0.0886 s cold | 0.0072 s |
| 500 | 58 | 58 | 58 | 0.0078 s | 0.0070 s |
| 5,000 | 58 | 58 | 58 | 0.0074 s | 0.0070 s |

The load count is the primary invariant: **58 / 58 / 58 regardless of terminal history**.

This directly converts hot scan complexity from O(lifetime jobs) to O(active jobs) after migration.

## Test-isolation incident and recovery

The first full-suite runs after adding startup migration exposed a separate test-harness defect: pytest inherited the operator's real `PCMMAD_PROJECTS_ROOT`, and indirect Runtime startup migrated real project execution records.

This was detected **before A-035 promotion** by an explicit side-effect audit.

Observed unintended mutation window:

- approximately 2026-09-06 00:39–00:42 ET;
- 94 test-created `active/terminal` directories;
- 1,158 records moved, all into `terminal/`;
- 0 active moved records;
- 0 destination-name conflicts;
- 3,853,013 bytes total.

An exact pre-restore manifest was frozen and registered server-side:

`notes/maintenance/A035_TEST_ISOLATION_RECOVERY_PLAN.json`

SHA-256:
`fafb83d8674be0d37c5625d8dd1a863368b49a7bde20bce6e5bd4cf471e313a7`

Recovery:

- 1,158 / 1,158 files atomically restored to original flat paths;
- 94 / 94 test-created partition directories removed;
- 0 nonempty leftover dirs;
- 0 source remnants;
- 0 restored-target hash failures.

### Test-isolation repair

Added `tests/conftest.py`, loaded before test module collection, which assigns an ephemeral temp root for:

- `PCMMAD_PROJECTS_ROOT`
- `PCMMAD_SYSTEM_ROOT`
- `PCMMAD_SANDBOX_ROOT`
- `PCMMAD_TEMP_ROOT`

and removes it at pytest session end.

This is a test-harness boundary; production migration behavior is not branched on pytest detection.

Qualification check:

- real project `active/terminal` directories before isolated suite: **0**;
- after focused + full isolated suites: **0**.

## Evaluator/currentness scars

A-035 produced several test-surface failures that were repaired without weakening Runtime semantics:

- wrong request-model import in the new partition test;
- A-034 poison test initially bypassed startup migration and asserted the old flat physical path;
- poison identity read happened after its patched temp-root context exited;
- cross-project lock test exposed ambient-root traversal when startup migration was placed in the wrong pre-admission location.

Each was localized as test/currentness or startup-placement evidence. Runtime partition semantics were not rolled back to preserve stale flat-path assumptions.

## Verification

Final isolated execution/partition cluster:

**34 / 34 PASS**

Final isolated complete V30 suite:

**279 collected tests GREEN**

Existing conditional Windows symlink-privilege skip remains the only skip.

Current identities before Git publication:

- `execution_routes.py` SHA-256 `11d888186db1f365ca76aada5512f9fcef420c93c2ec0b0976e9dcfd8c8e2a40`
- `tests/test_execution_active_terminal_partition.py` SHA-256 `28b3b667a7332690bb251d01f0a73e7344a434e3d41870dfdf82dc0980be01c7`
- `tests/test_execution_scheduler_poison_isolation.py` SHA-256 `673b5b227584d5da3552f2b34249fbe9756ef3da2f36fce67b01c8736e67e272`
- `tests/conftest.py` SHA-256 `43d8b6b940b19a88932197f54d13fa2b677642eaa46ca28c20381cb342714ab7`

## Claim ceiling

A-035 earns active/terminal metadata partitioning and active-set-bounded hot scans.

It does **not** claim:

- retention/deletion of terminal history;
- bounded default drain batch;
- optimized all-history `/execution/list` for huge terminal histories;
- process-global admission lock solved across multiple receiver processes;
- legacy bare-PID reuse solved;
- production WSGI serving model solved;
- live V30 promotion.

Those remain separate discriminators.
