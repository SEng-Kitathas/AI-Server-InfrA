# PCMMAD Runtime ↔ OBE / Skills Duality — Current Handoff Contract

Status: CURRENT CROSS-THREAD HANDOFF / ARCHITECTURE BOUNDARY
Date: 2026-09-05
Authority ceiling: architecture/placement continuity derived from current Commander’s Intent + audited Runtime adapter contract. Candidate Skill portfolio and mechanism-quarry items remain research until reconciled/earned.

## Foundational maxim

**INTENT IS A CONSTRAINT, NOT A CEILING.**

Intent constrains what success means and what must not be casually violated. It does not forbid stronger lawful mechanisms merely because an earlier design did not envision them.

Related project law:
**JUST BECAUSE IT WAS NOT ENVISIONED OR INTENDED DOES NOT MEAN IT CANNOT BE DONE — BUT NEW CAPABILITY MUST STILL SURVIVE AUTHORITY, EFFECT, CURRENTNESS, VERIFICATION, AND COMPOSITION PRESSURE.**

## Canonical ontology / placement

### PCMMAD
PCMMAD is the methodology:
- hostile engineering;
- controlled evidence intake;
- continuity and ICF-CS;
- research/derivation metabolism;
- promotion/demotion discipline;
- verification/readback;
- multi-model/operator work allocation.

### Laboratory Runtime
The Runtime owns durable machine truth and deterministic/stateful capability:
- capability registry/contracts/effects/currentness/availability;
- projects, repos, mounts, nodes, environments where earned;
- jobs, queues, lifecycle, idempotency, replay, process ownership;
- services and supervision state;
- results/artifacts and bounded retrieval;
- continuity state;
- authority/approval/policy;
- verification/readback;
- transfer;
- resource/telemetry state where earned.

### Adapters
MCP, OpenAPI/Custom GPT Actions, CLI, HUD, and future transports project Runtime truth.

**TRANSPORT IS NOT ARCHITECTURE AUTHORITY.**

Adapter-local state is limited to harmless transport/presentation concerns such as session IDs, cursors, window/layout state, and rendering preferences.

Adapters SHALL NOT own parallel durable truths for jobs, projects, artifacts, approval, process ownership, continuity, or scheduling.

### OBE / Skills
OBE/Skills carry reusable AI/operator intelligence:
- capability discovery grammar;
- project rehydration/reincarnation workflow;
- evidence/authority/currentness reasoning;
- hostile engineering campaign routing;
- artifact/release sealing judgment;
- environment/runtime qualification judgment;
- cross-project archaeology/donor mining;
- mission control and composition logic;
- workspace/tool intent routing.

They are **not process daemons** and SHALL NOT duplicate durable Runtime state/lifecycle semantics.

### Model / Project Chat
- Model = replaceable co-processor.
- Project Chat = replaceable mission interaction surface.

The architecture must survive either changing.

## Placement law

**MECHANISM LIVES WHERE STATE LIVES.**

Expanded form:
**THE MECHANISM LIVES WHERE THE STATE LIVES; JUDGMENT ABOUT HOW TO COMPOSE MECHANISMS USUALLY LIVES IN SKILL/MODEL SPACE UNTIL AN INVARIANT IS EARNED STRONGLY ENOUGH TO LOWER INTO RUNTIME ENFORCEMENT.**

Promotion direction:
Skill behavior → repeated hostile evidence → stable invariant → composition/model discretion no longer desirable → server-native embodiment.

Do not lower judgment merely because it can be coded. Do not leave deterministic durable state in Skill space merely because a model can remember it.

## Cross-thread production split

Server/Runtime thread produces:
- actual native Runtime semantics;
- capability/effect/availability/currentness truth;
- authority/approval semantics;
- lifecycle/job/process/project/artifact/result truth;
- adapter-lossiness boundaries;
- verification/readback behavior;
- release qualification.

OBE/Skill thread produces:
- operating intelligence;
- Skill ecosystem/taxonomy;
- discovery grammar;
- rehydration/mission-control workflows;
- hostile evaluation campaign;
- adapter projection expectations;
- research over compositional mechanisms.

They meet at:
- `reports/PCMMAD_RUNTIME_ADAPTER_COMPATIBILITY_CONTRACT_V0_1.md`
- `reports/PCMMAD_RUNTIME_ADAPTER_PROJECTION_MATRIX_V0_1.md`
- `reports/PCMMAD_RUNTIME_ADAPTER_PROJECTION_MATRIX_V0_1.json`

**A second PCMMAD ontology SHALL NOT emerge in the Skill thread.**

When Skill assumptions disagree with audited Runtime truth:
1. preserve Runtime authority;
2. adapt at the projection boundary where possible;
3. mark the Skill assumption candidate/stale;
4. escalate core change only when a native invariant is actually insufficient;
5. record the discriminator before mutation.

The final OBE↔Runtime interface vocabulary SHALL NOT freeze before audited-successor reconciliation.

## AI attention / long-running work law

**LONG-RUNNING WORK SHALL NOT REQUIRE LONG-RUNNING MODEL ATTENTION.**

Queues/jobs/research/browser/build/download/archive/model work should return compact decision-grade receipts rather than hold a model in an open-ended tool wait.

