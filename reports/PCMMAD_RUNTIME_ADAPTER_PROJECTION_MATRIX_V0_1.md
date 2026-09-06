# PCMMAD Runtime Adapter Projection Matrix v0.1

Status: CURRENT CANDIDATE SHARED CONTRACT / runtime-audit derived / reconciled through A-031
Purpose: meeting surface between audited Laboratory Runtime semantics and OBE/Skill/MCP projection work. This does NOT freeze final adapter vocabulary.

## Governing laws
- AXIOM-01: INTENT IS A CONSTRAINT, NOT A CEILING.
- Transport is not architecture authority.
- Runtime owns durable truth/state; adapters project it.
- Long-running work shall not require long-running model attention.
- Return decision information early; store bulk work locally.
- Adapter-local persistent truth that cannot reconcile to a native Runtime object is an architecture smell.
- JSON/OpenAPI schemas are projections/validation mechanisms, not the native ontology.

## Matrix

| Native concept / holon | Native authority | Current native evidence | MCP candidate projection | OpenAPI / Actions projection | HUD projection | Adapter lossiness allowed | Lifecycle | Authority / approval | Idempotency | Result / readback | Version / currentness | Adapter-only durable state allowed? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Runtime identity | Runtime/health | `/health`, lab health, roots, version, constitutional seed | `runtime.identity` | `/health` | corona/global identity | representation only | live | read | n/a | health receipt | runtime/version + doctrine digest | no |
| Runtime health | Runtime/plane health | aggregate lab health, execution scheduler health, optional-plane states | `runtime.status` | `/health`, `/lab/health` | core readiness + plane matrix; optional browser degradation remains visible without disqualifying core | may summarize, not alter required/optional truth | live | read | n/a | plane health receipt | timestamp/currentness | no |
| Constitutional seed | Runtime doctrine seed | `runtime_axioms.py`, `/health`, `lab.health` | included in identity/status | health payload | subtle boot/corona surface | zero semantic loss | versioned | read | n/a | digest | axiom version + digest | no |
| Capability | Native registry | 100 native tools; ToolSpec contract/effect/availability metadata | `capabilities.list/describe/invoke` | `/lab/tools`, `/lab/dispatch` | command palette/tool explorer + static availability + explicit selected-tool currentness | filtering/summarization only; invocation semantics zero-loss | versioned/current availability | effective policy per capability | capability-specific | verifier/readback metadata | capability_version + schema_version + schema_hash + contract_digest + availability contract/currentness | no |
| Capability family | Native registry projection | category/family cards incl. declared + effective approval counts | list filters/family describe | capability router descriptor; closed schema includes `effective_approval_required_tools` | topology/family browser | summary allowed, but effective authority count zero-loss | live/versioned | effective policy derived from constituents | n/a | constituent capability refs | digest/currentness desirable | no |
| Project | Project registry/layout | project roots, manifest, status, continuity surfaces | `projects.resolve/bootstrap` | project routes | project selector/context wing | zero identity loss | persistent | project-scoped | n/a | project/manifest receipt | project revision/currentness needed | no |
| Job | Canonical execution scheduler | durable job JSON, queue/status/replay/cancel | `jobs.submit/status/progress/wait/cancel` | execution routes + lab execution tools | jobs/queue wing | status may be compact; lifecycle semantics zero-loss | durable lifecycle | submit/cancel mutation policy | existing key+payload fingerprint semantics | compact progress + output/result/artifact links | job revision/currentness desirable | no |
| Job progress | Execution scheduler + receipts | `execution.progress`, bounded `execution.wait` | progress/status/notifications | bounded wait/status | live progress rows | summary required; no bulk-log requirement | live/derived | read | n/a | decision-grade receipt; bulk output separate | timestamp + heartbeat/output age | no |
| Queue/admission | Canonical scheduler | queue_position, global/per-project limits, scheduler stats | jobs status / queue summary | execution capabilities/status | queue pressure/position | summary allowed, admission truth zero-loss | live | read/control separated | submit idempotency | queue/admission receipt | current snapshot | no |
| Process identity | Runtime ownership subsystem (evolving) | PID, launcher PID, worker PID, creation time, Job Object membership | process inspect/control via native capability | execution/control routes | process/service topology | presentation may omit internals; ownership identity must remain exact | ephemeral/live | high authority for control | mutation-specific | identity/readback receipt | creation time + owner epoch/fingerprint target | no |
| Service | Runtime supervisor/control (partial) | receiver restart controller, HUD operator plane | service resolve/status/restart candidate | control tools | service constellation | summary allowed; target identity zero-loss | live | target-bound approval desired | restart key/receipt where applicable | health/process/listener convergence receipt | current generation/receipt | no |
| Approval | Runtime policy/authority subsystem | target/argument/contract-bound short-lived single-use approval challenge + separate authority envelope; legacy inline path transitional only | approval handle/object | separate `authority` envelope | approval modal/inbox | zero semantic loss | expiring/consumable | canonical authority | n/a | approval challenge/receipt | args/target/capability contract digest + expiry/consumption | no |
| Result | Native result store | result handles, stored batch/background payloads, bounded auto/metadata/preview/range/explicit-full retrieval | `results.get/preview/range` candidate | `/lab/results/get` bounded retrieval modes | result viewer | representation/range allowed; content identity exact | persistent/bounded | inherited/scoped | n/a | handle/hash/size/preview/range | immutable content hash + metadata | no |
| Artifact | Project artifact registry | manifests, registration, hashes | artifact resolve/read/seal candidate | artifact/project routes | artifact browser | zero identity/hash loss | persistent | scoped mutation | operation-specific | exact hash/manifest | sealed lineage/currentness | no |
| Transfer | Transfer plane | tickets/chunks/finalize/hash | capability discovery/invoke or transfer typed subset | transfer HTTP routes | transfer status | chunking representation allowed; ticket/hash/offset semantics exact | staged/expiring | mutation approval | offset/hash semantics | transfer receipt/hash | ticket expiry/currentness | no |
| Continuity | Continuity subsystem | current/next/doctrine/revisit/trace/live-shadow/design-thread surfaces | bootstrap/read/update candidate | project/file/native tools | continuity wing | summaries allowed; source identity/currentness exact | persistent/append where applicable | project-scoped mutation | append/update-specific | exact source artifact readback | hash/revision/currentness | no |
| Node | Topology/runtime config (partial) | mounts/local host; remote-node model not fully normalized | nodes.list/describe candidate | future/native router | topology wing | summary allowed | live | node authority | n/a | health/environment receipt | heartbeat/currentness | no |
| Mount/path scope | Runtime configuration + path guards | mount summary/resolve/path safety | resource/path resolution through capabilities | filesystem/project routes | mounts view | display lossiness okay; scope decision exact | live/configured | scoped | n/a | resolved canonical path/scope check | config revision desirable | no |
| Browser session | Browser bridge/native browser tools | session IDs, health, action tools | discover/invoke or bounded browser set | browser tools | browser panel | transport interaction representation allowed; session identity exact | ephemeral | browser mutation policy | operation-specific | screenshot/state/action receipt | session/current bridge health | no |
| Research campaign/result | Research plane | bounded hunts/cache/distillation | capability discovery + async job/result when long | research tools/routes | research panel | result summarization encouraged; provenance exact | bounded/async candidate | read/network policy | query-specific | source/provenance result handle | source/cache currentness | no |
| Semantic retriever | Semantic plane | assets present; default runtime currently unavailable; dynamic native availability provider exposes blocker `no_qualified_python_runtime` | capability unavailable with blockers + explicit availability read | semantic tools | degraded optional plane | no fake availability | live dependency state | read | n/a | blocker/resource/qualified-runtime receipt | contract digest + default-runtime probe currentness | no |
| Plugin/capability contributor | Plugin loader + registry | plugin load/error records | capability registry only; plugin lifecycle projection optional | native lab router | degraded family/plugin indicator | adapters need not expose loader internals unless diagnostic | load/current runtime | high for reload | n/a | plugin load/error receipt | plugin/version/digest pending | no |
| SOP/governed ingestion | Runtime SOP subsystem | registration/status/chunk/guard/proceed gate | capability discovery/invoke | SOP tools | governance panel | zero gate-semantic loss | staged/persistent | mutation-specific | package identity | ingestion/gate receipts | corpus/hash/currentness | no |
| Protocol state | Append-only typed protocol plane | protocol events/snapshot/mode gates | capability discovery/invoke | protocol tools | governance/mode view | summary allowed; event identity/order exact | append-only/persistent | scoped | append semantics | event/snapshot readback | sequence/currentness | no |
| Operator HUD layout | Adapter-local UI state | window/panel preferences | n/a | n/a | local UI state | arbitrary presentation | local/session | user-local | n/a | n/a | adapter-local version | yes, only presentation state |
| MCP/HTTP session/cursor | Adapter transport | not runtime truth | adapter-local | adapter-local | n/a | arbitrary transport semantics | ephemeral | transport auth | n/a | n/a | transport-defined | yes, transport only |

