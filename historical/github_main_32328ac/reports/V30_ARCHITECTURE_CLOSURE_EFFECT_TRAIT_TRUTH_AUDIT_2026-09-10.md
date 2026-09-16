# V30 Architecture Closure / Effect-Trait / GitHub Truth Audit — 2026-09-10

Status: **AUDIT COMPLETE / LOW-LEVEL ICF CURRENTNESS FIX CANONICAL-SOURCE QUALIFIED / CURRENT-SURFACE RECONCILIATION REQUIRED BEFORE LIVE PROMOTION**

Audited source: remote/current `main` at `9be7ad603f50c079acc92d542add6a011a2ea2d7`.
Current engineering feature beneath that front door: `673e3b15fa16053e6da6594604d9ce6db7faad1c` (`Harden substrate durability and package embedding`).

Fresh full-suite readback at audit start: **769 collected / 767 passed / 2 skipped / 0 failed**.
Native tool count: **158**.
Compact imported action count: **30**.

This audit was triggered by an external review of effect-trait semantics, compact-surface selection, UCM compatibility coexistence, continuity-plane authority boundaries, and prerequisites for a future Plan-VM / compositional schema branch.

## 1. Architecture-closure verdict

**VERIFIED WITH SCOPE:** the current Runtime substrate is at the end of the presently earned core-architecture road.

The statement means:
- canonical durable machine truth is owned by Runtime rather than model/chat/UI/transport;
- project state, execution, results, continuity, authority, UCM, RES, transfer, currentness, durability, package embedding and supervision have current native homes;
- no currently reproduced defect requires inventing another core state/authority/scheduler/runtime plane;
- the final compositional external schema / planner work remains a deliberately separate campaign.

It does **not** mean:
- no future implementation bug exists;
- current machine-readable effect metadata is ready to schedule arbitrary composition;
- compact-30 membership has already been derived from native semantics;
- legacy compatibility APIs can remain forever without a migration decision;
- every Git-contained recovery surface is current;
- the loaded live process already equals source.

Current best classification:

`CORE_RUNTIME_ARCHITECTURE_CONVERGED != FINAL_COMPOSITION_SCHEMA_COMPLETE`.

The effect-trait/compact/legacy-memory findings below are prerequisites for the separate schema/composition branch, not evidence that another present Runtime truth plane is missing.

## 2. Effect-trait census

Current native registry at `9be7ad6...`:
- tools: **158**;
- distinct `effect_traits` strings: **204**;
- traits used by exactly one tool: **133**;
- traits used by more than one tool: **71**.

The field is therefore a broad descriptive vocabulary, not a closed behavioral algebra.

### Runtime behavior actually consuming named traits

Four trait strings currently change Runtime behavior:

1. `project_mutation_fenced`
   - consumed by native dispatch to decide whether project mutation fencing applies;
2. `idempotent_replay_while_unacked`
   - consumed by `ToolSpec.effective_idempotency_semantics`;
3. `exact_offset_required`
4. `requires_chunk_hash`
   - the latter two are consumed together to derive `position_bound_replay`.

Other effect traits are projected into tool cards and included in `contract_digest`; some properties represented by them are independently enforced by code/tests, but the trait string itself is not a generic verifier or policy branch.

Therefore the external review's central concern is **substantively correct**:

`TRAIT_DECLARED != PROPERTY_HELD_BY_TYPE_SYSTEM`.

The stronger nuance is that current Runtime already treats automatic policy derivation from arbitrary effect traits as unearned. Existing Revisit continuity explicitly records “Effect traits should drive policy automatically” as an open/separate item and states that descriptive truth is earned while policy automation is not.

### Named guarantee-like traits checked

The review cited `atomic_replace`, `fsync`, and `snapshot_cas_supported`.

Fresh source inspection shows those properties are **currently held by mechanisms**:
- transfer chunk writes flush + `fsync`;
- import finalization uses atomic `os.replace` after content/destination-currentness verification;
- user-continuity snapshot compaction checks supplied authoritative ledger-head CAS and fails on mismatch.

