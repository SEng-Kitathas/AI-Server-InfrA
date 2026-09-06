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

## Verified pre-handoff baseline

Immediately before creation of this Git handoff mutation:
- Git local/remote `main` were exact at `f63f31f7f2ae89f9253d21609a1d431df29e0a69`;
- tree `6dbdc6fa9a42531ae0252b634cfd3f8e0d749ba3`;
- working tree clean;
- V30 registry 100 tools / 16 families;
- full suite 245 collected tests GREEN with one existing conditional Windows symlink-privilege skip;
- A-028 availability/currentness, A-029 MCP availability projection, A-030 HUD availability/readiness, and A-030 projection-currentness reconciliation were earned/published.

Because this file and `handoff/current/` are a later mutation, the pre-handoff SHA is historical context only. Resolve the **current** repository commit dynamically with Git and verify it against origin.

## Current handoff-candidate qualification

After materializing the repo recovery bundle and its hostile handoff regression:
- `tests/test_git_handoff_current.py`: **6 / 6 PASS**;
- complete V30 suite: **251 collected tests GREEN**;
- one existing conditional Windows symlink-privilege skip;
- basic secret-like scan over the new handoff/ingress/Commander delta: no hits.

See `handoff/current/HANDOFF_QUALIFICATION.md`.

These are pre-commit candidate facts until Git commit/push/remote-readback completes.

## Active engineering frontier after handoff publication

1. Complete remaining OpenAPI/imported-action/runtime-surface adapter-lossiness classification; mark each mismatch ACCEPTABLE / DEFERRED / FIX-NOW.
2. Rank the next genuinely-open Runtime seam by evidence among:
   - process/service identity;
   - async malformed/stale/race/final qualification;
   - semantic executor restoration;
   - node/resource maturation;
   - live V30 promotion.
3. Keep visual Liquid-Aero/HoloFont/three-wing HUD embodiment downstream of operational truth hardening.
4. Keep final schema research/redesign **locked until whole-runtime convergence / explicit final trigger**.
5. Maintain Git commit -> push -> remote-readback and ICF continuity after every earned load-bearing delta.

## Release/live ceiling

**GIT_PUBLICATION != LIVE_RUNTIME_PROMOTION**

**V30_WORKING_TREE_SUCCESS != RELEASE_QUALIFICATION != LIVE_DEPLOYMENT**

The live Desktop receiver/HUD/services remain a separate promotion gate.
