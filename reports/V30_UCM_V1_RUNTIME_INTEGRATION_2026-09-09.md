# V30 User Continuity System v1.0 Runtime Integration — 2026-09-09

Status: **ENGINEERING FEATURE PUBLISHED / REMOTE-VERIFIED / LIVE UNCHANGED**

Base server HEAD: `36b146eef72980638fa5d438af3fb36cfaf999a6`

Donor neutral release:
- `USER_CONTINUITY_SYSTEM_V1_0_2026-09-09.zip`
- bytes: `60620`
- SHA-256: `055a25fd8c02856d2a875aadc714dfa4ff49c0edeb0e63dd4d67415849fd5909`

Donor private release:
- `PRIVATE_USER_CONTINUITY_INSTANCE_V1_0_2026-09-09.zip`
- bytes: `388252`
- SHA-256: `997d09e0691526cc5924e22fb5b5557a0de91b73c474d2261c093c4b4eb1a731`

Authority effect: **NONE**. UCM is user-owned/global continuity and remains explicitly `not_project_authority`, `not_runtime_truth`, and `not_doctrine_authority`.

No private user values are embedded in source code, tests, reports, qualification artifacts, or Git. Private-package engineering uses only structural counts, schemas, hashes, ingress measurements, verifier outputs, and synthetic substitutes.

## 1. Donor qualification replay

Both detached receipts matched their uploaded archive identities.

Fresh clean-extraction replay of the neutral release:
- UCS semantics: **66/66 PASS**;
- recovered mechanisms: **25/25 PASS**;
- hostile base: **31/31 REJECTED**;
- hostile recovered: **17/17 REJECTED**.

Fresh clean-extraction replay of the private release:
- private verifier: **PASS**;
- private hostile: **11/11 REJECTED**;
- facts: 683;
- donor events: 683;
- identities: 10;
- referents: 12;
- decisions: 10;
- fresh-instance ingress: 7,251 bytes;
- required 12,000-byte budget;
- 4,749 bytes actual headroom;
- required minimum headroom: 2,000 bytes.

Independent JSON-schema replay over the actual private normalized release:
- facts: **683/683 valid**;
- identities: **10/10 valid**;
- referents: **12/12 valid**;
- decisions: **10/10 valid**;
- donor events: **683/683 valid**;
- control state: **1/1 valid**;
- collaboration contract: **1/1 valid**;
- memory candidates: 0.

Server-side structural audit receipt (no private values):
`quarantine/ucm_dyno/UCM_PRIVATE_RELEASE_STRUCTURAL_AUDIT.json`
SHA-256: `a52ffd23736dc1710990f4b3d070d35e8422f6e7cb7905e8f3a3e197f1d12a11`.

## 2. Composition-before-invention result

The previous Runtime memory layer was not a trivial stub. It already provided strong substrate mechanics:

- append-only SHA-256 hash-chained event ledger;
- cross-process profile locks;
- idempotency keys + semantic request fingerprints;
- content-addressed snapshot objects;
- current snapshot manifest;
- optional expected-head-hash CAS;
- supersession and verification evidence;
- forget-request tombstones;
- bounded reads/search;
- hydration priority and revalidation hazard reporting;
- authority trait `not_project_authority`.

Therefore UCS v1.0 does **not** earn another persistence backend.

The canonical design is:

```text
existing user_continuity_store
        |
        | remains the one authoritative Runtime user-continuity store
        |
        +-- legacy memory.* compatibility API
        |
        +-- canonical ucm.* v1 semantic/API contract
```

`BACKEND_REPRESENTATION != CONSUMER_CONTRACT`.

## 3. Pre-implementation gap probe

Untouched source at `36b146e...` exposed:
- 126 total native tools;
- eight `memory.*` operations;
- backend schema `pcmmad.user-continuity-ledger.v1.1`;
- old core budget 32 KiB;
- optional head-hash CAS only;
- descriptive `PROJECT_STATE` class still drove live-verification behavior;
- no canonical identity/referent/decision/candidate/control/source-coverage surfaces;
- no ten-surface UCM fresh-instance ingress contract;
- no canonical UCM failure taxonomy;
- no bounded adaptive context compiler under the neutral v1 contract;
- no administrative lossless private-release importer.

