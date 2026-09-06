# PCMMAD Receiver V30 — Commander's Intent / Architecture Direction / Active Campaign

Status: **ACTIVE / CURRENT AS OF 2026-09-06 00:51 ET**
Purpose: this is the governing engineering-direction surface for the V29→V30 modernization. It is not release evidence. It exists so a fresh thread can recover not only *what is being worked on*, but *why the architecture is being shaped this way*, which choices are locked, which are provisional, and which paths are explicitly demoted.

This file supersedes older status/checklist readings inside prior revisions of `V30_COMMANDERS_INTENT_AND_WORKLIST.md`. Historical pre-normalization copy is preserved under `reports/_history/`.

---

## 1. Foundational axiom

**AXIOM-01 — INTENT IS A CONSTRAINT, NOT A CEILING.**

Meaning:
- inherited intent constrains direction, safety, and desired outcome;
- ancestry informs possibility but does not bound possibility;
- absence of precedent is not evidence of impossibility;
- composition should be tried before invention, but “not previously envisioned” is not a prohibition;
- novel mechanisms are lawful when they preserve/improve intended outcome, fit runtime invariants, and survive hostile verification;
- implementation ancestry is evidence and quarry, not capability ceiling.

AXIOM-01 should ride boring, unavoidable identity/health/bootstrap touchpoints in compact machine-readable form rather than depending on conversational repetition.

---

## 2. Commander's Intent — desired end state

Build a **production-worthy PCMMAD Laboratory Runtime** from the V29 receiver lineage.

The target is not “a better Custom GPT backend” and not “an MCP server with lots of tools.” The target is a durable local laboratory substrate that can survive changing clients, models, transports, threads, and UI layers.

Desired end-state qualities:
- canonical truth and durable state live where the machine state actually lives;
- runtime primitives are typed, inspectable, current, bounded, composable, and verifiable;
- long-running work proceeds durably without occupying model attention for its entire duration;
- authority is explicit, scoped, target-bound, current, and resistant to replay/smuggling;
- projects/jobs/results/artifacts/processes/services/continuity remain first-class runtime truths rather than adapter inventions;
- adapters remain thin enough to replace without architecture loss;
- unfamiliar competent agents can discover current capability safely, call it correctly, distinguish partial vs complete, resume, and verify without hidden platform knowledge;
- UI and AI share the same machine truth through different ergonomics;
- local-first storage/execution/search/rehydration preserves thread life and avoids giant avoidable payloads;
- the final architecture is open to mechanisms that ancestry did not envision, provided they improve the intended outcome and survive hostile qualification;
- presentation becomes personally distinctive and operationally excellent, not merely functional.

---

## 3. Governing build metabolism

Canonical loop:

FIX THE INTENDED OUTCOME
→ inspect reality / ancestry / constraints
→ try composition before invention
→ PROBE — what actually happens?
→ DERIVE — mechanism/invariant
→ VERIFY — distinguish strongest alternative
→ BUILD smallest justified change
→ ATTACK IT — assumptions, boundaries, harnesses, authority, currentness, resources, concurrency, malformed/stale state, restarts, partial failures, wrong inputs
→ ISOLATE FAILURE — implementation / wiring / representation / authorization / execution / resource / observability / evaluator / harness
→ STRIP / MUTATE — remove machinery, vary variables, counterexamples, attack explanation
→ EMBODY — only the survivor becomes code/invariant/test/instrumentation/protocol/continuity/scar
→ RECURSE — next highest-value discriminator
→ CSC / semantic gate / release qualification.

**BUILD != EMBODY.**

### Supporting R4.4 machinery
These are functional obligations, not ceremonial parallel stages:
- **Attention Reservoir** = neglected anomalies, deferred alternatives, unresolved seams, anti-isomorphs.
- **Semantic Helix** = observation → explanation → discriminator → attack → scar → improved understanding.
- **OARR** = observation / attack / replay / revision recurrence around verify/attack/isolate/strip/recurse.
- **Loop+** = external science/architecture strip-for-parts, including positive and anti-isomorphs translated into native PCMMAD terms.
- **CSC** = convergence / semantic / release qualification after recursive survival.
- **Revisit / Trace / Live Shadow / Design Thread** = persistent support instruments, not optional bookkeeping.

