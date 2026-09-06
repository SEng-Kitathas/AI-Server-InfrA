# V30 A-037 — Protocol Incremental Fold / Recovery Backstop Derivation

Date: 2026-09-06
Status: **TECHNICALLY EARNED IN V30 WORKING TREE / GIT PUBLICATION PENDING**

## Commander intent
Embody the newly promoted hostile audit lens:

**DERIVED_STATE_IS_A_FOLD_NOT_A_REBUILD**

without violating:

**INCREMENTAL_STEADY_STATE != NO_FULL_RECOVERY_PATH**.

The authoritative protocol ledger, append+fsync durability boundary, sequence/hash-chain semantics, corruption refusal, and deterministic crash-gap recovery SHALL survive.

## Pre-fix current-V30 cost model
`_append_event_locked` performed:
1. full `read_events`;
2. full `verify_events`;
3. append + flush + fsync;
4. full `build_snapshot`;
5. a second full `verify_events` inside snapshot build;
6. full `_apply_event` fold.

Public mutators could pay additional rebuild work through `ensure_protocol()` before append.

### Private append benchmark before A-037
| ledger depth | append ms | historical parsed | verify-event work | fold applications |
|---:|---:|---:|---:|---:|
| 100 | 10.421 | 100 | 201 | 101 |
| 1,000 | 26.411 | 1,000 | 2,001 | 1,001 |
| 4,000 | 81.705 | 4,000 | 8,001 | 4,001 |

### Public `record_continuity` benchmark before A-037
| ledger depth | mutation ms | full ledger reads | historical parsed | build/fold passes | fold applications |
|---:|---:|---:|---:|---:|---:|
| 100 | 11.3 | 3 | 300 | 2 | 201 |
| 1,000 | 48.2 | 3 | 3,000 | 2 | 2,001 |
| 4,000 | 167.8 | 3 | 12,000 | 2 | 8,001 |

## Derived survivor
A-037 does **not** make `state.json` authoritative and does **not** remove full verification.

### Authority
- `events.jsonl` remains the append-only authoritative ledger.
- append -> flush -> fsync remains the durability boundary.
- `state.json` remains a replaceable derived projection/checkpoint only.

### Healthy steady state
A verified in-memory `ProtocolSnapshot` is cached per authoritative ledger path.
Each healthy mutation:
1. validates that the authoritative ledger fingerprint has not changed since the cached fold was verified/advanced;
2. derives sequence and previous hash from the verified fold;
3. appends one event and fsyncs it;
4. applies exactly one `_apply_event` fold step;
5. advances the in-memory cache fingerprint;
6. publishes `state.json` only at genesis or every 128 events.

### Recovery/currentness backstop
Any of the following remove fast-path authority:
- process restart/cache loss;
- missing ledger;
- observed ledger size/mtime/ctime change;
- post-fsync projection/checkpoint failure.

On the next mutation, the Runtime falls back to the pre-existing full hash-chain verification + full fold before it is allowed to append again. Recovery also republishes the replaceable projection.

### Why the persistent checkpoint is not trusted across restart
A-037 does not yet have a cryptographic proof that lets a fresh process trust an old projection against arbitrary historical ledger tampering without reading history. Therefore a fresh process deliberately full-verifies/folds the authoritative ledger once.

Cheap persistent inclusion/append-consistency proof is reserved for the later Certificate-Transparency/Merkle raid.

## Native contract clarification
`docs/protocol/NATIVE_PROTOCOL_CONTRACT.md` now states explicitly:
- `state.json` is a derived checkpoint projection and may lag the ledger;
- any published projection follows successful ledger fsync;
- healthy in-process mutations extend a verified fold;
- cache loss/restart/external fingerprint change triggers full verify/fold;
- clients SHALL NOT infer ledger currentness from `state.json`;
- current checkpoint cadence is every 128 events plus genesis and is not client authority.

## Hostile tests
Added:
`tests/test_protocol_incremental_fold.py`.