Before-probe SHA:
`9e4495df016f91015863a4ee285483ea5b391f72452b0139b96cd120c3422bd8`.

## 4. Canonical server-native UCM v1 API

The isolated candidate adds the full neutral **31-operation** contract under the existing `memory` capability category.

Read:
- `ucm.describe`
- `ucm.head`
- `ucm.read_core`
- `ucm.read_sections`
- `ucm.search`
- `ucm.events_tail`
- `ucm.get_fact`
- `ucm.resolve_identity`
- `ucm.resolve_referent`
- `ucm.verification_debt`
- `ucm.read_decisions`
- `ucm.read_control_state`
- `ucm.memory_candidates`
- `ucm.compile_context_packet`
- `ucm.source_manifest`

Write:
- `ucm.add`
- `ucm.update`
- `ucm.supersede`
- `ucm.verify`
- `ucm.conflict`
- `ucm.retire`
- `ucm.rediscover`
- `ucm.forget_request`
- `ucm.materialize`
- `ucm.lock`
- `ucm.unlock`
- `ucm.session_reset`
- `ucm.decision_add`
- `ucm.decision_supersede`
- `ucm.memory_candidate_confirm`

Export:
- `ucm.export_filtered`

Legacy eight `memory.*` operations remain present and continue using the same ledger.

Candidate source registry: **157 tools**.

No new capability family, compact action schema operation, database, scheduler, daemon, project-authority plane, Runtime-truth plane, or doctrine-authority plane was created.

All canonical UCM capabilities expose:
- `user_owned_continuity`;
- `not_project_authority`;
- `not_runtime_truth`;
- `not_doctrine_authority`.

Mutating `ucm.*` tools remain subject to normal Runtime approval policy. `DIRECT_USER_AUTHORIZED` UCM write posture never bypasses unrelated external-effect/tool authorization.

## 5. Fact semantics

UCS v1 facts keep orthogonal components:
- stable fact key;
- value;
- descriptive tags;
- lifecycle;
- authority target/source role;
- currentness;
- verification requirement/result/reference;
- temporal identity;
- provenance + independence group;
- sensitivity;
- export class;
- hydration groups;
- relations;
- optional assistant utility.

The Runtime now enforces:

`DESCRIPTIVE_CLASS != BEHAVIORAL_POLICY`.

A descriptive tag such as `PROJECT_STATE` cannot itself force or satisfy verification. Project/Runtime/deployment continuity instead requires explicit `verification.requirement=REQUIRED`; a fact is usable as current only when `verified_live=true` and an exact `verification_ref` exists.

`VERIFIER_AVAILABLE != ASSERTION_VERIFIED`.

Generic metadata update cannot forge currentness or verification. Material fact value/authority/lifecycle/verification/currentness changes require dedicated semantic transitions.

Other preserved laws:
- `RECORDED_AT != ASSERTED_AT != OBSERVED_AT`;
- `TWO_REPORTERS_AGREEING != INDEPENDENT_CONFIRMATION`;
- `HIGH_UTILITY != HIGH_AUTHORITY`;
- `HYDRATION_PRIORITY != TRUTH_PRIORITY`.

## 6. Identity, referent, decisions, candidate queue, user controls

First-class identity resolution uses:
- identity kind;
- intended use;
- scope;
- status;
- explicit precedence.

`ONE_PERSON != ONE_NAME_STRING`.

Referent resolution similarly uses term/scope/status/precedence and preserves historical/superseded meanings.

Decision history is first-class and retains stable IDs, rationale, evidence roots, alternatives, reopening triggers and related facts. It remains user-continuity context, never project authority.

AI-observed memory candidates are constrained to:
- `source_role=INFERENCE`;
- `write_posture=PROPOSE_ONLY`;
- `PENDING_USER_CONFIRMATION` until user-confirmed/rejected.