Base-tier functional obligations may be embodied without ritualized named pipeline stages, but their functions must not silently disappear.

---

## 4. Architecture authority / placement rules

### PCMMAD
PCMMAD is the methodology: hostile engineering, controlled evidence handling, continuity, research metabolism, verification, promotion/demotion discipline, and multi-model/operator work allocation.

### Laboratory Runtime
The Runtime owns canonical truth and durable machine state:
- capability registry/contracts/currentness
- projects/repos/mounts/nodes
- jobs/queue/lifecycle/process ownership
- services
- results/artifacts
- continuity
- authority/approval/policy
- verification/readback
- transfer
- availability/degradation
- resource/telemetry state where earned.

### Adapters
Adapters project Runtime truth only:
- MCP
- OpenAPI / Custom GPT Actions
- CLI
- Operator HUD
- future transports.

**TRANSPORT IS NOT ARCHITECTURE AUTHORITY.**

Allowed adapter-local state:
- transport/session IDs
- cursors
- window/layout preferences
- rendering/presentation preferences.

Forbidden duplicate durable adapter truths:
- MCP job
- HUD project
- adapter approval
- adapter artifact
- adapter process ownership
- adapter-specific second scheduler.

### OBE / Skills
OBE/Skills carry reusable AI/operator intelligence:
- discovery grammar
- rehydration workflow
- evidence/currentness reasoning
- hostile engineering campaigns
- artifact sealing
- mission control
- capability scouting
- composition logic.

They do **not** duplicate durable Runtime state/lifecycle semantics.

Mechanism placement law:
**The mechanism lives where the state lives; judgment about how to compose mechanisms usually lives in Skill/model space until an invariant is earned strongly enough to lower into Runtime enforcement.**

### Model / Project Chat
- Model = replaceable co-processor.
- Project Chat = replaceable mission interaction surface.

The system should survive both changing.

---

## 5. Local-first / thread-life doctrine

Anything the server can inspect, store, execute, search, rehydrate, checkpoint, or verify should generally happen server-side unless there is a specific reason not to.

Operational consequences:
- avoid pulling large files/logs/results into chat;
- store bulk work locally and return bounded receipts/handles;
- prefer resumable/ranged retrieval;
- use server-side rehydration and continuity surfaces;
- do not make model context the durable job store, event log, or archive;
- preserve thread life as an operational resource.

**RETURN DECISION INFORMATION EARLY; STORE BULK WORK LOCALLY.**

---

## 6. AI attention / async control law

**LONG-RUNNING WORK SHALL NOT REQUIRE LONG-RUNNING MODEL ATTENTION.**

The AI should never need to sit in an open-ended tool wait just to learn whether work is progressing.

Requirements:
- queues, research, model runs, browser automation, builds, downloads, archive work, etc. return compact decision-grade progress;
- bounded wait/check is default;
- progress may distinguish PROGRESSING / QUIESCENT / POSSIBLY_STALLED / DEGRADED / TERMINAL when evidence permits;
- Runtime owns lifecycle truth regardless of whether an adapter polls, streams, subscribes, or bounded-waits;
- bulk stdout/stderr/results remain behind handles/ranges;
- useful progress receipt fields include identity, stage, actually-started state, elapsed time, queue position, heartbeat/progress age, warnings/failure digest, next expected transition, suggested recheck, output availability, and result/log handles.

Lifecycle distinctions must remain explicit:
**submitted != queued != started != running != completed != output-durable != registered != promoted.**

---

## 7. Async / process ownership direction

Locked:
- one canonical durable scheduler owns admission, queue, lifecycle, idempotency, replay, reconciliation, and promotion-facing execution truth;
- subordinate worker/runner processes may actuate one job but are not a second scheduler;
- restart-safe process control must survive receiver process loss;
- PID alone is not stable ownership identity;
- process identity should converge toward PID + creation time + executable/command fingerprint + runtime owner + job/service/node identity where justified;
- named Windows Job Object existence alone was disproven as durable ownership; the current survivor uses a runner-held handle/handshake composition.

Scars to preserve:
- global admission lock contention across unrelated projects was real;
- receiver venv Python identity is not receiver-service identity;
- `PowerShell -NoExit` wrappers can outlive children;
- submitted/start/completed/registered must not be conflated.

