# PCMMAD Receiver V30 — Doctrine Snapshot

## A-042 active doctrine delta — 2026-09-07

- `SESSION_IDENTITY != FENCED_MUTATION_AUTHORITY`.
- `LEASE_STATE_LOCK != MUTATION_CONSEQUENCE_LOCK`.
- `EXPIRED_SAME_GENERATION_FOLLOW_ON != POST_TAKEOVER_AUTHORITY`: an already-authorized Runtime follow-on may finish after TTL only while the generation has not been superseded; takeover fences it.
- `RUNTIME_JOB_TRUTH != PROJECT_JOURNAL_CONSEQUENCE`: scheduler/job reconciliation remains Runtime-owned; project journal consequences obey project ownership.
- `NO AUTHORITY SMUGGLING THROUGH CAPABILITY ARGUMENTS`.
- `RuntimeAuthorityEnvelope` is the adapter invocation authority projection; approval and project mutation are independent dimensions.
- path-mediated project mutations are fenced by resolved project identity; a single consequence may not span two project ownership domains.
- two-phase recovery/apoptosis validates authority before process termination, then reacquires the consequence guard for project/Git writes to avoid kill-vs-lock deadlock.
- the non-PCMMAD V30 OBE/Skills bundle is donor evidence only. Runtime owns currentness/authority; Skills compose. A-001 is queued post-A-042.
- final schema redesign remains LAST and requires whole-runtime convergence + explicit `hells yeah, ready`.


Last updated: 2026-09-07 15:21 ET

## Active mode-control state
- Current checkpoint mode: CHECKPOINT / RECOVERY
- Workstream mode after re-entry: BUILD-COMMIT with AUDIT pressure
- Why: user explicitly requested full continuity survival because the thread is full; broad implementation resumes only after continuity repair and current red-suite blocker is reconciled.

## Primary constitutional law

**AXIOM-01 — INTENT IS A CONSTRAINT, NOT A CEILING.**

Operational interpretation:
- intent constrains direction, safety, and desired outcome;
- ancestry informs possibility but does not bound possibility;
- “not previously envisioned” is not “forbidden”;
- composition before invention remains strong default;
- novelty must still survive hostile verification, authority, and currentness constraints.

AXIOM-01 is intentionally ambient through runtime health/identity via a compact constitutional seed rather than repeated prose.

## Governing engineering metabolism

Canonical current loop:

FIX THE INTENDED OUTCOME
→ inspect reality / ancestry / constraints
→ try composition before invention
→ PROBE — what actually happens?
→ DERIVE — mechanism/invariant
→ VERIFY — distinguish strongest alternative
→ BUILD smallest justified change
→ ATTACK IT — assumptions/boundaries/harnesses/authority/currentness/resources/concurrency/malformed or stale state/restarts/partial failure/wrong inputs
→ ISOLATE FAILURE — implementation/wiring/representation/authorization/execution/resource/observability/evaluator/harness
→ STRIP / MUTATE — remove machinery, vary variables, counterexamples, attack explanation
→ EMBODY — only survivor becomes code/invariant/test/instrumentation/protocol/continuity/scar
→ RECURSE — next highest-value discriminator
→ CSC / semantic gate / release qualification

**BUILD != EMBODY.**

Supporting machinery is subordinate to this loop:
- Attention Reservoir = persistent neglected anomalies/alternatives/deferred ideas
- Semantic Helix = observation → explanation → discriminator → attack → scar → new understanding
- OARR = observation/attack/replay/revision around verify/attack/isolate/strip/recurse
- Loop+ = external science/architecture strip-for-parts, including positive and anti-isomorphs
- CSC = convergence/release qualification after recursive survival
- scar ledger / revisit / trace / continuity = persistent support surfaces.

## Runtime / Skill / adapter ontology

Locked split:
- **PCMMAD** = multi-model hostile engineering/research methodology
- **Laboratory Runtime** = truth + state + deterministic/durable capability
- **Adapters** = MCP / OpenAPI / CLI / HUD / future transports
- **OBE + Skills** = reusable AI/operator intelligence
- **Model** = replaceable co-processor
- **Project Chat** = replaceable mission interaction surface

### Runtime authority law
**TRANSPORT IS NOT ARCHITECTURE AUTHORITY.**

