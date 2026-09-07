# PCMMAD Receiver V30 — NEW SERVER THREAD HANDOFF — CURRENT

Prepared: 2026-09-07 13:53 ET
Status: **EMERGENCY ROLLOVER / CURRENT RECOVERY DISPATCHER**
Project: `PCMMAD_RECEIVER_LAB`
Repository: `https://github.com/SEng-Kitathas/AI-Server-InfrA.git`
Branch: `main`
Authority ceiling: recovery/control surface only. Fresh persisted/Git/worktree/live readback outranks this document before mutation.

## 0. Incident and supersession
The visual chat rolled back behind persisted project/worktree reality. A continuation later failed with `this thread is full`. Fresh inspection proved the previous rollover handoff stale: it described A-042 as one 455-line untracked module, then an intermediate recovery pass captured 11 files; the final current worktree freeze is **13 files**.

This handoff supersedes that recovery description. Do not recover from chat memory.

Binding laws:
`CHAT_VISIBLE_FRONTIER != PERSISTED_PROJECT_FRONTIER`
`WIP_WORKTREE_BYTES != LAST_CHECKPOINT_SUMMARY`
`RECENT_INFERENCE != CURRENT_AUTHORITY`
`CURRENT_INGRESS_POINTER != CURRENT_STATE_PROOF`
`CHECKPOINT_PUBLICATION != A042_ENGINEERING_PUBLICATION`

## 1. Mandatory first actions
Start **RECOVERY/AUDIT**, role **R1 Conservative Auditor**.
1. project info + manifest;
2. Current -> ICF -> canonical SOP pointer -> Commander -> Next/Doctrine/Revisit/Trace -> Live -> DTS tail -> this handoff;
3. fresh Git root/branch/HEAD/tree/status/remote readback;
4. compare dirty worktree against the **13-file v2** `handoff/current/wip/A042_WIP_INVENTORY.json`;
5. verify current A-042 hashes;
6. re-run `tests/test_project_mutation_authority.py`;
7. only after reproducing the current discriminator may BUILD resume.

## 2. Published lineage — do not replay
Last engineering publication: A-041 `a97a00f67f3b79dbbe18e092d29b8971e588d4a2`.
Verified recovery HEAD before this emergency seal: `77da92c7e8693287c2b541aa89275c062f0af558` / tree `3764bf8fe5caf39e82c36316719a2042f764bff6`. Resolve current HEAD dynamically because this recovery checkpoint may advance it.

A-037 incremental protocol fold, A-038 deterministic lifecycle replay, A-039 PID identity, A-040 event-driven scheduler wake/resync, and A-041 Merkle receipts are published survivors.

## 3. A-042 actual WIP
A-042 is **integrated dirty WIP / uncommitted / unqualified**.
- core: 20,926 bytes / SHA `5e294d1ae20601d9a5404f5b4712d82c676ca6acc55c9530a5787dc6239ed04e`;
- projection: 10,247 bytes / SHA `d638688c2f47c09972ef70487ec0742d94b487c71bec254f7d95c05284e3411f`;
- hostile test: 16,818 bytes / SHA `959849fd4b02bd8e577e1a704150c0fe811fa3d6ad4dabedea789b57f2748b4c`.

All 11 current WIP files and hashes are preserved under `handoff/current/wip/`. Recovery copies are not source authority when current worktree exists.

Existing integration includes persistent generation-fenced lease core, native inspect/acquire/renew/release tools, dispatch-level `project_mutation_fenced` scope, fencing traits on Git/project/protocol mutations, authority fields on execution/power/write/legacy requests, and compact schema regeneration.

### Final observed 13-file freeze
The first emergency snapshot captured 11 files. Before sealing, fresh Git status showed `execution_routes.py` and `power_routes.py` had also changed. The exact current recovery baseline is therefore:
- V2 manifest SHA `fad436518624dae080a1fb990a5097c9a0d1a55a7438aa43330f62499a6e9fe2`;
- V2 ZIP SHA `6bd6aba1a615ebcd90cd6691a62b09554e6e2af6252d8fca27453fc19a6f4a4b`;
- `execution_routes.py` SHA `08279eeddae69f5c51177df40043f2399f9d490345caa5f050d400f76c19ed37`;
- `power_routes.py` SHA `8df583f4d679a0652ae71e06d84e270eb923bed12b1d83d9a86e1e4afed513a3`.
Focused A-042 re-run after this expansion remains **7/8 with the same compatibility-authority blocker**.

