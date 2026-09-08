# OBE / SKILL PORTFOLIO RECONCILIATION — 2026-09-08

Status: **CURRENT RECONCILIATION / PORTFOLIO UNFROZEN / NEXT SPECIMEN IDENTIFIED**

This report reconciles the historical OBE v0.3 11-Skill specimen against the current Laboratory Runtime and the user's expanded operating-library roadmap. It does not freeze a final Skill ontology.

## Donor/evidence boundary

Current-session uploaded donor artifacts were inspected and hash-verified outside the server project store:

- `OBE_V30_HANDOFF_BUNDLE_2026-09-06.zip`
  - SHA-256 `5b351f98bfeae088f7ed244167f170f71ab74c9777d9059d64eea9c96a3be670`;
  - 9 ZIP entries including top-level manifest plus v0.3 campaign/A-001 carriers;
  - embedded v0.3 campaign SHA-256 `88c8f91ea67126d93a629deab37dde4cdf23d07881f20ab0e7906fc525b6631e`.
- `OBE_SKILL_THREAD_TURN_BASED_VERBATIM_TRANSCRIPT_2026-09-08.md`
  - SHA-256 `33766ec84f268c83de9dba780d7b278b38b5db9fb881e6883f6f94b5b8b244b9`;
  - approximately 106 KB turn-based visible-thread transcript.

These uploads are donor/evidence inputs. They do not overwrite Runtime authority.

## Historical v0.3 specimen requalification

The embedded campaign contains 11 concrete `SKILL.md` specimens:

1. `obe-bootstrap`
2. `runtime-capability-scout`
3. `laboratory-mission-control`
4. `project-rehydration`
5. `evidence-authority-resolver`
6. `hostile-engineering-campaign`
7. `artifact-release-sealer`
8. `environment-runtime-qualifier`
9. `cross-project-donor-miner`
10. `pcmmad-methodology`
11. `skill-forge`

The historical package was read before execution. Its validators are local filesystem/manifest/semantic mutation checks; they do not contact the network or mutate the authoritative Runtime.

Requalification in the active uploaded-artifact sandbox:

- campaign verifier: **PASS**;
- Skill format validator: **PASS / 11 Skills**;
- hostile semantic package campaign: **16 / 16 mutants rejected, 0 unexpected passes**.

An unrelated spreadsheet-runtime warmup warning occurred during the sandbox Python interpreter startup but did not affect verifier exit codes or Skill/hostile results.

## Historical specimen vs current Runtime

The v0.3 package is intentionally historical, not to be rewritten in place.

Historical v0.3 facts:

- Runtime source contact: 100 tools / 16 families;
- ordinary `expected_contract_digest` was ignored/accepted;
- A-001 was a donor candidate, not Runtime authority;
- final Skill/Runtime interface deliberately unfrozen.

Current Runtime facts:

- current native registry: **108 tools / 17 families**;
- zero missing core contract fields across capability version, schema version/hash, contract digest, side-effect class, effect traits, input schema, output schema;
- A-001 is already engineering-published and ordinary stale/malformed expected-contract assertions fail before downstream dispatch work;
- HTTP and batch both project the currentness assertion;
- omission remains compatible for legacy callers;
- R12 adds `continuity.convergence.inspect`;
- R13 adds optional request-bound workload proof without promoting identity into mutation authority;
- current adapter/projection parity cluster: **31 / 31 PASS**.

Disposition: v0.3 survives as a valid historical specimen and donor. Its stale-contract defect is historical evidence, not current Runtime truth.

## Portfolio law

The user's expanded roadmap is accepted as the forward operating-library roadmap, with one binding anti-proliferation rule:

**named internal mechanisms do not each become top-level Skills merely because they have names.**

Helix, OARR, Loop+, PDVER, Attention Reservoir, CSC, Live Shadow, RES and similar mechanisms remain internal machinery unless a distinct recurring user job/failure boundary later earns separate Skill existence.

## Reconciliation of the original 11

