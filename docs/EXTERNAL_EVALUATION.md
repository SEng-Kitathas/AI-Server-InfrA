# External Evaluation Guide

This guide is the shortest path for an evaluator who did not participate in the PCMMAD development threads.

## 1. Establish the exact source identity

Record the checkout before interpreting any report:

```bash
git rev-parse HEAD
git status --short --branch
git remote -v
```

The latest mechanism frontier immediately before this evaluation-documentation refresh is:

`8714dd87d2092e0f4c66f261fcf5cee8b75a0798`

Do not substitute a continuity checkpoint, report timestamp, V29 package version, or deployed-process identity for Git source identity.

## 2. Understand the authority split

The repository follows these boundaries:

```text
PCMMAD                         methodology/process
Runtime                        durable truth, state, capability, authority mechanisms
MCP / OpenAPI / CLI / HUD      transport and presentation projections
Skills / operating libraries  composition and AI/operator intelligence
reports / donor material       evidence, not automatic authority
handoff/current                recovery mirror, not Runtime truth
```

A transport may expose a capability but does not own its semantics. A donor may motivate a mechanism but does not become doctrine merely because code inspired by it passes tests.

## 3. Install for source testing

Target Python: 3.12.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

The project-local packaged-runtime command surface is also available through `PCMMAD.ps1`, but source evaluation does not require live promotion.

## 4. Inspect the native capability catalog

The canonical source body is `baseline/pcmmad_receiver/` and the native registry is assembled by `lab_tools.py` plus its family modules.

At the RES mechanism frontier, source introspection returns **126 registered native tools**. The five governance tools remain, and five RES tools are added to the existing `continuity` family:

```text
governance.contacts.resolve
governance.contacts.admit
governance.exhaustion.enumerate
governance.exhaustion.evaluate_table
governance.exhaustion.compress_witnesses
continuity.res.addendum.validate
continuity.res.addenda.project
continuity.res.snapshot.validate
continuity.res.materiality.classify
continuity.res.handoff.readiness
```

The RES tools are read-only/authority-neutral. Durable RES writes reuse project/protocol/artifact mutation machinery; there is no RES database, scheduler, daemon, or authority plane. The compact imported action schema remains a deliberately smaller transport surface. Do not treat the compact operation count as the Runtime capability count.

## 5. Run the most relevant focused tests

RES continuity mechanics:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_res_runtime.py tests/test_res_runtime_hostile.py
```

Governance mechanics:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_governance_runtime.py tests/test_governance_runtime_hostile.py
```

Authority/currentness/mutation adjacency:

```powershell
.\.venv\Scripts\python.exe -m pytest -q `
  tests/test_expected_contract_binding.py `
  tests/test_project_mutation_authority.py `
  tests/test_project_mutation_chokepoints.py `
  tests/test_bound_approval_dispatch.py `
  tests/test_git_grounding_postconditions.py
```

Execution/bounded-result adjacency:

```powershell
.\.venv\Scripts\python.exe -m pytest -q `
  tests/test_execution_async_unification.py `
  tests/test_execution_worker_restart_recovery.py `
  tests/test_result_bounded_retrieval.py `
  tests/test_batch_result_boundedness.py `
  tests/test_subprocess_bounded_capture.py
```

Observability/HUD:

```powershell
.\.venv\Scripts\python.exe -m pytest -q `
  tests/test_runtime_observability.py `
  tests/test_hud_telemetry_projection.py `
  tests/test_hud_availability_presentation.py
