# PCMMAD Laboratory Runtime — Thread Rollover Checkpoint

Status: **CURRENT ROLLOVER / GITHUB-CENTERED / RELEASE GATES STILL OPEN**
Created: 2026-09-10 18:40 ET
Mode: CHECKPOINT / HANDOFF
Authority ceiling: recovery/control artifact; fresh Git, GitHub Actions, live Runtime and owning-plane readback outrank this file.

## 1. Re-entry order

1. `git rev-parse HEAD`
2. `git status --short --branch`
3. `git ls-remote origin refs/heads/main`
4. GitHub Actions for that exact remote HEAD
5. local action/ngrok health
6. live Runtime identity/capability/concurrency readback
7. this checkpoint
8. `CURRENT_INGRESS.md` + `handoff/current/*CURRENT*`

Do not widen or promote live until those agree.

## 2. GitHub source truth at rollover

Repository: `https://github.com/SEng-Kitathas/AI-Server-InfrA.git`
Remote `main`: `e1b2b8eddd92e8ad9159a548f9e6d6b2beb895f4`
Tree: `8fbded01e519a938ded1f2177378cd6693d788b7`
Parent: `2753e87b9cc8f3309666ab479413306ba85e9b11`
Title: `Add project-aware access logging`

Recent lineage:

```text
e1b2b8e  Add project-aware access logging
2753e87  Repair remaining hosted cleanbox failures
529345e  Expose cleanbox CI failures
3213509  Close remaining cross-platform cleanbox failures
f38c564  Refresh current surfaces for schema v11
0cc7894  Make Runtime clean-box reproducible
7e4c66a  Add v11 capability microkernel schema
```

## 3. Current schema truth

Canonical v11 source schema:
`baseline/pcmmad_receiver/pcmmad_lab_action_schema_v11_0_capability_microkernel_8.json`

SHA-256: `ee62b261d6e5518b585faccd4af21a42d9b7bd6b3dc63f8af0e1242ef9fb9010`
Operations: **8**
Bytes: **33,844**
Mechanism commit: `7e4c66a769884269d71babdb92217ba80eb66e74`

Canonical operations: `orient / invoke / flow / compose / execute / observe / resume / transfer`.

The canonical JSON/generator/schema runtime/routes/validator were checked from `7e4c66a` through `e1b2b8e`: **no Git diff**. Published clean-box/transfer/telemetry/access-log repairs therefore did not change v11 schema bytes.

An older uncommitted real-wire hardening donor exists separately. If re-earned against current source it would require documenting `413`, `415`, and a 1 MiB `/lab/vnext/*` request-body ceiling. It is not current schema authority.

## 4. Hosted clean-box CI — CURRENT RELEASE BLOCKER

GitHub Actions run: `34537723493`
Head: `e1b2b8eddd92e8ad9159a548f9e6d6b2beb895f4`
Conclusion: **FAILURE** on Windows and Ubuntu full-suite steps.

Ubuntu public annotation gives one exact current discriminator:

```text
test_hot_scan_cost_is_independent_of_terminal_history_count
AssertionError: 38 != 50
tests/test_execution_active_terminal_partition.py:200
self.assertEqual(len(queued), 50)
```

Windows still exposes only a suite-level/full-suite failure for this run.

Node.js 20 deprecation warnings for GitHub Actions are present but are **not established as the pytest cause**.

Prior local repaired-byte qualification reached 995 JUnit cases / 0 failures / 2 skips in serial, loadscope and worksteal. Hosted CI outranks local green for release readiness.

`LOCAL_GREEN != HOSTED_CLEANBOX_GREEN`

## 5. Published project-aware access logging

Commit `e1b2b8eddd92e8ad9159a548f9e6d6b2beb895f4` is published source and directly answers the operator's busy-console request.

Format contract:

```text
[PCMMAD] [job:DEADBEEF12] POST /echo 200 12.3ms
[RAHL] POST /project/files/read 200 ...
[MULTI] ...
[GLOBAL] GET /health 200 ...
```

