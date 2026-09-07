# PCMMAD Receiver V30 — NEW SERVER THREAD HANDOFF — CURRENT

Prepared: 2026-09-07 15:21 ET
Status: **FINAL THREAD-FULL ROLLOVER / CURRENT RECOVERY DISPATCHER**
Project: `PCMMAD_RECEIVER_LAB`
Repository: `https://github.com/SEng-Kitathas/AI-Server-InfrA.git`
Branch: `main`
Authority ceiling: recovery/control surface only. Fresh project/Git/worktree/test readback outranks this handoff before mutation.

## Incident / authority order
Visual chat rolled back behind persisted reality and continuation hit `this thread is full`. Some filesystem continuity files were also newer than registered hashes. Therefore:
`PERSISTED PROJECT + EXACT WORKTREE + GIT/REMOTE + CURRENT TEST READBACK > REGISTERED/RECOVERY MIRROR > CHAT NARRATIVE`.
Conflict -> RECOVERY/AUDIT -> localize -> repair/supersede -> register/readback.

Binding rollover scars:
`CHAT_VISIBLE_FRONTIER != PERSISTED_PROJECT_FRONTIER`
`WIP_WORKTREE_BYTES != LAST_CHECKPOINT_SUMMARY`
`PERSISTED_CONTINUITY != CURRENT_WIP_BYTES`
`CHECKPOINT_PUBLICATION != A042_ENGINEERING_PUBLICATION`

## Cold start
Start RECOVERY/AUDIT, R1. Read project info+manifest -> Current -> ICF+SOP pointer -> Commander -> Next/Doctrine/Revisit/Trace -> Live -> DTS tail -> this handoff -> New Thread Prompt -> fresh Git/worktree/tests. Only then mutate.

## Published lineage
- recovery Git baseline at checkpoint time `4c31f4cee2393650c090e49d585ae61b14879944` / tree `2efa45bc35463e45902395d2ddb5af4ace668ae6`; resolve dynamically;
- A-041 `a97a00f67f3b79dbbe18e092d29b8971e588d4a2` last published engineering feature;
- A-037..A-041 are published survivors; do not replay;
- live Desktop receiver separate/unpromoted.

## A-042 exact WIP
A-042 is **integrated dirty WIP / uncommitted / unqualified** across exactly 13 files. Fresh 13/13 hash readback matches V2 manifest `fad436518624dae080a1fb990a5097c9a0d1a55a7438aa43330f62499a6e9fe2`; V2 ZIP `6bd6aba1a615ebcd90cd6691a62b09554e6e2af6252d8fca27453fc19a6f4a4b`.

