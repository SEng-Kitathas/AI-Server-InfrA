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

Last remote-verified Git base before A-034:
- commit `2eeebd9182fdbf8e02241f4edd1b482a6862caa7`;
- tree `9a2b9009fe5f645f83375b5bdd06e09d0d474577`;
- A-033 admission hotpath current; full suite 264 GREEN.

Current A-034 candidate:
- poison repro before: 5/5 tick aborts, drain 0/5, poison RUNNING;
- after: 5/5 clean, drain 5/5, poison FAILED/supervision_lost;
- record-local reconcile telemetry is typed; output excerpts deferred to explicit bounded output read;
- execution 24/24 PASS; full suite 269 GREEN.

Resolve current Git identity dynamically; this snapshot does not prove whether A-034 has been pushed.

## Current handoff-candidate qualification

A-034 engineering qualification before mirror refresh: execution **24 / 24 PASS**; complete suite **269 GREEN**.

The refreshed handoff regression passed **6 / 6**. A final exact-candidate handoff/execution/full-suite gate follows this qualification update, with no repo mutation before commit.

## Active engineering frontier after A-034 publication

1. Publish/remote-read A-034.
2. A-035 derive active/terminal execution-store partition so hot scans depend on active work rather than lifetime history.
3. Preserve direct status/replay/history and legacy-flat compatibility during partition migration.
4. A-036 retention/bounded drain follows separately.
5. Serving/PID/multi-receiver audits remain independent.

## Release/live ceiling

**GIT_PUBLICATION != LIVE_RUNTIME_PROMOTION**

**V30_WORKING_TREE_SUCCESS != RELEASE_QUALIFICATION != LIVE_DEPLOYMENT**

The live Desktop receiver/HUD/services remain a separate promotion gate.
