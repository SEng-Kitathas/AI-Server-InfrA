# PCMMAD Laboratory Runtime — Current ICF-CS Ingress

Status: **CURRENT INGRESS POINTER — NAVIGATION, NOT STATE PROOF**
Standard: **Intent–Constraint–Frontier Continuity Standard — ICF-CS v1.2**
Authority: **active binding additive continuity/process doctrine over sealed R4.4**
Updated: 2026-09-09

`CURRENT_INGRESS_POINTER != CURRENT_STATE_PROOF`

## Exact current authority

Current standard carrier:
`handoff/current/INTENT_CONSTRAINT_FRONTIER_CONTINUITY_STANDARD.md`

SHA-256:
`f966029496fd6e31a76a36a6e967db37ca2147acfa890a880426ae6a7fa79d92`

Activation receipt:
`handoff/current/ICF_CS_V1_2_ACTIVATION_RECEIPT_2026-09-09.json`
SHA-256 `893409f28ea181c60ca9e3681eb9a1a4d08fa279befac4d679d2cfdb958d7279`

Detached qualification receipt:
`handoff/current/ICF_CS_V1_2_DETACHED_RELEASE_RECEIPT_2026-09-09.json`
SHA-256 `59f66d7707508faa4015df86c728302961c0a13e2f4e8655425ce783248cbc7e`

Machine contract:
`handoff/current/ICF_CS_V1_2_MACHINE.json`
SHA-256 `4ae30568317de49f9613e226b7601b0de440ba35becb9f5d817870c3c598747c`

Fresh-instance contract:
`handoff/current/ICF_CS_V1_2_FRESH_INSTANCE_CONTRACT.json`
SHA-256 `4fdee32a990791ff2b70bacdf6fed07c75a7fc5a8feb662e36dcb81e700c2519`

Qualified parent ICF-CS v1.1 remains preserved as historical parent; it is no longer the current ingress contract.

Rahl activation closed under Continuity Guard at epoch **43**:
- closure `edef92465daa7e28fb64600d096ad709`;
- close receipt SHA `ebb10e71fd31ec51a83ed41ec2c98cc027ca3065c98f4a2c22aca34298d0d06f`.

## Continuity topology

`LIVE_SHADOW != DTS != RES != UCM`

- Live Shadow: current project state.
- DTS: chronological/decision recovery spine.
- RES: project/research epistemic state; never automatic doctrine authority.
- UCM: user-owned/global continuity; never project/runtime/doctrine authority.

Binding laws:

- `RES_CONTENT != GOVERNING_DOCTRINE`
- `UCM != PROJECT_AUTHORITY`
- `UCM != RUNTIME_TRUTH`
- `UCM != DOCTRINE_AUTHORITY`
- `MISSING != NOT_APPLICABLE`
- `RETRIEVAL_PACKET != AUTHORITY`
- `VERSION_LABEL != CURRENT_AUTHORITY_BYTES`

## Current cold-start grammar

`CURRENT STATE -> CURRENT ICF-CS -> CURRENT CANONICAL SOP + NEXT/DOCTRINE/REVISIT/TRACE -> LIVE SHADOW -> DTS -> RES APPLICABILITY/CURRENTNESS -> UCM APPLICABILITY + SYSTEM DESCRIPTOR + USER STORE HEAD -> BOUNDED UCM CORE -> TASK-RELEVANT LAZY UCM HYDRATION -> OWNING-PLANE LIVE VERIFICATION -> LIVE READBACK BEFORE MUTATION`

Runtime implementation uses explicit session applicability. It SHALL NOT guess a UCM profile.

Session modes:
- `INTERACTIVE_RESEARCH_USER_SESSION`: RES REQUIRED, UCM REQUIRED.
- `INTERACTIVE_NONRESEARCH_USER_SESSION`: UCM REQUIRED; RES may be N/A with basis unless the project requires it.
- `NONUSER_RESEARCH_AUTOMATION`: RES REQUIRED; UCM N/A with basis.
- `NONUSER_NONRESEARCH_AUTOMATION`: both may be N/A with explicit basis.

## Current Runtime embodiment

Published prerequisite features:
- RES Runtime feature `8714dd87d2092e0f4c66f261fcf5cee8b75a0798`;
- UCM Runtime feature `f01418c546e449acb3f98f4b64f5b4a7ad3f0960`.

This checkout additionally contains the qualified fresh-instance orchestrator candidate:
`continuity.ingress.rehydrate`

It composes exact ICF-CS currentness, explicit RES/UCM applicability, required RES/UCM currentness, bounded project rehydration, and the owning-plane/live-readback next gate.

Before using this pointer as Git publication evidence, independently read `git rev-parse HEAD`, worktree status, tests, and `origin/main`. Do not infer publication identity from this document.

`SOURCE_QUALIFIED != LIVE_PROMOTED`

Live Runtime was not reloaded by the ICF-CS v1.2 doctrine activation or by this source candidate.

## Current verification ceiling

Detached candidate qualification on the current source worktree:
- dedicated v1.2 ingress: **13/13 PASS**;
- handoff/ingress/budget gate: **37/37 PASS**;
- wider ICF/context/RES/UCM composition gate: **215 passed / 1 conditional skip / 0 failed**;
- complete Runtime: **676 collected / 675 passed / 1 conditional skip / 0 failed**;
- native candidate tool count: **158**;
- compact 30-operation schema unchanged, SHA `132dff5967d7b45278d63da11e4ab87a72bd3fbd0507af3b652ffd34ee88787f`.

A later publication child may bind the exact Git feature commit after it exists. Until then, Git/worktree/remote readback outranks this navigation pointer.
