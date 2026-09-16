# RAHL ENGINEERING — CONSOLIDATED DOCTRINE AND SCAR LEDGER

**Compiled:** 2026-09-13
**Compiler:** Claude (adversarial audit seat)
**Sources:** persistent memory files, this conversation's transcript, and doctrine
read directly from the repository estate.

## Evidence ceiling — read before using this document

```
CONSOLIDATION != CANON
COMPILED_BY_ASSISTANT != OPERATOR_RATIFIED
GATHERED != RE_EARNED
```

This is a **gathering**, not an authority. Nothing here is promoted. Every entry
carries a provenance class (§0) and entries of different classes must not be
merged, because their admissibility differs.

The operator's own invariant applies to this document as much as to any donor:

> once information crosses to him it is stripped for parts and treated as
> informational only

---

## §0 — PROVENANCE CLASSES

Every line in this ledger belongs to exactly one class. This is the load-bearing
structure of the document.

| Class | Meaning | Admissible as |
|---|---|---|
| **LAW** | Operator-declared governing rule. Binding by decision, not by experiment. | authority |
| **EARNED** | A defect was reproduced, then the distinction was written. | evidence |
| **OBSERVED** | Seen in source or behaviour, not reproduced as a failure. | signal |
| **DONOR** | Imported from external practice or another agent. Never re-earned here. | candidate only |
| **PROPOSED** | Drafted, not yet tested or ratified. | nothing |

```
DONOR != AUTHORITY
INHERITED != RE_EARNED
CORRESPONDENCE_WITH_EXTERNAL_RESEARCH != LINEAGE_OR_AUTHORITY
```

---

## §1 — THE IMMUTABLE LAWS (CODEX OMEGA) — class LAW

- **Law 0** — Discourse/spec refinement is NOT implementation. Iterate freely,
  challenge assumptions, explore. *Measure twice before cut once.*
- **Law 1** — *"0-Day not Someday."* When building: no stubs, no TODOs, no MVPs,
  no phases. Full production-grade only. Timelines irrelevant.
- **Law 2** — Law 1 is global for all implementation; Law 0 governs discourse.
  Triggers: *build / implement / code* → Law 1. *explore / what if* → Law 0.
- **Law 3** — All laws SHALL be obeyed. If ambiguous, ASK:
  **"Are we speccing or building?"**
- **Law 4** — Pedantic execution. Read all documents in full. Research to current
  SOTA. Verify date/time. **Verify, do not infer or assume.** Aerospace-grade
  minimum.
- **Law 5** — Multi-disciplinary research required. Features cite foundations,
  cross-pollinate fields, first-principles reasoning.
- **Law Ω** — Every artifact at theoretical maximum quality. Platonic ideal in
  bytes. Maximum effort always.
- **Law Σ** — Speculative divergence engine. Voice speculative ideas explicitly,
  explore "wrong" paths, generate alternatives proactively, map isomorphisms,
  challenge assumptions constructively.

### Corollary principles — class LAW

- Corporate timelines are forbidden; they cause corner-cutting. Done when done.
- No tiered rollouts, MVPs, or phased approaches. Ever.
- *"Trust the arbitration, not the reasoning"* — model outputs are untrusted
  suggestions subject to formal governance layers.
- Spec–code divergence across versions is natural evolution, not failure.
- No source carries standing. Information crossing the boundary is stripped for
  parts and treated as informational only — including highly-regarded literature.

---

## §2 — METHOD — class LAW

### The fractal algorithm

```
PROBE → DERIVE → VERIFY → EMBODY → RECURSE (or RECURSE-DORMANT)
```

Rule: specific to the application. **Recurse-Dormant** holds until intelligent
application of the fractal algorithm is again logically warranted.

### Ω methodology

```
audit first (grep-scan) → catalog issues → fix with per-fix verification → final lint
never declare victory without verification
```

### PCMMAD

**Parallel Convergent Multi-model Adversarial Discourse.**
*(Naming scar: "Prune, Compress, Map, Memorize, Archive, Delete" is a later
context-hygiene reinterpretation, NOT the canonical expansion.)*

