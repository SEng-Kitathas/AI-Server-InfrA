# V30 ICF-CS v1.2 Fresh-Instance Runtime Embodiment — 2026-09-09

Status: **ENGINEERING FEATURE PUBLISHED / REMOTE-VERIFIED / LIVE UNCHANGED**

Base Runtime HEAD: `f01418c546e449acb3f98f4b64f5b4a7ad3f0960`

Active doctrine binding:
- ICF-CS v1.2 current standard SHA-256: `f966029496fd6e31a76a36a6e967db37ca2147acfa890a880426ae6a7fa79d92`
- ICF-CS v1.2 activation receipt SHA-256: `893409f28ea181c60ca9e3681eb9a1a4d08fa279befac4d679d2cfdb958d7279`
- ICF-CS v1.2 sealed archive SHA-256: `b82803be3ebd37f6ac58fb95beb3df5a043f5167e66b94846419817bbf8d5606`
- detached qualification receipt SHA-256: `59f66d7707508faa4015df86c728302961c0a13e2f4e8655425ce783248cbc7e`
- Rahl continuity activation closure: epoch `42 -> 43`, closure `edef92465daa7e28fb64600d096ad709`, close receipt SHA `ebb10e71fd31ec51a83ed41ec2c98cc027ca3065c98f4a2c22aca34298d0d06f`
- published RES Runtime feature: `8714dd87d2092e0f4c66f261fcf5cee8b75a0798`
- published UCM Runtime feature: `f01418c546e449acb3f98f4b64f5b4a7ad3f0960`

Authority effect: **NONE beyond continuity-process embodiment**. This Runtime change implements the already-qualified/activated ICF-CS v1.2 contract. It does not create or revise doctrine authority.

## 1. Defect exposed after doctrine activation

After ICF-CS v1.2 was qualified and activated, a source audit found the exact machine-embodiment gap the successor was meant to prevent:

- source had first-class RES validation/currentness machinery;
- source had full 31-operation UCS/UCM v1 machinery;
- low-level `project.context.rehydrate` still seeded Live Shadow + DTS but did not seed RES as a current ICF continuity anchor;
- fresh-instance rehydration had no UCM applicability/profile/currentness orchestration at all.

Therefore:

`RES_AND_UCM_CAPABILITIES_PRESENT != FRESH_INSTANCE_INGRESS_EMBODIED`

Updating documentation alone would have been symbolic compliance.

## 2. Runtime composition decision

The low-level project context engine remains useful and compatible. It was not replaced.

A single current normative orchestration capability is added in the existing `continuity` family:

`continuity.ingress.rehydrate`

It composes:

1. exact current ICF-CS v1.2 standard identity;
2. explicit session-mode applicability;
3. required RES currentness/readiness;
4. required UCM profile + bounded ten-surface core currentness;
5. ordinary bounded project-context rehydration;
6. explicit owning-plane verification requirement;
7. live readback requirement before consequential mutation.

No new persistence engine, authority plane, capability family, daemon, scheduler, or compact action operation is introduced.

Candidate native tool count: **158**.

Compact 30-operation transport schema is unchanged; SHA-256 remains `132dff5967d7b45278d63da11e4ab87a72bd3fbd0507af3b652ffd34ee88787f`.

## 3. Explicit session applicability

Runtime has no safe authoritative mapping from an arbitrary request to a user UCM profile. Therefore the orchestrator SHALL NOT guess.

The caller must declare exactly one ICF-CS v1.2 session mode:

- `INTERACTIVE_RESEARCH_USER_SESSION`
- `INTERACTIVE_NONRESEARCH_USER_SESSION`
- `NONUSER_RESEARCH_AUTOMATION`
- `NONUSER_NONRESEARCH_AUTOMATION`

Applicability:

- interactive research user -> RES REQUIRED + UCM REQUIRED;
- interactive nonresearch user -> UCM REQUIRED; RES N/A with basis unless project override requires it;
- non-user research automation -> RES REQUIRED; UCM N/A with basis;
- non-user nonresearch automation -> both may be N/A with explicit basis.

`MISSING != NOT_APPLICABLE`.

A non-user mode that also supplies a UCM profile is rejected as `ICF_CS_APPLICABILITY_CONFLICT`; Runtime does not let callers use contradictory applicability declarations as an ingress bypass.

## 4. Exact ICF-CS currentness

The orchestrator checks the governed project's current standard at:

`state/doctrine_snapshot/INTENT_CONSTRAINT_FRONTIER_CONTINUITY_STANDARD.md`

and requires exact SHA-256:

`f966029496fd6e31a76a36a6e967db37ca2147acfa890a880426ae6a7fa79d92`

Missing or different bytes fail as `ICF_CS_CURRENTNESS_FAILURE` before RES/UCM hydration.

`VERSION_LABEL != CURRENT_AUTHORITY_BYTES`.

## 5. RES embodiment

When RES is required, Runtime calls the existing server-native RES readiness/currentness machinery and fails closed on missing/invalid/stale/unbound RES as:

`HANDOFF_EPISTEMIC_CONTINUITY_INCOMPLETE`.

The low-level context engine also now treats `continuity.research_epistemic_shadow` as an ICF continuity anchor and labels its authority role `epistemic` rather than generic history.

The ordinary `continuity/` candidate path now includes:

- Live Shadow;
- Research Epistemic Shadow;
- Design Thread Stream.

`LIVE_SHADOW != DTS != RES`.

RES remains subject to:

`RES_CONTENT != GOVERNING_DOCTRINE`.

## 6. UCM embodiment

