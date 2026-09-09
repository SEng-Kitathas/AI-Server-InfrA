# V30 T0.2 PROJECT REHYDRATION DOGFOOD — RUNTIME REPAIRS

Date: 2026-09-08
Status: **ENGINEERING QUALIFIED / PUBLICATION PENDING**
Live Runtime: **FROZEN / UNTOUCHED**
Final schema: **LAST / LOCKED / UNTRIGGERED**
Skill canonical promotion: **NOT CLAIMED**
UCM refactor/import: **PAUSED / OUT OF SCOPE**

## Trigger

The verified ecosystem convergence carrier supplied `PROJECT_REHYDRATION_REINCARNATION_OPERATOR_V0_2_2026-09-08.zip` as a candidate Skill requiring newest-Runtime real-project dogfood.

The source carrier was independently verified at ingress. A manual chat-to-server base64 transfer of the nested T0.2 ZIP was corrupt by 3 bytes and was explicitly rejected; no test claim relies on that corrupt fixture. Dogfood instead used the independently verified candidate semantics/receipt contract as the oracle while executing the current Runtime's native read/currentness primitives against `PCMMAD_RECEIVER_LAB`.

## Dogfood sequence

1. Run candidate-style `RECOVERY_ONLY` using native project rehydration/read/currentness surfaces.
2. Compare the reconstructed receipt against an independent Git/Runtime/persisted-artifact oracle.
3. If credible recovery exposes Runtime defects, enter `RECOVER_AND_CONTINUE_SERIOUS_WORK` under explicit PDVER / Helix / Attention Reservoir / OARR / Loop+ / CSC accounting.
4. Hostile-qualify repairs before publication.
5. After publication, rerun cold recovery from a clean frontier.

## Defect 1 — advertised project rehydration failed at execution

### Observation

`project.context.rehydrate` was registered and advertised but actual dispatch raised:

`NameError: RehydrateRequest is not defined`

Inspection showed `lab_tools_project.py` referenced a family of `context_engine` request types while importing only `FileListRequest`.

Affected request types:

- `FileReadRequest`
- `FileSearchRequest`
- `RehydrateRequest`
- `ModelListRequest`
- `ArchiveListRequest`
- `ArchiveExtractRequest`

### Repair

Import the complete request-type family actually used by the project tool module.

### Law

`ADVERTISED_CAPABILITY != BEHAVIOR_QUALIFIED_CAPABILITY`

## Defect 2 — context responses crossed the lab boundary as dataclasses

### Observation

After fixing the missing imports, actual calls to:

- `project.files.read`
- `project.files.search`
- `project.models.list`
- `project.archives.list`

executed the context engine but failed at the lab router with `BAD_TOOL_RESULT`, because the handlers returned typed response objects rather than JSON objects.

`project.context.rehydrate` returned a dict and therefore masked the sibling projection defect.

### Repair

The shared `_context_wrap` boundary now:

1. executes the context operation;
2. calls `to_dict()` when the result exposes that projection;
3. requires the projected result to be a JSON object;
4. fails typed `BAD_CONTEXT_RESULT` if a context operation still returns an unsupported result type.

This fixes the family at one projection seam rather than special-casing individual handlers.

### Law

`INTERNAL_TYPED_RESPONSE != ROUTER_JSON_PROJECTION`

## Defect 3 — native Git currentness could not ground nested project repositories

### Observation

`git.status` for `PCMMAD_RECEIVER_LAB` probed the outer project root, which intentionally contains the Git worktree at:

`V30_WORKING/PCMMAD_receiver`

The native tool returned `GIT_REPO_INVALID`. A supplied generic `path` field was ignored because the Git family had no repository-path concept.

### Repair

The native Git family now accepts optional project-relative `repo_path` grounding.

Mechanism:

1. `project_id` grounds the allowed project root;
2. `repo_path` is resolved through the existing safe project-CWD boundary;
3. Git `rev-parse --show-toplevel` must equal that exact resolved candidate;
4. identity records both project root and repo root/path;
5. default remains `.` for projects whose root is the repository.

The same grounding is used by status, diff, commit, reset, and clean so read and mutation identity semantics cannot diverge.

Real-project readback after repair:

- project: `PCMMAD_RECEIVER_LAB`
- repo path: `V30_WORKING/PCMMAD_receiver`
- repo grounded: true
- branch: `main`
- persisted HEAD before this repair publication: `22a38e7b82994597616c87d6e3cb4aff4b3cb91d`

### Laws

- `PROJECT_ROOT != NECESSARILY_GIT_REPO_ROOT`
- `NESTED_REPO_SUPPORT != ANCESTOR_REPO_AMBIGUITY`
- `REPO_PATH_MUST_REMAIN_PROJECT_SCOPED`

## Defect 4 — rehydration could return fresh bytes with stale semantic currentness

### Observation

Once `project.context.rehydrate` executed, full stored-result inspection revealed two currentness failures despite the index cache itself using canonical path + size + mtime_ns currentness:

1. ICF authority anchors always seeded line 1 / file prefixes. The maintained project surfaces are append-updated, so `CURRENT_STATE.md` foregrounded stale A-042 publication-pending text while current hardening/recovery state existed near the tail.
2. default recursive search indexed internal staging/scratch replicas such as `.pcmmad_*_stage` directories and root-level `.pcmmad_*.md` files. Stale duplicated staging material could outrank canonical authority files.

This proved:

`FRESH_FILE_BYTES != CURRENT_SEMANTIC_WINDOW`

and

`INTERNAL_STAGING_REPLICA != RECOVERY_AUTHORITY`

### Repair

- default context traversal excludes `.pcmmad_*_stage` directories;
- default context traversal excludes root/internal files beginning `.pcmmad_`;
- explicit targeting behavior remains separate from default broad recovery traversal;
- moving ICF anchor classes seed from a bounded tail window;
- the static ICF standard remains head-seeded;
- seeded results expose `seed_window = tail|head` and honest line ranges.

Tail-seeded classes:

- `state.current`
- `continuity.intent`
- `state.next_steps`
- `state.doctrine_snapshot`
- `state.revisit_ledger`
- `state.trace_matrix`
- `continuity.live_shadow`
- `continuity.design_thread_stream`

### Real-project acceptance

The same query that previously foregrounded stale A-042 and staging replicas now satisfies all checks:

- current anchor seed is `tail`: PASS
- current anchor starts after line 1: PASS
- no internal stage/scratch paths selected: PASS
- engineering feature `c22381b...` recovered: PASS
- recovery HEAD `22a38e7...` recovered: PASS
- live freeze `416360645...` recovered: PASS
- final schema LAST/LOCKED recovered: PASS

Observed current seed window after repair:

`CURRENT_STATE.md` lines 627–635

which contains the server-hardening recovery handoff rather than the stale A-042 header.

## T0.2 RECOVERY_ONLY result

A bounded candidate-style recovery receipt was persisted outside Git under:

`quarantine/t0_2_dogfood/RECOVERY_ONLY_RECEIPT.json`

and independently compared against direct Git / Runtime registry / persisted artifact bytes:

`quarantine/t0_2_dogfood/RECOVERY_ONLY_ORACLE_COMPARISON.json`

All oracle checks passed, including:

- native Git head matches direct Git;
- persisted recovery head matches native/direct Git;
- branch matches;
- Runtime tool count matches;
- Runtime family count matches;
- bounded checkpoint hash matches direct file bytes;
- live freeze recovered;
- final schema lock recovered;
- Skill-thread boundary recovered;
- UCM pause recovered;
- RECOVERY_ONLY mutation gate remained closed.

The first recovery receipt intentionally recorded the repair worktree as dirty WIP after the published frontier rather than smoothing it into a clean-state claim.

## Serious-work machine accounting

The repair campaign then entered `RECOVER_AND_CONTINUE_SERIOUS_WORK`.

- **PDVER — ACTIVE:** probe → embody → verify/converge; four defects reproduced before repair; focused and full tests required.
- **Semantic Helix — ACTIVE:** T0.2 recovery split survived; four Runtime scars retained; prior no-open-defect claim demoted by fresh evidence.
- **Attention Reservoir — ACTIVE:** sibling project tools, Git mutation/read grounding, ICF windows, staging directories and staging files were all pressured rather than stopping at the first NameError.
- **OARR — ACTIVE:** rival `only RehydrateRequest is missing` was falsified by sibling projection and currentness discriminators.
- **Loop+ — ACTIVE:** adjacent Git grounding and semantic currentness were attacked after basic execution was repaired.
- **CSC — ACTIVE:** claim ceiling held to Runtime repair + dogfood; no Skill canonical promotion, UCM promotion, live promotion, or final-schema work.

Machine receipt:

`quarantine/t0_2_dogfood/SERIOUS_WORK_REPAIR_RECEIPT.json`

## Test embodiment

New/expanded regressions cover:

- shared context response projection;
- all context request types used by project tool handlers;
- nested exact Git repo path grounding;
- nested path escape rejection;
- native `git.status` nested repo behavior;
- `.pcmmad_*_stage` traversal exclusion;
- root-level `.pcmmad_*` file exclusion;
- append-maintained ICF anchor tail seeding.

## Qualification

Focused project/Git/rehydration cluster before currentness expansion:

**27 passed / 1 conditional skip**

Currentness-focused cluster:

**12 / 12 PASS**

Final full Runtime suite on the complete repair bytes:

**441 collected / 440 passed / 0 failed / 1 conditional skip**

Real-project rehydration acceptance after the final currentness repair: **7 / 7 PASS**.

## T0.2 disposition

This campaign materially validates T0.2's recovery design by dogfooding its semantics against the newest Runtime and finding real defects.

It does **not** canonically promote the Skill. Reasons:

- Skill ecosystem authority remains with the parallel Skill thread;
- the exact nested package was verified at ingress, but the attempted manual chat-to-server package transfer was corrupt and explicitly rejected;
- canonical package hygiene still includes the previously observed interpreter-specific `__pycache__/*.pyc` scar;
- post-publication clean-frontier cold recovery is still required before this server thread calls the dogfood cycle complete.

## Claim ceiling

This feature does not:

- promote/restart/redeploy live Runtime;
- trigger final schema work;
- resume UCM redesign/import;
- ingest real user memory;
- promote the T0.2 Skill canonically;
- change the 30-operation compact imported schema merely to expose `repo_path` (native Git tools remain server-native contracts).

## Publication gate

Before calling this repair published:

1. compile changed Python;
2. Git diff hygiene;
3. exact candidate inventory/hash;
4. commit + push;
5. independent remote `main` readback;
6. refresh recovery handoff;
7. rerun `RECOVERY_ONLY` from a clean published frontier.