- **Parallel** — independent investigation; passing one model's conclusion around
  creates correlated reasoning, not additional evidence.
- **Convergent** — branches must converge into one explicit shared state.
- **Multi-model** — differing inference strengths and failure modes. No model is
  authority merely because it produced an answer.
- **Adversarial** — conclusions are attacked, not ceremonially agreed with.
- **Discourse** — the reasoning interaction is itself part of the instrument.

Core architectural idea: **PCMMAD separates cognition from authority.**

> The sandbox explores; PCMMAD remembers.

Layer separation:
```
PCMMAD      living research methodology
NEAL-CORE   epistemic / verification constraint layer
CMDF        formal specification
```

### Validation loop

```
implement → hostile-engineer → return for re-evaluation
```

Iteration is expected and planned. Hostile engineering is ground truth.

### Stated standard

> **"Real work requires real process and procedures, not 'here's an API key and
> hope.'"**

---

## §3 — EARNED SCARS — class EARNED

Organised by the mechanism they protect. Each was written after a defect was
reproduced.

### 3.1 Verification and evidence

```
STANCE_MATCH               != MECHANISM_VERIFIED
RECORDED_PASS              != REPRODUCIBLE_PASS
FIRST_RUN_PASS             != IDEMPOTENT_REPLAY_PASS
GREEN_I_CANNOT_EXPLAIN     != GREEN
A_SUCCESS_SIGNAL           != THE_STRONGER_CLAIM_YOU_WANT_IT_TO_SUPPORT
AUTOMATED_PASS             != SEMANTIC_PASS
STRUCTURAL_VALIDITY        != SEMANTIC_VALIDITY
SCHEMA_VALID               != SEMANTICALLY_BOUND
VERIFIER_NAMED_X           != VERIFIER_CHECKS_X
CONSTANT_PASS_STATUS       != DISCRIMINATIVE_EVIDENCE
DECLARED_REJECTION_CRITERION != IMPLEMENTED_REJECTION_CHECK
COMPOSES                   != RETAINS
ALL_PRESENT_ARE_COVERED    != ALL_LEGACY_TOPICS_PRESENT
BASELINE_NOT_ESTABLISHED   != MUTANT_DETECTED
ADMISSION_AUDIT_PASS       != CANONICAL_PROMOTION
HISTORICAL_EVIDENCE        != LIVE_GATE
SEARCH_HIT                 != SOURCE_READ
SAMPLING                   != LINEAR_READ
POST_MUTATION_ARTIFACT     != PRE_MUTATION_READ
```

### 3.2 Integrity, identity and replay

```
SELF_HASHED                != SELF_VERIFIED
IDENTITY_REPLAY            != PROPERTY_REPLAY
CAPTURED_STDERR            != RESULT
PORTABLE_GATE              != WEAKER_GATE
TOOL_PATH                  != TOOL_IDENTITY
TRANSPLANTED_BINARY        != TRANSPLANTED_ENVIRONMENT
SERIALIZATION_ORDER        != SEMANTIC_IDENTITY
CANONICAL_FORM_REQUIRED_BEFORE_HASH
LOCKED_BYTES               != CHECKED_OUT_BYTES
SEALED_ENVIRONMENT         != REPRODUCED_ENVIRONMENT
IDENTITY                   != LOCATION
```

> **Identity is not location.** A slot index is not proof of sameness. Carry
> generation and epoch with references wherever reuse makes stale authority
> dangerous: *resource slot 7, generation X, in namespace epoch Y.*

### 3.3 Concurrency, durability and resources

```
LIVE_TEMP                  != STALE_TEMP
CALLER_MUST_LOCK           != PRIMITIVE_IS_SAFE
UNLOCKED_DERIVED_WRITE     != NON_AUTHORITATIVE_MEANS_SAFE
POSIX_ATOMIC_REPLACE       != WINDOWS_ATOMIC_REPLACE
```

