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

Last remote-verified Git base before the current A-031 publication step:
- commit `cc2802f6d0a0ea24fe036aad9bdb6abfde925566`;
- tree `b93f7973a3c29c6f6ddfcbc88df9405e0c61d095`;
- V30 registry 100 tools / 16 families;
- full suite 251 collected tests GREEN with one conditional Windows symlink-privilege skip.

Current A-031 candidate carried by this recovery snapshot:
- compact capability-family schema now preserves native `effective_approval_required_tools`;
- focused A-031 cluster 32/32 PASS;
- full V30 suite 254 collected tests GREEN;
- compact action surface remains exactly 30 operations;
- schema SHA `2d845dce9312a1a86a1217059a5dc046d435fb4f66540f703a92d4609b37a4ce`.

Resolve the **current** repository commit dynamically with Git and verify it against origin. The snapshot itself does not prove whether this candidate has been pushed.

## Current handoff-candidate qualification

A-031 current candidate evidence:
- engineering compact-schema/effect/authority cluster: **32 / 32 PASS**;
- refreshed Git handoff regression: **6 / 6 PASS**;
- final projection-currentness/A-031/handoff cluster after stale-evaluator repair: **20 / 20 PASS**;
- complete V30 suite: **254 collected tests GREEN**;
- one existing conditional Windows symlink-privilege skip.

The first final full-suite attempt caught stale test expectations pinned to A-030; the evaluator was advanced to A-031 without removing A-030 HUD invariants. See `handoff/current/HANDOFF_QUALIFICATION.md` and the DTS tail.

## Active engineering frontier after A-031 publication

1. Verify/publish A-031 under current per-step Git cadence and remote-read the exact head.
2. Next isolated discriminator: compact `/lab/results/get` request exposes historical `summary_only`, while native Runtime supports `auto|full|metadata|preview|range` plus byte range and preview controls.
3. Continue adapter-lossiness classification one separately qualified/pushed seam at a time.
4. After adapter ledger converges, rank the next genuinely-open Runtime seam.
5. Keep visual HUD work downstream of operational truth hardening.
6. Keep final schema research/redesign locked until whole-runtime convergence / explicit final trigger.

## Release/live ceiling

**GIT_PUBLICATION != LIVE_RUNTIME_PROMOTION**

**V30_WORKING_TREE_SUCCESS != RELEASE_QUALIFICATION != LIVE_DEPLOYMENT**

The live Desktop receiver/HUD/services remain a separate promotion gate.