Features:
- bounded project tags;
- known PCMMAD/Rahl aliases;
- optional `PCMMAD_PROJECT_LOG_ALIASES_JSON` custom aliases;
- short job tags;
- `MULTI` for multi-project payloads;
- `GLOBAL` when no project applies;
- oversized bodies are not parsed merely for logging;
- `PCMMAD_ACCESS_LOG=0` disables hooks.

Source-published != live-promoted.

## 6. Local adaptive mutation-guard campaign — NOT GITHUB AUTHORITY

Working copy:
`E:\new pc\AI_Pushes_Sandbox\projects\PCMMAD_RECEIVER_LAB\quarantine\mutation_guard_f38c564`

Local commit directly on this rollover source head:
`12ccc208ec2e9183e3b280618f266211cc00179b`
Tree: `10cefc1ec3d31708c6f4af241035574343d2855b`
Parent: `e1b2b8eddd92e8ad9159a548f9e6d6b2beb895f4`
Title: `Make project mutation contention adaptive`

Intent:
- `LEASE_LIFETIME != CONSEQUENCE_LOCK_LIFETIME`;
- same-project unknown-effect execution remains conservative/project-exclusive;
- contenders queue before spawn instead of burning worker slots on guard contention;
- cross-project work still uses other worker capacity;
- holder heartbeat is coordination evidence, never authority;
- healthy-holder wait is adaptive/bounded and dormant after release;
- generation fencing stays load-bearing.

The clone is one local commit ahead and also contains uncommitted refinements. Rebase/read/diff/qualify before any push.

Known uncommitted file identities at rollover:
- `baseline/pcmmad_receiver/access_logging.py` SHA `0ab7075451841f5b9944df7d9caadeb4416989b305fc8808abfc6595f6ce7681`;
- `baseline/pcmmad_receiver/project_mutation_authority.py` SHA `27cbb2adb9f9233b1e46077c10d97760b2588ab91188971355d43d07413987c5`.

Do not conflate scheduler capacity with same-project mutation concurrency.

## 7. Local schema-wire hostile campaign — DONOR / STALE BASE

Working copy:
`E:\new pc\AI_Pushes_Sandbox\projects\PCMMAD_RECEIVER_LAB\quarantine\ci_shallow_f38c564`

Base: `f38c564c486b03278ba9f10dbc87aa4b1c9c07d1` — stale relative to current main. Reproduce against current source before porting.

Tracked candidate files:
- `lab_routes.py` SHA `b986670ee5ee11c2e5584ec758b6e22abddae88169a3ca4e1f90258f8ccd6c44`;
- `lab_schema_validation.py` SHA `7a7275688e9d7635c9d8b25c21f0bbdc58fa5a607ce4419a29250cd2568503b2`.

Untracked intended regression:
- `tests/test_schema_vnext_http_conformance.py` SHA `accc64984ebda23c6a9192a19f8ac6f8408d65f0bfa5f07757d94aaddfe381aa`.

Real HTTP pressure previously exposed malformed-JSON HTML errors, unenforced OpenAPI unknown/size/pattern constraints and generic transfer 500s. Candidate repair closed those in an isolated Waitress instance and real-capability dogfood verified lease non-grant, plan/effect tamper rejection, dataflow, mutation blocking, continuation currentness/single-use/concurrent resume, and v10 compatibility.

Treat as donor evidence, not as a patch to cherry-pick blindly.

## 8. Source vs loaded live Runtime

Current action-server health at checkpoint time came back online but reports the **older compact 30-operation control surface** and global execution concurrency **8**. GitHub source is materially ahead.

`ENGINEERING_TRUTH != LIVE_PROCESS_TRUTH UNTIL EMBODIED + READ BACK`

No current V30 source promotion/restart was completed in this thread.

Rollback snapshot preserved at:
`C:\Users\ancal\Desktop\PCMMAD_LIVE_ROLLBACKS\20260910_134056_pre_92010b5_full_parity`

Rollback manifest SHA:
`e694349a89e6d66526a439a584427aabe176bc0bdd6ddb78091bba000b29d908`

Live venv scar: relative executable resolution during clean-box diagnosis accidentally installed development dependencies into the Desktop venv. Before final promotion, rebuild/replace a clean runtime-only venv from declared runtime dependencies.