`AI_NOTICES_PATTERN != USER_CONFIRMED_FACT`.

Manual locks control memory admission/adaptive hydration/collaboration adaptation without granting tool/project authority.

`MANUAL_LOCK_OVERRIDES_ADAPTIVE_BEHAVIOR`.

Session reset increments session generation but does not erase durable facts, provenance, decision history, source evidence or append-only event history.

`SESSION_RESET != DURABLE_MEMORY_DELETE`.

Forget remains a separate direct-user-authorized `FORGET_REQUEST` transition.

## 7. Canonical writes and currentness

Every canonical semantic write requires both:
- `expected_head_seq`;
- `expected_head_hash`.

They bind the one authoritative ledger head before consequence.

Idempotent response-loss retry is checked before stale-CAS failure so the exact already-landed consequence can be returned without replaying mutation.

All successful canonical writes perform authoritative post-write head readback and return the actual event sequence/hash.

`CONSEQUENCE_READBACK > TRANSPORT_STATUS`.

## 8. Fresh-instance ingress

UCS v1 server ingress requires exactly these ten logical surfaces:
- `SYSTEM_DESCRIPTOR`
- `USER_STORE_HEAD`
- `CORE_SNAPSHOT`
- `IDENTITY_INDEX`
- `COLLABORATION_CONTRACT`
- `REFERENT_INDEX`
- `DECISION_INDEX`
- `CONTROL_STATE`
- `VERIFICATION_DEBT`
- `CANDIDATE_QUEUE_HEAD`

Core budget:
- maximum: **12,000 bytes**;
- minimum required unused headroom: **2,000 bytes**;
- system descriptor excluded from user-core budget exactly as the donor contract specifies.

Failure taxonomy:
- omitted required UCM -> `USER_CONTINUITY_INCOMPLETE`;
- snapshot/ledger mismatch -> `UCM_CURRENTNESS_FAILURE`;
- provenance failure -> `UCM_PROVENANCE_FAILURE`;
- core/headroom violation -> `UCM_CORE_BUDGET_EXCEEDED`;
- forbidden authority -> `AUTHORITY_FIREWALL`.

Canonical writes preflight the projected ingress core **before authoritative append**. A write that would exceed the budget or consume mandatory headroom produces `UCM_CORE_BUDGET_EXCEEDED` with zero new authoritative event.

## 9. Hydration / retrieval

`ucm.read_core` and `ucm.read_sections` explicitly distinguish:
- OFFERED;
- HYDRATED;
- CONSUMED;
- USED_IN_DECISION.

Read-only hydration reports offered/hydrated counts but leaves consumed/decision-use at zero.

Lazy project/personal-sensitive/deployment/historical/task-specific groups are not loaded into the required core merely because they exist.

The bounded context compiler can include current facts, decision history, contradictions, verification debt, referents, collaboration state, recent event tail and source pointers under a caller budget.

Retrieval strategy order is bounded/reversible:
1. exact key;
2. snapshot shard;
3. lexical/structured;
4. semantic locator;
5. source fallback.

Repeated failure advances strategy rather than repeating an identical search.

`SEARCH_HIT != CLAIM_SUPPORT`.
`RETRIEVAL_RELEVANCE != EVIDENTIARY_SUPPORT`.
`VECTOR_MATCH != TRUTH`.
`RETRIEVAL_PACKET != AUTHORITY`.

## 10. Source evidence and absence semantics

Original imported source bytes are preserved content-addressed.

`NORMALIZED_MEMORY != ORIGINAL_SOURCE_BYTES`.

Source manifests keep source instance, artifact hash/bytes, coverage, policy absences and source role. Missing categories in one platform source are coverage metadata, not contrary evidence.

`ABSENCE_IN_SOURCE != NEGATION`.
`SOURCE_POLICY_GAP != USER_FACT_CONFLICT`.
`IMPORT_COMPLETENESS != CROSS_SOURCE_COMPLETENESS`.

