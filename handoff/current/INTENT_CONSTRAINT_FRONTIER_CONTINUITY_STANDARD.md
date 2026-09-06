# Intent–Constraint–Frontier Continuity Standard — ICF-CS v1.0

Date: 2026-09-05
Status: BINDING ADDITIVE DOCTRINE ABOVE CANONICAL R4.4 WHEN QUALIFIED
Scope: project-agnostic / thread-agnostic continuity, rehydration, current-ingress, and continuity-adjacent evaluation-data hygiene.

## Standard definition
ICF-CS is a continuity and rehydration pattern that prevents fresh-instance rollback by separating three live continuity classes that age at different rates while keeping history as a distinct chronological/forensic lineage class:

1. **Intent** — what the project is ultimately trying to become and what success means.
2. **Constraints** — load-bearing decisions, authority ceilings, sequencing laws, scars, and anti-regressions that must not be casually reopened.
3. **Frontier** — what is actually earned, provisional, blocked, deferred, and next right now.
4. **History** — chronological and forensic lineage used for recovery, explanation, and provenance rather than automatic current authority.

Core law:

`DIRECTION != CONSTRAINTS != FRONTIER != HISTORY`

A healthy continuity system preserves all four without collapsing one into another.

## Why the separation is necessary
The four classes decay differently.

- Intent is durable but may change by explicit governing decision.
- Constraints are durable only while their evidence, authority, and scope remain load-bearing.
- Frontier is high-churn and must remain close to live evidence.
- History is append-oriented and may remain valuable long after it stops being current authority.

A continuity system that stores all four in one undifferentiated handoff will eventually roll backward: stale status can hide inside correct philosophy; current tasks can lose the project's reason for existing; polished donor or historical text can become easier to discover than the current ingress; and old green verification can be mistaken for present evidence.

## ICF-CS record contract
A project applying ICF-CS SHOULD maintain a compact current ICF-CS record or equivalent structured surface containing:

### Intent
- governing direction;
- success definition or success boundary;
- scope and authority of that direction;
- provenance for any governing instruction;
- explicit note where intent is authorized direction rather than factual truth.

### Constraints
- load-bearing decisions and invariants;
- authority ceilings;
- sequencing or dependency laws;
- active scars and anti-regressions;
- what must not be casually reopened;
- source/provenance and current authority basis for each consequential constraint.

### Frontier
- verified current state;
- provisional hypotheses or partial results;
- blockers;
- deferred work;
- immediate next actions;
- current evidence basis and unresolved seams.

### History
History is not copied wholesale into the current ICF-CS record. The record points to the chronological recovery spine and historical artifacts needed for lineage. History remains inspectable without being silently promoted.

## Discoverable current ingress
Each governed project SHALL expose at least one explicit, discoverable **current-ingress pointer** from its manifest, bootstrap/start surface, or equivalent entrypoint. The pointer SHALL lead a fresh instance toward current intent, constraints, and frontier without requiring an unconstrained semantic search through historical files.

The pointer itself is navigation, not proof. Consequential currentness still requires readback against the underlying current surfaces and live state where applicable.

Binding non-equivalences:

`HISTORICAL_HANDOFF != CURRENT_INGRESS`

`DONOR != AUTHORITY`

`RECENT_TIMESTAMP != CURRENT_AUTHORITY`

`STALE_GREEN != CURRENT_EVIDENCE`

`CURRENT_INGRESS_POINTER != CURRENT_STATE_PROOF`

A historical handoff SHALL be marked or treated as historical when superseded. Donor, foreign, imported, or archaeology material SHALL retain provenance and SHALL NOT supply project direction authority merely because it is detailed, polished, recent-looking, or easy to retrieve.

## Standard cold-start grammar
The version-agnostic cold-start order is:

`CURRENT STATE -> ICF-CS -> CURRENT CANONICAL SOP + NEXT/DOCTRINE/REVISIT/TRACE -> LIVE SHADOW -> DTS -> LIVE READBACK BEFORE MUTATION`

Interpretation:
1. Contact Current State first to establish the most compact claimed present reality.
2. Contact the current ICF-CS surface to recover direction, load-bearing constraints, and frontier separately.
3. Contact the **current canonical SOP** plus Next Steps, Doctrine Snapshot, Revisit Ledger, and Trace Matrix as applicable. The grammar SHALL NOT hard-code an obsolete SOP version.
4. Contact Live Shadow for the active minimal state.
5. Contact Design Thread Stream for chronological recovery and the decisions that produced the present state.
6. Before consequential mutation, perform live readback of the state that the mutation can affect: exact files, source-control head, runtime/process state, remote state, manifests, receipts, or other consequence-bearing surfaces as applicable.

