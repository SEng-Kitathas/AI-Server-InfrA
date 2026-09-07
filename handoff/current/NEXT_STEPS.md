# PCMMAD Receiver V30 — Next Steps

Last updated: 2026-09-06 22:38 ET

## Immediate — rollover-safe active frontier

Completed / verified:
- [x] A-041 Git-current at `a97a00f67f3b79dbbe18e092d29b8971e588d4a2`, final 318 GREEN.
- [x] live server checkpoint readback: online; scheduler alive 0.25s; 96 native tools / 16 families; compact surface 30.
- [x] A-042 WIP source discovered and byte-identified; AST parse PASS; still unqualified.
- [x] repaired rollover handoff regression **9/9 PASS**; complete suite **321 GREEN**.
- [x] rollback localized: outer canonical state current, Git handoff mirror stale; thread saturation/compaction remains suspected causal contributor, not proven.

| Priority | Action | Why | Done when |
|---|---|---|---|
| P0 | Publish full rollover checkpoint + repaired Git handoff mirror | new thread must not replay A-037..A-041 or lose A-042 WIP | remote commit contains current mirror, dedicated server handoff, and byte-exact WIP recovery copy |
| P0 | New thread re-read persisted surfaces + exact Git/live readback | prevent second rollback | it states A-041 published and A-042 active WIP from evidence, not chat memory |
| P0 | Linear audit existing A-042 module before editing | 455 lines already embody intended lease/generation architecture | invariants, gaps, duplicate mechanisms, and integration points mapped |
| P0 | Add hostile lease-core tests | project mutation exclusivity is correctness, not convenience | two-writer, stale-generation, expiry/takeover, stale-token, owner/session mismatch, corrupt-state, read-nonblocking tests pass |
| P0 | Audit consequential mutation chokepoints | avoid scattered symbolic checks | smallest authoritative integration surface identified for project/Git/continuity mutation |
| P0 | Integrate/projection + hostile cross-client race test | reproduce the real failure mechanism | exactly one writer survives; stale thread cannot regress continuity/Git after newer generation |
| P0 | Full suite + continuity + Git A-042 | per-step law | remote exact; A-042 claim ceiling explicit |
| P1 | Re-derive OBE A-001 stale-contract ordinary invocation seam | old donor remains ancestry-stale but current source still lacks expected contract assertion | current-head repro decides native mechanism |
| P1 | Then idempotency / Job Object resource raids | remain valuable but must not contaminate A-042 | separate discriminators/commits |

## Near-term all-plane audit

Do not use this section as a blind task queue. Reconciliation is authoritative first. Current likely survivors requiring further pressure include:

| Priority | Candidate seam | Current reason |
|---|---|---|
| P1 | Remaining OpenAPI/imported-action/runtime-surface parity | MCP + HUD availability projections are earned; permissive/static evidence surfaces remain |
| P1 | Async malformed/stale/race/final qualification | current runner/scheduler composition is strong but not release-promoted |
| P1 | Control/HUD/service/process identity | process/service truth still has open maturation work |
| P1 | Semantic executor | assets exist; no qualified executor |
| P1 | Live/V30 parity + release qualification | working tree success is not live promotion |

## Runtime capability contract / adapter readiness

| Priority | Action | Why it matters | Done when |
|---|---|---|---|
| P1 | Extend availability providers only from evidence | core model is earned; more providers may be justified by real dependency drift | each added provider has reproduced currentness need + hostile tests |
| P1 | Preserve effect/availability contract truth | effect classification is complete; future tools must not regress to unknown/empty metadata | registry invariant remains green |
| P1 | Approval cleanup/revocation/introspection | bound challenge is earned but operational lifecycle can mature | expiry cleanup and justified inspection/revocation behavior defined |
| P1 | Plan legacy inline approval retirement | legacy path is known unbound authority | all adapters use bound challenges, then default disable/remove legacy path |
| P1 | Mature process identity | PID alone is insufficient | pid + creation time + executable/command fingerprint + runtime owner/job/service/node are represented where needed |
| P1 | Mature node/resource model | future multi-node/GPU/resource orchestration needs real state | current resource/authority/currentness model survives tests |
| P1 | Reconcile projection matrix with OBE campaign | prevents two PCMMAD ontologies | server native concepts and Skill assumptions agree under audited successor runtime |

## Operator HUD / presentation