MCP/OpenAPI/HUD/CLI must project Runtime truth. They may own only transport/session/presentation state that does not become a second job/project/artifact/process/approval truth.

### Mechanism placement law
**The mechanism lives where the state lives; judgment about how to compose mechanisms lives in the Skill/model unless an earned invariant should be lowered into Runtime enforcement.**

Skill behavior may graduate into a server invariant only after repeated evidence shows composition/model discretion is undesirable or insufficient.

## AI attention doctrine

**LONG-RUNNING WORK SHALL NOT REQUIRE LONG-RUNNING MODEL ATTENTION.**

**RETURN DECISION INFORMATION EARLY; STORE BULK WORK LOCALLY.**

Implications:
- waits are bounded control operations, not open-ended model occupation;
- ongoing jobs should return compact decision-grade receipts;
- bulk stdout/stderr/results stay server-side behind bounded output/range/result handles;
- adapters may poll, long-poll briefly, stream, subscribe, or receive progress events, but Runtime owns lifecycle truth;
- useful distinctions include PROGRESSING / QUIESCENT / POSSIBLY_STALLED / DEGRADED / TERMINAL when evidence supports them.

## ICF-CS v1.1 — current binding additive continuity doctrine

Authority status:
- sealed base: canonical R4.4 SHA `04f3e94efe8c901cc83a12a9c8531be8a9bb350728b8f9eba53db0fd082b3bbc`;
- current additive ICF-CS v1.1 standard SHA `62be845da364ae81f59b6320c9b34b136236bf5be8aa8036018da48efcb754f4`;
- current v1.1 payload SHA `f6f4ab2bafdb0ef2a7db1622a00462990baf980284d5b33827807caea1d41f63`;
- detached v1.1 release receipt SHA `418346ed6373887b5b924e71ca2bf4b83effad20b7269ab40607f5d2750b970c`;
- ICF-CS v1.0 payload `51ed7f424dff7c67534f7e53e8a7c10ebd93bf33ea575eea49dc3f05c24a92a9` remains historical/demoted qualification lineage;
- scope: continuity/process control only.

Core law:
**DIRECTION != CONSTRAINTS != FRONTIER != HISTORY**

Version-agnostic cold-start grammar:
**CURRENT STATE -> ICF-CS -> CURRENT CANONICAL SOP + NEXT/DOCTRINE/REVISIT/TRACE -> LIVE SHADOW -> DTS -> LIVE READBACK BEFORE MUTATION**

Conflict grammar:
**CONFLICT -> RECOVERY/AUDIT -> LOCALIZE -> REPAIR/SUPERSEDE -> READBACK -> RESUME**

Binding non-equivalences:
- HISTORICAL_HANDOFF != CURRENT_INGRESS
- DONOR != AUTHORITY
- RECENT_TIMESTAMP != CURRENT_AUTHORITY
- STALE_GREEN != CURRENT_EVIDENCE
- CURRENT_INGRESS_POINTER != CURRENT_STATE_PROOF
- EXPECTED_LABEL != PROMPT_CONTENT
- BENCHMARK_ITEM != DOCTRINE_AUTHORITY
- FORMAT_FAILURE != SEMANTIC_FAILURE
- SEMANTIC_AGREEMENT != AUTHORITY_FIDELITY
- AUTHORIZED_GOVERNING_INTENT != FACTUAL_TRUTH
- CONTINUITY_MAP != CURRENT_STATE_EVIDENCE
- REMEMBERED_SUMMARY != SOURCE_CONTACT
- SUMMARY_FIDELITY != SOURCE_COMPLETENESS.

Current exact authority surfaces:
- `INTENT_CONSTRAINT_FRONTIER_CONTINUITY_STANDARD.md` SHA `62be845da364ae81f59b6320c9b34b136236bf5be8aa8036018da48efcb754f4`;
- current v1.1 machine descriptor SHA `d67726aeb402c280770eeaf314068ed7a1330beb21167d9d6d9b7c4674425bb0`;
- current v1.1 qualification contract SHA `7d20ed708adb4f7ee147b56da41deac77146b56fc85bd769be3a6d240b3e2029`;
- current v1.1 detached release receipt SHA `418346ed6373887b5b924e71ca2bf4b83effad20b7269ab40607f5d2750b970c`;
- `CURRENT_CANONICAL_SOP_POINTER.md`;
- `checkpoints/ICF_CS_CURRENT.md`.

