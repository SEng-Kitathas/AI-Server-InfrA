# V30 USER-OWNED CONTINUITY MEMORY DERIVATION

Date: 2026-09-08
Status: **QUALIFIED ENGINEERING CANDIDATE / PUBLICATION PENDING / REAL USER MEMORY NOT YET INGESTED**
Live promotion: NOT PART OF THIS CAMPAIGN
Final schema: UNTOUCHED / LAST / LOCKED

## Quarry

This campaign turns the user-owned continuity design into a server-native mechanism rather than leaving it as chat-platform memory or Skill-local state.

Primary donor/spec inputs were the user's `RAHL_USER_CONTINUITY_MEMORY_2026-09-07.md` and the cross-model design attack in `CLAUDE CONTINUITY EXPORT 2026-09-08.md`. The original documents remain donor evidence. Their contents are not silently imported by this engineering feature.

The donor design's core law survives intact:

`CONTINUITY IS NAVIGATION, NOT PROOF.`

The Claude attack contributed several schema/currentness improvements that survive implementation: source-instance provenance, causal supersession evidence, bounded/lazy hydration, ledger/snapshot sequence currentness, revalidation triggers, portable/user/project/deployment export classes, addressable snapshots, and the law `TWO ASSISTANTS AGREEING != INDEPENDENT CONFIRMATION`.

## Architectural placement

User continuity is a distinct global Runtime plane.

It is not:

- project authority;
- PCMMAD protocol state;
- a Skill-owned database;
- model conversational memory;
- live evidence.

Authority remains:

`LIVE EVIDENCE > PROJECT AUTHORITY > PERSISTED USER CONTINUITY > CONVERSATIONAL MEMORY > INFERENCE`

Derived laws:

- `USER_CONTINUITY != PROJECT_AUTHORITY`.
- `MEMORY_MECHANISM != MEMORY_CONTENT`.
- `PORTABLE_STACK != USER_SPECIFIC_OVERLAY`.
- `PROJECT_STATE != GLOBAL_USER_STATE`.
- `SKILL_LOGIC != USER_MEMORY`.
- `MODEL != CONTINUITY_STORE`.
- `TWO_ASSISTANTS_AGREEING != INDEPENDENT_CONFIRMATION`.
- `FORGET_REQUEST != PHYSICAL_ERASURE`.
- `MATERIAL_MEMORY_CHANGE_REQUIRES_CAUSAL_SUPERSESSION`.
- `MEMORY_APPENDS_MAY_COMMUTE; SNAPSHOT_MATERIALIZATION_MUST_BE_SERIALIZED`.
- `DERIVED_MEMORY_SNAPSHOT_IS_A_FOLD_NOT_AUTHORITY`.

## Native Runtime family

Eight server-native capabilities are added behind the existing `/lab/dispatch` router:

1. `memory.add`
2. `memory.update`
3. `memory.supersede`
4. `memory.verify`
5. `memory.forget_request`
6. `memory.compact_snapshot`
7. `memory.read`
8. `memory.search`

The native Runtime grows from 108 to **116 tools**. The compact imported action schema remains **exactly 30 operations**. This campaign therefore does not trigger or prejudge the final-schema redesign.

`shared_core.capabilities()` adds only `user_continuity_memory=true`.

## Durable layout

Default global root:

`SYSTEM_ROOT/user_continuity`

Optional deployment override:

`PCMMAD_USER_CONTINUITY_ROOT`

Per profile:

- `events.jsonl` — authoritative append-only hash-chained event ledger;
- `profile.lock` — cross-process serialization boundary;
- `objects/<sha256>.json` — content-addressed materialized objects;
- `snapshots/<seq>-<head-prefix>.json` — immutable snapshot manifests;
- `current.json` — atomic current materialization pointer/manifest.

Schemas:

- `pcmmad.user-continuity-ledger.v1.1`
- `pcmmad.user-continuity-snapshot.v1.1`
- `pcmmad.user-continuity-object.v1.1`

## Append authority and currentness

Each event carries:

- monotonic `event_seq`;
- stable event ID;
- timestamp;
- profile ID;
- actor;
- source instance/thread/event;
- evidence-independence group;
- semantic operation;
- payload;
- previous event hash;
- required idempotency key;
- semantic request fingerprint;
- canonical event hash.

Cold recovery verifies the full sequence/hash chain before folding.

Healthy in-process mutation extends a verified cached fold. External ledger fingerprint changes invalidate that cache and force a full verify/fold before mutation.

Materialized snapshots carry:

- `snapshot_from_seq`;
- `ledger_head_seq`;
- `ledger_head_hash`.

Healthy `memory.read`/`memory.search` do not full-fold the ledger. They read the atomic manifest, content-addressed objects, and a bounded last-ledger-event currentness witness. A valid later append without matching materialization causes `MEMORY_SNAPSHOT_STALE` rather than stale-as-current hydration.

`memory.compact_snapshot` is the explicit recovery/reconciliation path: verify/fold authoritative history and rebuild derived objects.

## Hydration/read-amplification control

The always-loaded core is hard-capped at **32 KiB** encoded bytes.

Ordinary hydration is:

`hard-capped core + explicitly relevant lazy sections + optional bounded ledger tail`

rather than a full memory-document preload.

Addressability includes a content-addressed target index, so an exact dotted target can identify its section without scanning every section.

Materialization is bounded before the authoritative append:

- core max: 32 KiB;
- section max: 2 MiB each;
- target-index max: 2 MiB;
- max materialized sections: 512.

If a projected mutation would violate these ceilings, the mutation fails **before** the authoritative ledger append.

Implicit search is also bounded: if more than 128 sections exist, callers must specify search sections rather than scanning the whole store by default.

