# V30 Schema v11 Capability Microkernel — 2026-09-10

Status: **CANONICAL SOURCE QUALIFIED / PUBLICATION PENDING**

Base Git/source head: `92010b57dfc275dd6f9753121cd8def98792ed41`

Scope: final Assistant-facing server schema redesign and its thin Runtime projection only. No live Runtime reload, no private UCM import, no ICF-CS normative revision, and no product-side ChatGPT Action installation are claimed.

## 1. Result

The 30-operation v10.3 Assistant-facing OpenAPI surface has a qualified v11.0 successor candidate built as an **8-operation capability microkernel** over the same 158-capability native Runtime.

v10.3 compatibility schema remains present and functional.

v11.0 candidate:
- path: `baseline/pcmmad_receiver/pcmmad_lab_action_schema_v11_0_capability_microkernel_8.json`;
- operations: **8**;
- bytes: **33,844**;
- SHA-256: `ee62b261d6e5518b585faccd4af21a42d9b7bd6b3dc63f8af0e1242ef9fb9010`;
- size reduction versus v10.3: ~**73.7%**.

v10.3 retained compatibility identity:
- operations: **30**;
- bytes: **128,843**;
- SHA-256: `132dff5967d7b45278d63da11e4ab87a72bd3fbd0507af3b652ffd34ee88787f`.

The 8 external primitives are:

1. `orientCapabilities`
2. `invokeCapability`
3. `flowCapabilities`
4. `composePlan`
5. `executePlan`
6. `observeRuntime`
7. `resumeContinuation`
8. `transferData`

The external schema is a bootloader/control algebra into the live native capability graph. It is not a second Runtime ontology or authority plane.

`SCHEMA_OPERATION_COUNT != SERVER_CAPABILITY_COUNT`.

## 2. Why the build order changed

External review correctly identified a sequencing risk: effect-aware automatic parallelism is unsafe if effect declarations are merely descriptive or stale. The current 158-capability catalog contains more than 200 distinct free-form descriptive `effect_traits`; they are useful observability metadata but are not a scheduler-grade algebra.

The redesign therefore follows this order:

1. server-side dataflow references on the existing batch plane;
2. bounded/unified observation;
3. closed scheduler-effect profile with fail-closed currentness;
4. deterministic compose with static admission cost;
5. execute under current native/effect contracts;
6. continuation semantics with explicit freshness/recovery rules;
7. goal-planning mode deferred.

`DESCRIPTIVE_EFFECT_TRAITS != SCHEDULER_AUTHORITY`.

`DECLARED_EFFECT_CLASS != VERIFIED_EFFECT_TRUTH`.

## 3. `flow`: dataflow first, no new scheduler

The existing `/lab/batch` plane now supports exact backward-only payload references:

`{"$ref":"prior_step.result.field"}`

The reference moves the exact prior value server-side; it does not round-trip through model context.

Runtime rules:
- step IDs are bounded and unique;
- references are backward-only;
- unresolved references fail typed;
- authority-envelope references are forbidden;
- resolved step payload is capped at 65,536 bytes;
- dataflow-ref batches execute sequentially;
- legacy no-ref batch parallelism remains backward-compatible for v10 clients.

The v11 Assistant projection is intentionally narrower than the legacy batch route:
- max **12** steps;
- `parallelism` is exactly **1**;
- every step requires `expected_contract_digest`;
- authority remains a separate top-level step field;
- larger workflows should use statically cost-admitted compose/execute.

`FLOW_DATA_REF != AUTHORITY_REF`.

`V11_FLOW != LEGACY_PARALLEL_BATCH`.

## 4. `orient` and capability leases

`orient` performs task-conditioned discovery over the live native capability catalog and returns a bounded lease containing exact capability contract digests.

A lease is advisory narrowing/currentness context only:

`CAPABILITY_LEASE != CAPABILITY_GRANT`.