---

## 8. Capability contract direction

Native capability registry should describe what the Runtime can *currently and lawfully* do, not merely list names.

Target contract fields include:
- capability identity/domain/tags
- capability version
- schema version/hash/contract digest
- input/output contract
- availability + blockers/currentness
- side-effect class
- composable effect traits
- effective authority/approval requirement
- target grounding requirements
- idempotency semantics
- sync/async/durable/replay/wait/progress traits
- resource class
- result/artifact outputs
- preconditions/postconditions/verifier where earned
- failure classes/retryability
- deprecation/supersession.

Historical scar:
**`mutating=false` does not mean “read-only.”**

Examples already proving multi-dimensional effects:
- status/progress may reconcile durable lifecycle;
- browser evaluation can mutate external state;
- research performs network IO/cache effects;
- transfer ticket creation creates ephemeral state;
- plugin reload changes capability surface;
- arbitrary execution can have process/filesystem/network consequences.

---

## 9. Authority / approval direction

Authority is a Runtime object, not a boolean argument.

Current earned direction:
- risky operation challenge bound to exact capability contract;
- exact canonical argument digest;
- target summary;
- freshness/expiry;
- integrity;
- single-use/replay semantics;
- provenance/consumer identity;
- authority envelope separated from capability arguments.

Legacy inline `approval:{permit:true}` is transitional compatibility only and explicitly unbound.

Composite law:
**EMERGENT CAPABILITY IS ALLOWED; EMERGENT AUTHORITY IS NOT.**

A composed workflow/capability must requalify its own:
- boundary
- preconditions
- effects
- authority
- currentness
- resource envelope
- failure semantics
- verification/readback
- result contract
- lineage/provenance.

Parts may compose. Guarantees and authority do not silently compose.

---

## 10. MCP / adapter projection direction

The Runtime may contain a broad capability surface while the client-facing projection remains compressed.

Historical scar from lineage:
- huge flat external capability surfaces create selection noise, stale schemas, context hunger, overlapping-tool collisions, and compatibility burden.

Current design hypothesis:
- keep broad capability server-native;
- project a relatively skinny stable control plane for MCP/other constrained clients;
- use lazy typed discovery/list/describe/invoke patterns rather than projecting every capability schema every turn.

Candidate primitive neighborhood (NOT frozen vocabulary):
- runtime identity/status
- capability list/describe/invoke
- project resolve/bootstrap
- job submit/status/progress/wait/cancel
- result get/preview/range
- batch invoke.

`capabilities.invoke` must **not** become an arbitrary command-text god tool.

Stale contract law:
- invocation should be able to bind expected capability/schema/contract digest so a remembered old client contract fails cleanly rather than guessing.

Batch law:
- `batch` does not imply transaction;
- ordering/parallelism/partial failure/idempotency/cancellation must be explicit;
- atomicity is false unless explicitly guaranteed.

Wait law:
- Runtime owns waitable lifecycle; adapter representation may be bounded wait, polling, event, stream, or subscription.

Result law:
- handles/ranges/preview/hash/metadata should prevent whole-result context flooding.

---

## 11. Holonic / ECS-ish native direction

The runtime already has useful holonic/ECS-like bones. Do not layer a foreign framework/ontology over it.

Working interpretation:
- **Entity** = stable runtime identity: Project, Job, Process, Service, Artifact, Result, Node, BrowserSession, Transfer, Capability, etc.
- **Component** = independently attachable state/contract/trait: Lifecycle, Ownership, Authority, Verification, Waitable, Cancelable, RangeReadable, Availability, ResourceBudget, Telemetry, InputContract, OutputContract, etc.
- **System** = runtime mechanism acting on compatible state/components: scheduler, approval, transfer, continuity, verification, health, routing, etc.
- **Holon** = whole from below and component from above; qualified wholes may compose into larger wholes.

No “ECS rewrite” is authorized.
Normalize the implicit model incrementally where current hostile audits expose a real payoff.

---

## 12. Architectural Mechanism Quarry / Loop+

We are **not** researching architectures to choose an architecture.
We are quarrying mechanisms that sharpen structures PCMMAD already earned.

Campaign laws:
- **MECHANISM FIRST. REPRESENTATION SECOND.**
- **DONOR != AUTHORITY.**
- **EMERGENT CAPABILITY IS ALLOWED; EMERGENT AUTHORITY IS NOT.**

