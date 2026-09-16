# PCMMAD Receiver V30 — Commander's Intent / Active Worklist

Status: ACTIVE
Purpose: single current workstream map for V29→V30 modernization. This is not release evidence; it is the governing work queue and architecture boundary.

## Foundational axiom

**AXIOM-01 — INTENT IS A CONSTRAINT, NOT A CEILING.**

Meaning:
- inherited intent constrains direction, safety, and desired outcome;
- ancestry informs possibility but does not bound it;
- absence of precedent is not evidence of impossibility;
- composition should be tried before invention, but "not previously envisioned" is not a prohibition;
- novel mechanisms are lawful when they preserve/improve intended outcome, fit runtime invariants, and survive hostile verification.

This axiom SHOULD be injected through boring unavoidable runtime identity/health/bootstrap touchpoints in compact machine-readable form, not repeated as prose on every turn.

## Governing build metabolism

FIX THE INTENDED OUTCOME
→ inspect reality / ancestry / constraints
→ try composition before invention
→ PROBE
→ DERIVE
→ VERIFY
→ BUILD smallest justified change
→ ATTACK IT
→ ISOLATE FAILURE
→ STRIP / MUTATE
→ EMBODY
→ RECURSE
→ CSC / semantic gate / release qualification

BUILD != EMBODY.

## Architecture authority

### Runtime
PCMMAD Laboratory Runtime owns canonical truth and durable state:
- capability registry
- projects/repos/mounts/nodes
- durable jobs/process ownership
- results/artifacts
- continuity
- auth/policy/approval
- verification/readback
- availability/currentness

### Adapters
Adapters project runtime truth only:
- MCP
- OpenAPI / Custom GPT Actions
- CLI
- Operator HUD
- future transports

Transport is not architecture authority.

### Skills / OBE
AI-side operating intelligence composes runtime primitives and carries workflow doctrine. Skills do not duplicate durable runtime state or server-owned lifecycle semantics.

## AI attention / progress law

**LONG-RUNNING WORK SHALL NOT REQUIRE LONG-RUNNING MODEL ATTENTION.**

Derived runtime requirements:
- queueing, waiting, routing, research, model execution, browser automation, downloads, builds, archive work, and other long-running operations should return bounded decision-grade progress receipts;
- `jobs.wait` should default to bounded wait/check semantics, not indefinite tool occupation;
- ongoing work should distinguish PROGRESSING / QUIESCENT / POSSIBLY_STALLED / DEGRADED / TERMINAL where evidence permits;
- return only enough information for the AI to decide, explain status to the user, or choose the next action;
- bulk logs/results stay server-side behind handles/ranges;
- adapters may implement polling, bounded wait, progress events, subscriptions, or streaming, but Runtime owns lifecycle truth;
- recommended receipt fields: identity, lifecycle stage, actually-started state, elapsed time, queue position, last progress/heartbeat, health/stall signal, next expected transition, suggested recheck interval, output availability, warnings/failure digest, result/log handle.

**RETURN DECISION INFORMATION EARLY; STORE BULK WORK LOCALLY.**

## Holonic / ECS-ish native direction

The final runtime model SHOULD surface and regularize the holonic/ECS-like bones already present rather than layering a foreign meta-ontology over PCMMAD.

Interpretation:
- Entity = stable runtime identity (Project, Job, Process, Service, Artifact, Result, Node, BrowserSession, Transfer, Capability, etc.).
- Component = independently attachable state/contract/trait (Lifecycle, Ownership, ResourceBudget, Authority, Verification, Waitable, Cancelable, RangeReadable, Availability, InputContract, OutputContract, Telemetry, etc.).
- System = runtime mechanism that operates on entities/components (scheduler, approval, artifact, continuity, transfer, verification, routing, health, etc.).
- Holon = whole from below and component from above; bounded units should be independently inspectable/healthful/degradable while composing into larger wholes.

No "ECS rewrite" is authorized. Normalize the implicit model incrementally as current audits expose real seams.

## Final schema redesign — DEFERRED UNTIL WHOLE-RUNTIME QUALIFICATION