Target-filtered ledger-tail reads fold explicit history once rather than once per event.

## Semantic mutation discipline

### `memory.add`

Adds a new stable dotted target. A current fact already occupying the target rejects with `MEMORY_TARGET_EXISTS`; material corrections must use supersession rather than overwrite.

### `memory.update`

May adjust non-material metadata/currentness such as confidence, status (except dedicated lifecycle states), provenance, export class, sensitivity, hydration priority, section routing, and revalidation metadata.

It cannot modify material fact value/identity. It cannot synthesize `SUPERSEDED` or `FORGET_REQUESTED` states.

### `memory.supersede`

Requires:

- a current memory fact;
- replacement value/reason;
- the same stable dotted target;
- one or more `superseded_by_evidence` records.

The old fact remains in history with `SUPERSEDED`, links to its replacement, and preserves the evidence that forced the correction. The replacement records the superseded memory ID.

### `memory.verify`

Appends verification evidence without elevating memory into live/project authority.

Verification summary distinguishes write-path count from independent evidence count. GPT and Claude reading the same artifact can create two verification events while still contributing only one `evidence_independence_group`.

### `memory.forget_request`

Appends a tombstone and removes the fact from normal hydration/search. It explicitly returns `physical_erasure=false`; append-only provenance is not dishonestly described as erased.

Physical purge/redaction, if later required, is a separate governed lifecycle with different lineage semantics and is not claimed here.

## Revalidation/currentness metadata

Facts can carry:

- `last_verified_at`;
- timezone-aware `revalidate_after`;
- event-driven `revalidate_when` triggers;
- `requires_live_verification`.

Read/search compute revalidation hazards at request time. Expired time deadlines and live-verification requirements are surfaced as hazards rather than quietly returning stale-capable content as current proof.

All `PROJECT_STATE` memories are required to set `requires_live_verification=true`. The memory plane can therefore remember navigation/status claims while mechanically refusing to masquerade them as current project authority.

## Portability / overlay separation

Each fact carries an orthogonal `export_class`:

- `PORTABLE`
- `USER`
- `PROJECT`
- `DEPLOYMENT`

`memory.read` and `memory.search` accept mechanical export-class filters. This makes future neutral-stack projections possible without relying on prose cleanup.

The portable mechanism can therefore be distributed independently from:

- user-specific continuity;
- project-specific remembered pointers/state;
- machine/deployment-specific facts.

## Concurrency and response loss

Profile mutation uses both:

- in-process per-profile `RLock`;
- cross-process file locking (`msvcrt.locking` on Windows).

Every authoritative mutation requires an idempotency key.

Same key + same semantic request returns the original event receipt even if unrelated later events advanced the ledger head. Same key + different semantic request fails with `MEMORY_IDEMPOTENCY_CONFLICT`.

Callers may also supply `expected_ledger_head_hash` for optimistic CAS. A stale writer fails with `MEMORY_HEAD_CONFLICT` rather than last-writer-wins.

Snapshot materialization occurs while the profile mutation lock is held.

## Hostile evidence

`tests/test_user_continuity_memory.py` currently proves **25 / 25 PASS**, including:

- empty reads are non-initializing;
- healthy hydration/search do not full-fold the ledger;
- hard-capped core and lazy sections;
- exact target addressability;
- response-loss idempotent replay after unrelated head advance;
- idempotency conflict on semantic mismatch;
- head CAS stale-writer rejection;
- duplicate target rejection;
- causal supersession with forcing evidence;
- stable-target supersession law;
- generic update cannot change material value or bypass semantic lifecycle tools;
- two assistant writes over one evidence group count as one independent group;
- project-state live-verification boundary;
- forget tombstone without fake erasure;
- pre-append core budget rejection;
- pre-append section budget rejection;
- stale snapshot fail-closed + compact recovery;
- snapshot-object hash tamper detection;
- ledger hash-chain tamper detection;
- bounded current snapshot search;
- revalidation hazard computation;
- timezone-aware revalidation timestamps;
- target history folds once;
- six separate concurrent processes serialize to event sequences 1..6 with one valid final hash chain and current snapshot.

Final memory/registry/adapter/currentness cluster: **59 / 59 PASS**.

Final full Runtime suite on the exact candidate bytes:

**423 collected / 422 passed / 0 failed / 1 conditional skip**.

Changed/new Python compile: PASS.

CRLF-aware `git diff --check`: PASS.

## Claim ceiling

This campaign does **not** claim:

- that chat-platform memory has been replaced globally;
- that project state can be trusted from user memory without project/live readback;
- that a forget request physically erases immutable history;
- semantic/vector search; current search is bounded lexical retrieval over current snapshot sections;
- encrypted-at-rest memory beyond deployment/filesystem controls;
- multi-host/distributed consensus;
- live Runtime promotion;
- final imported-action schema redesign;
- that the real user memory exports have already been ingested.

The real continuity documents remain untouched donor artifacts until this mechanism is published and recoverable. Their later semantic merge must occur through v1.1 operations while preserving original source artifacts and causal/currentness distinctions.

## Next sequence after publication

1. Publish and remote-verify this six-file engineering feature.
2. Persist/register exact post-publication continuity.
3. Refresh and remote-verify the Git recovery handoff.
4. Only then initialize the real user profile and semantically merge the user + Claude continuity exports through the published v1.1 contract.
5. Preserve project-status imports as `PROJECT_STATE / UNKNOWN_CURRENTNESS / requires_live_verification=true` until project readback earns currentness.
6. Keep live frozen.
7. Keep R10/final schema LAST/LOCKED until explicit user trigger `hells yeah, ready`.
