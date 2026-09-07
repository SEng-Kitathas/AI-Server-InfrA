# PCMMAD Receiver V30 — NEW SERVER THREAD HANDOFF — CURRENT

Status: **CURRENT ROLLOVER / RECOVERY AUTHORITY POINTER**
Prepared: 2026-09-06 22:38 ET
Project: `PCMMAD_RECEIVER_LAB`
Repository: `https://github.com/SEng-Kitathas/AI-Server-InfrA.git`
Branch: `main`
Authority ceiling: this handoff is a recovery/control surface. It does not replace fresh local/Git/live Runtime readback before consequence-bearing mutation.

## 0. Why this handoff exists

The saturated server thread visibly rolled back behind persisted project reality more than once. Current evidence supports:

- **VERIFIED:** canonical outer project state remained current through A-041 publication and A-042 activation.
- **VERIFIED:** Git `handoff/current` had become stale at the A-041 pre-publication candidate and therefore was not a sufficient standalone recovery mirror.
- **SUSPECTED, NOT PROVEN:** full-thread saturation/compaction caused `CHAT_VISIBLE_FRONTIER` to lag persisted project state.

Carry these laws forward:

`CHAT_VISIBLE_FRONTIER != PERSISTED_PROJECT_FRONTIER`

`RECENT_INFERENCE != CURRENT_AUTHORITY`

`CURRENT_INGRESS_POINTER != CURRENT_STATE_PROOF`

`RECENT_TIMESTAMP != CURRENT_AUTHORITY`

`HISTORICAL_HANDOFF != CURRENT_INGRESS`

If any material surface disagrees:

`CONFLICT -> RECOVERY/AUDIT -> LOCALIZE -> REPAIR/SUPERSEDE -> READBACK -> RESUME`

## 1. FIRST ACTIONS IN THE NEW THREAD — DO NOT SKIP

Start in **RECOVERY / AUDIT**, role **R1 Conservative Auditor**.

Before discussing architecture or mutating source:

1. call project info / manifest / bounded rehydrate for `PCMMAD_RECEIVER_LAB`;
2. read this file;
3. read Current State -> ICF-CS -> Current Canonical SOP pointer + Commander -> Next/Doctrine/Revisit/Trace -> Live Shadow -> DTS tail;
4. run exact Git readback:
   - `git rev-parse --show-toplevel`
   - `git branch --show-current`
   - `git rev-parse HEAD`
   - `git rev-parse HEAD^{tree}`
   - `git status --short --branch`
   - `git ls-remote origin refs/heads/main`
5. call live server health/capabilities if Runtime behavior matters;
6. verify the A-042 WIP source hash before touching it;
7. only then continue BUILD work.

Never resume from the newest-looking chat paragraph alone.

## 2. VERIFIED CURRENT GIT TRUTH

At checkpoint creation:

- local HEAD = remote `main` = `a97a00f67f3b79dbbe18e092d29b8971e588d4a2`;
- tree = `2fa1ffff0d3cf3a8f8cd018f930adbb8862a4a53`;
- subject = `Add protocol Merkle proof receipts`;
- branch was clean except the intentionally untracked A-042 source candidate described below.

`GIT_PUBLICATION != LIVE_RUNTIME_PROMOTION`.

Published raid lineage that SHALL NOT be replayed:

| Step | Commit | Earned mechanism | Qualification at publication |
|---|---|---|---|
| A-037 | `59b4b5e5d6339127e50e052827f27bc94a14c832` | protocol mutation as incremental verified fold/checkpoint | protocol 18/18; full 284 GREEN |
| A-038 | `cb2b4ee2c54c2aab02fa29b8feca6c40c666148e` | deterministic execution lifecycle replay harness | focused 39/39; 100/100 current seeds; full 289 GREEN |
| A-039 | `d887213d8fa341af79e59ac1070ebf66225e107f` | legacy PID identity binding / recycle defense | focused 29/29; 100/100 seeds; full 297 GREEN |
| A-040 | `486eee4a9c8a053bc5f5f301199010ba1a7f8d42` | event-driven execution wake + slow level-triggered resync | focused 37/37; full 306 GREEN |
| A-041 | `a97a00f67f3b79dbbe18e092d29b8971e588d4a2` | CT-style Merkle inclusion/consistency protocol receipts | targeted 20/20; full 318 GREEN |

Do not re-derive these as open work unless new evidence specifically demotes them.

## 3. LIVE SERVER CURRENTNESS — SEPARATE SURFACE

Fresh live action-server readback during this checkpoint:

- status: online;
- scheduler: alive;
- scheduler interval: 0.25 s;
- native router: **96 tools / 16 families**;
- compact imported control surface: **30 operations**;
- global execution concurrency: 8.

