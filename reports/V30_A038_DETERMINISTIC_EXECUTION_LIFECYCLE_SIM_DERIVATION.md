# V30 A-038 — Deterministic Execution Lifecycle Simulation / Replay On-Ramp

Date: 2026-09-06
Status: **TECHNICALLY EARNED IN V30 WORKING TREE / GIT PUBLICATION PENDING**

## Commander intent
Turn hostile engineering from operator discipline alone into an executable schedule-search mechanism for execution lifecycle failures.

The first survivor must be:
- bounded;
- seeded;
- exactly replayable;
- grounded in real Runtime lifecycle/store/admission/reconciliation code rather than a toy reimplementation;
- capable of rediscovering/protecting against at least one already-earned schedule-level scar;
- small enough to qualify before any giant virtual-OS effort.

## Embodiment
Added:
`tools/hostile/execution_lifecycle_sim.py`

The simulator keeps current execution scheduler/store/admission/reconciliation code real and virtualizes only nondeterministic boundaries needed for the on-ramp:
- process spawn/liveness;
- process generation/PID recycle witness;
- wall clock;
- action schedule through `random.Random(seed)`.

Every action records a deterministic trace including active/terminal store state, alive PID generations, scheduler telemetry, drain count, and PID-alias observations.

Unexpected schedule-level action exceptions are converted to `SimulationInvariantError` containing:
- `A038_REPLAY_SEED=<seed>`;
- exact deterministic JSON trace.

CLI replay surface:
```text
python tools/hostile/execution_lifecycle_sim.py --seed <N> --steps <N> --scheduler-variant current|pre_a034
```

## Historical vulnerable-reference specimen
A-038 includes a deliberately bounded `pre_a034` scheduler variant reproducing one already-earned historical scar:
- reconciliation has no per-record exception isolation;
- one reconcile exception escapes before `_drain_queue`;
- otherwise it uses current Runtime helpers/store/admission behavior.

This reference is a hostile scar specimen, not production authority.

## Current survivor campaign
Before adding permanent tests, current production was pressure-run through:
- seeds `0..99`;
- 40 actions per seed;
- current scheduler variant.

Result:
**100 / 100 seeds PASS**, no structural invariant failures.

Structural invariants include:
- no job ID simultaneously present in active and terminal stores;
- only active statuses remain in active store;
- only terminal statuses remain in terminal store;
- current simulated live RUNNING count never exceeds global concurrency;
- per-project live RUNNING count never exceeds project concurrency;
- every clean/injected-reconcile scheduler tick reaches queue drain;
- injected reconcile errors surface in typed scheduler telemetry.

## Mechanical rediscovery of A-034 scar
Bounded search:
- scheduler variant: `pre_a034`;
- seed search: `0..99`;
- 40 steps.

First counterexample:
**seed 0**.

Minimal discovered prefix:
1. `dead_running:p2` creates a dead RUNNING supervision-loss specimen;
2. scheduled `tick_reconcile_fault` injects `PermissionError("A038 injected reconcile fault")`;
3. pre-A-034 scheduler lets the exception escape before drain;
4. failure envelope contains `A038_REPLAY_SEED=0` and exact trace with `drain_calls=0`.

The same vulnerable seed was replayed twice and produced an **exact byte-for-byte identical failure envelope/trace**.

The same seed/current scheduler completed successfully while exercising:
- 3 injected reconcile-fault ticks;
- 2 PID recycle events;
- queue drain 11 times in the observed 40-step run.

This demonstrates both rediscovery and survivor protection with one schedule identity.

## Permanent regression
Added:
`tests/test_execution_lifecycle_sim.py`.

It proves:
1. a current seed replay returns byte-identical structured result;
2. bounded search rediscovers pre-A-034 with seed 0;
3. vulnerable seed 0 failure replays exactly twice;
4. same seed/current scheduler survives and cumulative reconcile-error telemetry matches injected fault count;
5. a small multi-seed current campaign preserves active/terminal disjointness;
6. unknown scheduler variants are rejected.

## Focused verification
Current execution/simulation cluster:
**39 / 39 PASS**.

Included:
- A-038 lifecycle simulation;
- A-033 admission hotpath;
- A-034 poison isolation;
- A-035 active/terminal partition;
- async unification;
- bounded progress;
- cross-project locking;
- ownership handshake;
- worker restart recovery.

## Full verification
Complete V30 suite:
**289 collected tests GREEN**, existing conditional Windows symlink-privilege skip only.

Current identities:
- simulator SHA-256 `98990c6024a3ab9defbbc1220e640f139490b2bdd54ae5a7048b0d85a3a8221a`
- A-038 test SHA-256 `c61e0f6e6fc51f8d4fb8427c2438eb2cd44bd272eee2db4724c99f8758fb57ee`.

## New mechanically exposed open seam — legacy PID reuse
The simulator's current-production seed-0 run performed two PID recycle actions. Final state reported:
- `job-00003` as active RUNNING with recycled PID identity;
- `job-00007` as active RUNNING with recycled PID identity;
- both listed in `pid_alias_jobs` because simulator generation differs from the generation originally assigned to the job.

Current non-worker reconciliation still uses bare `_pid_alive(job.pid)` and therefore cannot distinguish this simulated PID reuse. Worker-capsule ownership separately carries `worker_creation_time_100ns`.

Disposition:
**REAL CURRENT DISCRIMINATOR / NOT FIXED IN A-038.**

Do not encode the defect itself as a passing invariant. Hand it to its own Runtime raid after A-038 publication unless a stronger dependency ordering emerges.

## Evaluator scars
- first 100-seed campaign command used POSIX heredoc syntax inside PowerShell and failed before simulator execution; rerun through server Python executor;
- first focused pytest selection referenced stale filename `test_execution_store_partition.py`; current inventory uses `test_execution_active_terminal_partition.py`; no tests collected in failed selection;
- first permanent focused run was 38/39 because the test incorrectly required final `last_tick_reconcile_errors == 0`; seed 0 can legitimately end on an injected fault tick. Test was corrected to compare cumulative typed error telemetry with injected fault count; Runtime/simulator behavior was not weakened.

## Claim ceiling
A-038 is an on-ramp, not FoundationDB-scale exhaustive simulation.

It does **not** yet virtualize:
- filesystem durability/reordering;
- Windows kernel Job Object semantics;
- real process creation time/PID allocator;
- network/HTTP transport;
- receiver restart as a whole process image;
- arbitrary thread interleavings;
- disk-full/slow/partial-write schedules;
- every scheduler timing boundary.

Seeded pseudo-random schedule search is not formal model checking and does not prove absence of undiscovered schedules.

Current law:
**SCHEDULE_FAILURES_REQUIRE_SCHEDULE-LEVEL TESTS WHERE PRACTICAL.**

Replay law:
**A FAILURE SEED + DETERMINISTIC TRACE IS A STRONGER RECEIPT THAN AN UNREPLAYABLE FLAKE.**

## Next
After A-038 Git publication, prioritize the newly mechanized legacy PID-reuse identity seam before informer/watch work unless current-tree inspection falsifies its materiality. That repair should bind legacy RUNNING liveness to process identity (PID + creation-time witness or equivalent) without weakening worker-capsule ownership semantics.

Informer/watch+slow-resync, Merkle receipts, idempotency, and Job Object resource envelopes remain queued raids after this correctness seam.