Missing surfaces SHALL be reported as missing. They SHALL NOT be silently reconstructed from memory, donor material, or the most convenient historical document.

## Material disagreement protocol
If the material surfaces disagree, do not choose a winner by polish, timestamp, filename, proximity, or convenience.

Use:

`CONFLICT -> RECOVERY/AUDIT -> LOCALIZE -> REPAIR/SUPERSEDE -> READBACK -> RESUME`

### RECOVERY/AUDIT
Identify the strongest surviving evidence and authority surfaces. Distinguish current claims, historical claims, inferred relationships, and unknowns.

### LOCALIZE
Name the exact disagreement: intent, constraint, frontier, history, authority class, currentness, provenance, or embodiment.

### REPAIR/SUPERSEDE
Repair the lowest necessary surface or create an explicit successor/superseding pointer. Preserve append-only lineage where required; do not silently rewrite sealed ancestors or smooth contradictory records into fake coherence.

### READBACK
Verify the exact consequence-bearing state after repair.

### RESUME
Only then return to build/research/execution work.

## Fresh-instance rollback defenses
ICF-CS specifically rejects these failure modes:

- correct project philosophy paired with stale work status;
- current task queue with missing or drifted project intent;
- historical or donor prose outranking current authority because it is easier to discover;
- recent modification timestamp used as a substitute for authority lineage;
- previously green verification reused after the verified bytes/state changed;
- a continuity summary treated as complete source contact;
- a remembered pointer acted on as current without consequence-bearing verification;
- an old version identifier baked into a supposedly reusable cold-start standard.

## Continuity-adjacent data and evaluation extension
Steering sets, benchmark prompts, expected labels, adjudication keys, and evaluation records can change model or operator behavior. They therefore require provenance, currentness, explicit scope, and an authority class even when they are not doctrine.

Binding laws:

`EXPECTED_LABEL != PROMPT_CONTENT`

`BENCHMARK_ITEM != DOCTRINE_AUTHORITY`

`FORMAT_FAILURE != SEMANTIC_FAILURE`

`SEMANTIC_AGREEMENT != AUTHORITY_FIDELITY`

### Expected-label hygiene
An expected label or adjudication key SHALL NOT be embedded in the evaluated prompt unless label visibility is explicitly the property under test. Ground truth and prompt content SHALL remain separable so the evaluation does not leak the answer it claims to measure.

### Benchmark authority ceiling
A benchmark item is an evaluation instrument. Its answer key can be wrong, stale, scoped differently, or derived from older doctrine. Before a benchmark is used to test authority fidelity, its expected answer SHALL be checked against the currently governing authority surface.

### Failure typing
Formatting noncompliance and semantic failure SHALL be recorded separately when they are separable. A structurally invalid answer may still contain the right semantics; a perfectly formatted answer may still violate the governing authority.

### Agreement versus fidelity
Agreement with an answer key measures agreement with that key. It does not by itself prove fidelity to current doctrine, current project authority, or reality. Where authority fidelity is the target, evaluation SHALL preserve the authority source and currentness basis used to generate or validate the key.

## Minimum provenance/currentness fields for steering or evaluation data
For consequence-bearing continuity-adjacent data, record or make recoverable:
- source/provenance;
- creation or capture time as navigation metadata, not authority;
- governing scope;
- authority class;
- currentness basis or last validation point;
- expected-label source when labels exist;
- supersession/deprecation state when known.

## Authority and truth ceiling
ICF-CS is a continuity-control standard, not a truth oracle.

`AUTHORIZED_GOVERNING_INTENT != FACTUAL_TRUTH`

`CONTINUITY_MAP != CURRENT_STATE_EVIDENCE`

`REMEMBERED_SUMMARY != SOURCE_CONTACT`

`SUMMARY_FIDELITY != SOURCE_COMPLETENESS`

Intent may govern direction without proving an external claim. Constraints remain scoped to the authority/evidence that earned them. Frontier claims must remain current or explicitly provisional. History preserves lineage without automatically regaining current authority.

## Reusable implementation rule
A project implements ICF-CS successfully when a fresh instance can discover the current ingress, recover intent/constraints/frontier as separate classes, locate the chronological history without mistaking it for current authority, detect material disagreement, and reach live evidence before consequential mutation.

Implementation path, filenames, storage backend, and UI are local choices. The separation, discoverability, currentness discipline, conflict grammar, and authority boundaries are the portable standard.
