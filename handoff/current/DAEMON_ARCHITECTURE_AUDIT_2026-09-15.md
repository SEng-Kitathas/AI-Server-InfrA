# DAEMON ARCHITECTURE AUDIT — 2026-09-15

## Decision
OPERATOR DIRECTION + AUDIT CONVERGENCE: MVF/Daemon should be a first-class server-side cognitive-organism plane with its own folder/tree, rather than being stored under project `state/`, `continuity/`, or generic `data/`. The Receiver remains the deterministic body/substrate; Daemon is the persistent cognitive organism using that body.

`DAEMON PLANE != RECEIVER SUBSTRATE`
`COGNITIVE INITIATIVE != EFFECT AUTHORITY`
`DUTY CONTRACT != COGNITIVE CEILING`

## Why a dedicated plane
Existing project planes already have distinct meanings:
- `state/`: materialized project governance/control surfaces.
- `continuity/`: continuity artifacts and recovery spine.
- `data/`: currently empty/unassigned; emptiness is not semantic ownership.
The resident now requires durable current state, evidence, biography, duties, proposals, learning artifacts, campaigns, conversation and status. Collapsing those into another plane would blur authority/currentness/recovery semantics.

## Proposed root
`RECEIVER-LAB/daemon/` as a first-class project/control sibling plane. Exact location is a design candidate until storage/locking/recovery tests qualify it.