| Priority | Action | Why it matters | Done when |
|---|---|---|---|
| P1 | Bound-approval HUD behavior | blocker resolved; retain regression/security pressure | focused tests remain green |
| P1 | Preserve server truth ownership | HUD availability/readiness is now presentation-only and ephemeral | no adapter-only durable truth beyond presentation/session |
| P1 | Build responsive three-wing cockpit | user wants original personal UI vision embodied | three-wing layout works across relevant viewport classes |
| P1 | Integrate Aero-Glass / Liquid-Aero tier | presentation modernization | balanced material system performs without unreadable glass excess |
| P1 | Integrate selective HoloFont | preserve legibility and original design intent | HoloFont is structural/accent language, not readability tax |
| P1 | Integrate Ui/YuiUI/CogTerm language | recover original cockpit/command semantics | operator can navigate and command keyboard-first |
| P1 | Show queue/job/progress/topology | make long-running work observable without trapping AI/user | bounded progress/state receipts visible |
| P1 | Add restart/transfer/result/continuity/Git/project views | expose runtime wholes without duplicate truth | all views source native Runtime receipts |
| P1 | Hostile security/performance/accessibility pass | sexy must not mean fragile | no authority leaks, runaway polling, inaccessible core control, or optional-plane collapse |

## Semantic plane

| Priority | Action | Why it matters | Dependency | Done when |
|---|---|---|---|---|
| P1 | Restore/qualify semantic executor | assets exist but capability is honestly unavailable | decide whether composition can reuse qualified env or create dedicated one | full dependency probe passes and search works under isolated tests |
| P1 | Keep donor path non-authoritative | CTO retriever is implementation donor, not runtime ontology | executor restoration | runtime config remains neutral and source provenance visible |
| P1 | Hostile semantic qualification | prevent fake health/data-path drift | qualified executor exists | health/search share resolver; stale/missing models/indexes/DB/runtime fail typed |

## Async/execution final qualification

| Priority | Action | Why it matters | Done when |
|---|---|---|---|
| P1 | Malformed/stale execution state matrix | restart-safe ownership exists but release needs corrupted-state pressure | stale receipts/PIDs/heartbeats/job-object data fail safely |
| P1 | Cancel/timeout/finalize race matrix | avoid lifecycle split-brain | repeated races converge deterministically |
| P1 | Cross-project pressure / lock telemetry | earlier global lock contention was real | unrelated projects remain responsive under slow scans/reconciliation |
| P1 | Result registration failure semantics | completed != registered | job/result/artifact truth remains distinct and recoverable |

## Architectural Mechanism Quarry / Loop+

Active donor families:
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
- typed-state planning
- resource/component queries
- graph/query systems.

For each donor mechanism: compare current PCMMAD mechanism vs donor-derived candidate; record gain, complexity, authority consequences, state consequences, failure modes, strongest counterexample, discriminator, and disposition: REJECT / DEFER / QUARRY / CANDIDATE / EARNED.

Rules:
- mechanism first, representation second
- donor != authority
- emergent capability allowed; emergent authority forbidden
- no vocabulary replacement without earned distinction
- no ECS/framework rewrite merely because the runtime is ECS-ish.

## Waiting on evidence / cross-thread inputs

| Evidence needed | Why blocked | Source/acquisition path | Revisit trigger |
|---|---|---|---|
| OBE research/derivation artifacts | final adapter/Skill interface must reconcile, not diverge | Skill thread | when `OBE_RESEARCH_AND_DERIVATION_CAMPAIGN_V0_1` and projection work are available |
| Complete live successor audit | final MCP vocabulary cannot be frozen from V29 assumptions | ongoing V30 audit | whole-plane qualification materially complete |
| Qualified semantic Python environment | semantic capability cannot be promoted | local runtime discovery/composition | environment found/built and probed |

## Deferred until whole-runtime convergence

### Final schema redesign
Do not polish the inherited static schema prematurely.

Only after explicit whole-runtime convergence / user "hells yeah, ready" trigger:
1. start a dedicated research/hostile campaign;
2. treat native holonic/ECS-like Runtime model as source authority;
3. quarry type/effect/capability/reflective/hypermedia/planning/resource/graph systems for useful mechanisms;
4. make JSON Schema/OpenAPI/MCP projections leaves, not ontology authority;
5. optimize for compressed typed composability, currentness, lawful emergent workflows, bounded agent context, and precise authority;
6. generate/derive adapter contracts, docs, hashes, and tests from native runtime contracts where practical;
7. preserve thin compatibility frontends for old clients only where justified.

## Demotion / replay candidates

| Candidate | Why replay | What decides it | Status |
|---|---|---|---|
| Worker capsule/runner architecture details | mechanism evolved through failed named-Job-Object durability hypothesis | continued restart/malformed-state tests | integrated candidate, not live-promoted |
| Legacy inline approval | explicitly unbound | adapter migration + hostile authority review | transitional only |
| Static final OpenAPI architecture | user identifies original design as stiff/brittle and first-principles constrained | final schema research after runtime convergence | demoted as architecture authority |
| Any `mutating=false => read` inference | proven false for execution/browser/research/reload | per-tool effect audit | demoted globally |
| CFE/Microseed or other external architecture analogies | useful quarry but not receiver doctrine automatically | explicit discriminator | evidence only unless separately earned |

## Queue hygiene

Web and already-audited research slices are qualified. Fix continuity rehydration ranking/cache-currentness next, then reconcile remaining checklist/tree state before opening another plane.