It proves:
1. warm mutation performs zero `read_events`, zero `verify_events`, zero `build_snapshot`, exactly one `_apply_event`, and no sequence-2 checkpoint write;
2. external ledger tamper changes the fingerprint, forces full verification, refuses append, and leaves ledger size unchanged;
3. a durable append followed by injected projection failure invalidates cache; the next mutation performs exactly one full rebuild, preserves the durable event, continues at sequence 3, and verifies clean;
4. checkpoint writes occur exactly at genesis and sequence 128 in the bounded test;
5. simulated restart/cache loss performs one full rebuild before another append.

## Hostile evaluator scars
Several benchmark/test fixture assumptions were stale and were repaired without weakening Runtime:
- lowercase rigor `standard` rejected; current enum is `STANDARD|ELEVATED|CRITICAL`;
- nonexistent continuity kind `CHECKPOINT` rejected; current kind `MAINTENANCE` used;
- `verify_events()` returns a dict, not an object with `.ok`;
- verification failures are under `failures`, not `errors`;
- `ProtocolPaths` projection member is `.snapshot`, not `.state`.

These are evaluator-currentness defects, not Runtime defects.

## Post-fix benchmark
### Warm public mutation
| existing ledger depth | mutation ms | full reads | full verifies | rebuilds | fold applications | checkpoint writes |
|---:|---:|---:|---:|---:|---:|---:|
| 100 | 2.111 | 0 | 0 | 0 | 1 | 0 |
| 1,000 | 2.367 | 0 | 0 | 0 | 1 | 0 |
| 4,000 | 3.007 | 0 | 0 | 0 | 1 | 0 |

### Periodic checkpoint boundary
| existing depth | next sequence | mutation ms | projection bytes |
|---:|---:|---:|---:|
| 127 | 128 | 2.956 | 20,307 |
| 1,023 | 1,024 | 6.778 | 161,004 |
| 4,095 | 4,096 | 17.917 | 646,380 |

Checkpoint publication remains history/current-state-size dependent because the projection contains growing collections. That cost is explicit and periodic rather than hidden in every mutation.

### 20k discriminator
Synthetic 20,000-event ledger on operator Windows host:
- cold cache/recovery full verify+fold: ~273.342 ms;
- immediately following warm mutation: ~12.252 ms;
- authoritative ledger after mutation verified `ok=True` at 20,001 events.

Cold recovery remaining O(history) is intentional in A-037.

## Verification
- current protocol cluster including A-037 hostile regression: **18/18 PASS**;
- complete V30 suite: **284 collected tests GREEN**, existing conditional Windows symlink-privilege skip only.

Current identities:
- `baseline/pcmmad_receiver/protocol_store.py` SHA-256 `c7defa22e8fa37922ab20f5a6207553e8b1eae92aa86be2c77e8d728feb9ec0e`
- `tests/test_protocol_incremental_fold.py` SHA-256 `bd1c4ada05bbac4ef3e1d48574833c6c3c2bb4074d4e36e3251eb5357596ef89`
- `docs/protocol/NATIVE_PROTOCOL_CONTRACT.md` SHA-256 `83fc8bf6fef0bc359914ec357cece777ded26846a90fec9d6419f9e7ec2f80df`.

## Security / integrity claim ceiling
A-037's O(1)-ish in-process fast-path currentness witness is the ledger filesystem fingerprint `(size, mtime_ns, ctime_ns)` plus the previously verified in-memory fold.

It detects ordinary external writes/truncation/replacement that change those metadata. It does **not** claim cryptographic detection of an adversary who can rewrite historical bytes while perfectly preserving/restoring the fingerprint. Solving cheap persistent proof of arbitrary historical integrity is explicitly reserved for the later Merkle/Certificate-Transparency raid.

Therefore:
`A037_FAST_CURRENTNESS_WITNESS != CRYPTOGRAPHIC_HISTORY_PROOF`.

## Claim ceiling / next
A-037 earns the second-system embodiment of fold-not-rebuild for healthy protocol mutation.
It does not fix:
- cold-start full-history verification/fold cost;
- cryptographic proof-carrying checkpoints;
- protocol append idempotency;
- `/execution/list(limit=N)` history indexing;
- informer/watch scheduling;
- deterministic schedule simulation;
- final schema redesign.

After A-037 Git publication, the next raid is the deterministic simulation/state-machine on-ramp unless current-tree inspection produces a stronger dependency ordering.