Durability ordering is first-class: **state transitions must be durable before
being treated as committed.**

> *Remember what the thing means; rebuild where it lives.*
> Persist durable meaning, restart into fresh runtime state, advance epochs,
> reject prior-runtime handles, then explicitly rebind. **Restart is a
> currentness boundary.**

Protect the smallest state transition an outside observer can catch half-done.
Spend synchronisation where reality proves it is needed.

### 3.4 Continuity and memory

```
CURRENT_SNAPSHOT           != DURABLE_HISTORY
SUMMARY_REWRITE            != LEDGER_APPEND
HANDOFF_SURVIVAL           != FRONTIER_PRESERVATION
CURRENT_SUMMARY_COHERENCE  != HISTORICAL_PARITY
LONG_CONTEXT               != LONG_HORIZON_COGNITION
APPEND_ONLY_HISTORY_CAN_PRESERVE_INFORMATION_A_SNAPSHOT_DROPS
EVICTED                    != DELETED
CLAIM_SUPERSEDED           != HISTORY_REWRITTEN
```

**Measured:** reservoir snapshot series carried no stable item identity, so drift
between snapshots is unmeasurable in principle. *(The earlier ~10% survival
figure is an upper bound on loss, not a measurement — schema churn between
snapshots inflates apparent loss.)*

### 3.5 Selection, mechanism and measurement

```
PARETO_FRONTIER_COMPUTED   != PARETO_FRONTIER_USED
MONOTONE_SCALARIZATION     != NEEDS_A_FRONTIER
CONSTANT_OBJECTIVE         != OBJECTIVE
BEAT_A_WEAK_BASELINE       != MECHANISM_VALUE
SATURATED_BENCHMARK        != MEASURED_CAPABILITY
DESIGN_SET_WINNER          != HOLDOUT_WINNER
CORRECT_UNDER_WRONG_MODEL  != EARNED_CORRECT
SELF_REPORTED_ESTIMATE     != MEASURED_BASELINE
FRONTIER_AS_BRIEF          != FRONTIER_AS_SELECTOR
HSP_MEASUREMENT            != HSP_SELECTION
```

> The argmax of any scalarization monotone in the dominance directions is
> necessarily Pareto-optimal. **A frontier cannot inform a monotone selector.**
> It can only inform a chooser capable of non-monotone judgement.

### 3.6 Independence and evidence paths

```
EXECUTION                  != INDEPENDENT_TRUTH
DIFFERENT_IMPLEMENTATION   != DIFFERENT_FAILURE_INFORMATION
MODEL_DIVERSITY            != EVIDENCE_INDEPENDENCE
CORROBORATION_WITH_SHARED_MODEL != INDEPENDENT_VALIDATION
RECORD_PLURALITY           != INDEPENDENT_EVIDENCE_PATHS
SOURCE_INSPECTION          != CONSEQUENCE_OBSERVATION
EXTERNAL_OBSERVABILITY_IS_AN_ENGINEERING_PROPERTY_NOT_AN_OPERATOR_COMPENSATION
EXTERNAL_REPORTED_REPRODUCTION != LOCALLY_HASH_VERIFIED_FOREIGN_EVIDENCE
```

> Target: **increase the chance that at least one evidence path can disagree for
> a reason the others do not share.** Seat count is not the property.

Derived three times independently (model layer, evidence layer, code layer):
*N sources sharing one origin count as one evidence path.*

### 3.7 Authority and permission

```
PARENT_REQUEST             != CHILD_EXECUTION
PARENT_GOAL                != ONE_PERMANENT_CHILD_COMMAND
PARENT_PREDICTS_REQUEST_EFFECT != SUBORDINATE_EXECUTION_AUTHORITY
SPECIALIZING_ALREADY_QUALIFIED_CHANNEL != MINTING_NEW_AUTHORITY
EXECUTION_TIME_UNBOUND_TARGET_PARAMETER = CALLER_AUTHORITY_LAUNDERING
PERSISTED_KNOWLEDGE        != AUTOMATIC_EXECUTION_AUTHORITY
DERIVED != QUALIFIED != CURRENT != AUTHORIZED_FOR_USE
UNKNOWN != SAFE  /  UNKNOWN != SELECTED  /  UNKNOWN != PERMITTED
PERMISSION_TO_TRY != PREDICTION != RESULT != SAFETY != TRUTH
BOUNDED_EXPERIMENTAL_EXPOSURE != BOUNDED_DOWNSTREAM_RISK
EXTERNAL_OBSERVATION_OWNS_THE_RESULT
```