## Native capability contract required minimum

Every promoted native capability should converge toward exposing:
- capability_id/name
- domain/category/tags
- capability_version
- schema_version
- schema_hash / contract_digest
- input contract
- output contract
- availability + blockers/currentness
- side-effect class
- effective approval/authority requirement
- target grounding requirements
- idempotency semantics
- sync/async/durable/replay/wait/progress traits where applicable
- resource class where meaningful
- result/artifact outputs
- preconditions/postconditions/verifier where earned
- failure classes + retryability
- deprecation/supersession

## Holonic / ECS interpretation

This matrix is a projection of native holons/components/systems, not a mandate for an ECS rewrite.

Examples:
- Job entity + Lifecycle + Waitable + Cancelable + Ownership + Telemetry + ResultLinks components → scheduler/progress/cancel/output systems become applicable.
- Result entity + RangeReadable + ContentIdentity components → preview/range/get systems become applicable.
- Service entity + OwnershipVerified + Restartable + Health components → status/restart/verify systems become applicable.
- Capability entity + Contract + Authority + Availability + Verifier components → discovery/invocation/policy systems become applicable.

The eventual schema should expose these existing compositional bones rather than require every useful workflow to have been pre-imagined as a flat verb.


### A-031 adapter-lossiness disposition
- **FIX-NOW / EARNED:** closed compact `CapabilityFamilyCard` omitted native `effective_approval_required_tools`, making the declared OpenAPI response shape contradict native serialization and hide effective policy count. Fixed/qualified without expanding the 30-operation surface.
- **ACCEPTABLE CURRENT COMPATIBILITY:** `/lab/tools.tools[]` remains permissive (`additionalProperties=true`) so native tool cards cross the wire without truncation; this is validation/documentation lossiness, not semantic wire loss. Strongly typing the entire evolving capability card is deferred until final schema campaign unless a concrete client failure appears.
- **NEXT UNCLASSIFIED:** compact `/lab/results/get` request still exposes historical `summary_only` while native Runtime has bounded `auto|full|metadata|preview|range`; evaluate next because it intersects the bounded-agent-attention/result law.

## Current open reconciliation items before interface promotion
Earned and removed from the open list: full effect classification, bound approval authority, bounded result preview/range, plugin transactional lifecycle/currentness, and native availability/currentness core.

Remaining genuinely open:
1. process identity object completion and service/node ownership normalization;
2. node/resource model maturation;
3. research/semantic long-run projection and qualified semantic executor restoration;
4. remaining OpenAPI/imported-action/runtime-surface parity where native contract fields are still intentionally/permissively compressed;
5. async malformed/stale/race/final release qualification;
6. final runtime audit reconciliation with OBE research/derivation campaign;
7. live V30 promotion/restart/CSC/package qualification;
8. final schema redesign only after whole-runtime convergence.

## Claim ceiling
Candidate shared contract. It is grounded in the current V30 audit and verified runtime mechanisms but does not freeze final MCP tool names, final OBE interface, or final schema ontology.