| Historical v0.3 Skill | Current disposition | Forward placement |
|---|---|---|
| `runtime-capability-scout` | SURVIVES / GENERALIZE | T0.1 **MCP / Connector Capability Scout**; broaden beyond Laboratory Runtime to any MCP/plugin/server/API bridge/connector while preserving advertised/observed/inferred/behavior-qualified truth |
| `project-rehydration` | SURVIVES | T0.2 **Project Rehydration / Reincarnation Operator** |
| `evidence-authority-resolver` | SURVIVES | T0.3 **Evidence / Authority / Currentness Resolver** |
| `hostile-engineering-campaign` | SURVIVES | T0.4 **Hostile Engineering Campaign Operator**; Helix/OARR/Loop+/PDVER/Attention Reservoir/CSC remain internal metabolism |
| `artifact-release-sealer` | SURVIVES | T0.5 **Artifact / Release Sealer** |
| `environment-runtime-qualifier` | SURVIVES | T0.6 **Environment & Runtime Qualifier** |
| `cross-project-donor-miner` | SURVIVES / BROADEN | T0.7 **Cross-Project Archaeologist / Donor Miner** |
| `laboratory-mission-control` | SURVIVES / USER-FACING NAME OPEN | T0.8 **PCMMAD Mission Control** in the user's roadmap, but implementation must preserve `PCMMAD methodology != Laboratory Runtime`; the mission-control Skill operates the Runtime and may invoke the PCMMAD methodology Skill when appropriate |
| `obe-bootstrap` | COMPOSE / DO NOT FORCE AS TOP-LEVEL PRODUCT | OBE-core bootstrap profile composing capability scouting, rehydration, authority/currentness resolution, environment qualification, and intent routing; can remain a Skill if product/runtime trigger evidence continues to justify it |
| `pcmmad-methodology` | SURVIVES AS OPTIONAL METHODOLOGY | separate methodology Skill; never Runtime ontology and not required for simple machine operations |
| `skill-forge` | DEFERRED META-SKILL | T0.10 **Skill Forge / Skill Qualification Factory**, only after 2–3 structurally different new Skills provide enough specimens to extract shared grammar without Drive/MCP overfit |

## New T0 capability not represented strongly enough by v0.3

### T0.9 Tool / Workspace Intent Router

This should exist as a generalized user-intent composition layer over connected surfaces. It resolves the owning surface and target, chooses the narrowest lawful tool combination, preserves permissions/currentness, and verifies result state.

It should compose with the Connector Capability Scout and Evidence Resolver rather than duplicate their registries/currentness logic.

## Expanded roadmap accepted

The user's tiered roadmap is preserved as the current forward portfolio, not a commitment to build every item immediately.

### T0 operating layer

1. MCP / Connector Capability Scout
2. Project Rehydration / Reincarnation Operator
3. Evidence / Authority / Currentness Resolver
4. Hostile Engineering Campaign Operator
5. Artifact / Release Sealer
6. Environment & Runtime Qualifier
7. Cross-Project Archaeologist / Donor Miner
8. PCMMAD Mission Control
9. Tool / Workspace Intent Router
10. Skill Forge / Skill Qualification Factory — deferred until enough specimens exist

### T1 engineering/research layer

- Codebase Archaeologist / Semantic Cartographer
- Practical Coding + CSC Reviewer
- Experiment / Discriminator Designer
- Research Evidence Synthesizer
- Portable Model / Toolchain Qualification
- Dataset / Corpus Steward
- Git / Repository Operator
- CI / Build Failure Localizer
- Knowledge Currentness Cache
- Integration Security / Permission Auditor
- Long-Run Campaign Launcher / Resume Operator
- Untrusted Artifact Intake / Quarantine Operator

### T2 attention/business/personal operating layer

- Executive Attention Operator
- Storage / Archive Hygiene Operator
- Business Workflow Automation Analyst
- Opportunity / Offer Builder
- Technical Document / White-Paper Producer
- Systems Programming Tutor
- Multi-Model Router / Qualifier
- Dependency / Capability Drift Watcher
- Decision / Contradiction Registry Maintainer

### T3 evidence-triggered bounded domain Skills

Visual architecture/Figma mapping, Windows/remote support, lead scraping, reporting/dashboard operators, and other specialized Skills should be built only after recurring workload evidence earns them.

