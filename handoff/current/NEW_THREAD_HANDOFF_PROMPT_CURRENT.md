# PCMMAD Receiver V30 — NEW THREAD HANDOFF PROMPT — CURRENT

```text
Re-enter project PCMMAD_RECEIVER_LAB under PCMMAD RECOVERY/AUDIT.

INCIDENT: the prior visual chat rolled back and a continuation attempt hit `this thread is full`. Do NOT trust visible-chat recency. Persisted project state + exact Git/worktree/test readback outrank chat memory and any recovery copy.

Mandatory cold-start order before mutation:
1. project info + manifest;
2. state/current/CURRENT_STATE.md;
3. checkpoints/ICF_CS_CURRENT.md + state/doctrine_snapshot/CURRENT_CANONICAL_SOP_POINTER.md;
4. checkpoints/COMMANDERS_INTENT_CURRENT.md;
5. Next/Doctrine/Revisit/Trace;
6. Live Shadow;
7. DTS tail;
8. checkpoints/SERVER_THREAD_HANDOFF_CURRENT.md;
9. fresh Git/worktree hashes/status/remote;
10. only then inspect/modify A-042.

Binding rollover laws:
CHAT_VISIBLE_FRONTIER != PERSISTED_PROJECT_FRONTIER
WIP_WORKTREE_BYTES != LAST_CHECKPOINT_SUMMARY
PERSISTED_CONTINUITY != CURRENT_WIP_BYTES
FRONTIER_CURRENTNESS_REQUIRES_GIT_WORKTREE_TEST_READBACK
THREAD_FULL_RECOVERY != CHAT_MEMORY_RECOVERY
CURRENT_INGRESS_POINTER != CURRENT_STATE_PROOF
CHECKPOINT_PUBLICATION != A042_ENGINEERING_PUBLICATION
GIT_PUBLICATION != LIVE_RUNTIME_PROMOTION

Published lineage:
- A-041 `a97a00f67f3b79dbbe18e092d29b8971e588d4a2` is the last published ENGINEERING feature.
- Recovery HEAD before the emergency seal was `77da92c7e8693287c2b541aa89275c062f0af558` / tree `3764bf8fe5caf39e82c36316719a2042f764bff6`.
- Resolve current HEAD dynamically because the recovery-only rollover commit may be newer.
- A-037..A-041 are earned/published. Do not replay them.

Actual frontier:
A-042 project mutation ownership/exclusivity is INTEGRATED DIRTY WIP / UNCOMMITTED / UNQUALIFIED across **13 files**.
Core SHA `5e294d1ae20601d9a5404f5b4712d82c676ca6acc55c9530a5787dc6239ed04e`.
Native projection SHA `d638688c2f47c09972ef70487ec0742d94b487c71bec254f7d95c05284e3411f`.
Hostile test SHA `959849fd4b02bd8e577e1a704150c0fe811fa3d6ad4dabedea789b57f2748b4c`.
V2 outer recovery manifest SHA `fad436518624dae080a1fb990a5097c9a0d1a55a7438aa43330f62499a6e9fe2`.
V2 ZIP SHA `6bd6aba1a615ebcd90cd6691a62b09554e6e2af6252d8fca27453fc19a6f4a4b`.
Git handoff inventory is v2 / 13 files and passed recovery verifier 11/11.
Worktree bytes always outrank recovery copies if newer.

Current qualification ceiling:
- changed/new Python compile PASS;
- compact schema JSON parse PASS;
- handoff verifier 11/11 PASS;
- focused project-mutation authority tests 7/8 PASS;
- complete dirty-tree suite: **331 collected = 328 PASS / 2 FAIL / 1 skip**;
- A-042 engineering publication NOT DONE; live promotion NOT DONE.

Known discriminator #1 — lease/session authority:
`test_compatibility_session_guard_fences_other_legacy_session_only_when_lease_active`
Current code: active governed lease requires explicit lease/generation/owner fenced authority; same textual session_id alone is insufficient.
Test expectation: same textual legacy session may pass.
Do not auto-fix code or test. Derive from Commander intent, stale/restarted same-session threat, generation fencing, compatibility obligation, and cross-client exclusivity.

Known discriminator #2 — adapter authority projection:
`test_compact_schema_authority_parity.py::CompactSchemaAuthorityParityTests::test_dispatch_projects_authority_separately_from_capability_payload`
Current WIP schema: `authority -> RuntimeAuthorityEnvelope`.
Parity test: expects `authority -> BoundApprovalAuthority`.
Do not revert schema or rewrite test by green pressure. Determine whether RuntimeAuthorityEnvelope is the lawful generalized projection or an unintended widening, using native authority semantics + Runtime Adapter Compatibility Contract + no-authority-smuggling law.

Exact continuation:
A. fresh status/head/remote/hash readback; verify 13-file inventory;
B. reproduce both failures;
C. linear audit A-042 core/projection/test/integration;
D. derive both authority contract survivors before mutation;
E. confirm authoritative mutation chokepoints and bypasses;
F. hostile cross-process/cross-client/stale-generation/token/expiry/takeover/corrupt-state/killed-guard/read-nonblocking/long-mutation/legacy-bypass/Git-continuity race tests;
G. adjacent authority/protocol/project/Git/schema regressions;
H. full suite GREEN;
I. update all continuity;
J. commit/push/remote-read A-042 as its own ENGINEERING step;
K. only then OBE stale-contract, idempotency, Job Object resource raids.
Final schema redesign remains last.

Architecture boundary remains:
PCMMAD = methodology; Laboratory Runtime = durable truth/state/capability; adapters = projections; OBE/Skills = reusable operator intelligence; model = replaceable co-processor; Project Chat = replaceable mission surface.
TRANSPORT IS NOT ARCHITECTURE AUTHORITY.
MECHANISM LIVES WHERE STATE LIVES.
EMERGENT CAPABILITY IS ALLOWED; EMERGENT AUTHORITY IS NOT.

First response in the new thread:
Mode: RECOVERY/AUDIT
Role: R1 Conservative Auditor
State verified vs provisional, published baseline vs dirty WIP, fresh Git/worktree identities, 13-file V2 hash status, both known failures, and immediate no-mutation discriminators. Hand off to R5 only after re-grounding.
```