- `baseline/pcmmad_receiver/api_wire_execution.py` — 8911 bytes — SHA `ab497e79803aa8efb7117faed0b7d81d7fa618923760f0d0fa0e30ac719e9f17`
- `baseline/pcmmad_receiver/api_wire_power.py` — 10090 bytes — SHA `b6cea2f1cccf74057f7c53485549eb3adf40bfd35df116de793d34a7861892a2`
- `baseline/pcmmad_receiver/execution_routes.py` — 97012 bytes — SHA `08279eeddae69f5c51177df40043f2399f9d490345caa5f050d400f76c19ed37`
- `baseline/pcmmad_receiver/lab_tools.py` — 41251 bytes — SHA `42dffdb3bc124e8bdf0b1911e21d6a8c33535305ef55bd67dac44a44d0c25966`
- `baseline/pcmmad_receiver/lab_tools_ops.py` — 33370 bytes — SHA `56728c417fafd82bd1af766ed82fd3d6d20b7310a1dd9c462164e589f4de78f8`
- `baseline/pcmmad_receiver/lab_tools_project.py` — 32407 bytes — SHA `cc4c877541f5075e6ca4b56ac2d481316d3e8d4b6105331f6f9bf9042f147475`
- `baseline/pcmmad_receiver/lab_tools_protocol.py` — 23416 bytes — SHA `6a27835ee00a7f2477774b610df4af7f7a4e7a8aa8e00c85b57c4dbe9b9189e4`
- `baseline/pcmmad_receiver/legacy_routes.py` — 18526 bytes — SHA `636a21ee6489edf949eba73677682dd719d8b7a9372129449ad35bc29c44a79f`
- `baseline/pcmmad_receiver/pcmmad_lab_action_schema_v10_3_pcmmad_native_protocol_compact_30_router.json` — 121257 bytes — SHA `65f841072cfdae76df3b4ea38c9217c99daf17f4b5751aa30f9dc9404a90cf9b`
- `baseline/pcmmad_receiver/power_routes.py` — 30001 bytes — SHA `8df583f4d679a0652ae71e06d84e270eb923bed12b1d83d9a86e1e4afed513a3`
- `baseline/pcmmad_receiver/lab_tools_mutation_authority.py` — 10247 bytes — SHA `d638688c2f47c09972ef70487ec0742d94b487c71bec254f7d95c05284e3411f`
- `baseline/pcmmad_receiver/project_mutation_authority.py` — 20926 bytes — SHA `5e294d1ae20601d9a5404f5b4712d82c676ca6acc55c9530a5787dc6239ed04e`
- `tests/test_project_mutation_authority.py` — 16818 bytes — SHA `959849fd4b02bd8e577e1a704150c0fe811fa3d6ad4dabedea789b57f2748b4c`

Recovery copies under `handoff/current/wip` preserve bytes only; never overwrite newer worktree WIP without localization.

## Fresh qualification ceiling
- changed/new Python compile PASS;
- compact schema parse PASS;
- authority suite 7/8 PASS;
- combined authority+schema discriminator 9 collected = 7 PASS / 2 FAIL;
- complete dirty-tree suite **331 collected = 328 PASS / 2 FAIL / 1 conditional Windows skip**;
- A-042 engineering publication NOT DONE; live promotion NOT DONE.

Failure 1: `test_compatibility_session_guard_fences_other_legacy_session_only_when_lease_active` — code requires explicit fenced lease/generation/owner under active governed lease; test expects same textual legacy session passage. Derive, do not auto-fix.

Failure 2: `test_dispatch_projects_authority_separately_from_capability_payload` — WIP schema uses `RuntimeAuthorityEnvelope`; parity test expects `BoundApprovalAuthority`. Derive from native authority + compatibility contract, do not green-fix.

## Governance Contact
Locator `authority/rahl-sop/GOVERNANCE_CONTACT_V1_0_ACTIVATION.md` SHA `380059a4e8204c35f82b3a232d45f962bb20038eec3d9eecb44f4411809346bd` exists. Required token SHA `b5a2e35f300c6f72d93fc80b877ef0478a3628442b705e50f6893cbceafb5094` absent; ACTIVE receipt absent. Current result: `GOVERNANCE_CONTACT_NOT_ACTIVE_AT_THIS_TARGET`; global ACTIVE forbidden. Phase-1 locator propagation did not touch A-042.

## Exact continuation
A. fresh Git/worktree/hash readback; B. reproduce both failures; C. linear audit core/projection/test/integration; D. derive lease/session law; E. derive adapter authority-envelope law; F. map chokepoints/bypasses; G. hostile multi-process/client/stale-generation/token/session/expiry/takeover/corruption/killed-guard/long-mutation/read-nonblocking/legacy-bypass/Git-continuity races; H. adjacent regressions; I. full suite GREEN; J. continuity; K. A-042 engineering commit/push/remote readback; L. only then OBE/idempotency/Job Object raids. Final schema redesign remains last.

## First response in new thread
State Mode RECOVERY/AUDIT; Role R1; fresh Git/remote/worktree identities; A-041 engineering baseline vs recovery commits; exact 13-file A-042 hash state; both failures; 331-test ceiling; Governance Contact NOT ACTIVE; immediate no-mutation discriminators. Then begin useful recovery work.
