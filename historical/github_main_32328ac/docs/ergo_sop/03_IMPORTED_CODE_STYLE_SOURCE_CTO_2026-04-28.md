# 05 — CTO Unified Code Style Guide SOP

## Purpose
This SOP is the standalone CTO-local code style guide derived from the Unified Code doctrine, CODEX OMEGA, and the localized CTO doctrine stack.

It is not advisory.
It is the local operational style baseline for load-bearing CTO code.

## Intent: the physics of computation
CTO treats software as a physical and informational process rather than a purely aesthetic artifact.

### Thermodynamic floor
Mutation erases information and should therefore be treated as costly.
CTO should prefer where practical:
- immutable values
- append-only records and ledgers
- explicit state transitions
- event-style history over opaque overwrite chains

### Informational ceiling
Refactoring is compression.
Any structure that exceeds the minimum needed to express the invariant is accidental complexity.

### Cognitive conservation
A developer should be able to hold a module in working memory.
CTO therefore pressures:
- bounded directory depth
- bounded parameter count
- bounded function span
- bounded nesting depth
- local naming that reveals domain truth without extra mental decompression

## Governance laws

### Law Omega
The target is the strongest attainable embodiment, not merely acceptability.

### Law 0 — discourse precedes implementation
Discussion, derivation, and implementation are distinct modes.
Do not confuse speculative design with embodied project truth.

### Law 1 — zero stubs
No TODO theater, no stub surfaces, no fake phased readiness.
Ship complete structure or leave the seam explicit and unclaimed.

### Law 4 — verified truth
Claims require machine-checkable anchors whenever possible.
Confidence should be dominated by evidence.

### Substrate sovereignty
Dependencies are consumables, not architecture.
The truth of CTO must live in CTO-owned boundaries, models, and invariants.

## Holonic architecture rule
Every load-bearing unit should be explainable as a holon with:
1. purpose
2. boundary
3. interface
4. invariants
5. hazards

No mysterious runtime unit is acceptable.

## PDVER lifecycle rule
All serious changes should move through:
- Probe
- Derive
- Verify
- Embody
- Recurse

A code style correction is not complete unless it is embodied and verified.

## Naming and structure mandates

### Encode domain truth
Names should represent what the thing is in the problem domain, not the incidental implementation trick.

### Explicit units
Units must appear in names where relevant.
Examples:
- `timeout_ms`
- `distance_meters`
- `price_usd`

### Boolean formatting
Boolean names must use predicate form:
- `is_...`
- `has_...`
- `can_...`
- `should_...`

### Directory depth
Target directory depth is `<= 4` levels from the governed root unless there is a justified local holonic reason.

## Function and logic mandates

### Single responsibility
One function should express one coherent job.

### Purity where possible
Functions should remain pure unless side effects are the actual owned boundary.
When side effects exist, isolate them clearly.

### Early returns
Prefer early returns and flatter control flow over nested branching towers.

### Cognitive bounds
Target limits unless a stronger invariant requires otherwise:
- function parameters `<= 4`
- cyclomatic and nesting pressure kept locally legible
- function span kept small enough to remain inspectable as one mental unit

## Type system mandates

### Parse, do not merely validate
Prefer typed construction that makes invalid states hard or impossible to represent.

### Product and sum types
Use:
- product types for composite records
- enums / unions / tagged variants for exclusive states

### Typed, not dict
Loose `dict` typing is disfavored.
Prefer:
- dataclasses
- explicit record classes
- TypedDict only at unavoidable boundary surfaces

### String prohibition
Stringly-typed APIs are forbidden where typed variants are realistically possible.
Strings should not smuggle state machines or undocumented domain modes.

## Error-handling mandates

### Errors are explicit
Where the substrate permits, treat errors as explicit values or explicit typed outcomes rather than invisible control-flow haze.

### No silent failures
Empty catches, bare suppression, and hidden no-op failure paths are forbidden.

### Actionable reporting
Errors should distinguish recoverable vs fatal conditions and guide the operator toward resolution.

## Boundary and serialization mandates

### JSON is boundary-only
JSON is allowed only where it is a true hard-boundary requirement, such as:
- external manifest/config formats
- persisted report artifacts
- explicit interoperability boundaries

JSON should not be the casual internal architecture language.

### No anonymous projection smear
Do not collapse structured models into anonymous dicts unless the boundary truly requires it.
Keep typed structure intact until the final boundary conversion.

## Verification and alignment mandates