Active donor families:
- ECS
- holonic systems
- entity/component relational models
- capability security
- effect systems
- blackboard architecture
- actor/supervisor systems
- self-describing systems
- hypermedia affordances
- dynamic service composition
- reflective systems
- typed-state planning
- resource/component queries
- graph/query systems.

Every donor-derived candidate is compared against the current PCMMAD mechanism for:
- special-case reduction
- schema rigidity reduction
- lawful composition
- currentness
- authority isolation
- discovery
- observability
- context/tool load
- failure containment
- query expressiveness
without unacceptable duplicate truth, hidden mutable state, orchestration burden, weaker determinism, harder simple operations, authority widening, or transport coupling.

Disposition:
REJECT / DEFER / QUARRY / CANDIDATE / EARNED.

Vocabulary restraint:
No donor gets to rename existing PCMMAD concepts unless the distinction itself earns its way in.

---

## 13. Operator HUD / presentation intent

RAHL-HUD is the behavioral/security/presentation lineage for the server operator UI.
It is **not** Runtime truth authority.

Core presentation law:
**Human operator and AI should see the same machine truth through different ergonomics.**

The HUD should become the physical instrument panel for the same neutral control plane the AI operates programmatically.

Recovered personal design requirements:
- Aero-Glass / Liquid-Aero material language
- HoloFont, used selectively rather than as a readability tax
- Ui / YuiUI operational language
- CogTerm command/interaction ideas
- Forge / Singularity Works lineage
- responsive three-wing cockpit
- top corona / global state band
- bottom command dock
- keyboard-first navigation / command palette
- queue/job/progress/topology
- restart/transfer/result/continuity/Git/project state views
- explicit degraded optional-plane states.

Desired presentation feel:
- personally distinctive / “sexy” as originally imagined
- local and dependency-light where practical
- fast, inspectable, and debuggable at 2 AM
- operator-friendly and agent-friendly
- security/performance/accessibility hostile-tested
- no gratuitous React/Tailwind cathedral unless evidence justifies it
- no decorative glass that destroys legibility or state clarity.

Potential global operational states:
- CORE DOWN
- DEGRADED OPTIONAL PLANE
- HEALTHY WITH WARNINGS
- FULLY NOMINAL.

Current priority is **authority correctness before visual modernization** because the current failing suite cluster is HUD bound-approval behavior.

---

## 14. Semantic / health / degraded-plane direction

Presence of files/assets is not proof of executable capability.

Health should distinguish:
- present
- configured
- dependency-qualified
- available
- degraded
- unavailable
- blocked and why.

Optional-plane outage should not collapse whole-runtime health unless the plane is actually required for the requested operation.

Current semantic truth:
- corpus/index/model assets survive;
- no qualified Python executor currently satisfies the semantic stack;
- semantic capability is honestly `unavailable` with blocker rather than fake green.

---

## 15. Context / filesystem / Git direction

Project scope is exact project authority, not merely “somewhere on an allowed drive.”

Context/file laws earned:
- response bound must also imply bounded execution/materialization;
- project-scoped resolved paths remain under the exact base root;
- reparse/junction escape must fail;
- rehydration byte budget must be real.

Git laws earned:
- running Git successfully from cwd does not prove exact repo ownership;
- mutations require exact repo root grounding;
- reads may return grounded negative state but never silently fall into ancestor repo;
- commit/reset/clean prove intended postconditions rather than equating subprocess exit 0 with task success.

---

## 16. Continuity is an engineering plane

Continuity is not documentation garnish.

Required persistent surfaces:
- Current State
- Next Steps
- Doctrine Snapshot
- Revisit Ledger
- Trace Matrix
- Live Shadow
- Design Thread Stream
- checkpoints/maintenance notes at recovery/promotion boundaries.

Rules:
- ad-hoc reports are not substitutes;
- continuity must be updated when load-bearing state changes;
- local persisted state outranks chat memory;
- contradictions are preserved, not smoothed away;
- current readback outranks stale summaries;
- if cached rehydration excerpts disagree with registered artifact hashes/current files, treat cache currentness as the defect.

This project violated that rule once: directories existed but were empty while engineering reports stayed current. That scar must remain visible.