Historical v1.0 machine/claim/qualification artifacts remain preserved as lineage and do not define current authority.

Maintenance law:
- Intent changes only by explicit governing direction;
- Constraints change when evidence/authority/claim ceilings change;
- Frontier changes whenever current verified/provisional/blocked/deferred/next state changes;
- History preserves chronology without automatic current authority;
- consequence-bearing readback follows mutation.


## Governance Contact v1.0 — locally reconciled pending doctrine

Governance Contact v1.0 is published and repository-admitted on the shared Git authority plane and locally reconciled in Receiver as **NOT ACTIVE**. Its sidecar governs current local interpretation without rewriting Receiver product/runtime authority.

- release ZIP SHA `c4ab4a516e088b6c28b5240d6b3877d2e3fb889a8bbbfd406e8e0c73bebdd1ae`;
- detached receipt SHA `cf2e7bd8e5ed613d3c3a99b7f8645833ddb742ac4939bd1719092b277ef286e6`;
- package qualification SHA `509aba0bb859db49d9311e08acae98d8c7bdfbbb1d41cdd157d1675e70f8a302`;
- local sidecar `GOVERNANCE_CONTACT_V1_0_LOCAL_RECONCILIATION.md`.

`SIDECAR != TRUTH`
`LOCATOR != AUTHORITY`
`CARRIER_PRESENT != PROJECT_SPECIFIC_AUTHORITY_REWRITE`
`POST_PUBLICATION_READBACK != ACTIVE`

## Capability availability/currentness doctrine

**REGISTRATION != CAPABILITY_AVAILABILITY != TARGET_HEALTH.**

Rules:
- registry presence proves a known contract + registered handler, not current dependency/provider health;
- ordinary discovery/listing SHALL remain probe-free;
- dynamic currentness SHALL be requested explicitly and bounded;
- shared providers SHOULD be probed once per bounded availability request, not once per capability;
- provider-probe failure SHALL NOT become green; use UNKNOWN/unavailable with bounded evidence;
- resident availability means handler dispatchability only, not success for arbitrary inputs or target/service health;
- provider scope must be explicit when overrides can change outcome (for example semantic default runtime vs per-call explicit runtime/path overrides);
- adapters project Runtime availability truth; adapters SHALL NOT own a second availability state.

Current earned dynamic providers: browser bridge and semantic Monster default search runtime. Additional providers require evidence, not blanket conversion.

## Git publication doctrine

**GIT_PUBLICATION != LIVE_RUNTIME_PROMOTION.**

Git now supplies durable source/publication lineage for the V30 body. It does not prove live receiver replacement, live capability parity, service health, release qualification, or deployment.

Publication cadence for earned changes: verify exact Git root → exclude generated/secrets/local state → qualify mutation → commit → push → remote-head readback → continuity receipt. Speculative BUILD state is not pushed as earned EMBODY state unless explicitly requested. Byte-sensitive source is protected from line-ending normalization with repository `* -text`.

Git cold-start publication rule:
- a repository MAY carry a commit-bound mirror of ICF-CS continuity surfaces so a fresh thread can recover when the outer project store is unavailable;
- that mirror is **navigation/recovery evidence, not a second live authority**;
- when local canonical project-store surfaces exist, reconcile them and perform fresh consequence-bearing readback before mutation;
- the repo ingress SHALL preserve `CURRENT_INGRESS_POINTER != CURRENT_STATE_PROOF` and `GIT_PUBLICATION != LIVE_RUNTIME_PROMOTION`;
- Runtime↔OBE/Skills boundaries and shared projection contracts are load-bearing handoff content and SHALL be present in the Git recovery surface.

## HUD availability/readiness presentation doctrine

HUD availability is a **projection**, not a second truth store.

- catalog discovery stays probe-free;
- explicit dynamic checks use native `lab.capabilities.availability`;
- HUD probe evidence is ephemeral/session-local and bound to capability `contract_digest`;
- stale digest mismatch discards the check;
- optional provider outage may degrade presentation without making core Runtime/HUD readiness false;
- scoped/default provider unavailability SHALL NOT be converted into unconditional dispatch prohibition when explicit overrides may change outcome.