Properties:
- `authority_effect = NONE`;
- a lease is optional for `invoke` and `compose`;
- bare capability + exact contract digest remains valid for `invoke`;
- if a lease is supplied, capability/project context must remain inside that lease;
- lease self-consistency cannot bypass native approval or project mutation authority;
- catalog/capability drift stales the lease.

The lease deliberately is not cryptographic permission. Native Runtime authority remains the only permission plane.

## 5. `invoke`: deliberate escape hatch

`invoke` is the exact single-capability fast path and deliberate uniform-algebra escape hatch.

It requires either:
- an explicit current `expected_contract_digest`; or
- a current advisory lease containing the capability.

Arguments and authority are separate. Native dispatch still owns:
- availability/currentness;
- approval;
- project mutation authority;
- schema validation;
- consequence semantics.

The adapter does not mint or infer authority.

`UNIFORM_ALGEBRA_REQUIRES_EXPLICIT_ESCAPE_HATCH`.

## 6. Closed scheduler-effect profile

New Runtime artifact:
`baseline/pcmmad_receiver/scheduler_effect_profile_v1.json`

Current qualified identity before final source seal:
- bytes: **124,319**;
- SHA-256: `a7ee841edb47010978a13d884e899520c6bd6e22d2907a9ba4bbb169f8e58ce3`;
- capability catalog digest: `1ac52b95171a2eb4487a1b8c702b0b9bc76f0d7800da62e6af7b360bb470b99f`.

The profile exactly covers all **158** native capabilities and is bound to every native `contract_digest`.

Closed vocabularies include:
- effect kind;
- schedule class;
- resume-replay class;
- retry class;
- freshness classes.

The profile explicitly records:
- `descriptive_effect_traits_are_scheduler_authority = false`;
- `declared_effect_class_is_effect_truth = false`.

Production v11.0 intentionally has:
- effect-truth verified capabilities: **0**;
- automatically parallel capabilities: **0**;
- automatically replayable completed-read capabilities: **0**.

This is not a missing feature. It is the conservative qualified starting point.

An unwitnessed capability receives:
- verified effect kind `UNVERIFIED`;
- schedule class `SERIAL`;
- resume class `RECOMPOSE_REQUIRED`;
- all currentness planes conservatively possible;
- worst-case static admission cost **10 units**.

An exact-digest effect-truth witness may later verify the declared effect class and lower its static cost. That witness **still does not** earn parallelism or continuation replay. Those require separate exact-digest witnesses.

Parallel and resume-replay witnesses are rejected unless the same capability/contract also has verified read effect truth.

`EFFECT_TRUTH_VERIFIED != PARALLELISM_VERIFIED`.

`EFFECT_TRUTH_VERIFIED != RESUME_REPLAY_VERIFIED`.

## 7. Static plan cost

`compose` is deterministic and node-explicit. It does not turn natural-language `goal` text into executable nodes.

`GOAL_TEXT != EXECUTABLE_PLAN`.

Every sealed plan binds:
- native capability contract digests;
- scheduler-effect profile digest;
- capability catalog digest;
- closed effect snapshot per node;
- static admission cost;
- caller cost ceiling;
- resolved-argument ceiling;
- dependency stages;
- assertions;
- authority effect `NONE`.

Static admission cost is exact/computable under the closed profile but **is not a wall-time, CPU, or money SLA**.

`STATIC_PLAN_COST != WALL_TIME_SLA`.

Current bounds:
- max plan nodes: 32;
- default max static cost: 120;
- absolute max static cost: 320;
- unwitnessed effect cost: 10;
- max sealed plan bytes: 65,536.

Because all production v11.0 capabilities are currently effect-truth-unverified, the default cost admits up to roughly 12 ordinary nodes and explicit max cost can admit the full 32-node plan ceiling. Future truth witnesses can reduce individual costs without weakening the unknown default.

## 8. Deterministic sealing