## 9. Architecture state — DO NOT REOPEN WITHOUT NEW EVIDENCE

Core Runtime architecture remains converged at the current claim ceiling.

```text
PCMMAD = methodology
Runtime = durable truth/state/capability/execution
v11 = compact Assistant-facing capability microkernel
MCP/OpenAPI/CLI/HUD = transport projections
OBE/Skills = reusable operating intelligence
Models = replaceable co-processors
```

Load-bearing laws:

```text
TRANSPORT IS NOT ARCHITECTURE AUTHORITY
MECHANISM LIVES WHERE STATE LIVES
EMERGENT CAPABILITY IS ALLOWED; EMERGENT AUTHORITY IS NOT
CAPABILITY_LEASE != CAPABILITY_GRANT
DESCRIPTIVE_EFFECT_TRAITS != SCHEDULER_AUTHORITY
DECLARED_EFFECT_CLASS != VERIFIED_EFFECT_TRUTH
CONTINUATION != CURRENTNESS
LIVE_SHADOW != DTS != RES != UCM
EXPECTED_FAILURE != ANY_FAILURE
SOURCE_QUALIFIED != LIVE_PROMOTED
```

Current source has 158 native capabilities. v11 remains 8 operations; v10.3 remains the 30-operation compatibility/import surface.

ICF-CS v1.2 remains current process/continuity doctrine; standard SHA `f966029496fd6e31a76a36a6e967db37ca2147acfa890a880426ae6a7fa79d92`.

## 10. Known stale-currentness repair performed by this checkpoint child

The pre-checkpoint repository contained current-facing prose that still named `0cc7894...` as the source frontier. This checkpoint child refreshes the current/navigation surfaces to the `e1b2b8e` mechanism frontier while leaving dated/historical receipts unchanged.

Fresh Git still wins over this checkpoint.

## 11. Immediate next actions — ordered

### P0 — confirm fresh Git/CI/local health
- read current remote main;
- inspect Actions for exact head;
- verify local action endpoint + live Runtime identity.

### P0 — close hosted CI
- first Ubuntu discriminator is queued-count 38 vs 50 in active-terminal partition test;
- obtain/emit exact Windows testcase if still red;
- do not live-promote until Windows + Ubuntu serial suites are green and Windows parallel burns run green.

### P0 — reconcile adaptive mutation guard
- begin from local commit `12ccc208ec2e9183e3b280618f266211cc00179b`;
- compare uncommitted refinements;
- re-run authority/admission/real concurrency pressure;
- publish only if generation fencing and conservative unknown-effect execution still hold.

### P1 — re-derive schema-wire hardening against current source
- do not blindly cherry-pick stale `f38c564` WIP;
- reproduce the wire defects first;
- if still present, port minimal validation/error/body-bound repair and update schema docs for 413/415/1 MiB.

### P1 — final live promotion
Only after source + hosted CI are green:
- rebuild runtime-only venv;
- preserve rollback;
- deploy exact GitHub-tracked bytes;
- canonical restart receiver/ngrok;
- read back source/live identity, 158 capabilities, ICF-CS v1.2, schema projection, intended execution capacity 12, scheduler/watcher/HUD/observability/access logging;
- run real >=10 simultaneous async pressure;
- drain queue/running/orphans/errors to zero;
- preserve before/after telemetry and promotion/rollback receipts.

### P2 — private UCM import
Still separate unless explicitly promoted in priority.

## 12. Things already earned / do not redo

- Runtime / methodology / transport / Skill separation;
- v11 eight-op microkernel architecture;
- static plan-cost admission (`max_cost_units` exists);
- capability lease non-authority;
- separate conservative effect truth;
- continuation-currentness law;
- expected capability contract binding;
- clean-box dependency/environment isolation;
- relative executable currentness hardening;
- project-aware access logging;
- transfer object-currentness law;
- ICF-CS v1.2 + Live/DTS/RES/UCM separation.

## 13. Claim ceiling

This checkpoint does not claim:
- hosted CI green;
- adaptive guard GitHub-published;
- wire hardening GitHub-published;
- product-side v11 schema installed;
- live Runtime promoted;
- private UCM imported;
- packaged V30 release identity.