---

## 16A. ICF-CS continuity authority

Qualified binding additive overlay above sealed R4.4.

Core law: **DIRECTION != CONSTRAINTS != FRONTIER != HISTORY**.

Cold start: **CURRENT STATE -> ICF-CS -> CURRENT CANONICAL SOP + NEXT/DOCTRINE/REVISIT/TRACE -> LIVE SHADOW -> DTS -> LIVE READBACK BEFORE MUTATION**.

Current ingress is navigation, not proof. Historical handoffs, donor material, recency, stale green verification, benchmark keys, and summaries retain explicit authority ceilings under the qualified standard.

Exact overlay outer SHA: `51ed7f424dff7c67534f7e53e8a7c10ebd93bf33ea575eea49dc3f05c24a92a9`.
Qualification receipt: `checkpoints/ICF_CS_ADDENDUM_QUALIFICATION_RECEIPT.md`.

---

## 17. Final schema redesign — LOCKED DEFERRED

Do **not** redesign the final external schema during current all-plane audit.

The inherited OpenAPI/JSON shape is not architecture authority and should not be polished into permanence.

Only after explicit whole-runtime convergence / user “hells yeah, ready” trigger:
1. begin a dedicated research/hostile campaign;
2. start from the surviving native holonic/ECS-ish Runtime model;
3. treat JSON Schema/OpenAPI/MCP contracts as validation/projection leaves;
4. quarry effect systems, capability security, self-description, hypermedia, typed planning, graph/resource calculi, workflow/build systems, authorization models, actor/supervisor mechanisms, and related fields;
5. optimize for compressed lawful composability, discoverability, currentness, authority isolation, bounded context, and deterministic verification;
6. derive/generate adapter projections/docs/hashes/tests from native contracts where practical;
7. retain compatibility adapters only where justified.

The final schema should make many lawful solutions discoverable from a compact native model instead of requiring every operation to have been pre-imagined as a flat verb.

---

## 18. Cross-thread OBE / Skill coordination

Status: ACTIVE COORDINATION CONSTRAINT.

OBE/Skill research and derivation may proceed now using current architecture authority and recurring workflow evidence.

It **shall not freeze** the final OBE↔Runtime interface until reconciled against the audited successor runtime.

Shared meeting artifacts:
- `PCMMAD_RUNTIME_ADAPTER_COMPATIBILITY_CONTRACT_V0_1.md`
- `PCMMAD_RUNTIME_ADAPTER_PROJECTION_MATRIX_V0_1.md`
- machine-readable projection companion.

Server thread continues producing:
- actual native Runtime semantics
- effective authority/currentness
- lifecycle truth
- adapter lossiness boundaries
- result/process/project/artifact semantics.

OBE thread produces:
- operating intelligence
- Skill ecosystem
- capability discovery grammar
- rehydration/mission-control semantics
- hostile evaluation campaign
- adapter projection expectations.

They meet at the projection contract so two PCMMAD ontologies do not emerge.

---

## 19. Promotion / release discipline

Nothing in this file implies live promotion unless explicitly stated.

**V30 working-tree success != release qualification != live deployment.**

Before promotion:
- all-plane hostile audit materially complete
- current full suite green under release candidate
- clean extraction/install/restart qualification
- live/V30 capability parity reconciled
- no unresolved P0/P1 authority/currentness blocker
- continuity current
- manifests/hashes fresh
- final schema/adapter campaign completed only at the locked final stage
- CSC / semantic release gate satisfied.

---

## 20. Current verified campaign state

### Baseline / runtime
- [x] V29 baseline preserved and V30 isolated.
- [x] duplicate async lifecycle authority removed/delegated; canonical scheduler wins.
- [x] cross-project global-lock contention reproduced and first-layer repaired.
- [x] restart-safe runner receipts integrated.
- [x] fresh-cancel / Windows receipt race / launcher-vs-worker identity issues addressed.
- [x] Windows Job Object ownership handshake integrated and hostile-tested.
- [ ] malformed/stale execution-state and final release qualification still open.

