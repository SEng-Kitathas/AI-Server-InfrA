# PCMMAD Receiver V30 — SOP-Governed Hostile Build Contract

Status: ACTIVE BUILD GOVERNOR
Baseline: immutable V29 RC1 copy, SHA-256 5baf9b66a9137d950aeabac2ea76fbbb919e177f90788e5341ee6e15a80b89d8
Working body: V30_WORKING/PCMMAD_receiver

## Authority
1. PCMMAD canonical runtime specification
2. Unified implementation doctrine / CODEX-Omega-derived standards
3. CSC SOP set, especially holonic audit, anti-pattern inversion, promotion/recursion, freshness/mutation lag, general universalization, unreliable-plane execution methodology
4. Receiver architecture invariants and release contract
5. V29 spec and verified runtime behavior
6. External systems and other projects as evidence/parts donors only

## Build cycle — mandatory at every meaningful slice
PROBE -> DERIVE -> VERIFY -> EMBODY -> RECURSE.

A slice is not complete because code exists or a process exits zero. It is complete only when the claimed invariant is directly tested, read back from machine truth, integrated into release gates where appropriate, and recursively checked for cross-plane regressions.

## Hard invariants
- Baseline V29 tree remains immutable.
- Reads do not mutate.
- Submitted != started != running != completed != durable-output != registered != promoted.
- All long-running work owns durable machine-readable state and output paths.
- Queue/bridge failure causes escalation to a stronger surviving plane; repeated blind retry is a defect.
- Required planes fail hard; optional planes degrade explicitly and visibly.
- Server-native capability may expand without forcing GPT schema expansion.
- No anonymous filesystem surface; capability tokens are narrow, scoped, expiring, and revocable.
- Project roots/mount roots remain authoritative path boundaries.
- Mutations are explicit, typed, observable, and recoverable where feasible.
- Final-artifact verification outranks in-memory success.
- Every promoted change receives negative-contract, concurrency/replay/failure-injection pressure appropriate to its risk.
- No big-bang rewrite without a demonstrated invariant that incremental replacement cannot satisfy.

## Hostile failure classes to inject
- process dies between submit and persist
- persist succeeds but worker never starts
- worker starts twice
- timeout races completion
- terminate races completion
- server restarts while jobs are pending/running/completed-unregistered
- stdout/stderr exceed response ceilings
- result registration fails after execution succeeds
- output file exists but is truncated/partial
- stale PID/job identity reuse
- queue saturation/backpressure
- cancellation during blocking child I/O
- orphan subprocess after parent/server death
- source file mutates after export ticket creation
- upload duplicate/out-of-order/corrupt chunk
- cross-volume atomicity assumptions
- browser sidecar unavailable or wedged
- research provider returns partial/stale results
- plugin load failure/collision
- schema claims capability absent from runtime

## Donor import rule
For every external or cross-project idea:
1. identify donor mechanism
2. state functional contract / invariant
3. positive isomorph: why it could solve a receiver seam
4. anti-isomorph: where the analogy breaks
5. smallest native embodiment
6. failure injection / verification
7. promotion only if receiver-native and measurably stronger

## Priority attack order
P0 — execution/async truth, durability, restart recovery, cancellation, registration/readback
P0 — transfer plane integration and security/resume/cleanup/revocation
P1 — observability and one coherent machine-truth event surface across planes
P1 — capability registry/schema/runtime parity and plugin isolation
P1 — supervisor/health model for receiver, ngrok, browser sidecar, workers
P1 — backpressure/resource budgets and host-friendly scheduling
P2 — artifact/result registry, lineage, promotion certificates where generalized
P2 — research/browser/semantic plane resilience and deterministic handoff contracts
P2 — cross-project component reuse / plugin packaging
P3 — operator cockpit, diagnostics, self-healing playbooks, release automation

## Promotion rule
No V30 release archive is created until fresh-extraction verification, regression, negative contracts, replay, concurrency, security boundary, live parity, package integrity, launcher audit, SOP freshness, and final manifest verification all pass against the V30 body.

## AI-native / vendor-neutral operator invariant
The receiver is primarily operated by AI agents and SHALL be optimized for agent usability without platform lock-in.

Required properties:
- provider-neutral HTTP/JSON and server-native tool contracts; no OpenAI-, Anthropic-, Google-, or single-SDK authority assumptions
- model/vendor identity is metadata, never a control-plane dependency
- stable capability discovery with explicit versions, schemas, danger/mutation semantics, and feature flags
- small composable tools preferred over giant ambiguous calls
- bounded outputs, pagination/ranges/result handles, resumable binary transfer, and server-side storage by default
- typed errors with retryability and stage semantics; no success-by-HTTP-200 ambiguity
- idempotency for mutation/execution surfaces where duplicate agent calls are plausible
- explicit lifecycle truth: accepted/submitted/queued/started/running/completed/output-durable/registered/promoted remain distinct
- machine-readable receipts and hashes designed for agent readback rather than prose parsing
- deterministic dry-run/plan surfaces before destructive mutation where practical
- introspection surfaces that expose current capability, constraints, queue pressure, degraded planes, and recovery options
- transport and protocol semantics SHALL remain usable by arbitrary future agents/CLIs/MCP-style clients without requiring a proprietary hosted control plane
- vendor-specific adapters MAY improve ergonomics but SHALL be leaf adapters over the neutral core and SHALL NOT own project truth, execution truth, or continuity

Agent-UX test question for every new surface: "Can an unfamiliar competent agent discover what this does, call it safely, distinguish partial from complete success, resume after interruption, and verify the result without hidden platform knowledge?"