Do NOT treat the current OpenAPI/JSON schema as architecture authority.

At final "hells yeah, ready" stage:
- redesign the dated schema from the surviving runtime outward;
- use the holonic/ECS native model as the source of truth;
- treat JSON Schema/OpenAPI as validation/projection mechanisms, not the ontology;
- research and strip for parts from ECS, holonic systems, capability security, effect systems, reflective APIs, HATEOAS/hypermedia, workflow/state-machine systems, actor/supervisor models, typed planners, build systems, authorization models, resource calculi, and related fields;
- target compressed composability: many lawful operations/solutions derivable from native entities/components/systems rather than a giant flat catalog of pre-imagined verbs;
- preserve typed discovery/currentness/authority/verification and bounded projection;
- compile/derive MCP, OpenAPI, HUD, CLI, Skills discovery, docs, contract hashes, and test scaffolds from native runtime contracts where practical;
- `capabilities.invoke` must never become arbitrary-command god-tool behavior.

## Current active workstream

### P0 — execution truth
- [x] Preserve V29 baseline / isolated V30 working tree.
- [x] Remove duplicate async lifecycle authority; canonical scheduler wins.
- [x] Prove/fix cross-project global-lock contention first layer.
- [x] Build restart-safe runner receipts.
- [x] Fix fresh-cancel race.
- [x] Fix Windows atomic receipt replace race.
- [x] Distinguish venv launcher PID from actual worker PID.
- [x] Derive/integrate per-job Windows Job Object ownership anchor.
- [x] Prove ownership handshake / wrong-token / cancel-before-release / orphan cleanup negative contracts.
- [x] Full V30 tests green after P0-003 integration.
- [ ] Continue malformed/stale execution state matrix and full release qualification later.

### P1 — whole-server all-plane/all-tool hostile audit
- [x] Registry parity found/fixed seven missing live capabilities (transfer family + browser.upload).
- [x] Aggregate lab health optional-browser failure fixed.
- [x] Foreground batch bounded-result offload fixed.
- [x] Semantic plane changed from misleading health to truthful unavailable state when no qualified executor exists.
- [ ] VERIFY current ToolSpec/capability-contract edits before further mutation.
- [ ] Finish native capability metadata/effective authority/side-effect audit.
- [ ] Add bounded decision-grade progress/wait receipts across job/routing/queue/long-running surfaces.
- [ ] Result-handle range/preview/currentness audit.
- [ ] Research plane audit.
- [ ] Project/filesystem/context plane audit.
- [ ] Git plane audit.
- [ ] Continuity/state plane audit.
- [ ] SOP/governed-ingestion plane audit.
- [ ] Protocol plane audit.
- [ ] Transfer hostile pressure.
- [ ] Plugin lifecycle/isolation audit.
- [ ] Control/restart/HUD plane audit.
- [ ] Browser plane degraded/optional semantics audit.
- [ ] Schema/runtime/policy/imported-action parity audit.

### P1 — capability contract / MCP readiness
- [ ] capability_version / schema_version / schema_hash / contract_digest verified in cards.
- [ ] effective approval semantics visible in native descriptors.
- [ ] side-effect model clarified; historical `mutating=false` must not silently mean read-only.
- [ ] output contracts normalized where useful.
- [ ] capability availability/currentness normalized.
- [ ] target-bound approval object/handle design and tests.
- [ ] process identity object maturation (PID + creation time + executable/command fingerprint + owner/job/node).
- [ ] native projection matrix shared with Skill/MCP thread.
- [ ] contextual/lazy capability discovery without flattening full registry.

### P1 — donor quarry / Loop+
- [ ] Systematic cross-project strip-for-parts beyond UI work.
- [ ] External architecture/science research per unresolved plane.
- [ ] Preserve donor != authority and positive/anti-isomorph evidence.

