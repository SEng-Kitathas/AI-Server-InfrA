# Intent–Constraint–Frontier Continuity Standard — ICF-CS v1.1

Date: 2026-09-05
Status: BINDING ADDITIVE DOCTRINE ONLY WHEN ACCOMPANIED BY A VALID DETACHED RELEASE RECEIPT
Scope: project-agnostic/thread-agnostic continuity, rehydration, current-ingress, currentness conflict handling, and continuity-adjacent evaluation-data hygiene.

## Standard definition
ICF-CS prevents fresh-instance rollback by separating three live continuity classes that age at different rates while keeping history as a distinct chronological/forensic lineage class:

1. **Intent** — what the project is ultimately trying to become and what success means.
2. **Constraints** — load-bearing decisions, authority ceilings, sequencing laws, scars, and anti-regressions not casually reopened.
3. **Frontier** — what is verified/earned, provisional, blocked, deferred, and next right now.
4. **History** — chronological/forensic lineage used for recovery and provenance, not automatic current authority.

`DIRECTION != CONSTRAINTS != FRONTIER != HISTORY`

Intent can remain durable while frontier changes quickly. Constraints can remain load-bearing while their evidence/scope remains valid. History can remain valuable after losing current authority.

## Current-ingress requirement
A governed project SHALL expose at least one explicit discoverable current-ingress pointer from a manifest/bootstrap/start surface or equivalent. The pointer is navigation, not proof.

`HISTORICAL_HANDOFF != CURRENT_INGRESS`
`DONOR != AUTHORITY`
`RECENT_TIMESTAMP != CURRENT_AUTHORITY`
`STALE_GREEN != CURRENT_EVIDENCE`
`CURRENT_INGRESS_POINTER != CURRENT_STATE_PROOF`

A polished or complete imported/donor account SHALL NOT acquire governing authority merely because it is easier to retrieve than the current project state. A recent timestamp SHALL NOT resolve an authority conflict. Prior passing evidence SHALL be revalidated whenever consequence-bearing bytes/state within its assurance scope changed.

## Version-agnostic cold-start grammar
`CURRENT STATE -> ICF-CS -> CURRENT CANONICAL SOP + NEXT/DOCTRINE/REVISIT/TRACE -> LIVE SHADOW -> DTS -> LIVE READBACK BEFORE MUTATION`

1. Current State establishes the compact claimed present.
2. ICF-CS recovers Intent, Constraints, and Frontier separately.
3. Current canonical SOP plus applicable Next Steps, Doctrine Snapshot, Revisit Ledger, and Trace Matrix recover governing process and open obligations without hard-coding an obsolete SOP version.
4. Live Shadow restores minimum high-fidelity active state.
5. DTS restores chronology and decision lineage.
6. Before consequential mutation, live consequence-bearing state SHALL be read back: exact bytes, source-control head, runtime/process state, remote state, manifests, receipts, or equivalent.

Missing surfaces are reported missing. They are not reconstructed from memory, donor prose, or the newest-looking file.

## Material disagreement protocol
`CONFLICT -> RECOVERY/AUDIT -> LOCALIZE -> REPAIR/SUPERSEDE -> READBACK -> RESUME`

- **RECOVERY/AUDIT:** identify strongest surviving evidence and authority surfaces; separate verified, provisional, historical, inferred, and unknown.
- **LOCALIZE:** name the exact disagreement class: intent, constraint, frontier, history, currentness, authority, provenance, or embodiment.
- **REPAIR/SUPERSEDE:** repair the lowest necessary surface or create an explicit successor/superseding pointer; preserve append-only lineage where required.
- **READBACK:** verify consequence-bearing state after repair.
- **RESUME:** return to work only after the conflict is localized and current state re-established.

## Evaluation/steering-data extension
Steering sets, benchmark prompts, expected labels, adjudication keys, and evaluation records can alter model/operator behavior and therefore require provenance, currentness, explicit scope, and authority class.

`EXPECTED_LABEL != PROMPT_CONTENT`
`BENCHMARK_ITEM != DOCTRINE_AUTHORITY`
`FORMAT_FAILURE != SEMANTIC_FAILURE`
`SEMANTIC_AGREEMENT != AUTHORITY_FIDELITY`

Expected labels/adjudication keys SHALL NOT be exposed to the evaluated input unless label visibility is the property under test. Copying a scoring key into model input changes the measurement and SHALL NOT be treated as a clean semantic evaluation.

A benchmark answer key is an evaluation instrument, not governing doctrine. When authority fidelity is being tested, expected answers SHALL be validated against the current governing authority surface.

Formatting failure and semantic failure SHALL be recorded separately when separable. Agreement with an answer key measures agreement with that key; it does not prove fidelity to current authority or reality.

Minimum recoverable metadata for consequence-bearing steering/evaluation data: provenance, scope, authority class, currentness basis/last validation point, expected-label source when labels exist, and supersession/deprecation state when known.

## Mechanized currentness profile
Where durable local state and deterministic tooling are available, projects SHOULD prefer the mechanized profile in `MECHANIZED_EPOCH_PROFILE.md` over operator-memory-only currentness checks. This preference is about reducing stale-read risk, not granting semantic authority to counters.

`TOKEN_MATCH != FACTUAL_TRUTH`
`EPOCH_MATCH != AUTHORITY_MATCH`
`CAS_SUCCESS != SEMANTIC_VALIDITY`

## Release authority
ICF-CS v1.1 payload bytes do not activate themselves.

`SELF_VERIFYING_PACKAGE != VERIFIED_PACKAGE`

A detached release receipt produced outside the specimen is required for active binding status. The receipt must pin at least payload SHA-256, canonical-base SHA-256, manifest SHA-256, semantic-ledger SHA-256, qualification-contract SHA-256, release-critical file hashes, hostile case set/count, CRC, deterministic seal result, and clean-extraction replay result.

## Authority ceiling
ICF-CS is continuity/process doctrine, not a truth oracle. Authorized intent may govern direction without proving external facts. Constraints remain scoped to the evidence and authority that earned them. Frontier claims must remain current or explicitly provisional. History preserves lineage without automatic authority promotion.

ICF-CS adds no product/domain/architecture/legal/regulatory/scientific-result authority merely by inclusion.