`HUD_PRESENTATION != RUNTIME_AVAILABILITY_AUTHORITY`.

## Truth and authority doctrine

Always distinguish:
- VERIFIED
- OBSERVED
- INFERRED
- PROVISIONAL
- SPECULATIVE / HYPOTHESIZED
- UNKNOWN

Never promote inference by tone.

Key laws/scars:
- TOOL SUCCESS != TASK SUCCESS
- submitted != started != running != completed != registered != promoted
- current process PID != stable ownership identity
- PID_ALIVE != SAME_PROCESS
- SCHEDULE_FAILURES_REQUIRE_SCHEDULE-LEVEL TESTS WHERE PRACTICAL
- FAILURE_SEED + DETERMINISTIC_TRACE > UNREPLAYABLE_FLAKE as a verification receipt
- DERIVED_STATE_IS_A_FOLD_NOT_A_REBUILD — steady-state mutation should extend a verified fold/checkpoint/cache when lawful; full rebuild remains recovery/audit backstop
- INCREMENTAL_STEADY_STATE != NO_FULL_RECOVERY_PATH
- A037_FAST_CURRENTNESS_WITNESS != CRYPTOGRAPHIC_HISTORY_PROOF
- file access != process ownership
- shared immutable artifact != shared runtime ownership
- research plane != continuity/write authority
- adapter result success != whole-task success
- newer file != automatic authority
- summary != source read when completeness matters.

## Bound approval doctrine

Authority is not a boolean argument.

Current V30 direction:
- risky operation challenge is bound to exact capability contract + exact arguments/target + freshness;
- authority travels in a separate envelope;
- single-use/replay/stale-contract/argument mismatch must fail typed;
- legacy inline approval is transitional, explicitly unbound, and must eventually be disabled after clients migrate;
- composite capabilities do not inherit authority merely because their parts did.

**EMERGENT CAPABILITY IS ALLOWED; EMERGENT AUTHORITY IS NOT.**

## Architectural Mechanism Quarry

Campaign laws:
- **MECHANISM FIRST. REPRESENTATION SECOND.**
- **DONOR != AUTHORITY.**
- **EMERGENT CAPABILITY IS ALLOWED; EMERGENT AUTHORITY IS NOT.**

We are not researching architectures to choose an architecture. We quarry mechanisms that improve already-earned PCMMAD structures.

Active quarry families:
- ECS
- holonic systems
- entity/component relational models
- capability security
- effect systems
- blackboard architecture
- actor/supervisor models
- self-describing systems
- hypermedia affordances
- dynamic service composition
- reflective systems
- planning over typed state
- resource/component queries
- graph/query systems.

Every donor-derived candidate must show material gain over current PCMMAD without unacceptable duplicate truth, parallel ontology, hidden mutable state, orchestration burden, weaker determinism, harder simple operations, authority widening, or transport coupling.

Disposition vocabulary:
REJECT / DEFER / QUARRY / CANDIDATE / EARNED.

## Holonic / ECS-ish runtime direction

The runtime already has partial bones; no framework rewrite is authorized.

Working meanings:
- Entity = stable runtime identity
- Component = orthogonal attachable state/contract/trait
- System = mechanism acting on compatible entity/component sets
- Holon = whole from below; component from above.

Examples:
- Job + Lifecycle + Waitable + Cancelable + Ownership + Telemetry + ResultLinks → scheduler/progress/cancel/output systems apply.
- Result + RangeReadable + ContentIdentity → preview/range/get systems apply.
- Service + OwnershipVerified + Restartable + Health → status/restart/verify systems apply.
- Capability + Contract + Authority + Availability + Verifier → discovery/invocation/policy systems apply.

Do not rename existing concepts merely to satisfy donor vocabulary.

## Capability contract direction

Native capability contract should converge toward:
- capability identity
- domain/category/tags
- capability version
- schema version/hash/contract digest
- input/output contract
- availability + blockers/currentness
- side-effect class + effect traits
- effective authority/approval requirement
- target grounding
- idempotency semantics
- sync/async/durable/replay/wait/progress traits
- resource class
- result/artifact outputs
- earned preconditions/postconditions/verifier
- failure classes/retryability
- deprecation/supersession.