An early candidate included `created_at` inside the sealed plan, contradicting the claim that identical compose inputs produce identical plan digests.

Repair:
- temporal metadata is outside sealed plan identity as `composed_at`;
- identical compose inputs produce identical plan bytes/digest;
- goal text may change sealed metadata/digest but does not change executable nodes/stages/effects.

All content digests use sorted-key finite canonical JSON, so semantic identity does not depend on Python dictionary insertion order.

`SEMANTIC_HASH != PYTHON_INSERTION_ORDER`.

## 9. Plan dataflow amplification bound

A compact plan can reference a large prior result. Without another gate, a 30 KB result referenced three times can inflate a tiny sealed plan into a >90 KB downstream native payload.

Repair:
- execution resolves refs immediately before native dispatch;
- resolved node arguments are capped at **65,536 bytes**;
- oversize fails `PLAN_DATAFLOW_ARGUMENT_TOO_LARGE` pre-dispatch;
- the exact ceiling is sealed in the plan and revalidated on execute;
- larger data must travel by existing bounded result handles.

`COMPACT_PLAN != UNBOUNDED_RESOLVED_ARGUMENTS`.

## 10. Execute and scheduler semantics

`execute` revalidates:
- plan digest;
- expected plan digest;
- native capability contracts;
- current scheduler-effect profile;
- catalog identity;
- derived effects;
- static cost;
- resolved-argument ceiling;
- dependency stages.

Automatic parallelism is **only** permitted for nodes whose exact capability contract has:
1. a matching effect-truth witness proving a read effect; and
2. a separate matching parallel-read witness.

Production v11.0 has zero such entries, so plans execute conservatively serially.

Synthetic qualification proves the exact witness mechanism can enable independent read parallelism when earned.

`SPECULATIVE_READ != SPECULATIVE_EFFECT`.

No speculative/hedged execution mode is shipped in v11.0.

## 11. Continuations and currentness

An early prototype preserved completed read results and resumed from them. That would manufacture currentness after an approval delay.

The current law is:

`CONTINUATION != CURRENTNESS`.

Continuation behavior:
- continuation grants no authority;
- resume token is single-use;
- completed evidence is marked stale on resume;
- automatic re-execution of a completed read requires an exact contract-digest resume-replay witness plus verified read effect truth;
- production v11.0 has zero replay witnesses;
- therefore a plan blocked after any completed unwitnessed node returns `BLOCKED_RECOVERY_REQUIRED` with no automatic continuation;
- a plan blocked before prior work may issue a continuation;
- witnessed safe reads, when introduced/tested, are re-executed rather than reused;
- if refreshed data invalidates an old approval challenge, native authority rejects the stale challenge pre-effect and the caller must recompose/re-execute to obtain new authority.

Prior effectful/cache-mutating work is never automatically replayed through a continuation.

## 12. `observe`: bounded resource algebra

`observe` consolidates existing readback planes for:
- leases;
- plans;
- capabilities;
- scheduler effect profile;
- result handles;
- continuations;
- durable execution jobs.

Effect-profile observation is bounded: it reports profile/catalog identity, closed vocabularies, verification counts, and optionally one capability entry rather than dumping the full 124 KB profile.

The v11 Assistant-facing `observe` mode **does not expose full-result materialization**. It exposes bounded:
- auto;
- metadata;
- preview;
- range;
- job status/progress/wait/output.

The lower-level Runtime retains its explicit legacy/internal full-result escape, but v11 does not advertise it.

## 13. Transfer

`transfer` remains an explicit binary boundary and delegates directly to existing transfer-plane capabilities. It does not create new transfer tickets/state or weaken the existing file-object/content-currentness hardening.

## 14. OpenAPI and packaging integrity

The generator copies the existing Runtime authority envelope plus its nested `ProjectMutationAuthority` component. A new local `$ref` verifier caught the initially omitted nested component before qualification.