When UCM is required, an explicit `ucm_profile_id` is mandatory. Runtime invokes the canonical UCS/UCM v1 bounded `read_core` contract and preserves its exact failure taxonomy, including:

- `USER_CONTINUITY_INCOMPLETE`;
- `UCM_CURRENTNESS_FAILURE`;
- `UCM_PROVENANCE_FAILURE`;
- `UCM_CORE_BUDGET_EXCEEDED`;
- `AUTHORITY_FIREWALL`.

The fresh-ingress packet does not promote UCM into project/runtime/doctrine authority.

`UCM != PROJECT_AUTHORITY`.
`UCM != RUNTIME_TRUTH`.
`UCM != DOCTRINE_AUTHORITY`.

## 7. Owning-plane verification boundary

A successful continuity packet ends with:

`required_next_gate = OWNING_PLANE_LIVE_VERIFICATION_THEN_LIVE_READBACK_BEFORE_MUTATION`

The orchestrator does not claim that hydrated project/runtime/deployment continuity is live truth merely because the continuity surfaces are current.

`RETRIEVAL_PACKET != AUTHORITY`.
`VERIFIER_AVAILABLE != ASSERTION_VERIFIED`.
`SOURCE_QUALIFIED != LIVE_PROMOTED`.

## 8. Boundedness defect exposed by composition

The first fresh-ingress run exposed a pre-existing context-engine bug unrelated to ICF semantics but directly triggered by the new orchestrator.

`RehydrateRequest(budget_bytes=None)` was normalized to the internal `MAX_REHYDRATE_BUDGET_BYTES` sentinel (`10^15`). `_read_prefix_bounded()` then passed approximately that amount directly into `file.read()`, causing `MemoryError` rather than bounded rehydration.

Repairs:

1. omitted budget (`None`) now uses finite default **40,000 bytes**;
2. explicit `0/-1` still means unbounded overall selection;
3. a single prefix read is capped to actual file size even when overall selection is unbounded.

Earned laws:

`DEFAULT_BUDGET_OMITTED != EXPLICIT_UNBOUNDED`.

`UNBOUNDED_SELECTION_BUDGET != UNBOUNDED_SINGLE_READ_ALLOCATION`.

Two explicit regressions preserve those semantics.

## 9. Handoff authority carrier

The isolated source candidate carries exact current doctrine evidence under `handoff/current/`:

- `INTENT_CONSTRAINT_FRONTIER_CONTINUITY_STANDARD.md` — exact active v1.2 bytes / SHA `f9660294...`;
- `ICF_CS_V1_2_ACTIVATION_RECEIPT_2026-09-09.json`;
- `ICF_CS_V1_2_DETACHED_RELEASE_RECEIPT_2026-09-09.json`;
- `ICF_CS_V1_2_MACHINE.json`;
- `ICF_CS_V1_2_FRESH_INSTANCE_CONTRACT.json`.

`SNAPSHOT_MANIFEST_SHA256.json` is updated to bind those current carrier members. An initial full-suite run correctly failed the handoff manifest integrity test after the standard changed but before its manifest row was updated; the manifest was then repaired and the full suite rerun.

`AUTHORITY_BYTES_CHANGED -> CARRIER_MANIFEST_MUST_CHANGE`.

## 10. Qualification

Dedicated v1.2 fresh-ingress suite: **13/13 PASS**.

Ingress + old ICF + bounded context + RES + UCM + private migration + legacy memory + contract-currentness integration gate:

- passed: **215**;
- conditional skip: **1**;
- failed: **0**.

The old ICF rehydration fixture initially assumed the pre-v1.2 anchor set. It was upgraded to include an explicit RES fixture and `epistemic` authority role rather than weakening the anchor requirement.

Full detached Runtime after handoff-manifest repair and direct boundedness regressions:

- collected: **676**;
- passed: **675**;
- conditional skip: **1**;
- failed: **0**;
- Python 3.12.10.

Canonical source reproduced the final carrier exactly:
- Python compile: PASS;
- current-handoff + v1.2 ingress + old-ICF + budget gate: **37/37 PASS**;
- complete Runtime: **676 collected / 675 passed / 0 failed / 1 conditional skip**;
- native source tool count: **158**;
- current `ICF_CS_CURRENT.md` replaced with compact v1.2 navigation pointer and rebound in handoff manifest.

Whitespace/EOL-aware `git diff --check`: PASS.

## 11. Claim ceiling

This candidate earns at isolated-source depth:

- ICF-CS v1.2 current authority bytes are machine-bound before fresh-instance rehydration;
- RES is now a true rehydration anchor rather than merely a separately available capability;
- UCM applicability/profile/currentness is part of fresh-instance continuity orchestration;
- non-applicability is explicit and mode-grounded;
- bounded project rehydration remains beneath the normative orchestrator;
- the new ingress operation does not change the compact transport schema;
- the pre-existing unbounded-read allocation defect is repaired.

It does not yet earn at this report stage:

- canonical-source publication;
- GitHub publication/readback;
- live Runtime reload;
- actual private UCM import;
- a claim that continuity hydration itself verifies live project/runtime/deployment truth.

## Feature publication readback

Engineering feature: `d926e2004b0a5794fb2934200091b836c0780104`
Tree: `3f3f124f19a379c86e1232a3691319dcf77f3084`
Parent: `f01418c546e449acb3f98f4b64f5b4a7ad3f0960`
Exact 17-file source candidate inventory SHA-256: `480919d3469fb610cdce3dce18753612f0c4270f0f122fed98c293c92d42ac56`.

`origin/main` was independently read back at the exact feature after push. A later repository-front-door child updates public evaluation prose and the current ICF navigation pointer against this real commit. Live Runtime remains unreloaded.