So the present defect is **not** that these three properties are false today. The defect is that the common `effect_traits` type cannot prove or distinguish “enforced predicate” from “descriptive property.”

### Schema-branch gate

Before any future planner/`compose` mechanism uses effects to schedule parallelism, infer safety, authorize retries, or compute dependency ordering, the effect model SHALL be split into at least:
- a closed, exhaustively-consumed enforced-predicate/effect algebra;
- descriptive/free-form annotations that carry no automatic guarantee.

Any enforced effect predicate must have a consumer and hostile regression. Adding one without a consumer must fail validation/qualification.

`TRAIT_DECLARED != PROPERTY_HELD`.
`DESCRIPTIVE_EFFECT != SCHEDULING_AUTHORITY`.

No partial Plan-VM/effect-algebra redesign is landed by this server audit; that belongs to the separate schema branch.

## 3. Contract identity nuance

`ToolSpec.contract_digest` currently includes the entire sorted `effect_traits` list.

Consequence:
- descriptive trait edits can change a capability contract digest even when executable behavior is unchanged;
- enforced and descriptive metadata therefore share not only one namespace but one currentness identity.

This is additional evidence that the future schema branch should separate those concepts deliberately rather than teaching an automatic planner to trust the current list.

No current server behavior is changed here because existing clients already bind the present digest contract.

## 4. Compact 30-operation surface

Verified:
- source has 158 native tools;
- compact imported OpenAPI contains exactly 30 unique operations;
- parity/currentness tests verify count, uniqueness, authority fields and selected projection semantics;
- `tools/runtime_surface_contract.py` verifies the 30-operation ceiling.

Not found:
- a machine-readable `compact_eligible` criterion;
- a generator that derives the selected 30 operations from the native registry;
- an exhaustive proof that every current native capability either belongs or does not belong under a declared eligibility law.

Verdict: the review is correct.

**Current compact membership is curated and tested, not derived.**

This is acceptable for the current compatibility surface because the Runtime explicitly states transport is not architecture authority and no automatic selection is claimed. It becomes a schema-branch gate when the compact/compositional projection is redesigned.

`COMPACT_COUNT_CORRECT != COMPACT_MEMBERSHIP_DERIVED`.

## 5. Legacy `memory.*` coexistence

Verified current surface:
- canonical UCM: **31 `ucm.*` operations**;
- legacy compatibility: **8 `memory.*` operations**;
- both operate over the same authoritative user-continuity store.

Search across current source/docs found compatibility wording but no explicit sunset date, version, usage threshold, removal criterion, or deprecation clock for the eight legacy operations.

Verdict: the review is correct.

This is not presently a duplicate truth store or architecture split, because both APIs project one authoritative ledger. It is a **migration-governance debt** that should be resolved on the schema/migration branch before compatibility becomes permanent by inertia.

`COMPATIBILITY_PROJECTION != SECOND_TRUTH_PLANE`.
`MIGRATION_STATE_WITHOUT_EXIT_CRITERION != CLOSED_MIGRATION`.

## 6. RES / UCM / DTS authority separation

### UCM — mechanism enforced

Verified:
- `decision_can_be_project_authority(...) -> False`;
- `collaboration_can_widen_authority(...) -> False`;
- UCM validators enforce authority/currentness fields independently of descriptive tags;
- ICF ingress requires owning-plane live verification before consequential use of project/runtime/deployment assertions.

`UCM != PROJECT_AUTHORITY` is mechanically embodied.

### RES — mechanism enforced

Verified independently of `effect_traits`:
- RES addenda reject any `authority_effect` other than `NONE` with `RES_AUTHORITY_FIREWALL`;
- consolidated RES snapshot validation requires the explicit `RES_CONTENT != GOVERNING_DOCTRINE` firewall;
- missing/violated firewall fails validation;
- research-handoff readiness is derived from current registered/project protocol state and does not grant mutation authority.