The private release also contains 661 normalized source assertions distinct from its five source-manifest entries. The first server adapter incorrectly conflated those two surfaces; the migration audit caught and repaired that distinction before publication.

## 11. Derived-state storage amplification defect

A private-scale synthetic campaign intentionally reproduced the released private instance's logical magnitude without using private content:
- 683 facts;
- 10 identities;
- 12 referents;
- 10 decisions;
- one collaboration contract;
- 716 canonical writes.

First run on the old backend snapshot policy:
- authoritative ledger: **1,491,882 bytes**;
- total profile: **452,347,608 bytes**;
- immutable snapshot manifests retained: **716**;
- snapshot objects retained: **2,927**;
- ingress: 7,172 bytes / 4,828 bytes headroom.

The blow-up was derived snapshot/cache history, not authoritative history. UCS explicitly defines the event ledger as history and snapshots as rebuildable folds.

Repair:
- canonical `ucm.*` writes retain only the latest two derived snapshot manifests and their referenced current objects;
- append-only ledger remains untouched;
- legacy `memory.*` behavior is unchanged for compatibility.

Identical rerun after repair:
- authoritative ledger: **1,491,882 bytes**;
- total profile: **3,982,992 bytes**;
- snapshot manifests: **2**;
- snapshot objects: **14**;
- ingress unchanged at **7,172 bytes / 4,828 bytes headroom**;
- reduction: ~**113x** total derived/profile footprint.

Final scale receipt SHA:
`55b03e2bf4f4eb7e6665bdaaea499b462079c5ed7fd68d858cbd42c71627313d`.

This earned:

`APPEND_ONLY_HISTORY != UNBOUNDED_DERIVED_SNAPSHOT_HISTORY`.

## 12. Private release migration machinery

The private release is **not** embedded in Runtime source.

Administrative helper:
`tools/import_private_ucm_v1.py`

It is intentionally not a model-facing native capability and does not expand the neutral 31-operation contract.

Verify-only checks:
- exact qualified private ZIP bytes/SHA;
- optional detached receipt binding;
- ZIP traversal/symlink safety;
- CRC;
- exact manifest members/bytes/SHA;
- donor event-chain sequence/prev-hash/event-hash;
- donor USER_STORE_HEAD binding;
- donor ingress surface/budget binding;
- normalized fact/identity/referent/decision/collaboration/control/candidate schemas;
- distinct normalized source assertions;
- content-addressed source original/blob equality;
- migration expectations;
- private ingress qualification.

Import mode additionally:
- requires an empty target Runtime profile;
- preserves the sealed private release by content hash;
- preserves the original donor event JSONL as immutable source evidence;
- preserves all original source blobs content-addressed;
- creates server-native UCM records/events under the existing authoritative Runtime ledger;
- builds one bounded current derived snapshot;
- requires post-import fresh-instance ingress PASS;
- returns only structural counts/hashes/paths and never emits private record values.

Critical lineage law:

`DONOR_EVENT_HASH != SERVER_NATIVE_EVENT_HASH_AFTER_MIGRATION`.

The donor event chain remains evidence of the sealed source instance. Server-native events have new sequence/hash lineage and do not counterfeit donor hashes.

Clean-room synthetic migration suite: **6/6 PASS**, including manifest-resigned tamper, event-chain tamper, non-empty-target rejection and lossless evidence/readback behavior.

Actual private user content was not transferred into the dev-machine Runtime during source engineering because the chat upload `/mnt/data` plane is not mounted into the Windows server Runtime. The migration tool is ready for a server-local private ZIP path after source promotion/authorization.

## 13. Candidate qualification

Canonical/hostile UCM + legacy-memory + migration focused suite:
- **130/130 PASS**.

Complete detached Runtime on final candidate state:
- collected: **661**;
- passed: **660**;
- failed: **0**;
- conditional skip: **1**;
- Python 3.12.10.

