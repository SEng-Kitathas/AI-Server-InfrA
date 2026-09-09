# External Evaluation Guide

This guide is the shortest path for an evaluator who did not participate in the PCMMAD development threads.

## 1. Establish the exact source identity

Record the checkout before interpreting any report:

```bash
git rev-parse HEAD
git status --short --branch
git remote -v
```

The source frontier immediately before this evaluation-documentation refresh is:

`874b0b3745d1528098956bb499c8de82ee3d79b7`

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

At source frontier `874b0b3...`, source introspection returns **121 registered native tools**. The five newest governance tools are:

```text
governance.contacts.resolve
governance.contacts.admit
governance.exhaustion.enumerate
governance.exhaustion.evaluate_table
governance.exhaustion.compress_witnesses
```

The compact imported action schema remains a deliberately smaller transport surface. Do not treat the compact operation count as the Runtime capability count.

## 5. Run the most relevant focused tests

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

1. `reports/V30_GOVERNANCE_ENFORCEMENT_DONOR_PRESSURE_2026-09-09.md`
2. `reports/V30_RUNTIME_OBSERVABILITY_HUD_2026-09-09.md`
3. `reports/V30_ASYNC_12_WORKER_AND_SUBMITTED_RECOVERY_2026-09-09.md`
4. `reports/V30_SKILL_DYNO_TELEMETRY_AND_GIT_TAXONOMY_2026-09-09.md`
5. `reports/V30_T0_2_REHYDRATION_DOGFOOD_RUNTIME_REPAIRS_2026-09-08.md`
6. `reports/V30_SERVER_HARDENING_AND_OPERATOR_COCKPIT_2026-09-08.md`
7. `reports/V30_WHOLE_RUNTIME_CONVERGENCE_2026-09-08.md`

Historical V28/V29 reports remain useful lineage evidence but should not be used as current capability counts.

## 7. Current qualification claim ceiling

At the governance publication frontier, recorded source qualification was:

- governance hostile/positive suite: 57/57 PASS;
- existing composition discriminator: 55/55 PASS;
- combined focused source gate: 112/112 PASS;
- complete Runtime: 513 collected / 512 passed / 0 failed / 1 conditional skip;
- 4,096-case lawful-exhaustion smoke produced a 757,303-byte result retained server-side and successfully range-read in a bounded 2,048-byte slice.

The campaign also found and repaired two pre-publication defects:

1. a self-consistent but incomplete contact set could otherwise be re-signed after deleting a mandatory contact;
2. a local-currentness recheck needed project-root confinement to avoid becoming an arbitrary host-file read.

The important laws are:

```text
CONTACT_SET_DIGEST_VALID != CONTACT_SET_COMPLETE
ADMISSION_REQUIRES_CURRENT_REDERIVATION
LOCAL_RECHECK != ARBITRARY_HOST_FILE_READ
```

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
- current doctrine-thread R4.4 doctrine-to-embodiment coverage work is upstream/in progress and is not silently represented as completed server work;
- RES and other doctrine-state embodiment questions should be evaluated only after that coverage handoff is complete;
- source publication does not itself grant donor doctrine authority.

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
- recovery surfaces that are stale relative to Git or worktree reality.

A failure that exposes a real semantic gap is more valuable than superficial conformance. Please report the exact commit, command, expected invariant, observed result, and any retained artifact/result identity.
