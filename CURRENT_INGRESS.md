# PCMMAD Receiver V30 — CURRENT INGRESS

Status: CURRENT GIT COLD-START / RECOVERY POINTER
Repository: `https://github.com/SEng-Kitathas/AI-Server-InfrA.git`
Branch: `main`

**CURRENT_INGRESS_POINTER != CURRENT_STATE_PROOF**

This file exists so a fresh thread/model can recover the project without depending on the saturated chat or the outer local PCMMAD project store.

The repository handoff is a **commit-bound recovery mirror**, not a second live Runtime truth plane.

## First law

**INTENT IS A CONSTRAINT, NOT A CEILING.**

Preserve governing direction and load-bearing constraints, but do not assume earlier intent exhausted what lawful mechanisms can be discovered or composed.

## Cold-start read order

Use the qualified version-agnostic ICF-CS grammar:

`CURRENT STATE -> ICF-CS -> CURRENT CANONICAL SOP + NEXT/DOCTRINE/REVISIT/TRACE -> LIVE SHADOW -> DTS -> LIVE READBACK BEFORE MUTATION`

Repository mapping:
1. `handoff/current/CURRENT_STATE.md`
2. `handoff/current/ICF_CS_CURRENT.md`
3. `handoff/current/INTENT_CONSTRAINT_FRONTIER_CONTINUITY_STANDARD.md`
4. `handoff/current/CURRENT_CANONICAL_SOP_POINTER.md`
5. `handoff/current/COMMANDERS_INTENT_CURRENT.md`
6. `handoff/current/NEXT_STEPS.md`
7. `handoff/current/DOCTRINE_SNAPSHOT.md`
8. `handoff/current/REVISIT_LEDGER.md`
9. `handoff/current/TRACE_MATRIX.md`
10. `handoff/current/LIVE_SHADOW.md`
11. tail of `handoff/current/DESIGN_THREAD_STREAM.md`
12. `handoff/current/RUNTIME_OBE_SKILLS_DUALITY.md`
13. `reports/PCMMAD_RUNTIME_ADAPTER_COMPATIBILITY_CONTRACT_V0_1.md`
14. `reports/PCMMAD_RUNTIME_ADAPTER_PROJECTION_MATRIX_V0_1.md`
15. `reports/PCMMAD_RUNTIME_ADAPTER_PROJECTION_MATRIX_V0_1.json`
16. perform fresh Git/local/runtime readback before consequential mutation.

Snapshot membership/source hashes are in:
`handoff/current/SNAPSHOT_MANIFEST_SHA256.json`.

## Required fresh readback

At minimum, a fresh thread with this repo should verify:

```text
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short --branch
git remote -v
git ls-remote origin refs/heads/main
```

If the local PCMMAD project store is available, reconcile these repository recovery files against its registered Current/Next/Doctrine/Revisit/Trace/Live Shadow/DTS/ICF surfaces before mutation.

If live Runtime/services are relevant, read their actual health/capability/process/job state too.

If material surfaces disagree:

`CONFLICT -> RECOVERY/AUDIT -> LOCALIZE -> REPAIR/SUPERSEDE -> READBACK -> RESUME`

## Architecture in one screen

- **PCMMAD** = methodology.
- **Laboratory Runtime** = canonical durable machine truth/state/capability.
- **Adapters** = MCP/OpenAPI/CLI/HUD/future transport projections only.
- **OBE/Skills** = reusable AI/operator operating intelligence and composition judgment.
- **Model** = replaceable co-processor.
- **Project Chat** = replaceable mission interaction surface.

**TRANSPORT IS NOT ARCHITECTURE AUTHORITY.**

**MECHANISM LIVES WHERE STATE LIVES.**

**EMERGENT CAPABILITY IS ALLOWED. EMERGENT AUTHORITY IS NOT.**

The Skill thread must target the shared Runtime adapter/projection contracts rather than inventing parallel job/project/artifact/capability semantics.

## AI attention law

**LONG-RUNNING WORK SHALL NOT REQUIRE LONG-RUNNING MODEL ATTENTION.**

Do not stare at an open-ended wait for 45 minutes. Runtime jobs/queues/research/browser/build/download/archive/model work should provide small decision-grade progress receipts and store bulk output behind handles/ranges.

## Verified base and current candidate

Last remote-verified Git base before A-041:
- commit `486eee4a9c8a053bc5f5f301199010ba1a7f8d42`;
- tree `4299bb0e92b70c45c8f9e51cc8b3f1c014f6a618`;
- A-040 event-driven scheduler wake + slow resync current;
- full suite 306 GREEN.

Current A-041 candidate:
- CT-style Merkle root/inclusion/consistency proofs are derived from verified authoritative protocol JSONL;
- 3 new read-only protocol tools;
- currentness race repaired so receipts do not claim linear currentness;
- targeted 20/20 PASS; full suite 318 GREEN;
- next correctness frontier after publication is A-042 project mutation ownership/exclusivity.

Resolve current Git identity dynamically; this snapshot does not prove whether A-041 has been pushed.

## Current handoff-candidate qualification

A-041 engineering qualification before mirror refresh:
- targeted Merkle + protocol runtime **20 / 20 PASS**;
- complete V30 suite **318 GREEN**.

The refreshed handoff regression passed **6 / 6**. A final exact-candidate handoff/Merkle-protocol/full-suite gate follows this qualification update, with no repo mutation before commit.

## Active engineering frontier after A-041 publication

1. A-042 server-native project mutation ownership/exclusivity across tabs/clients.
2. Hostile two-writer/stale-owner/release/recovery tests.
3. Mutating lab/protocol idempotency expansion.
4. Windows Job Object resource envelope.
5. Remaining raid mechanisms evidence-ranked.
6. Final schema redesign remains locked last.

## Release/live ceiling

**GIT_PUBLICATION != LIVE_RUNTIME_PROMOTION**

**V30_WORKING_TREE_SUCCESS != RELEASE_QUALIFICATION != LIVE_DEPLOYMENT**

The live Desktop receiver/HUD/services remain a separate promotion gate.