### Whole-server audit
- [x] live/V30 missing capability parity issue found and seven capabilities recovered (transfer family + browser.upload).
- [x] optional browser failure no longer collapses aggregate health.
- [x] foreground batch bounded-result offload.
- [x] semantic plane truthful unavailable state.
- [x] bounded decision-grade execution progress/wait.
- [x] result metadata/preview/range/full-opt-in retrieval.
- [x] project/filesystem/context plane major boundedness/scope defects repaired and hostile-tested.
- [x] Git plane exact-root/postcondition hardening and compatibility reconciliation.
- [x] capability contract currentness fields verified in native cards.
- [x] effective approval semantics exposed.
- [x] side-effect model expanded with effect traits; high-risk ambiguous tools classified.
- [x] target/argument/contract-bound approval authority implemented and focused Runtime tests passed.
- [x] projection matrix shared with Skill/MCP direction.
- [x] HUD bound-approval adapter integration requalified; prior HTTP 421 cluster resolved as Host-guard representation mismatch without weakening Runtime approval semantics.
- [x] research bounded-control/cache/type-currentness slice qualified; deeper provider/provenance expansion only if new evidence demands.
- [x] verification command plane audit: shared subprocess physically bounded; typed/max-32 gate contract; command-exit-only evidence claim ceiling; full suite green.
- [x] web public-network authority + typed contract/currentness/credential/header/distillation slice qualified; DNS connection-time rebinding remains an explicit residual, not a fake-green claim.
- [x] native capability effect classification complete for current 99-tool registry: unknown=0 / empty traits=0; automatic effect→policy inference remains separately unearned.
- [x] native capability availability/currentness core qualified: registration/availability/target-health separated; explicit bounded provider probes; browser + semantic default providers; 100 tools / 232-test green.
- [x] SOP/governed-ingestion integrity/currentness/in-process-concurrency slice qualified; true streaming member inspection + multi-process locking remain explicit claim ceilings.
- [x] protocol non-initializing observation + current-GENESIS doctrine slice qualified; historical ledgers remain immutable.
- [x] plugin transactional registry/currentness reload slice qualified; **no plugin code sandbox/isolation claim.**
- [~] control/restart/HUD audit: approval/Host/process-ownership + A-030 availability/core-readiness slices earned; broader service constellation/visual/operator surfaces remain open.
- [~] transfer authority/scope/currentness/integrity hostile slice qualified; immutable export snapshot semantics remain unearned and final release promotion pressure remains.
- [x] browser optional-vs-core HUD readiness split qualified under A-030; browser remains an optional provider/plane.
- [~] schema/runtime/policy/imported-action parity audit: bound-authority + MCP/HUD availability + A-031 family effective-approval + **A-032 bounded result-handle request parity earned**; remaining adapter lossiness requires re-census after publication.
- [x] continuity/rehydration ranking + cache-currentness audit: **ICF-CS v1.0 embodied**, transient noise excluded, all authority roles seeded, cache source-currentness validated, full suite green 209.

### Capability/runtime maturation
- [~] capability availability/currentness core earned; provider expansion remains evidence-driven rather than blanket across all families.
- [ ] process identity maturation beyond PID/start time where needed.
- [ ] approval cleanup/revocation/introspection if justified.
- [ ] retire legacy inline approval after adapter migration.
- [ ] node/resource model maturation.
- [ ] resource-aware admission/orchestration only when justified by real workloads.
- [ ] service constellation supervision.
- [ ] multi-project/session/tab semantics.
- [x] plugin transactional reload/currentness/collision/rollback semantics earned; plugin code sandbox isolation remains a separate threat-model ceiling.

### Operator HUD
- [x] Aero-Glass/Liquid-Aero/HoloFont/YuiUI/ALCI donor corpus recovered.
- [x] CogTerm operational language recovered.
- [x] Forge/Singularity Works three-wing lineage recovered.
- [x] current RAHL-HUD preserved as behavioral/security ancestry.
- [x] receiver-owned operator-plane lifecycle started in V30.
- [x] bound-approval HTTP 421 cluster fixed; dedicated Host-guard + approval qualification 13/13 PASS.
- [x] core-vs-optional degraded qualification split earned under A-030.
- [ ] responsive three-wing layout.
- [ ] top corona / bottom command dock.
- [ ] Liquid-Aero material tier.
- [ ] selective HoloFont.
- [ ] queue/job/progress/topology presentation.
- [ ] restart/transfer/result/continuity/Git/project views.
- [ ] keyboard-first command palette/navigation.
- [ ] hostile security/performance/accessibility qualification.