Therefore the reviewer's uncertainty from the tool-card trait alone is understandable, but the Runtime implementation is stronger than the card makes visible.

### DTS — structural/protocol enforcement

Verified:
- `DESIGN_THREAD_STREAM` is a distinct `ContinuityKind`;
- context rehydration classifies DTS as `history`, while RES is `epistemic`;
- protocol continuity records retain their typed kind;
- direct `record_promotion(target_type="continuity", ...)` is rejected because promotion targets are restricted to `claim | artifact`;
- executable probe recorded a DTS continuity item and direct promotion failed with `ProtocolValidationError: target_type must be claim or artifact`.

DTS does not have a RES-style named `DTS_AUTHORITY_FIREWALL` validator, but its continuity record is not itself a promotable authority target. Its separation is structural/protocol-level rather than a free-form trait assertion.

Verdict:

`LIVE_SHADOW != DTS != RES != UCM` is materially embodied, though the current tool-card effect metadata does not communicate the enforcement provenance clearly enough for a future generic planner.

## 7. Low-level ICF currentness defect

Current source before this candidate had two ICF layers:
- top-level `continuity.ingress.rehydrate` correctly binds exact ICF-CS v1.2 authority bytes;
- low-level `rehydrate_context()` returned machine-readable `icf_cs.version = "1.0"`.

An existing regression explicitly expected the stale `1.0` value.

This is a real currentness/truth-surface defect, not a schema redesign issue.

Candidate repair:
- low-level response now reports `icf_cs.version = "1.2"`;
- the existing rehydration regression is updated to require v1.2.

`LOW_LEVEL_PROJECTION_VERSION != HISTORICAL_IMPLEMENTATION_VERSION`.

## 8. GitHub current-surface audit

Current public surfaces that are substantially current at `9be7ad6...`:
- `CURRENT_INGRESS.md`;
- current portions of `README.md` / `CHANGELOG.md` / `docs/EXTERNAL_EVALUATION.md`;
- `handoff/current/ICF_CS_CURRENT.md`;
- substrate durability/package report.

Materially stale or contradictory current-facing surfaces found:
- `README.md` current-source subsection still named `d926e20...` rather than current substrate feature `673e3b1...`;
- `handoff/current/COMMANDERS_INTENT_CURRENT.md` header still says current as of 2026-09-07 and contains a present-tense v1.1 ICF section;
- `handoff/current/CURRENT_CANONICAL_SOP_POINTER.md` declares ICF-CS v1.1 active while `ICF_CS_CURRENT.md` correctly says v1.2;
- unversioned `handoff/current/ICF_CS_CLAIM_CEILING.md` is still v1.0;
- `CURRENT_STATE.md`, `NEXT_STEPS.md`, `DOCTRINE_SNAPSHOT.md`, `REVISIT_LEDGER.md`, `TRACE_MATRIX.md`, `LIVE_SHADOW.md`, and `DESIGN_THREAD_STREAM.md` contain valid history but have no current `9be7ad6/673e3b1` precedence block;
- `GIT_PUBLICATION_CURRENT.md`, `SERVER_THREAD_HANDOFF_CURRENT.md`, and `NEW_THREAD_HANDOFF_PROMPT_CURRENT.md` still terminate on older 116-tool / 2026-09-08 state;
- `RUNTIME_OBE_SKILLS_DUALITY.md` still says ordinary `expected_contract_digest` enforcement does not exist, although it is now implemented and tested;
- `SNAPSHOT_MANIFEST_SHA256.json` top-level metadata still identifies the `fb89bb1...` era and an obsolete next step despite containing hashes for newer individual files.

These are recovery/currentness defects because the filenames and headers advertise present-tense use.

Dated historical evidence/qualification files are intentionally left unchanged.

## 9. Future schema branch gates from the supplied design review

These are now recorded as **separate branch prerequisites**, not current-main architecture work:

1. **Effect split before effect-aware automatic composition.** Closed/enforced predicates distinct from descriptive annotations.
2. **Dataflow references before planner complexity.** `$A.commit_sha`-style server-side references should avoid model round-trip for deterministic outputs.
3. **`CAPABILITY_LEASE != CAPABILITY_GRANT`.** Discovery/currentness leases must not become sticky authorization prerequisites.
4. **Static cost before `compose`/`execute`.** A plan whose cost bound cannot be computed must not auto-execute.
5. **Continuation currentness.** Every preserved node requires a currentness witness; resume must revalidate or re-execute stale nodes. `INGRESS_START_CURRENT != INGRESS_END_CURRENT` applies directly.
6. **Compact eligibility.** Declare the criterion and derive/verify membership rather than preserving a magic hand-curated 30 forever.
7. **Legacy UCM compatibility exit.** Give `memory.*` an explicit deprecation/sunset criterion before steady-state schema composition.
8. **Observe escape hatch.** If a uniform resource algebra cannot represent a resource, the escape hatch must be explicit and bounded rather than an ad-hoc `ioctl` analogue.
9. **Hedged reads should be delayed/pressure-aware, not fan-out-all by default.**
10. **Goal mode last.** Deterministic compose/currentness/cost semantics must be proven first.

None of these gates are treated as already-implemented server features by this audit.

## 10. Live-promotion gate

Architecture closure by itself is not enough to promote live.

Before live restart, current source must first satisfy:
- low-level ICF currentness repair qualified/published;
- all current GitHub recovery/control surfaces reconciled to the current feature/front-door truth;
- current snapshot manifest rebound to those bytes;
- fresh full source qualification after reconciliation;
- no schema-branch work merged accidentally;
- source/live dependency and launcher identity checked before replacement;
- restart followed by consequence readback of source tool count, current ICF ingress, execution capacity, dependencies, scheduler/watcher, HUD/observability and real async concurrency.

At audit time, live promotion is therefore **NO-GO PENDING CURRENTNESS RECONCILIATION**, not because a new core architecture is required.

## 11. Final audit classification

- **Core Runtime architecture:** CONVERGED AT CURRENT CLAIM CEILING.
- **Effect-trait field:** MIXED DESCRIPTIVE/ENFORCED SEMANTICS; CURRENTLY SAFE FROM AUTOMATIC EFFECT SCHEDULING BECAUSE NO SUCH GENERIC SCHEDULER EXISTS; HARD GATE FOR SCHEMA/COMPOSE BRANCH.
- **Compact 30:** CURATED + STRONGLY TESTED; NOT DERIVED; SCHEMA-BRANCH GATE.
- **Legacy memory compatibility:** ONE STORE / TWO API PROJECTIONS; NO SUNSET CLOCK; MIGRATION-BRANCH DEBT.
- **RES authority boundary:** MECHANISM-ENFORCED.
- **DTS authority boundary:** TYPED/STRUCTURAL + DIRECT CONTINUITY PROMOTION REJECTED; NO SEPARATE NAMED DTS FIREWALL.
- **UCM authority boundary:** MECHANISM-ENFORCED.
- **GitHub current surfaces:** NOT YET FULLY RECONCILED AT AUDIT START.
- **Live promotion:** BLOCKED ONLY UNTIL CURRENTNESS/TRUTH SURFACE REPAIR IS QUALIFIED AND PUBLISHED.

## 12. Detached qualification of the earned Runtime fix

- focused ICF/currentness: **32/32 PASS**;
- complete Runtime: **769 collected / 767 passed / 2 skipped / 0 failed**;
- no effect-trait type split, compact-schema redesign, planner/compose machinery, or memory API removal was introduced.

Canonical source reproduced the same result before publication:
- focused ICF/currentness: **32/32 PASS**;
- complete Runtime: **769 collected / 767 passed / 2 skipped / 0 failed**.