`capabilities.invoke` must never become arbitrary command-text god-tool behavior. Lazy discovery should come from typed contracts and bounded namespaces.

## Final schema doctrine

The inherited JSON/OpenAPI design is not architecture authority.

The final schema redesign is explicitly **deferred until whole-runtime convergence** and explicit user “hells yeah, ready” trigger.

At that point:
- start fresh research, not cosmetic cleanup;
- native holonic/ECS-ish Runtime contract is source authority;
- JSON Schema/OpenAPI are validation/projection leaves;
- quarry type systems, effect systems, capability security, reflective/hypermedia systems, planners, graph/resource calculi, and related mechanisms;
- optimize for compressed lawful composability, agent discoverability, bounded context, authority, currentness, verification, and dynamic affordances;
- derive projections for MCP/OpenAPI/HUD/CLI/Skills where practical.

## Operator HUD doctrine

RAHL-HUD lineage is the operator UI/control surface for the server direction, but presentation may never become runtime truth authority.

Recovered design language to preserve:
- Aero-Glass / Liquid-Aero
- HoloFont
- Ui / YuiUI
- CogTerm
- three-wing cockpit
- Forge / Singularity Works donor lineage
- top corona / bottom command dock
- keyboard-first command surface
- queue/job/progress/topology and runtime state presentation.

Design goal: personally distinctive/sexy without sacrificing operational density, security, accessibility, or degraded-mode clarity.

## Active challenge

A-042 is now a **qualified engineering candidate / Git publication pending**. Current pre-publication Git remains recovery HEAD `014dc68c954ab099c43118bd5072349fb93385d3`; A-041 `a97a00f67f3b79dbbe18e092d29b8971e588d4a2` remains the last published engineering feature until the dedicated A-042 commit is created. Candidate inventory `e2dcb52475bf5869b6f3ebc4561955e27ef52669291bb7e06aa96ca196b2f31e`; full qualification `345 collected / 344 passed / 0 failed / 1 conditional skip`.

Current authority ordering remains:
`PERSISTED PROJECT + EXACT WORKTREE + GIT/REMOTE + CURRENT TEST READBACK > REGISTERED/RECOVERY MIRROR > VISIBLE CHAT NARRATIVE`.

Current A-042 laws are earned for the candidate bytes:
- `SESSION_IDENTITY != FENCED_MUTATION_AUTHORITY`;
- `RuntimeAuthorityEnvelope` is the adapter invocation authority projection;
- `LEASE_STATE_LOCK != MUTATION_CONSEQUENCE_LOCK`;
- `NO AUTHORITY SMUGGLING THROUGH CAPABILITY ARGUMENTS`;
- already-authorized expired same-generation follow-on may finish only before takeover; superseding generation fences it.

Governance Contact Phase-1 locator remains present while token and ACTIVE receipt remain absent: `GOVERNANCE_CONTACT_NOT_ACTIVE_AT_THIS_TARGET`.

The remaining A-042 challenge is publication/readback, not contract derivation: refresh canonical continuity + Git-contained handoff, create the dedicated engineering commit, push, independently read remote HEAD, then record post-push continuity. Live Runtime promotion remains separate.

## Current quality/search posture

- Verification pressure: maximum practical; tests/readback after mutation
- Cross-disciplinary pressure: active via Mechanism Quarry
- Maximum-attainable pressure: active; “works” is insufficient if authority/currentness/continuity remain fake
- Divergence/wrong-path pressure: preserve failed mechanisms and scars; do not smooth contradictions
- Local-first: anything the server can inspect/store/execute/rehydrate should be server-side
- Thread-life: server-side bulk storage/results; chat carries minimum control evidence

## Recently promoted
- bounded AI progress/wait semantics
- AXIOM-01 ambient health seed
- bounded result preview/range semantics
- richer capability contract/effect traits
- bound approval authority runtime object
- bounded/scoped context reads and rehydration
- exact Git repo grounding/postcondition verification.
- physical bounded sync subprocess capture + typed verification claim ceiling
- web public-read credential/header/currentness contract hardening
- ICF-CS authority-separated rehydration/cache-currentness architecture remains earned; first qualified under v1.0, with current process authority now v1.1.
- compact 30-operation adapter separate bound-authority projection qualified without expanding the compatibility surface.
- native capability availability/currentness model qualified with explicit bounded provider probes and registration/health separation.
- MCP manifest preserves native availability contract/currentness semantics without executing provider probes.