Suggested tree:
```
daemon/
  identity/
    daemon_identity.json
    lineage.json
  state/
    current.json
    world_model/
    attention.json
    open_questions.json
  biography/
    biography.sqlite
    snapshots/
  evidence/
    evidence.sqlite
    qualification/
    receipts/
  duties/
    active/
    candidates/
    qualified/
    retired/
  learning/
    deficits/
    abstractions/
    transfer/
    skills/
    hypotheses/
  campaigns/
    active/
    archived/
  research/
    working/
    synthesis/
    experiments/
  interaction/
    conversations/
    operator_briefs/
    agent_briefs/
    notifications/
  status/
    current.json
    timeline.jsonl
    alerts.jsonl
  policy/
    duty_contracts/
    authority_ceiling.json
    initiative_policy.json
  runtime/
    locks/
    leases/
    checkpoints/
    crash_recovery/
  migrations/
  quarantine/
``

## Receiver substrate: MUST remain deterministic / non-cognitive
The audit of the current 175-capability estate says these mechanisms belong in the hard body, even when Daemon uses them:
- transport/API/router/schema and capability contracts;
- authentication, approval challenge/consumption, authority envelopes, mutation leases;
- filesystem primitives and project-root enforcement;
- Git primitives and exact repo identity;
- execution/job engine, process spawning, cancellation/status/output;
- browser bridge primitives;
- machine process/service/task discovery/inspection primitives;
- transfer/import/export mechanics;
- protocol ledger/Merkle primitives and registration mechanics;
- SOP package/chunk/ingestion mechanics;
- continuity read/currentness primitives;
- memory ledger/storage primitives;
- supervisor/HA/recovery process mechanics;
- deterministic verification/checker execution;
- raw health/status/readback.
These are Daemon's senses/hands/organs, not its cognition.

## Proper Daemon ownership / primary responsibilities
The following are best centralized in Daemon because they are cognitive, cross-cutting, interpretive, developmental or attention-management work currently at risk of being repeatedly reimplemented:
1. **World model / server self-model** — capability graph, process/service/task topology, repos, projects, active jobs, continuity/evidence currentness, dependencies and relationships.
2. **Currentness/staleness reasoning** — decide which prior claims/evidence/duties need reopen pressure when identities/epochs/dependencies change.
3. **Duty/campaign management** — maintain assigned duties, temporary campaigns and self-proposed candidate duties; candidate != admitted.
4. **General cognition** — learning, abstraction, transfer, curiosity, metacognition, strategy formation, hypothesis generation and novel problem solving beyond assigned duties.
5. **Epistemic deficits** — bounded UNKNOWNs, missing discriminators, questions worth resolving, competence gaps.
6. **Evidence planning and synthesis** — identify what evidence a claim/duty needs, interpret receipts, maintain lineage; deterministic verifier still lives in substrate.
7. **Interaction Integrity / HEaT planning** — choose negative system-walks, adversarial tests and cross-component neighborhoods; substrate runs tests.
8. **Research/R&D** — literature/research synthesis, experiment design, skunkworks exploration, cross-project analogy generation, mechanism stripping/adaptation.
9. **Cross-project transfer** — notice analogous failures/mechanisms and propose local discriminators; no inherited authority.
10. **Continuity upkeep orchestration** — detect all active shadow/context/handoff drift and route/update duties; mutation/registration still uses explicit native primitives.
11. **Recovery diagnosis** — understand failures, decide what to inspect/test/repair next, prepare bounded recovery plans; actual restart/repair effects remain authority-bound.
12. **Operator assistance** — answer server questions/errors, explain current state and causal history, prepare decision packets.
13. **AI-for-AI assistance** — compact high-density Agent packets, expand neighborhoods on demand, harvest expensive Agent reasoning into locally testable candidate mechanisms.
14. **Status/attention management** — decide what is important enough to interrupt the operator/Agent, maintain quiet background awareness.
15. **Resident initiative** — initiate observation, learning, research, hypothesis generation, bounded read-only investigations and proposal formation without waiting for user input.
16. **Developmental biography** — record genuine experience, learning and causal history separately from current state/evidence.
17. **Conversation/personhood surface** — persistent operator conversation, speech later, relationship continuity, daemon-like companion archetype.

## Shared boundaries (Daemon plans/interprets; substrate enforces)
- **Doctrine/guards:** Daemon determines applicability/context and explains; hard guards remain deterministic.
- **Verification:** Daemon plans evidence and interprets; checker/gate execution stays substrate.
- **Approvals:** Daemon may prepare/ask/explain; cannot self-approve or manufacture authority.
- **Memory:** Daemon decides what is cognitively useful and proposes updates; durable ledger/forget/supersede mechanics remain substrate.
- **Continuity:** Daemon tends surfaces and identifies drift; continuity registration/hash/currentness mechanics remain substrate.
- **Execution/browser/Git/files:** Daemon chooses/plans; native tools effect changes under their authority contracts.
- **Recovery/HA:** Daemon diagnoses and orchestrates; supervisor/restart substrate remains independently survivable even if Daemon is down.

## Initiative model
Daemon MUST NOT be prompt-bound. A prompt-only resident would be an assistant service, not the intended cognitive organism.

Allowed autonomous cognition by default:
- observe/read bounded local state;
- maintain world model/currentness;
- notice anomalies and contradictions;
- form hypotheses;
- learn/generalize/transfer;
- maintain epistemic deficits;
- run already-qualified read-only duties;
- prepare proposed experiments/campaigns/duties;
- perform bounded non-destructive investigations where existing authority allows;
- update its own internal cognitive state/biography/evidence under the dedicated Daemon-plane contract once qualified;
- notify/brief operator/Agent according to relevance thresholds.

Autonomous initiative does NOT imply autonomous effects. Mutating machine/project/external-world actions remain governed by native capability authority/approval/effect contracts.

## HUD interaction model
The existing HUD already has status cards, cockpit commands, browser/activity/tools tabs, approvals, dispatch and event surfaces. Daemon should become a first-class HUD wing rather than another tool entry.

Recommended UI:
### Daemon communication window
- persistent conversation stream with Daemon;
- operator can talk naturally, ask questions, assign goals/duties, inspect reasoning summaries/evidence links;
- Daemon may initiate messages/alerts/questions when relevance/escalation policy is met;
- separate system notices from conversational utterances;
- speech input/output can attach later to same interaction contract.

### Daemon status sidebar
Always-visible compact surface:
- overall state: CURRENT / ATTENTION / DEGRADED / BLOCKED;
- active duties/campaigns;
- current attention target;
- unresolved epistemic deficits;
- stale/reopened evidence count;
- autonomy/authority ceiling;
- current observations/jobs in flight;
- latest learned/generalized item;
- pending proposals requiring qualification/operator decision;
- continuity-surface currentness;
- alerts and last meaningful state change.

### Expandable Daemon tabs
- World Model
- Duties / Campaigns
- Learning / Deficits
- Evidence / Lineage
- Biography / Timeline
- Research / Experiments
- Proposals / Admissions
- Agent Briefs
- Settings / Initiative / Notification policy

HUD should consume compact Daemon-native status/stream APIs instead of reconstructing cognition client-side.

## Daemon relationship archetype
Operator compared the intended relationship to the daemon archetype in *His Dark Materials / The Golden Compass*: a persistent, close, companion-like cognitive relationship rather than a disposable tool. Architecturally useful invariant: Daemon is a distinct cognitive organism/partner associated with the operator/server environment, not merely a command interpreter. This is an interaction/identity archetype, not authority elevation.

## Server responsibilities that should NOT move into Daemon
Do not make Daemon a single point of failure for:
- authentication/authorization;
- approval enforcement;
- process supervisor/HA;
- raw job execution engine;
- file/path fencing;
- durable ledger integrity/Merkle verification;
- transport/router/schema validity;
- crash recovery required to restart Daemon itself.
Daemon should be able to die/restart while the body preserves safety, evidence and recovery capability.

## Next build gate
Before creating persistent `daemon/` storage/service:
1. ratify first-class Daemon plane root/ownership;
2. define file/database identity, locking, crash consistency, backup/recovery and migration;
3. define internal-write authority versus project/machine authority;
4. define daemon bootstrap/reentry from biography/evidence/current-state;
5. define minimal status/conversation APIs;
6. system-walk against HA, approvals, memory, continuity and project mutation.