```

Then run the complete suite. Focused green is not a substitute for whole-Runtime regression.

## 6. Read the evidence in the right order

For the latest major integrations:

1. `reports/V30_RES_COMPOSITION_AND_ENFORCEMENT_2026-09-09.md`
2. `reports/V30_GOVERNANCE_ENFORCEMENT_DONOR_PRESSURE_2026-09-09.md`
3. `reports/V30_RUNTIME_OBSERVABILITY_HUD_2026-09-09.md`
4. `reports/V30_ASYNC_12_WORKER_AND_SUBMITTED_RECOVERY_2026-09-09.md`
5. `reports/V30_SKILL_DYNO_TELEMETRY_AND_GIT_TAXONOMY_2026-09-09.md`
6. `reports/V30_T0_2_REHYDRATION_DOGFOOD_RUNTIME_REPAIRS_2026-09-08.md`
7. `reports/V30_SERVER_HARDENING_AND_OPERATOR_COCKPIT_2026-09-08.md`
8. `reports/V30_WHOLE_RUNTIME_CONVERGENCE_2026-09-08.md`

Historical V28/V29 reports remain useful lineage evidence but should not be used as current capability counts.

## 7. Current qualification claim ceiling

At the RES mechanism frontier, recorded source qualification is:

- dedicated RES policy/hostile suite: **43/43 PASS**;
- focused RES/context/protocol/authority/governance composition gate: **176 collected / 175 passed / 0 failed / 1 conditional skip**;
- complete Runtime: **556 collected / 555 passed / 0 failed / 1 conditional skip**;
- exact epoch-42 RES snapshot: **22/22 canonical sections VALID**;
- handoff-currentness smoke: `HANDOFF_READY -> HANDOFF_EPISTEMIC_CONTINUITY_INCOMPLETE -> HANDOFF_READY` only after a provenance-bound RES addendum;
- 96-addendum projection: 62,418 bytes retained server-side via the existing bounded result mechanism.

The RES campaign caught and repaired multiple pre-publication defects/ambiguities: an unwired tool registration, normalized-content/file-byte hash ambiguity, and a stale-handoff path where a fresh but unrelated addendum could otherwise mask the latest material protocol event.

The important added laws are:

```text
IMPLEMENTATION_PRESENT != CAPABILITY_REGISTERED
NORMALIZED_CONTENT_HASH != FILE_BYTE_IDENTITY
FRESH_RES_ARTIFACT != MATERIAL_EVENT_COVERAGE
RES_CONTENT != GOVERNING_DOCTRINE
RES_HANDOFF_READY != PROJECT_MUTATION_AUTHORITY
RUNTIME_RES_EMBODIMENT != ICF_CS_SUCCESSOR_RELEASE
```

Earlier governance qualification and its contact-set/currentness laws remain valid ancestry evidence.

## 8. Source versus live deployment

The repository intentionally does not claim that current `main` is the currently loaded Desktop Runtime.

At the last live readback, the loaded process still reflected the older Runtime (including global execution concurrency 8 and no governance family), while current engineering source contains the later scheduler and governance work.

Therefore:

```text
SOURCE QUALIFIED != LIVE PROMOTED
GIT PUBLICATION != PROCESS RELOAD
```

A live-deployment evaluation must independently inspect the running process after an explicitly authorized promotion/restart. Do not infer it from Git.

## 9. Known open boundaries

These are not hidden as release-complete claims:

- the final compact/schema redesign remains deliberately locked and has not been triggered;
- UCM/memory componentization is a separately paused seam;
- the R4.4 doctrine-to-embodiment audit is complete and project-side RES is restored; the source now contains the pressure-earned RES continuity-policy seam;
- ICF-CS v1.1 remains unchanged, and any additive successor/compatibility release that makes RES universal ingress is a separate doctrine-authority decision;
- source publication does not itself grant donor doctrine authority or live-deploy the newest Runtime.

## 10. What a useful external evaluation should attack

High-value pressure includes:

- stale contract replay and authority smuggling;
- mutation fencing under concurrent/takeover conditions;
- response loss and retry ambiguity;
- boundedness under large outputs and long-running jobs;
- source/live identity confusion;
- semantic contact-set omission or stale provenance;
- constrained finite grammars that are incorrectly treated as independent Boolean bases;
- evaluator failure accidentally collapsing into a valid unchanged result;
- projection/HUD claims that outrun Runtime telemetry truth;
- recovery surfaces that are stale relative to Git or worktree reality;
- RES addendum deletion/re-sign, silent truth-state rewriting, missing provenance, stale RES at research handoff, unrelated addenda masking material events, or RES synthesis attempting to cross the doctrine-authority firewall.

A failure that exposes a real semantic gap is more valuable than superficial conformance. Please report the exact commit, command, expected invariant, observed result, and any retained artifact/result identity.