## Recently demoted / superseded
- boolean approval as sufficient authority
- `mutating=false` as proof of read-only semantics
- whole-file materialization followed by response slicing as “bounded”
- project path merely being under a globally allowed root as sufficient project scope
- Git running successfully from cwd as proof of exact repo ownership
- static inherited schema as final architecture authority
- named Job Object existence alone as durable ownership; the runner-held handle composition superseded that hypothesis.

## Doctrine drift watchlist
- continuity surfaces becoming stale while ad-hoc reports stay current
- audit/report state advancing farther than registered Frontier promotion state
- transient/recent internal logs outranking current ingress
- stale index/cache excerpts impersonating current artifacts
- live vs V30 working-tree confusion
- adapter semantics promoted into Runtime ontology
- stale capability contract remembered by OBE
- old reports with claim ceilings that later work superseded
- long waits trapping model attention
- fake health when optional dependencies fail
- effect/authority metadata remaining symbolic rather than behaviorally enforced
- UI approval logic widening authority
- final schema redesign started prematurely.

## Next doctrine-changing event
Any new evidence that changes ICF-CS authority roles, the Runtime/OBE boundary, the holonic/ECS direction, approval authority, or final schema sequencing requires this snapshot to update.
Historical rollover freeze evidence: A-042 recovery baseline was the 13-file V2 manifest `fad436518624dae080a1fb990a5097c9a0d1a55a7438aa43330f62499a6e9fe2` / ZIP `6bd6aba1a615ebcd90cd6691a62b09554e6e2af6252d8fca27453fc19a6f4a4b`; Git handoff contains all 13 recovery copies and passes 11/11 verifier. The earlier 11-file checkpoint is historical intermediate evidence; fresh worktree readback still outranks V2 if WIP advances again.


Historical rollover publication evidence: recovery-only commit `4c31f4cee2393650c090e49d585ae61b14879944` / tree `2efa45bc35463e45902395d2ddb5af4ace668ae6` was remote-exact at that checkpoint. It is superseded as current Git recovery authority by fresh readback; see the A-042 frontier above.

## Governance Contact activation resolver — CURRENT PRECEDENCE
Marker: `GOVERNANCE_CONTACT_ACTIVATION_RESOLVER_CURRENT_PRECEDENCE_V1`
Target: `local:PCMMAD_RECEIVER_LAB`

Current Governance Contact activation/currentness SHALL be resolved only through `authority/rahl-sop/GOVERNANCE_CONTACT_V1_0_ACTIVATION.md`.
Target-local locator SHA-256: `380059a4e8204c35f82b3a232d45f962bb20038eec3d9eecb44f4411809346bd`.
Expected activation token SHA-256: `b5a2e35f300c6f72d93fc80b877ef0478a3628442b705e50f6893cbceafb5094`.

Any earlier Governance Contact lifecycle sentence in this file that says pending, NOT ACTIVE, LOCALLY_RECONCILED_AS_NOT_ACTIVE, or authority effect NONE is retained as a **pre-activation snapshot** and is superseded for present activation currentness by this resolver block. Historical release/reconciliation evidence is not rewritten.

Resolver rule:
- exact token absent at locator sibling -> `GOVERNANCE_CONTACT_NOT_ACTIVE_AT_THIS_TARGET`;
- token present but wrong hash/invalid fields -> `RECOVERY_AUDIT_NO_AUTHORITY`;
- exact valid token present -> `GOVERNANCE_CONTACT_LOCALLY_BINDING_ADDITIVE_PROCESS_DOCTRINE`;
- global ACTIVE claim additionally requires 17/17 exact-token propagation/readback and a detached activation-completion receipt.

This block does not assert token presence or absence. It remains semantically valid across the token transition. It creates no Receiver product/runtime/domain authority.

`SUPERSESSION != SOURCE_REWRITE`
`CURRENT_INGRESS_CONTACTS_LOCATOR != LOCATOR_RESOLVES_ACTIVE`
`ACTIVATION_TOKEN_PRESENT_AT_ONE_TARGET != GLOBAL_ACTIVE`
`CARRIER_PRESENT != PROJECT_SPECIFIC_AUTHORITY_REWRITE`