### Convergence / release
- [ ] strip unnecessary machinery.
- [ ] attack every promoted explanation.
- [ ] CSC / semantic convergence.
- [ ] clean extraction/install/launcher/restart qualification.
- [ ] fresh package inventory/hashes.
- [ ] final schema research/redesign from surviving native runtime model.
- [ ] final MCP/OpenAPI/HUD/CLI projection qualification.
- [ ] V30 promotion/release.

---

## 21. Current frontier / exact next move

A-035 active/terminal partition is earned locally:
- active metadata and terminal history are physically separated while identity/history/replay/restart remain compatible;
- terminal transitions are same-filesystem atomic; legacy migration is conflict-refusing and crash-repairable;
- 0/500/5000 terminal-history discriminator keeps hot scans at 58 active record loads;
- execution/partition cluster 34/34 PASS; full isolated suite 279 GREEN;
- first qualification accidentally migrated 1,158 real records, all were exactly restored, and suite-wide pre-import root isolation now proves ambient partition dirs 0 before/after.

Immediate sequence:
1. publish A-035 and remote-read exact head;
2. only then A-036 derive retention/bounded-drain policy;
3. keep all-history indexing, serving model, PID reuse, and multi-receiver admission separate;
4. preserve the A-035 test-isolation recovery scar as a permanent anti-regression.

---

## 22. Fresh-thread anti-regression list

A new thread/model SHALL NOT:
- treat V29 as the mutable work surface;
- live-promote V30 without explicit promotion gate;
- create another scheduler/job truth;
- equate Popen/PID with durable ownership;
- use `mutating=false` as proof of read-only semantics;
- replace bound approval with boolean approval;
- let adapter/HUD own durable runtime truths;
- expose a huge flat MCP catalog by default merely because the Runtime supports many capabilities;
- turn `capabilities.invoke` into arbitrary command execution by name/string;
- freeze OBE↔Runtime vocabulary before successor reconciliation;
- start final schema redesign before whole-runtime convergence;
- perform an ECS rewrite merely because ECS language is useful;
- import donor architecture vocabulary wholesale;
- let long-running work occupy the model indefinitely;
- dump large results/logs into chat when handles/ranges suffice;
- treat presence of assets as proof a capability is executable;
- trust project path just because it is on an allowed drive;
- trust Git cwd success as repo ownership;
- treat UI prettiness as permission to weaken state clarity/security/accessibility;
- trust stale green reports over fresh tests;
- let continuity surfaces go stale while ad-hoc reports remain current.

---

## 22A. Git-contained recovery handoff

When thread life or local control-plane availability is at risk, the source repository SHALL carry a commit-bound recovery snapshot sufficient to reconstruct Intent / Constraints / Frontier / History plus the Runtime↔OBE/Skills boundary.

That snapshot:
- is a recovery mirror, not a second live Runtime/project-store authority;
- must preserve source hashes and snapshot manifest;
- must point to the qualified ICF-CS/current canonical SOP identities;
- must include Current/Next/Doctrine/Revisit/Trace/Live Shadow/DTS and Commander’s Intent or equivalent recovery surfaces;
- must include the shared Runtime Adapter Compatibility Contract and Projection Matrix as the cross-thread server/Skill meeting surface;
- must instruct a fresh thread to perform live local/runtime/Git readback before consequential mutation.

`CURRENT_INGRESS_POINTER != CURRENT_STATE_PROOF`.

---

## 23. Fresh-thread handoff rule

For re-entry use the qualified version-agnostic grammar:
1. Current State;
2. `checkpoints/ICF_CS_CURRENT.md` + exact qualified ICF-CS standard;
3. `state/doctrine_snapshot/CURRENT_CANONICAL_SOP_POINTER.md` + Commander’s Intent + Next/Doctrine/Revisit/Trace;
4. Live Shadow;
5. DTS tail;
6. fresh consequence-bearing local/runtime readback before mutation.

If material surfaces disagree: RECOVERY/AUDIT → LOCALIZE → REPAIR/SUPERSEDE → READBACK → RESUME.

`CURRENT_INGRESS_POINTER != CURRENT_STATE_PROOF`.