The generated schema has:
- exactly 8 unique operations;
- no unresolved local component refs;
- deterministic byte generation;
- no authority field inside PlanNode;
- explicit lease non-authority law;
- explicit cost/effect/currentness bounds.

Package embedding:
- canonical modules under `pcmmad_receiver`;
- legacy top-level alias shims for `schema_vnext_runtime` and `scheduler_effect_profile`;
- v11 schema/profile JSON included as package data;
- clean wheel install verifies 158 native capabilities, zero plugin errors, current effect profile, and v11 schema presence.

## 15. Compatibility

v10.3 remains present and its 30-operation contracts/tests remain green. Existing `/lab/dispatch`, `/lab/batch`, result handles, native capabilities, job scheduler, approval authority, project authority, transfer plane, ICF/RES/UCM and Warfort hardening remain the owning mechanisms.

v11 adds seven new thin HTTP routes plus reuses existing `/lab/batch` as the eighth Assistant primitive. It does not duplicate jobs/results/authority/transfer state.

`ADAPTER != AUTHORITY`.

`PLAN_VM != SECOND_JOB_SCHEDULER`.

## 16. Qualification

Focused schema/package/compatibility gate:
- collected: **127 tests**;
- result: PASS.

This gate covers v11 runtime, hostile authority/currentness, closed effect profile, Stage-A dataflow, OpenAPI projection, clean wheel embedding, v10 authority parity, expected contract binding, and batch-result boundedness.

Complete detached Runtime on the original schema candidate:
- collected: **872**;
- passed: **870**;
- skipped: **2**;
- failed: **0**;

Rebased qualification against current source parent `92010b57...`:
- focused schema/package/compatibility gate: **127/127 PASS**;
- complete Runtime: **878 collected / 876 passed / 2 skipped / 0 failed**;
- Python 3.12.10.

Four-worker full-suite burns on the original candidate:
- `loadscope`: **870 passed / 2 skipped / 103 subtests passed**;
- `worksteal`: **870 passed / 2 skipped / 103 subtests passed**.

Rebased current-parent four-worker burns:
- `loadscope`: **876 passed / 2 skipped / 103 subtests passed**;
- `worksteal`: **876 passed / 2 skipped / 103 subtests passed**.

Canonical source independently reproduced the rebased candidate:
- focused schema/package/compatibility gate: **127/127 PASS**;
- complete Runtime: **878 collected / 876 passed / 2 skipped / 0 failed**;
- four-worker `loadscope`: **876 passed / 2 skipped / 103 subtests passed**;
- four-worker `worksteal`: **876 passed / 2 skipped / 103 subtests passed**.

## 17. Deliberately deferred work

v11.0 does **not** ship:
- natural-language goal-to-plan synthesis;
- speculative/hedged read racing;
- any production auto-parallel capability witness;
- any production continuation replay witness;
- replacement/removal of the v10.3 compatibility schema;
- product-side ChatGPT Action configuration changes;
- live Runtime reload/promotion.

These are future optimizations or separate deployment consequences, not hidden incompleteness in the v11.0 control algebra.

## 18. Claim ceiling

Earned in the detached clone:
- compact 8-operation Assistant control algebra can reach the current 158-capability Runtime without flattening all capabilities into OpenAPI operations;
- server-side flow removes common model round trips;
- compose/execute are deterministic, cost-admitted, contract/profile-bound and conservatively serial under unverified effect truth;
- native authority remains separate and cannot be minted by leases/plans/dataflow/continuations;
- continuation currentness no longer depends on cached reads;
- v11 is package-embeddable and v10-compatible;
- complete sequential and parallel Runtime qualification is green.

Not yet earned at this report stage:
- canonical-source publication;
- GitHub remote publication/readback;
- product-side Action schema installation;
- live Runtime promotion;
- any production effect-truth/parallel/replay witness set;
- natural-language planner correctness.
