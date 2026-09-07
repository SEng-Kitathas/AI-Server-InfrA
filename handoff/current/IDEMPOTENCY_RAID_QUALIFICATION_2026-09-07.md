# IDEMPOTENCY RAID QUALIFICATION — 2026-09-07

Status: **QUALIFIED ENGINEERING CANDIDATE / GIT PUBLICATION PENDING**

## Published baseline
- Current Git/remote `main`: recovery-only handoff `7618b0350c0266c70125d226baa9371bf3844a9d`.
- Last engineering feature: A-001 `a552af9957b99361c3aebf91c7abc65775e0ce43`.
- `RECOVERY_HANDOFF_HEAD != ENGINEERING_FEATURE_HEAD`.

## Candidate identity
- 7 changed/new engineering files.
- Inventory SHA-256: `1d81399d5f98e6e37481cb3070a5d987c340aab2c9bf067bf1efa600fa803efb`.

## Earned contracts
- `IDEMPOTENCY_INDEX != CONSEQUENCE_AUTHORITY`.
- `RETRY_SAFETY_REQUIRES_DURABLE_PRE_POST_CONSEQUENCE_WITNESS`.
- `UNPROVEN_EFFECTS_DEFAULT_TO_UNSAFE_RETRY`.
- No exactly-once claim is made where consequence and witness are not atomically coupled.

## Runtime embodiment
- `ToolSpec` exposes `idempotency_semantics` and includes it in the capability contract digest.
- Runtime registry census: 107 tools total.
  - `safe_repeat`: 31
  - `unsafe_retry`: 73
  - `keyed_replay_when_keyed`: 1 (`execution.submit`)
  - `state_bound_replay`: 1 (`sop.ingest.next_chunk`)
  - `position_bound_replay`: 1 (`transfer.chunk.write`)
- Durable execution writes an authoritative job reservation before process consequence, persists `STARTING` before process launch, reconstructs a missing auxiliary idempotency index from job records, rejects changed-payload key reuse, and fails closed on duplicate authoritative key claims.
- Legacy commit idempotency is write-ahead: PREPARED binds request fingerprint, before-state hash, and intended physical final hash; retry distinguishes before-state, intended-after-state, and conflict; append recovery does not duplicate bytes; key reuse with changed request returns explicit conflict.
- JSONL persistence flushes + fsyncs at its declared persistence boundary.

## Hostile evidence
- Dedicated response-loss suite: `12/12 PASS`.
- Broader idempotency/execution/SOP/transfer/capability/A-001 adjacency: `96/96 PASS`.
- Complete suite: `364 collected / 363 passed / 0 failed / 1 conditional skip`.
- Changed/new Python compile: PASS.
- CRLF-aware `git diff --check`: PASS.
- Registry census reproduced exact semantics above.

## Claim ceiling
This campaign does not claim that all mutations are idempotent. Most effectful capabilities are intentionally `unsafe_retry` until a response-loss-safe mechanism is earned at their authoritative consequence boundary.

## Sequencing
- Next server engineering campaign after publication: Windows Job Object resource envelope.
- Then remaining cross-domain raids.
- Final schema redesign remains LAST and untriggered; whole-runtime convergence plus explicit user `hells yeah, ready` remains required.
- OBE/Skills 11-Skill interface remains unfrozen and may dogfood the promoted Runtime semantics in parallel.
- `GIT_PUBLICATION != LIVE_RUNTIME_PROMOTION`.
