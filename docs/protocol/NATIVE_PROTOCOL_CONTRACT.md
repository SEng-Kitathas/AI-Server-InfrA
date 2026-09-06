# PCMMAD native runtime protocol contract

## Purpose

The receiver now embodies the canonical PCMMAD state classes instead of leaving them in operator memory or prose. The protocol is a server-native capability family behind `/lab/dispatch`; it does not expand the 30-operation Custom GPT schema.

## Authoritative body and sidecar

- `projects/<project_id>/system/protocol/events.jsonl` is the append-only authoritative ledger.
- `projects/<project_id>/system/protocol/state.json` is a replaceable derived checkpoint projection, not authority. It may lag the ledger between periodic checkpoints.
- Every event contains a sequence, project identity, previous hash, canonical event hash, actor, timestamp, kind, and typed payload.
- The authoritative durability boundary remains append -> flush -> fsync. A checkpoint is published only after that ledger boundary succeeds.
- Healthy in-process mutations extend a previously verified in-memory fold by one event instead of rebuilding history.
- Cache loss/restart or an observed external ledger fingerprint change forces full hash-chain verification + full fold before another mutation may extend the ledger.
- The current checkpoint cadence is every 128 events plus genesis. Checkpoint cadence is an implementation detail, not a client-visible authority contract.
- Protocol read/verify/status APIs continue to derive truth from the authoritative ledger; clients SHALL NOT infer ledger currentness from `state.json`.

**Cost/currentness law:** `DERIVED_STATE_IS_A_FOLD_NOT_A_REBUILD`, paired with `INCREMENTAL_STEADY_STATE != NO_FULL_RECOVERY_PATH`.

## State classes

The projection contains:

- runtime mode and rigor level
- active objective
- constraints with revisions and active state
- continuity records
- claims with kind, confidence, evidence, and revisions
- artifacts with class, digest, provenance, seal, and revisions
- adjudication/promotion records
- scoped waivers with owner, doctrine basis, state, expiry, and claim lineage

## Modes

`DISCUSSION`, `AUDIT`, `BUILD_PLAN`, `BUILD_COMMIT`, `RECOVERY`, `CHECKPOINT`, `MERGE`, and `PROMOTION` are structured values.

The mode guard recognizes four work domains:

- `READ`: allowed in every mode
- `GOVERNANCE`: allowed in every mode because it records truth about the process
- `SPECIMEN`: allowed only in `BUILD_COMMIT`, `RECOVERY`, and `MERGE`
- `PROMOTION`: allowed only in `PROMOTION`

`PCMMAD_PROTOCOL_POLICY_MODE` controls router enforcement:

- `off`: legacy dispatch behavior
- `advisory` (default): preserves execution and returns a visible warning
- `strict`: blocks a project-scoped specimen mutation when the initialized protocol mode forbids it

Projects without a protocol ledger preserve legacy behavior.

## Proportionate rigor

- `STANDARD`: at least 1 non-failed, non-expired evidence reference
- `ELEVATED`: at least 2 distinct evidence references, at least 1 marked `VERIFIED`
- `CRITICAL`: at least 3 distinct evidence references, at least 2 marked `VERIFIED`

Ratification rejects duplicate, failed, or expired evidence. `UNKNOWN` claims cannot be ratified.

## Artifact invariant

A sealed artifact requires a SHA-256 digest. Re-registering the same sealed artifact identity with a different digest is rejected; a new identity and explicit supersession/promotion record are required.

## Waiver invariant

A waiver must have an identity, scope, reason, doctrine basis, owner, status, optional future expiry, and explicit affected claims. Inactive or expired waivers cannot authorize promotion and remain visible in lineage.

## Tool family

- `protocol.initialize`
- `protocol.status`
- `protocol.guard.check`
- `protocol.mode.transition`
- `protocol.objective.set`
- `protocol.constraint.record`
- `protocol.continuity.record`
- `protocol.claim.record`
- `protocol.artifact.register`
- `protocol.promotion.record`
- `protocol.waiver.record`
- `protocol.ledger.verify`