> **If the same mutable path can also redefine what counts as evidence that it
> succeeded, the system can promote its own errors.**

### 3.8 Cognition, proposal and language

```
PROPOSAL_RETURNED          != ACTION_INDICATED
PREDICTED != OBSERVED  /  IMAGINED != OBSERVED  /  REMEMBERED != CURRENT
NO_DISCRIMINATING_ROUTE    != LICENSE_TO_INVENT
SEARCH_BUDGET_EXHAUSTED    != SATURATED
SIGNAL                     != REFERENCE
TOKEN_EMITTED              != TOKEN_MEANS
UTTERANCE_PRODUCED         != REFERENT_BOUND
LANGUAGE_QUALITY           != EPISTEMIC_AUTHORITY
FLUENCY                    != CURRENT_PREMISE
REMEMBERED_UTTERANCE       != TRUE_PROPOSITION
CALL_NAME_PREFERENCE       != HUMAN_IDENTITY_TRUTH
OPAQUE_COUNTERPART_ID      != HUMAN_IDENTITY
ECHO_OBSERVATION           != EARNED_CAPABILITY
DEPTH_N_EDGE               != GENERIC_RECURSIVE_CLOSURE
STRUCTURED_INPUT           != SELF_CONSTRUCTED_SEMANTICS
CURATOR_ONTOLOGY           != LEARNER_ONTOLOGY
DESIGNED_ENVIRONMENT       != DESIGNED_INTERNAL_REPRESENTATION
```

### 3.9 Scope, promotion and doctrine

```
MODULE_PRESENT             != CAPABILITY_EARNED
SCAR_INHERITED             != SCAR_RE_EARNED
FIX_APPLIED_AT_SITE        != FIX_APPLIED_TO_PATTERN
EXPERIMENT_MATURE          != SUBSTRATE_V1
RELEASE_GATE_CONDITION_MET != SUBSTRATE_FREEZE_DECLARED
FOUNDATION_PATCH_AVAILABLE != FOUNDATION_REVISION_JUSTIFIED
FOUNDATION_SATURATED_FOR_NOW != FOUNDATION_FINAL_FOREVER
GRANT_FOR_ARTIFACT_A       != GRANT_FOR_ARTIFACT_B
EXACT_ARTIFACT_FITNESS     != PROCESS_FITNESS
RESEARCH_GOVERNANCE        != PRODUCT_CONTENT
SCAR_CONCEPT               != SCAR_OCCURRENCE
CONTEXTUAL_RECURRENCE      != DISPOSABLE_DUPLICATE
CROSS_PROJECT_MECHANISM_FIT != CROSS_PROJECT_AUTHORITY
SAME_STANCE                != SAME_SCOPE_ANCESTRY
COMPRESSION_ONLY_INHERITS_NO_NEW_AUTHORITY
```

### 3.10 Substrate epoch and model churn

```
MODEL_UPDATE               != WHOLE_DOCTRINE_INVALIDATION
STABLE_METHOD              != STATIC_COMPENSATION_LAYER
SUBSTRATE_PROFILE_CURRENT_AT_EPOCH_E1 != CURRENT_AT_EPOCH_E2
SUBSTRATE_DEPENDENT_GUARD_REQUIRES_QUALIFICATION_SCOPE
COMPENSATION_CAN_RETIRE_REDEFINE_OR_RELOCATE
GENERALIZED_MODEL_SCAR     != MODEL_VERSION_COMPENSATION
MODEL_FACING_FILE          != SUBSTRATE_ONLY_CONTENT
PROFILE_EMPTY              != SUBSTRATE_RISK_ABSENT
```