### Traceability law
Every serious functional component should trace back to a requirement, invariant, or doctrine-backed need.
Dead code is liability.

### Non-LLM anchors
Verification should prefer:
- parser/compile checks
- type checks
- schema checks
- deterministic runtime checks
- artifact readback

LLM review is advisory only.

### Specimen vs governance split
Runtime specimen surfaces must remain separate from governance sidecars.
Do not contaminate execution specimens with admin chatter.

## Three Tens alignment
A CTO surface should align across:
- Intent — why it exists
- Structure — what architecture it uses
- Implementation — how the code expresses that structure

Misalignment across these dimensions is a real defect.

## Current CTO-local enforcement interpretation
CSC should pressure this SOP through executable findings where feasible, including at minimum:
- loose dict typing
- JSON outside hard-boundary files
- legacy typing aliases where builtin generics suffice
- broad exception handlers and silent failures
- mutable default arguments
- module-level mutable global state
- boolean naming discipline
- excessive path depth
- parameter/nesting/function-span overload
- TODO/stub residue

## Promotion rule
A surface does not become promotion-grade merely because it passes a weak lint profile.
It must survive doctrine pressure, boundary honesty, verification, and local cognitive legibility.

## CTO remediation/evaluation/recurse sync — 2026-04-16
This control surface is synchronized after the latest PDVER remediation pass that localized CSC typing discipline, removed mutable global-state findings from CSC core surfaces, flattened scanner/helper seams to stay within cognitive limits, and reduced dict-smear inside the DB helper boundary layer. Freshness here reflects real post-remediation alignment, not timestamp theater.

## CTO artifact-core synchronization — 2026-04-17
This control surface is synchronized after the local artifact-core build pass that added `tools/cto_core`, the SQLite-backed artifact registry, typed ingest, and context pack construction. Freshness here reflects the new non-extension core plane and its holonic bindings, not timestamp theater.

## CTO extension projection synchronization — 2026-04-17
This control surface is synchronized after the local-core-to-extension projection bridge build that added published extension bundles, a pure extension bundle parser, and explicit bundle import into extension scoped-pack cache. Freshness here reflects the projection bridge mutation and its operator/import path, not timestamp theater.

## CTO bundle promotion synchronization — 2026-04-17
This control surface is synchronized after the bundle-promotion and default-resolution build that separated active bundle from preferred bundle, added explicit promotion states, and tied injection/export defaults to promotion ordering rather than active editor focus. Freshness here reflects the promotion-resolution mutation and not timestamp theater.

## CTO signed promotion gate synchronization — 2026-04-17
This control surface is synchronized after the signed-promotion-gate build that added operator signature requirements, promotion classes, class-specific gate evidence, and adjudication entries that preserve the exact gate evidence authorizing promoted transitions. Freshness here reflects the signed-gate mutation and not timestamp theater.

## CTO local verifier plug synchronization — 2026-04-17
This control surface is synchronized after the local-verifier-plug build that projects machine-derived verifier evidence from local-core and CSC surfaces into extension bundle imports, persists that snapshot per workstream, and merges machine evidence with operator evidence during promotion authorization. Freshness here reflects the verifier-plug mutation and not timestamp theater.

## CTO verifier-class adapter synchronization — 2026-04-17
This control surface is synchronized after the verifier-class-adapter build that introduced explicit machine authority adapters, class-declared required adapter sets, adapter-aware promotion blocking, and adjudication output that preserves required adapter IDs plus machine adapter results. Freshness here reflects the verifier-adapter mutation and not timestamp theater.

## CTO promotion certificate chain synchronization — 2026-04-20
This control surface is synchronized after the promotion-certificate-chain build that introduced prior-certificate references, chain depth, append-only promotion certificate ledgers, and operator surfaces that expose latest certificate plus ledger traversal per workstream. Freshness here reflects the certificate-chain mutation and not timestamp theater.

## CTO branch fork and merge topology synchronization — 2026-04-21
This control surface is synchronized after the branch-fork-and-merge topology build that introduced parent-certificate sets, explicit topology kinds, thread-wide certificate topology ledgers, and operator surfaces for explicit merge-parent declaration and cross-branch certificate traversal. Freshness here reflects the topology mutation and not timestamp theater.

## CTO topology edge adjudication synchronization — 2026-04-22
This control surface is synchronized after the topology-edge-adjudication build that introduced explicit parent-edge classes, edge rationale, parent-edge readback in certificate and decision surfaces, and a compact thread topology graph for operator inspection. Freshness here reflects the topology-edge mutation and not timestamp theater.