Canonical source reproduced the same candidate:
- Python compile: PASS;
- canonical UCM + hostile + legacy-memory + migration focused suite: **130/130 PASS**;
- full Runtime: **661 collected / 660 passed / 0 failed / 1 conditional skip**;
- source registry: **157 tools**, including 31 `ucm.*` + 8 legacy `memory.*`, both in the existing `memory` category.

Post-implementation probe:
- total source tools: **157**;
- canonical UCM tools: **31**;
- legacy memory tools: **8**;
- one authoritative store;
- no new capability family/database/daemon/authority plane.

Post-probe SHA:
`91a71b87ba0a7f434c5f424f2b32048cc80dc14ef4763011f3b0028a4fba633b`.

## 14. Implementation defects caught before source publication

The campaign caught and repaired:

1. `DECISION_ADD` initially entered the update path rather than new-record append.
2. candidate confirmation initially inherited the `PROPOSE_ONLY` creation rule instead of requiring direct-user-authorized confirmation.
3. private migration initially conflated 661 normalized source assertions with the five source-manifest entries.
4. migration helper initially bound stale/nonexistent backend event-constructor names/arguments; clean-room importer execution exposed and repaired them.
5. derived snapshots amplified a 1.49 MB ledger into ~452 MB of profile state at realistic UCM scale; bounded derived-cache retention reduced it to ~3.98 MB without changing authoritative history or ingress.

Preserve:

`EXPECTED_FAILURE != ANY_FAILURE`.
`IMPLEMENTATION_PRESENT != END_TO_END_REGISTERED_AND_EXECUTED`.
`NORMALIZED_SOURCE_ASSERTION != SOURCE_MANIFEST_ENTRY`.
`APPEND_ONLY_HISTORY != UNBOUNDED_DERIVED_SNAPSHOT_HISTORY`.

## 15. ICF-CS successor implications

The completed donor explicitly requires the next ICF-CS continuity contract to teach a fresh instance how to:
1. discover current ICF-CS;
2. discover RES as project/research epistemic continuity;
3. discover UCS/UCM as user-owned global continuity;
4. read UCM descriptor/head;
5. verify snapshot/head currentness;
6. hydrate the bounded ten-surface UCM core;
7. lazily hydrate project/personal/deployment sections only when relevant;
8. keep `RES != UCM`;
9. verify project/runtime/deployment assertions through their owning planes;
10. preserve authority firewalls before mutation.

The Runtime mechanism is now stable enough for one coherent RES+UCM ICF-CS successor rather than the knowingly short-lived RES-only intermediate previously avoided.

`RUNTIME_CAPABILITY_TO_ENFORCE_NEW_OBLIGATION != AUTHORITY_TO_REVISE_RELEASED_NORMATIVE_CONTRACT`.

The ICF-CS successor must be separately qualified and released on the doctrine authority plane after canonical source publication of this UCM mechanism.

## 16. Claim ceiling

Earned in isolated engineering:
- neutral donor release and private release identities/replays independently verified;
- canonical UCM semantics compose over the existing Runtime store;
- full 31-operation neutral server contract exists in the existing memory family;
- legacy memory API remains compatible;
- private-release migration has a safe verify/import path without private source embedding;
- realistic private-scale ingress/storage pressure is green after repairing derived-state amplification;
- complete detached Runtime is green.

Not yet earned at this report stage:
- canonical-source publication;
- GitHub publication/readback;
- actual private-instance import into live Runtime;
- live Runtime UCM availability;
- ICF-CS successor qualification/release;
- claim that UCM facts become project/runtime/doctrine authority.

## Feature publication readback

Engineering feature: `f01418c546e449acb3f98f4b64f5b4a7ad3f0960`
Tree: `606017f70004a17063515d82f35578deff869efc`
Parent: `36b146eef72980638fa5d438af3fb36cfaf999a6`

`origin/main` was independently read back at the exact feature after push. Later ICF-CS v1.2 fresh-ingress work composes this published UCM mechanism; live Runtime/private-instance import remain separate.