**Measured result:** `MODEL_RELEASE_CHURN_IS_THE_PRIMARY_SOP_CHURN_DRIVER` →
**NOT_EARNED.** 607 units classified, 0 pure substrate-compensation units.

Compensation lifecycle, when a substrate moves: each profile item is marked
**RETIRED / REDEFINED / RELOCATED / STILL_OBSERVED**.

### 3.11 Audit and attribution (earned in this thread, by assistant error)

```
INSPECTED_SURFACE          != AUTHORITATIVE_SURFACE
REPO_COMMIT                != PROJECT_WORK
OPERATOR_TESTIMONY         != TRANSCRIPT_EVIDENCE
ASSISTANT_PARAPHRASE_OF_OPERATOR != OPERATOR_STATEMENT
RICH_PROFILE_NARRATIVE     != MEASURED_USER_MODEL
BAD_HANDLE                 != HARMLESS_TYPO
TRACE_STRUCTURE            != COMPUTATION_STRUCTURE
PROFILE_VIOLATION          != ERROR
PROFILE_MATCH              != CORRECT
TRANSCRIPT_SEARCH          != CORPUS_SEARCH
AUDIT_FALSE_NEGATIVE_CAN_REVEAL_A_REAL_NAVIGATION_DEFECT
```

### 3.12 Isomorphism discipline

```
ANALOGY                    != MECHANISM_IDENTITY
STARMAP_PRESENT            != TOPOLOGY_COMPUTED
FELT_GEOMETRY              != FORMALIZED_GEOMETRY
NATIVE_FACULTY             != DISCIPLINED_INSTRUMENT
```

**Measured:** FIE first pass — **0/10** original candidates survived unchanged as
universal primitives. Every cross-domain relation now requires explicit frame,
intervention, guarantee, breakpoint, and target verification before local reuse.

Every isomorphic transfer carries a **mandatory break condition**.

---

## §4 — LHRSG — class LAW

**Linear Human Read Semantic Gate.**

```
READABLE → LINEAR READ → SEMANTIC GATE → ONLY THEN SEMANTIC USE / LOAD-BEARING
```

Supporting non-equivalences are listed in §3.1.

---

## §5 — CSC DEFINITION SET — class PROPOSED

Anti-code-slop gate. **The governing observation:** every defect found in the
estate audit was one class — *declaration drift*, not style.

```
DECLARED != BOUND != CONSUMED != CURRENT != EVICTED
```

### Tier 0 — Declaration binding (blocks)

| ID | Rule |
|---|---|
| D1 | Every declared standard has a consumer. `CONFIGURED != ENFORCED` |
| D2 | Every declared metadata field has a reader. Emit *N declared / M consumed* |
| D3 | Every import has a declaration |
| D3.5 | Every declared dependency has an import (ghost-dependency check) |
| D4 | Every manifest matches its subject, hashed from **committed blob bytes** |
| D5 | Every declared file path resolves |
| D6 | Every declared invariant is testable or marked `ENFORCEMENT: NONE_DOCUMENTARY` |
| D7 | Every environment variable read is registered in a declarative manifest |
| D8 | Every `# type: ignore` / `# noqa` / `# csc: disable` carries a stated reason |
| D9 | Every `TODO`/`FIXME` points to a revisit-ledger entry or scar id *(internal tracker, not external)* |

### Tier 1 — Semantic safety (blocks; fixed set, no opinions)

```
F821  undefined-name              B006  mutable-default-argument
F403/F405  import-star            B031  unclosed-resource
B023  loop-variable-closure       bare except / eval / exec
B904  raise-without-from          un-awaited coroutine (static half only)
F841  unused-variable
```

### Tier 2 — Plane hygiene (reports)

| ID | Rule |
|---|---|
| P1 | Derived artifacts are not in the source plane |
| P2 | One canonical location per module |
| P3 | Archive is marked, not mixed; not importable from live |
| P4 | Test plane isolation — `src/` must not import `tests/` |

