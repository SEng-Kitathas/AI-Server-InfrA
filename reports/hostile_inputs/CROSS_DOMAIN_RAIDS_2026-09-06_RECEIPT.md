# External Mechanism Quarry Receipt — Cross-Domain Raids — 2026-09-06

Status: **FULLY READ / ADMITTED AS CONTROLLED RESEARCH EVIDENCE / NOT AUTOMATIC ARCHITECTURE AUTHORITY**

Source attachment: `CROSS DOMAIN RAIDS.md`
- bytes: `20441`
- SHA-256: `dcdafb71cd5a5a66b18139b4cada42dd131fa7a1eb1e01ff117afa5acf310027`

The attachment was read in full before this receipt was written.

## Central claim
The packet argues that multiple PCMMAD Runtime subsystems have **correct semantics with the wrong steady-state cost model**: they rebuild/reverify globally where an incremental extension/checkpoint/cache exists.

Scar candidate supplied by the packet:
`DERIVED_STATE_IS_A_FOLD_NOT_A_REBUILD`.

This was not promoted by source prestige. It was independently pressure-tested against current V30 `protocol_store` and the previously earned execution scheduler findings before promotion.

## Tier 1 raid candidates

### R1 — Kubernetes informer pattern
Quarry: preserve level-triggered reconciliation as correctness backstop while using edge-triggered directory-change notification/cache for steady-state cost. Candidate landing: execution active-store watcher/cache + slow full resync.

### R2 — WAL + checkpoint
Quarry: authoritative append-only log + incrementally extended derived snapshot + verified checkpoint; full fold/full verification become recovery/audit paths. Candidate landing: `protocol_store`.

### R3 — FoundationDB deterministic simulation
Quarry: put nondeterminism behind injectable seams; virtual clock/filesystem/process identity; seeded fault schedules with exact replay. On-ramp: Hypothesis `RuleBasedStateMachine` over execution lifecycle.

### R4 — Stripe idempotency
Quarry: client key -> canonical request/outcome; repeat same key replays result, different payload conflicts. Existing witness: execution submit. Candidate gaps: lab dispatch/batch and protocol appends.

## Tier 2

### R5 — Certificate Transparency
Quarry: Merkle inclusion and append-consistency proofs so append-only claims/receipts are independently verifiable without full-chain reads.

### R6 — Erlang/OTP supervision
Quarry: restart-intensity windows, bounded backoff, crash-loop terminal state, escalation rather than infinite restart.

### R7 — cgroups / Windows Job Objects
Quarry: process ownership primitive should also enforce resource envelope. Current Windows structure already declares memory/process fields but only kill-on-close is set.

### R8 — Chubby/ZooKeeper leases
Quarry: long-running authority should require renewal; revocation is refusal to renew. Candidate landing: approval lease renewed by worker heartbeat.

## Tier 3

### R9 — CoDel
Quarry: queue sojourn time is more decision-useful than depth; possible retry-after/oldest-queued-age admission semantics.

### R10 — gRPC reflection / feature probing
Quarry: when projection must agree with authority, derive projection from authority rather than maintaining both and testing parity. Candidate landing: final compact schema generation; final schema redesign remains locked until end-stage.

### R11 — Kafka consumer offsets
Quarry: caller owns read cursor. Current result-range request is already mostly aligned; verify no hidden server-side cursor and expose explicit next offset where needed.

### R12 — Version vectors / Dynamo siblings
Quarry: make stale-vs-divergent continuity disagreement computable across local store / Git mirror / live Runtime before invoking human conflict grammar.

### R13 — WireGuard/Tailscale / peer identity
Quarry: authenticate peer/workload, not only replayable bearer request. Candidate later security raid: peer auth/mTLS/key rotation; do not silently break hosted GPT reachability.

## Independent current-V30 evidence for the central claim

### Execution scheduler (already earned)
A-033 reproduced per-candidate full-tree capacity recomputation under a global lock and replaced it with one managed-aware census/local budget. A-035 then partitioned active/terminal execution metadata so hot scans no longer scale with terminal lifetime history.

### Protocol store (new independent reproduction)
Current `_append_event_locked` performs:
1. full `read_events`;
2. full `verify_events`;
3. append + fsync;
4. `build_snapshot` over all events;
5. `build_snapshot` calls full `verify_events` again;
6. full `_apply_event` fold.

Windows benchmark / instrumentation:

| Ledger depth | append ms | historical events parsed | events hashed/verified | events folded |
|---:|---:|---:|---:|---:|
| 100 | 10.421 | 100 | 201 | 101 |
| 1000 | 26.411 | 1000 | 2001 | 1001 |
| 4000 | 81.705 | 4000 | 8001 | 4001 |

This independently confirms linear steady-state append cost and ~3x-history derived processing after parse.

## Promotion
The repeated implementation failure is promoted as a project-level hostile audit lens:

**DERIVED_STATE_IS_A_FOLD_NOT_A_REBUILD**

Meaning:
When a mutation can lawfully extend previously verified derived state, the steady-state path SHOULD extend that fold/checkpoint/cache. Full reconstruction and full verification remain mandatory recovery/audit mechanisms where justified; the scar does **not** mean recomputation is universally forbidden.

Companion anti-overreach:
`INCREMENTAL_STEADY_STATE != NO_FULL_RECOVERY_PATH`.

## Raid ordering candidate after A-036
1. protocol-store incremental fold/checkpoint (already reproduced);
2. deterministic simulation/state-machine on-ramp before larger scheduler concurrency changes;
3. informer watch/cache + slow resync on the already-earned active partition;
4. Merkle proof-carrying protocol receipts after incremental ledger head/checkpoint semantics are stable;
5. small high-value raids: lab/protocol idempotency and Windows Job Object resource limits;
6. remaining R6/R8/R9/R10/R11/R12/R13 only after current-tree discriminators.

This ordering is provisional until each raid is inspected against current V30 reality.