`PERSISTED_CONTINUITY != CURRENT_WIP_BYTES`.
`FRONTIER_CURRENTNESS_REQUIRES_GIT_WORKTREE_TEST_READBACK`.
If a fresh worktree differs from V2, do not restore V2 over it; localize whether A-042 advanced after the freeze.

## 4. Exact qualification state
- all changed/new A-042 Python files compile: **PASS**;
- compact WIP schema JSON parses: **PASS**;
- strengthened 13-file Git handoff verifier: **11/11 PASS**;
- focused `tests/test_project_mutation_authority.py`: **7/8 PASS, 1 FAIL**;
- complete current dirty-tree suite: **331 collected = 328 PASS / 2 FAIL / 1 skip**.

Known blocker 1:
`test_compatibility_session_guard_fences_other_legacy_session_only_when_lease_active`
- code requires explicit fenced lease/generation/owner authority whenever a governed lease is active;
- one test expects same textual `session_id` legacy compatibility.

Known blocker 2:
`test_compact_schema_authority_parity.py::CompactSchemaAuthorityParityTests::test_dispatch_projects_authority_separately_from_capability_payload`
- WIP compact schema projects `authority` as `#/components/schemas/RuntimeAuthorityEnvelope`;
- parity test expects `#/components/schemas/BoundApprovalAuthority`.

Do not auto-fix either side of either disagreement. Derive the authority/projection boundaries first.

## 5. Laws to preserve
`THREAD_LOCAL_DISCIPLINE != PROJECT_MUTATION_EXCLUSIVITY`
`LEASE_AUTHORITY != OPTIMISTIC_CURRENTNESS`
`WAITING_FOR_NEW_OWNER_TO_FINISH != REGAINING_OLD_AUTHORITY`
`SESSION_IDENTITY != FENCED_MUTATION_AUTHORITY` is the strongest current candidate at the blocker but requires explicit confirmation.

Reads should remain nonblocking. Process crash must not create immortal lock. Expiry/takeover must recover. Long consequence-bearing mutation must not admit a second writer merely because TTL passes while the guard remains held.

## 6. Exact continuation
A. fresh Git/worktree/hash readback; if newer than V2, localize before restore;
B. reproduce both known failures;
C. linear audit core/projection/test/integration;
D. derive lease/session authority law with stale/restarted same-session counterexample;
E. derive adapter authority-envelope law from native Runtime authority + compatibility contract; preserve authority separation;
F. confirm minimum authoritative chokepoints and detect bypasses;
G. hostile simultaneous-process/stale-generation/token/expiry/takeover/corrupt-state/killed-guard/read-nonblocking/long-mutation/legacy-bypass/Git-continuity race tests;
H. adjacent authority/protocol/project/Git/schema regressions;
I. full suite must be green before qualification;
J. update all continuity;
K. A-042 engineering commit/push/remote readback;
L. only then OBE stale-contract/idempotency/Job Object raids.

## 7. Claim ceiling
Do not call A-042 fixed, exclusive, qualified, published, or live. Current dirty tree is explicitly **328 PASS / 2 FAIL / 1 skip**, not green. Do not stage active Runtime WIP into a recovery-only commit.

## 8. Runtime/OBE/Skills architecture
PCMMAD = methodology; Runtime = durable truth/state/capability; adapters = projections; OBE/Skills = operator intelligence; model = replaceable co-processor; Project Chat = replaceable mission surface.
`TRANSPORT IS NOT ARCHITECTURE AUTHORITY`; `MECHANISM LIVES WHERE STATE LIVES`; `EMERGENT CAPABILITY IS ALLOWED; EMERGENT AUTHORITY IS NOT`.
Final schema redesign remains last.

## 9. First-response requirement
New thread first response must state Mode, Role, fresh Git/worktree identities, A-041 engineering baseline vs recovery commits, exact 13-file dirty A-042 state, **both known failing tests**, current 331-test claim ceiling, and immediate no-mutation discriminators.
