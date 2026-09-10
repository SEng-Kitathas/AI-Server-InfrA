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

The fresh-instance orchestrator is engineering-published and remote-verified:
`continuity.ingress.rehydrate`

Feature commit: `d926e2004b0a5794fb2934200091b836c0780104`
Tree: `3f3f124f19a379c86e1232a3691319dcf77f3084`

Current warfort hardening feature: `c858914a1a9abac5d29f1943e23fed1e54c516d0`
Current substrate/package hardening feature: `673e3b15fa16053e6da6594604d9ce6db7faad1c`
Tree: `e39f0a6a3d3c3ba5ece16a04c48289186318096a`
Parent: `01a5e1d75ccb6e1da310c7a2aa47922ccbe25bdc`
Tree: `5b26071756f2798d9ed6f117490edf03f424eaa4`
Parent: `ecd99d600783dde06da718160c3fa02655fc3897`

It composes exact ICF-CS currentness, explicit RES/UCM applicability, required RES/UCM currentness, bounded project rehydration, and the owning-plane/live-readback next gate. Fresh Git/worktree/test/runtime readback still outranks this navigation pointer for consequence-bearing work.

`SOURCE_QUALIFIED != LIVE_PROMOTED`

Live Runtime was not reloaded by the ICF-CS v1.2 doctrine activation or by this source candidate.

## Current verification ceiling

Published source qualification:
- dedicated v1.2 ingress: **13/13 PASS**;
- handoff/ingress/budget gate: **37/37 PASS**;
- wider ICF/context/RES/UCM composition gate: **215 passed / 1 conditional skip / 0 failed**;
- complete Runtime: **769 collected / 767 passed / 2 skips / 0 failed**;
- substrate/package focused qualification: **63 passed / 13 subtests**;
- warfort-specific pressure: **65 passed / 1 skipped / 17 property subtests**;
- final four-worker loadscope/worksteal burns: **767 passed / 2 skipped / 103 subtests** each;
- native candidate tool count: **158**;
- compact 30-operation schema unchanged, SHA `132dff5967d7b45278d63da11e4ab87a72bd3fbd0507af3b652ffd34ee88787f`.

Git/worktree/remote readback remains the final source-currentness authority.

## 2026-09-10 Runtime currentness reconciliation
- low-level project rehydration now reports ICF-CS version **1.2** instead of stale 1.0;
- current Runtime/currentness feature `2c8b3205ce92ff09eb5b0cc213a0d211a3666969` / tree `a3fb8b3e4ce3d2bb0cd94e552d659208744fa312`;
- full source qualification 775 collected / 773 passed / 2 skipped / 0 failed;
- architecture/effect-trait audit `reports/V30_ARCHITECTURE_CLOSURE_EFFECT_TRAIT_TRUTH_AUDIT_2026-09-10.md`.

This does not alter ICF-CS v1.2 doctrine bytes or authority; it aligns the lower-level Runtime projection with already-current authority.