### P1 — Operator HUD
- [x] Recover Aero-Glass / Liquid-Aero / YuiUI / ALCI / HoloFont donor corpus.
- [x] Recover CogTerm operational language.
- [x] Recover Forge/Singularity Works three-wing cockpit lineage.
- [x] Preserve current RAHL-HUD as behavioral/security ancestry.
- [x] Start receiver-owned operator-plane lifecycle in V30.
- [ ] Core-vs-optional/browser-degraded qualification split.
- [ ] Three-wing responsive layout.
- [ ] top corona / bottom command dock.
- [ ] Liquid-Aero balanced material tier.
- [ ] selective HoloFont.
- [ ] queue/job/progress/plane topology presentation.
- [ ] restart/transfer/result/continuity/Git/project state views.
- [ ] keyboard-first navigation and command palette.
- [ ] hostile security/performance/accessibility qualification.

### P2 — whole-runtime maturation
- [ ] Unified event/receipt projection over existing authority surfaces.
- [ ] Resource-aware admission/orchestration (CPU/GPU/RAM/I/O/thermal/host responsiveness).
- [ ] Whole-service constellation supervision (receiver/ngrok/HUD/browser/optional workers/sidecars).
- [ ] Multi-project/session/tab semantics.
- [ ] Artifact/result lifecycle maturation.
- [ ] Security architecture hostile pass.
- [ ] Capability/plugin lifecycle currentness/degradation semantics.

### P3 — convergence / release
- [ ] Strip unnecessary machinery.
- [ ] Attack every promoted explanation.
- [ ] CSC / semantic convergence.
- [ ] clean extraction/install/launcher/restart qualification.
- [ ] fresh package inventory/hashes.
- [ ] final schema/adapter redesign using surviving holonic/ECS runtime model.
- [ ] final MCP/OpenAPI/HUD/CLI projection qualification.
- [ ] V30 promotion/release.

## Claim discipline
Nothing checked above implies live promotion unless explicitly stated. V30 working-tree success != release qualification != live deployment.

## Cross-thread OBE / Skill campaign handshake

Status: ACTIVE COORDINATION CONSTRAINT

The OBE/Skill thread is authorized to begin research and derivation immediately under the R4.4 SOP using current architecture authority, lineage, recurring workflow evidence, and the V30 runtime/adapter compatibility contract.

It SHALL NOT freeze the final OBE↔Runtime interface until reconciled against the audited successor runtime.

Server-thread obligation:
- continue producing the missing high-authority discriminator: current successor runtime tree, live capability semantics, effective authority/currentness, job/result/process/project/artifact truth, and adapter-lossiness boundaries;
- publish projection-ready native contracts rather than client-specific assumptions;
- preserve enough currentness/versioning that the OBE side can safely detect drift rather than remembering stale interfaces.

Shared meeting point:
- `PCMMAD_RUNTIME_ADAPTER_PROJECTION_MATRIX_V0_1` + machine-readable companion;
- exact Runtime native concept ↔ MCP/OpenAPI/HUD/CLI projection;
- lifecycle, authority/approval, idempotency, result/readback, currentness/version, adapter lossiness, and adapter-only-state allowance;
- no parallel job/project/artifact/process/approval truths.

OBE-thread first campaign artifact expected:
`OBE_RESEARCH_AND_DERIVATION_CAMPAIGN_V0_1`
covering Commander’s Intent, ontology/boundaries, authority hierarchy, donor map, recurring workflow inventory, candidate Skill portfolio, server-vs-Skill placement rules, projection scaffold, open unknowns, hostile hypotheses, discriminators, and promotion gates.

Promotion rule:
Research/derivation may proceed now; interface promotion waits for successor-runtime reconciliation and live audit evidence.

## Worklist synchronization — bound approval authority earned

- [x] Target/argument/contract-bound approval challenge object implemented in V30.
- [x] Authority envelope separated from capability arguments at dispatch/batch boundary.
- [x] Single-use / expiry / replay / stale-contract / argument-mismatch / integrity hostile tests.
- [x] Legacy inline approval retained only as explicitly warned compatibility path; disable switch exists.
- [ ] Adapter/HUD confirmation UX and provenance binding.
- [ ] Approval challenge cleanup/revocation/introspection hardening if justified.
- [ ] Disable legacy inline approval by default after adapter migration.