Useful receipt information includes:
- job/work identity;
- submitted/queued/started/running/terminal state;
- current stage;
- elapsed time;
- queue position when known;
- heartbeat/progress age;
- warnings/failure digest;
- next expected transition;
- suggested recheck interval;
- output availability;
- result/log handles or ranges.

Bulk output stays server-side behind handles/ranges.

Lifecycle distinctions remain explicit:
**submitted != queued != started != running != completed != output-durable != registered != promoted.**

## Capability composition / holonic law

Composed capabilities may become useful higher-order wholes, but a composite does not automatically inherit all guarantees from its parts.

A composite must earn its own:
- purpose/boundary;
- interface;
- preconditions/postconditions;
- effects;
- authority;
- currentness;
- resource envelope;
- failure semantics;
- verification/result contract.

**EMERGENT CAPABILITY IS ALLOWED. EMERGENT AUTHORITY IS NOT.**

Example candidate composition in Skill space:
`git.status + test.run + artifact.verify + git.commit + remote.verify -> QUALIFIED_COMMIT`

The composite remains Skill-side until repetition/hostile evidence justifies lowering it into Runtime.

## Current candidate Skill bootstrap sequence — RESEARCH, NOT RUNTIME AUTHORITY

Current cross-thread candidate ordering:
1. MCP / Connector Capability Scout
2. Project Rehydration / Reincarnation Operator
3. Artifact / Release Sealer
4. Environment & Runtime Qualifier
5. Hostile Engineering Campaign Operator
6. Cross-Project Archaeologist
7. PCMMAD Mission Control
8. then Skill Forge

Rationale: each earlier Skill reduces uncertainty/cost for constructing and qualifying later Skills.

Candidate != earned. This portfolio may change under Runtime audit and hostile evaluation.

## Architectural Mechanism Quarry — RESEARCH BRANCH

Mechanisms currently worth quarrying against existing PCMMAD structures include:
- ECS-style orthogonal state/querying;
- holonic part/whole composition;
- entity/component relational state;
- capability security;
- effect systems;
- blackboard/event publication;
- actor/supervisor models;
- self-describing/reflective systems;
- hypermedia/affordance-bearing state;
- dynamic service composition;
- planning over typed state;
- resource/component queries;
- graph/query systems.

Campaign law:
**WE ARE NOT RESEARCHING ARCHITECTURES TO CHOOSE AN ARCHITECTURE. WE ARE QUARRYING MECHANISMS THAT MAY SHARPEN STRUCTURES PCMMAD HAS ALREADY EARNED.**

Admission test for a donor-derived mechanism: does it reduce special cases/schema rigidity/context load, improve lawful composition/currentness/authority/discovery/observability/failure containment, and make important queries possible **without** duplicating state, creating another ontology, adding hidden mutable state, increasing orchestration, weakening determinism, or making simple operations harder?

If not: reject it.

Mechanism first. Representation second. ECS/graph/etc. terminology is not permission for a framework rewrite.

## Current shared Runtime facts the Skill thread must respect

As of this rollover checkpoint:
- Git `main` is current through A-041 at `a97a00f67f3b79dbbe18e092d29b8971e588d4a2` / final 318 GREEN;
- A-042 project mutation ownership/exclusivity is active WIP and unqualified;
- exact A-042 WIP recovery identity is carried in `handoff/current/SERVER_THREAD_HANDOFF_CURRENT.md` and `handoff/current/wip/A042_PROJECT_MUTATION_AUTHORITY_WIP.py`;
- current Git working-tree registry import reports **103 tools**;
- fresh live action server separately reports **96 native tools / 16 families / 30 compact operations**;
- `LIVE_ACTION_SERVER_SURFACE != CURRENT_GIT_WORKING_TREE_REGISTRY`;
- `REGISTRATION != CAPABILITY_AVAILABILITY != TARGET_HEALTH`;
- bound approval is a Runtime authority object/challenge, not boolean payload metadata;
- compact OpenAPI remains compatibility projection, not ontology;
- MCP/HUD availability projection consumes native capability cards;
- result/log payloads remain bounded via handles/ranges where needed;
- Git publication is source lineage, not live deployment;
- final schema redesign remains last-stage, after whole-runtime convergence.

## Current cross-thread open seam

OBE/Skill research remains candidate work and SHALL reconcile against audited current Runtime semantics before interface promotion.

High-priority donor seam after A-042:
- current Runtime has `contract_digest` and bound approvals/HUD use it;
- current source does **not** implement ordinary invocation `expected_contract_digest` / `CAPABILITY_CONTRACT_STALE` / `BAD_EXPECTED_CONTRACT_DIGEST` enforcement;
- ancestry-stale OBE A-001 patch is controlled evidence only;
- after A-042 publication, reproduce the stale ordinary-invocation contract case against then-current HEAD and derive the native mechanism only if still earned.

Do not mix this donor seam into A-042 mutation-exclusivity work.

## Re-entry rule

A fresh model/thread shall read this file after Current/ICF/Commander/Doctrine surfaces and before freezing any Skill/adapter interface.

Then perform fresh Git/local/runtime readback.

`CURRENT_INGRESS_POINTER != CURRENT_STATE_PROOF`.