Fresh current-Git working-tree import separately reported **103 native tools**.

Therefore:

`LIVE_ACTION_SERVER_SURFACE != CURRENT_GIT_WORKING_TREE_REGISTRY`

Do not infer live deployment from Git success or tool-count similarity/difference. Live promotion remains a separate gate.

## 4. ACTUAL FRONTIER — A-042 IS ALREADY IN PROGRESS

**A-042 project mutation ownership/exclusivity across tabs/clients is ACTIVE.**

It is not merely “next.” An uncommitted candidate already exists:

`V30_WORKING/PCMMAD_receiver/baseline/pcmmad_receiver/project_mutation_authority.py`

Current exact identity:

- bytes: 15,838;
- lines: 455;
- SHA-256: `3f5fdc3ab2d9ebf6e1abd17dac36a22600edbae456c8c99afa9a9b966117ebe1`;
- AST parse: PASS;
- Git status: untracked;
- qualification: **NONE YET**;
- route/tool integration: **NONE VERIFIED YET**;
- tests referencing this module: **NONE FOUND at checkpoint start**.

A byte-exact recovery copy is carried in the Git handoff at:

`handoff/current/wip/A042_PROJECT_MUTATION_AUTHORITY_WIP.py`

That copy is **WIP recovery material, not Runtime authority**.

### What the existing A-042 candidate already implements

Do not reinvent these pieces before auditing them:

- persistent project-scoped lease record under control state;
- persistent integer **generation fence**;
- lease ID + owner ID + optional session/client identity;
- bounded TTL (default 120s, min 10s, max 900s);
- ACTIVE / RELEASED / EXPIRED / UNOWNED states;
- record integrity hash;
- cross-process project guard file with Windows and POSIX locking paths;
- acquire with `expected_generation` stale-generation rejection;
- active-owner conflict rejection;
- expiry transition/recovery;
- renew;
- release;
- active mutation guard validating generation/lease/owner/session;
- backward-compatibility session guard that fences legacy sessions when a governed lease exists.

Key candidate law already embodied:

**a stale client must not merely wait for a newer owner to finish and then regain authority; the persistent generation fence must make its remembered mutation authority stale.**

### A-042 target law

`THREAD_LOCAL_DISCIPLINE != PROJECT_MUTATION_EXCLUSIVITY`

Consequential project/Git/continuity mutation needs server-native cross-client ownership. Reads should remain nonblocking.

## 5. EXACT A-042 CONTINUATION SEQUENCE

Do not redesign the module from scratch. Start by hostile-qualifying what exists.

### A. Inspect first

1. read `project_mutation_authority.py` linearly;
2. inspect current project/control/Git/continuity mutation chokepoints;
3. locate existing session/client identity and authority plumbing;
4. decide the minimum native projection for inspect/acquire/renew/release and mutation-guard use;
5. do not scatter lease checks across dozens of routes if a smaller authoritative choke point exists.

### B. Required hostile discriminators before integration can be called earned

At minimum prove:

1. two simultaneous owners cannot both acquire generation N;
2. stale `expected_generation` fails after another campaign advances generation;
3. old lease ID/generation cannot mutate after release + reacquire;
4. expired owner can be recovered/taken over without immortal lock;
5. wrong owner/session is rejected;
6. malformed or integrity-corrupt lease state fails safely/observably;
7. file-lock/process crash does not create permanent guard ownership;
8. reads remain available while a mutation lease is held;
9. legacy compatibility behavior is explicit and cannot bypass a different active governed session;
10. two tabs/process clients reproducing the observed continuity/Git race result in exactly one consequence-bearing mutation authority;
11. current optimistic hash/currentness checks remain in force — lease authority does not replace them;
12. lease expiry during a long mutation cannot silently allow two simultaneous consequence-bearing writers; derive the renew/fence semantics needed for that boundary.

### C. Only after core semantics survive

Then integrate the smallest justified native surfaces and fence actual consequential project mutation paths. Add telemetry/readback. Run focused hostile tests, full suite, continuity update, Git commit/push/remote readback.

A-042 SHALL be published as its own step before opening the next raid.

## 6. A-042 CLAIM CEILING RIGHT NOW

Current candidate is **implementation evidence only**.

Do NOT say:
- A-042 is fixed;
- project mutation is exclusive;
- routes are protected;
- the live server uses the lease;
- the lease survived hostile concurrency;
- the WIP source is current Git truth.

Those become true only after explicit tests/integration/readback prove them.

## 7. POST-A-042 QUEUE — DO NOT PULL FORWARD

After A-042 is earned/published:

1. **OBE A-001 ordinary-invocation stale-contract discriminator** — current V30 has `contract_digest`, and bound approvals/HUD use it, but current source contains no `expected_contract_digest`, `CAPABILITY_CONTRACT_STALE`, or `BAD_EXPECTED_CONTRACT_DIGEST` ordinary-invocation enforcement. The older OBE patch is donor evidence only; reproduce against then-current HEAD and derive natively.
2. mutating lab/protocol idempotency expansion (`RESPONSE_LOST != SAFE_TO_REPEAT_MUTATION`);
3. Windows Job Object resource envelope using already-declared memory/process limit fields;
4. remaining raid mechanisms only by discriminator;
5. **final schema redesign is last**, after whole-runtime convergence.

Do not mix these into A-042 merely because they are adjacent authority/safety concerns.

## 8. RUNTIME / OBE / SKILLS DUALITY — KEEP THIS STRAIGHT

- PCMMAD = methodology.
- Laboratory Runtime = durable machine truth/state/deterministic capability.
- Adapters = MCP/OpenAPI/CLI/HUD projections.
- OBE/Skills = reusable operator intelligence/composition judgment.
- Model = replaceable co-processor.
- Project Chat = replaceable mission interaction surface.

`TRANSPORT IS NOT ARCHITECTURE AUTHORITY`

`MECHANISM LIVES WHERE STATE LIVES`

`EMERGENT CAPABILITY IS ALLOWED. EMERGENT AUTHORITY IS NOT`

A second PCMMAD ontology SHALL NOT emerge in the Skill thread.

OBE/Skill candidate interfaces remain provisional until reconciled with audited current Runtime semantics.

## 9. LOAD-BEARING ENGINEERING LAWS / SCARS TO PRESERVE

Do not regress these:

- `INTENT IS A CONSTRAINT, NOT A CEILING`;
- `TOOL_SUCCESS != TASK_SUCCESS`;
- `SUBMITTED != STARTED != COMPLETED != REGISTERED != PROMOTED`;
- `DERIVED_STATE_IS_A_FOLD_NOT_A_REBUILD`;
- `INCREMENTAL_STEADY_STATE != NO_FULL_RECOVERY_PATH`;
- `CRYPTOGRAPHIC_VALIDITY != CURRENTNESS`;
- `THREAD_LOCAL_DISCIPLINE != PROJECT_MUTATION_EXCLUSIVITY`;
- `GIT_PUBLICATION != LIVE_RUNTIME_PROMOTION`;
- `V30_WORKING_TREE_SUCCESS != RELEASE_QUALIFICATION != LIVE_DEPLOYMENT`;
- `LONG-RUNNING WORK SHALL NOT REQUIRE LONG-RUNNING MODEL ATTENTION`;
- final schema redesign remains locked last;
- composition before invention; quarry mechanisms, not donor architectures wholesale.

## 10. ROLLOVER / ANTI-ROLLBACK PROCEDURE

For every fresh server thread or recovery event:

1. persisted project surfaces outrank conversational momentum;
2. exact Git readback outranks handoff prose about Git;
3. live Runtime readback outranks Git assumptions about deployment;
4. WIP worktree bytes outrank stale summaries about an active candidate;
5. the Git handoff mirror is fallback/recovery, not live authority;
6. if the mirror is stale, repair it before relying on it for another rollover;
7. append the recovery incident to DTS and update Live Shadow/ICF/Commander/Current/Next/Doctrine/Revisit/Trace together;
8. never let a “newest-looking” report outrank ICF currentness by timestamp alone.

## 10A. ROLLOVER CHECKPOINT QUALIFICATION

This handoff/mirror repair has now passed:
- strengthened Git handoff regression: **9 / 9 PASS**;
- complete V30 suite: **321 collected tests GREEN**;
- existing conditional Windows symlink-privilege skip only.

The first rollover checkpoint was Git/remote-verified as `86f410b373877dd8cde2b30a388512b928169178`. This handoff may itself be present in that or a later recovery-only commit, so a fresh thread SHALL read current Git dynamically. Recovery/checkpoint commits do **not** imply A-042 engineering publication.

`CHECKPOINT_PUBLICATION != A042_ENGINEERING_PUBLICATION`.

## 11. IMMEDIATE FIRST SENTENCE FOR THE NEXT THREAD

Use something equivalent to:

**“Mode: RECOVERY/AUDIT. I have re-read persisted Current/ICF/Commander/Live and performed fresh Git/worktree readback. A-041 is the last published engineering feature, any newer handoff/checkpoint commit does not promote A-042, and A-042 is active WIP at SHA `3f5fdc3ab2d9ebf6e1abd17dac36a22600edbae456c8c99afa9a9b966117ebe1` and is unqualified. I will inspect/hostile-test the existing A-042 candidate before any new architecture or mutation.”**

That is the lawful resume point.