## Shared research branch — Architectural Mechanism Quarry

Status: ACTIVE / cross-thread shared campaign branch

### Campaign law
We are NOT researching architectures to choose an architecture.
We are quarrying mechanisms that can sharpen structures PCMMAD already appears to have earned.

**MECHANISM FIRST. REPRESENTATION SECOND.**
**DONOR != AUTHORITY.**
**EMERGENT CAPABILITY IS ALLOWED; EMERGENT AUTHORITY IS NOT.**

A novel composite workflow/capability may lawfully emerge from existing runtime primitives when its requirements/effects compose and the whole survives verification. It does NOT inherit authority merely because its parts possessed authority. Composite guarantees, authority, currentness, resources, and verification must be requalified at the composite level.

### Donor families to quarry
- ECS: identity separated from orthogonal state; systems query compatible component sets.
- Holonic systems: bounded parts compose into higher-order qualified wholes.
- Entity/component relational models: relationships become queryable state.
- Capability security: explicit, attenuable authority rather than identity-implied authority.
- Effect systems: consequences represented explicitly in capability contracts.
- Blackboard architecture: producers publish useful state without pairwise consumer coupling.
- Actor/supervisor models: isolated ownership, messaging, lifecycle, restart/failure semantics.
- Self-describing systems: current runtime exposes current structure/capability.
- Hypermedia affordances: current state advertises lawful next transitions.
- Dynamic service composition: resolve providers by requirements/provides/currentness/resources.
- Reflective systems: controlled introspection over contracts/state/effects/resources/version.
- Planning over typed state: transitions chosen from explicit preconditions/effects.
- Resource/component queries: select providers by current capabilities/resources/authority.
- Graph/query systems: traverse provenance, ancestry, topology, authority, dependency/currentness.

### Required hostile admission test for every donor mechanism
Compare CURRENT PCMMAD MECHANISM vs DONOR-DERIVED CANDIDATE.

Candidate must materially improve one or more of:
- special-case reduction;
- schema rigidity reduction;
- lawful composition;
- currentness;
- authority isolation;
- discovery;
- observability;
- context/tool load;
- failure containment;
- important query expressiveness.

Without introducing unacceptable:
- duplicate truth/state;
- parallel ontology;
- hidden mutable state;
- orchestration burden;
- weaker determinism;
- harder simple operations;
- authority widening;
- transport coupling.

### Quarry record format
For each candidate:
- donor family
- mechanism
- historical provenance
- existing PCMMAD analogue
- candidate sharpening
- expected gain
- added complexity
- authority consequences
- state consequences
- failure modes
- strongest counterexample
- minimum discriminator/experiment
- disposition: REJECT | DEFER | QUARRY | CANDIDATE | EARNED

### Vocabulary restraint
No donor gets to rename existing PCMMAD concepts unless the new distinction earns its way in.
Examples:
- actor supervision may donate lifecycle invariants without renaming jobs as actors;
- ECS may donate orthogonal state/query mechanisms without requiring an ECS framework rewrite;
- capability security may donate attenuated authority without forcing an object-capability rewrite;
- effect systems may donate consequence contracts without building a programming language;
- blackboards may donate decoupled publication semantics without creating another central database.

### Immediate runtime relevance
Current V30 work already presents natural quarry targets:
- ToolSpec effect traits / authority / currentness → effect-system + capability-security quarry;
- bound approval authority → capability-security quarry;
- job progress/affordances → hypermedia/self-describing quarry;
- process/job ownership → actor/supervisor quarry;
- projects/jobs/artifacts/results/services/capabilities as stable identities with orthogonal state → ECS/relational quarry;
- projection matrix → reflective/self-describing quarry;
- resource-aware future admission → resource/component-query quarry.

### Composite law
A higher-order capability/workflow assembled from native primitives SHALL be treated as a new qualified whole when promoted:
- its own boundary;
- preconditions;
- effects;
- authority envelope;
- currentness;
- resource envelope;
- failure semantics;
- verification/readback;
- result contract;
- lineage/provenance.

Parts may compose. Guarantees and authority do not silently compose.