## Bootstrap sequence

The current recommended construction order is retained:

1. **Generic MCP / Connector Capability Scout**
2. **Project Rehydration Operator**
3. **Artifact / Release Sealer**
4. **Environment & Runtime Qualifier**
5. **Hostile Engineering Campaign Operator**
6. **Cross-Project Archaeologist**
7. **PCMMAD Mission Control**
8. then **Skill Forge**, after multiple structurally different specimens exist

Evidence / Authority / Currentness Resolver should be treated as shared infrastructure used throughout that sequence, even when not literally built second in the packaging order. Tool / Workspace Intent Router should emerge once at least two distinct connector/workspace adapters prove its generalized composition grammar.

## Why the first next Skill is still the Connector Scout

The Drive work and current Runtime dogfood converge on the same law:

**documentation/tool descriptions are evidence; current live capability discovery is authority for the current session.**

A generalized Connector Scout improves every subsequent Skill by discovering:

- protocol/version;
- auth context and scopes;
- tool/resource/prompt surfaces;
- schemas and currentness/version identifiers;
- pagination/bounds;
- transport behavior;
- dynamic availability/provider dependencies;
- advertised vs observed vs inferred capability;
- drift since last qualification;
- projection lossiness between native and adapter surfaces.

It must not call consequence-bearing methods merely to prove they exist.

## Exact next Skill artifact

**`MCP_CONNECTOR_CAPABILITY_SCOUT_V0_1`**

The historical `runtime-capability-scout` is donor specimen #1. Google Drive discovery work is exemplar #2. The current 108-tool Laboratory Runtime is a third structurally different target for dogfood.

The new Skill should strip Google-specific and PCMMAD-specific assumptions while retaining:

- lazy/task-relative discovery;
- evidence classes `ADVERTISED / OBSERVED / INFERRED / BEHAVIOR-QUALIFIED`;
- exact contract/currentness capture when surfaced;
- harmless existence probes only when advertisements may be incomplete;
- method-not-found vs auth/invalid-params/provider/transport discrimination;
- projection-drift report rather than a competing durable registry;
- security/permission scope inspection;
- bounded output/progressive disclosure;
- explicit no-mutation-for-discovery rule.

## Current Runtime / Skill boundary

Runtime owns durable deterministic truth:

- project/filesystem state;
- job/scheduler/process truth;
- mutation leases/fences;
- approvals;
- results/artifacts;
- Git truth and grounded repo identity;
- continuity/protocol state;
- capability contract/currentness;
- resource envelopes;
- replay/idempotency mechanisms;
- workload-proof verification evidence.

Skills own semantic operating behavior:

- task-relative discovery strategy;
- rehydration workflow;
- authority/evidence interpretation;
- composition/planning;
- discriminators/hostile campaign logic;
- archaeology/donor transfer judgment;
- operator-facing routing and attention allocation.

`SKILL_COMPOSITION != SECOND_RUNTIME_TRUTH_PLANE`.

## Convergence result

**OBE/Runtime boundary: RECONCILED ENOUGH TO BUILD THE NEXT SKILL SPECIMEN.**

The portfolio itself remains **UNFROZEN**. No final schema vocabulary is inferred from the Skill roadmap. Skill dogfood may still pressure new Runtime primitives, but any such primitive must be reproduced and re-earned in the Runtime thread before becoming authority.

## Skill-thread handoff requirement

After the server convergence receipt and this portfolio reconciliation are published/read back, prepare a direct response for the waiting Skill thread that states:

- A-001 was independently re-derived and published;
- current Runtime has advanced materially beyond the v0.3 100-tool snapshot to 108 tools / 17 families;
- the v0.3 11-Skill package remains internally qualified and useful as donor evidence;
- those 11 are seed specimens, not the final portfolio;
- the expanded tiered roadmap above is now the intended operating-library direction;
- `MCP_CONNECTOR_CAPABILITY_SCOUT_V0_1` is the recommended exact next artifact;
- Skill Forge remains deliberately deferred until multiple structurally different Skills exist;
- live Runtime promotion/final schema work are separate server concerns and must not block starting the next Skill specimen.
