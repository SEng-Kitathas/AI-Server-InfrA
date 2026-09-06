# ICF-CS v1.0 Additive Overlay — External Qualification Receipt

Date: 2026-09-05
Disposition: **ACTIVE_BINDING_ADDITIVE_DOCTRINE_ABOVE_SEALED_R4_4**
Scope ceiling: continuity/process control only; no product/domain/architecture/legal/regulatory/scientific-result authority is created by this overlay.

## Qualified source package

Package:
`RAHL_ENGINEERING_CANONICAL_SOP_R4_4_ICF_CS_V1_0_ADDENDUM_2026-09-05.zip`

Outer ZIP SHA-256:
`51ed7f424dff7c67534f7e53e8a7c10ebd93bf33ea575eea49dc3f05c24a92a9`

Package bytes:
`2,546,098`

Manifest SHA-256:
`953ca5683d16876dac573f3ad5c367c5b9c31af5726d7f92c676719c609a36b8`

Semantic-read ledger SHA-256:
`38eca2fa3d8cfae563bfa5d8225156e61fb4413d5600f52fc4e1db3852271c2b`

Exact sealed parent:
`RAHL_ENGINEERING_CANONICAL_SOP_R4_4_2026-09-04.zip`

Parent SHA-256:
`04f3e94efe8c901cc83a12a9c8531be8a9bb350728b8f9eba53db0fd082b3bbc`

Parent bytes:
`2,532,911`

## Qualification performed on exact uploaded bytes

The uploaded package was inspected as an archive before doctrine promotion.

Verified:
- outer ZIP CRC: PASS (`ZipFile.testzip() -> None`)
- 13 archive members present
- exact parent hash: PASS
- exact parent ZIP CRC: PASS through package verifier
- manifest membership, byte counts, and hashes: PASS
- project-agnostic active surfaces / no forbidden project-specific contamination: PASS
- required ICF-CS semantic bindings: PASS
- anti-binding witnesses: PASS
- machine contract identity/core-law/cold-start/conflict/discoverability checks: PASS
- semantic-read ledger coverage/hash/byte/disposition checks: PASS
- complete linear semantic read of every load-bearing readable overlay member performed during this qualification session
- hostile qualification: **22 / 22 mutants rejected as expected; 0 unexpected passes**
- clean extraction verifier: PASS
- deterministic re-seal: PASS — rebuilding the ZIP with the frozen member ordering/metadata/compression produced a byte-for-byte identical archive
- rebuilt ZIP SHA-256 exactly matched outer package SHA-256 `51ed7f...92a9`.

Package qualification runner result:
- verifier_rc = 0
- hostile_rc = 0
- hostile_cases = 22
- hostile_rejected = 22
- hostile_unexpected = []
- verifier state: `ACTIVE_BINDING_ADDITIVE_DOCTRINE`.

## Exact qualified members registered locally

Human standard:
`state/doctrine_snapshot/INTENT_CONSTRAINT_FRONTIER_CONTINUITY_STANDARD.md`
SHA-256:
`b22b6ba65992bf8e235df9acfb044da772282ae3820a1359af3b5309d1e1051b`

Machine contract:
`state/doctrine_snapshot/ICF_CS_V1_0_MACHINE.json`
SHA-256:
`527e4fa0926449155a8aa548656b3debc5292262f8cfaab0ca3f0470e7771f5a`

Claim ceiling:
`state/doctrine_snapshot/ICF_CS_CLAIM_CEILING.md`
SHA-256:
`079a523d017438cfd9057d5bfe78b4bf47e4550c20fc9bbd3840cbf6d66f245a`

The first project-store text update normalized line endings and therefore did not preserve the qualified source hash. That normalized copy was immediately superseded by byte-exact registration from a binary staging file. The registered human standard now matches the qualified package member exactly.

## Authority effect

The qualified overlay is additive above sealed R4.4. It does not mutate or replace R4.4.

Binding continuity laws include:
- `DIRECTION != CONSTRAINTS != FRONTIER != HISTORY`
- `HISTORICAL_HANDOFF != CURRENT_INGRESS`
- `DONOR != AUTHORITY`
- `RECENT_TIMESTAMP != CURRENT_AUTHORITY`
- `STALE_GREEN != CURRENT_EVIDENCE`
- `CURRENT_INGRESS_POINTER != CURRENT_STATE_PROOF`
- `EXPECTED_LABEL != PROMPT_CONTENT`
- `BENCHMARK_ITEM != DOCTRINE_AUTHORITY`
- `FORMAT_FAILURE != SEMANTIC_FAILURE`
- `SEMANTIC_AGREEMENT != AUTHORITY_FIDELITY`
- `AUTHORIZED_GOVERNING_INTENT != FACTUAL_TRUTH`
- `CONTINUITY_MAP != CURRENT_STATE_EVIDENCE`
- `REMEMBERED_SUMMARY != SOURCE_CONTACT`
- `SUMMARY_FIDELITY != SOURCE_COMPLETENESS`.

Version-agnostic cold-start grammar:
`CURRENT STATE -> ICF-CS -> CURRENT CANONICAL SOP + NEXT/DOCTRINE/REVISIT/TRACE -> LIVE SHADOW -> DTS -> LIVE READBACK BEFORE MUTATION`

Conflict grammar:
`CONFLICT -> RECOVERY/AUDIT -> LOCALIZE -> REPAIR/SUPERSEDE -> READBACK -> RESUME`

## Source archive locality note

A bounded search of obvious workstation ingress roots was attempted for the exact full addendum ZIP but timed out without finding a path before completion. No claim is made that the outer ZIP has been copied into the project store.

The full source archive remains identified by the exact outer SHA above; the load-bearing qualified standard/machine/claim-ceiling members and this qualification receipt are persisted locally for deterministic project ingress.