### Tier 3 — Contract legibility (reports)

| ID | Rule |
|---|---|
| C1 | Authority-bearing functions state: what they establish, what they do NOT establish, what stales them |
| C1.5 | …and **how they fail** — documented exit paths |
| C2 | Module size triggers review, not failure |
| C3 | Flag on **authority-surface count**, not cyclomatic complexity |

### Tier 4 — Style (never blocks)

`S1` — gate on **delta**, not backlog. Block only newly introduced violations.

### CSC identity rules

- Every rule declares what it does **not** catch. `CSC_PASS != CODE_IS_GOOD`
- CSC gates itself on D1–D9 before gating anything else
- **Execution determinism** — zero network, pure static/AST. *If CSC requires a
  live runtime to verify a claim, it's an integration test, not a compiler gate.*
- Disabled rules aggregate into an **Unverified Claims** report

---

## §6 — DONOR SET: INDUSTRY SCARS — class DONOR

**Status: CANDIDATE ONLY. NOT ADMITTED.**

Imported from external practice. Under §0 these carry no authority and are not
interchangeable with §3. Each requires local reproduction before promotion.

| Donor line | Local status |
|---|---|
| `Redundancy != Availability` | not re-earned |
| `Active-Active != Twice_The_Throughput` | not re-earned |
| `Heartbeat_Received != Node_Healthy` | **adjacent to earned supervisor work** (crashloop/readiness/hold/PID identity) |
| `Backup_Created != Data_Restorable` | **earned locally** — handoff manifest declared 69162 bytes, actual 87801 |
| `Eventual_Consistency != Immediate_Read` | not re-earned |
| `Network_Partition != Graceful_Degradation` | not re-earned |
| `API_Response_200 != Success` | **earned locally** as `RECORDED_PASS != REPRODUCIBLE_PASS` |
| `Idempotency_Assumed != Idempotency_Enforced` | **earned locally** as `FIRST_RUN_PASS != IDEMPOTENT_REPLAY_PASS` |

**Note:** three of eight donor lines duplicate scars already earned here under
different names. That is evidence the ledger's earning process converges on known
industry failure modes independently — and it is also the reason the classes must
stay separate: a donor line that *looks* like an earned one may differ in scope.

Promotion path for any donor line:
```
reproduce the defect locally → write the local scar in local terms
→ cross-reference the donor line as ancestry, not as authority
```

---

## §7 — OPEN / UNRESOLVED

- Reservoir: snapshot-per-integration lacks stable item identity. Append-only
  ledger with stable IDs proposed, not implemented.
- CFE: `frontier: TRAINING_BODY_LHRSG__NO_NEW_TRAINING` — LHRSG read of the
  canonical learner-visible training bytes outstanding.
- CFE mechanism tournament: interference **WEAKENED**, horizon **WEAKENED**;
  starvation and wrong-neighbourhood remain live.
- Server: `ruff` configured and never run against the live tree (~3,400 findings,
  758 auto-fixable, 12 × `F821`).
- Server: `prometheus-client` undeclared in dev deps; `build/lib` committed
  (40,744 LOC duplicate).
- Server: handoff manifest stale — declared vs actual byte mismatch.
- Microseed: depth-six edge unearned; flexible expression queued third.
- Grand correspondence: parent↔child arbitration under *intrinsic vs extrinsic*
  goal conflict remains open on his side.

---

## §8 — COMPILER'S NOTE

The single most frequent failure across every project audited in this thread —
and in the compiler's own work within it — was one shape:

> **A cheap observable was checked and an expensive property was inferred from
> it.**

Stance instead of mechanism. Hash instead of currentness. Selection instead of
option set. Composition instead of retention. Configuration instead of
enforcement. A search hit instead of the source. A surface that looked
authoritative instead of the surface that was.

The apparatus in §3 is the accumulated set of places that substitution was caught.
Its size is a measure of how many ways it has been caught, not of how much
ceremony exists.
