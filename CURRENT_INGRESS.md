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

Last remote-verified Git base before A-035:
- commit `07b83f12409e50c37942d517c6ac4bd812dbf203`;
- tree `b9327b495f13775266f346ae3253e0c15b9905ae`;
- A-034 poison-record scheduler isolation current;
- full suite 269 GREEN.

Current A-035 candidate:
- execution metadata partitioned into active vs terminal while direct identity/history/replay/restart compatibility remains explicit;
- 58 active jobs produce 58 hot record loads with 0, 500, or 5,000 terminal records;
- focused execution/partition cluster 34/34 PASS;
- isolated complete V30 suite 279 GREEN;
- ambient real partition dirs 0 before -> 0 after isolated qualification;
- execution SHA `11d888186db1f365ca76aada5512f9fcef420c93c2ec0b0976e9dcfd8c8e2a40`.

Critical scar: an earlier qualification pass unintentionally migrated 1,158 real terminal records; all were exactly restored before promotion and the suite now establishes isolated runtime roots pre-import. See Current/Doctrine/Trace/DTS and `reports/V30_A035_ACTIVE_TERMINAL_PARTITION.md`.

Resolve current Git identity dynamically; this snapshot does not prove whether A-035 has been pushed.

## Current handoff-candidate qualification

A-035 engineering qualification before mirror refresh:
- execution/partition **34 / 34 PASS**;
- isolated complete suite **279 GREEN**;
- ambient operator stores unchanged after isolated rerun (**0 -> 0 partition directories**).

The refreshed handoff regression passed **6 / 6**. A final exact-candidate isolated handoff/execution/full-suite gate and ambient side-effect readback follow this qualification update, with no repo mutation before commit.

## Active engineering frontier after A-035 publication

1. Publish/remote-read A-035 under per-step Git cadence.
2. A-036 derive terminal retention and bounded-drain policy; do not infer deletion policy merely because terminal history is now off the hot path.
3. Keep all-history indexing, WSGI serving model, legacy PID reuse, and multi-receiver admission ownership as separate evidence-driven seams.
4. Preserve the A-035 ambient-state qualification incident as a permanent anti-regression scar.

## Release/live ceiling

**GIT_PUBLICATION != LIVE_RUNTIME_PROMOTION**

**V30_WORKING_TREE_SUCCESS != RELEASE_QUALIFICATION != LIVE_DEPLOYMENT**

The live Desktop receiver/HUD/services remain a separate promotion gate.
