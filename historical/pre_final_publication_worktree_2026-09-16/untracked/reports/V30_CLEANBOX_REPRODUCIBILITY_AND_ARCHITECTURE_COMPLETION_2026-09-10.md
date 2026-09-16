# V30 Clean-Box Reproducibility and Architecture-Completion Gate — 2026-09-10

Status: **DETACHED CLEAN-BOX CANDIDATE QUALIFIED / CANONICAL PORT PENDING**

Audited remote/source base: `92010b57dfc275dd6f9753121cd8def98792ed41`.

Purpose: close the gap between "green on the operator's machine" and "the repository can reproduce its own qualification from declared dependencies and no inherited PCMMAD state." This campaign does not alter the Runtime architecture, ICF-CS v1.2 doctrine, compact 30-operation schema, UCM/RES authority model, or the separate schema/Plan-VM branch.

## 1. False-green reproduction

A fresh GitHub clone and fresh virtual environment exposed two independent qualification contaminants.

### Undeclared test dependency

`tests/test_warforts_property_fuzz.py` imports Hypothesis, but `requirements-dev.txt` did not declare it.

A genuinely fresh environment installed only from the repository requirements failed at collection with:

`ModuleNotFoundError: No module named 'hypothesis'`.

The prior local green therefore depended on an undeclared developer-machine package.

### Operator mount leakage into tests

`tests/conftest.py` stated that tests must not inherit the operator's real PCMMAD stores, but it replaced only project/system/sandbox/temp roots. It did **not** replace `PCMMAD_ROOT` or `PCMMAD_MOUNTS_JSON`.

The operator environment contained broad drive mounts. When all `PCMMAD_*`, `PYTHONPATH`, `PYTHONHOME`, and `VIRTUAL_ENV` variables were removed, the unchanged source produced **22 failures**. Twenty-one were context/ICF tests creating arbitrary temporary `base_root`s that had silently relied on inherited operator mount authorization.

Production containment was correct to reject those roots. The tests were not hermetic.

`LOCAL_ENVIRONMENT_GREEN != RELEASE_REPRODUCIBLE_GREEN`.

`TEST_ISOLATION_CLAIM != TEST_ISOLATION_HELD`.

## 2. Windows virtualenv Job Object harness defect

The remaining sanitized-environment failure was `test_active_process_limit_blocks_descendant_creation`.

The test launched `sys.executable` from a Windows venv under `active_process_limit=1`. The venv redirector can itself become the assigned process and then fail to create the real base interpreter under the process-count limit, meaning the test payload never executes and no `blocked:*` witness is written.

This was a harness race, not evidence that the Job Object process limit failed.

Repair: use `sys._base_executable` when available for that kernel-limit test so the assigned process is the actual interpreter being tested, not the venv launcher redirector.

## 3. Permanent clean-box repair

Candidate changes:

1. `requirements-dev.txt`
   - declares `hypothesis>=6,<7`;
   - declares `pytest-xdist>=3,<4` because repeated four-worker qualification is part of the engineering acceptance contract.

2. `tests/conftest.py`
   - explicitly replaces `PCMMAD_ROOT`;
   - explicitly replaces `PCMMAD_PROJECTS_ROOT`, `PCMMAD_SYSTEM_ROOT`, `PCMMAD_SANDBOX_ROOT`, and `PCMMAD_TEMP_ROOT`;
   - explicitly replaces `PCMMAD_MOUNTS_JSON` with test-only namespaces covering the isolated pytest runtime root, OS temp root used by `TemporaryDirectory`, and repository root;
   - never relies on operator mount configuration to authorize test fixtures.

3. `tests/test_execution_resource_envelope.py`
   - uses the base interpreter for the active-process-limit child test;
   - preserves the existing Windows Job Object mechanism and assertion.

4. `tests/test_cleanbox_environment_isolation.py`
   - proves the operator mount environment is replaced;
   - proves OS-temp context fixtures are explicitly allowed by the test namespace;
   - proves product roots are test-local rather than the operator's live Desktop state.

5. `.github/workflows/ci.yml`
   - runs on every `main` push and pull request;
   - matrix: `windows-latest` and `ubuntu-latest`;
   - installs only declared runtime + dev requirements;
   - runs `pip check`;
   - explicitly removes `PCMMAD_*`, `PYTHONPATH`, `PYTHONHOME`, and `VIRTUAL_ENV` before tests;
   - runs the full suite;
   - on Windows additionally runs full four-worker `loadscope` and `worksteal` burns.

The Linux job is a portability/non-Windows guard tripwire. Windows remains deployment authority because production resource-envelope semantics use Windows Job Objects.

## 4. Fresh-environment qualification

A second brand-new venv was created **after** the dependency declarations were patched. No manual package additions were made.

Declared dependency install: PASS.

`pip check`: PASS — no broken requirements.

All operator PCMMAD/Python environment variables were stripped before test launch.

Pytest collection:
- ordinary collected test functions: **778** across **101** test files;
- JUnit including unittest/property subcases: **881 cases**.

Sanitized serial full suite:
- JUnit cases: **881**;
- failures: **0**;
- errors: **0**;
- skipped: **2**.

Sanitized four-worker `loadscope`:
- JUnit cases: **881**;
- failures: **0**;
- errors: **0**;
- skipped: **2**.

Sanitized four-worker `worksteal`:
- JUnit cases: **881**;
- failures: **0**;
- errors: **0**;
- skipped: **2**.

Final sanitized Runtime candidate after executable/F821 repairs:
- serial JUnit: **889 cases / 0 failures / 0 errors / 2 skips**;
- four-worker loadscope: **889 / 0 / 0 / 2**;
- four-worker worksteal: **889 / 0 / 0 / 2**.

Changed test files pass Ruff.

## 5. Installed-package qualification

A PEP 517 wheel was built from the clean clone and installed into a separate install-only venv.

Wheel build: PASS.
Wheel install with declared runtime dependencies: PASS.
Installed `pip check`: PASS.

Import smoke from site-packages:
- `pcmmad_receiver` resolves from the install-only venv site-packages;
- native tool count: **158**;
- `continuity.ingress.rehydrate`: present;
- execution source default: **12** concurrent jobs;
- Windows Job Object resource-envelope backend: present.

This prevents source-tree `sys.path` behavior from masquerading as package correctness.

Final rebuilt wheel after all Runtime fixes:
- `pcmmad_receiver-29.0.0rc1-py3-none-any.whl`;
- bytes: **361,974**;
- SHA-256: `01d5c6ecf8d85f03a220d58b072b998e3043850c61dfcb53c8742e531d181ede`;
- installed-package readback: 158 tools, ICF ingress present, default execution concurrency 12, relative-executable hardening present, `pip check` PASS.

## 6. Execution-wrapper contamination discovered during audit

The project execution wrapper resolves relative executable paths before applying requested `cwd` on Windows. A command written as `.venv\\Scripts\\python.exe` therefore invoked the old live Desktop venv rather than the fresh clone venv.

This caused an earlier supposed clean-box dependency install to install pytest/ruff/dev dependencies into the live Desktop venv by accident.

No live code was copied and no process restart occurred. The live environment contamination is nevertheless real and must be corrected/rebuilt before live promotion.

All trustworthy clean-box qualification in this campaign uses **absolute interpreter paths**.

`REQUESTED_CWD != EXECUTABLE_RESOLUTION_CONTEXT`.

## 6A. Relative executable / requested cwd hardening

A second reproduced environment hazard was promoted into a Runtime invariant rather than left as operator knowledge. On Windows, a path-like relative executable such as `.venv/Scripts/python.exe` can otherwise be resolved against the receiver process environment rather than the caller's requested child `cwd`.

Runtime candidate semantics now are:
- bare executable name -> PATH lookup unchanged;
- absolute executable path -> unchanged;
- path-like relative executable -> resolve against requested child cwd and require an existing file before launch;
- drive-relative Windows executable such as `C:tool.exe` -> reject as ambiguous;
- asynchronous submission persists/fingerprints the same resolved command path.

Focused sync/async/resource/isolation regression: **25/25 PASS**.

`REQUESTED_CWD != EXECUTABLE_RESOLUTION_CONTEXT`.
`RELATIVE_EXECUTABLE_PATH_REQUIRES_EXPLICIT_CWD_BINDING`.

## 7. Architecture-completion interpretation

This campaign supports the existing architecture audit's conclusion:

**Core Runtime architecture is converged at the current claim ceiling.**

The clean-box failure was qualification/reproducibility debt, not evidence that another Runtime truth, authority, scheduler, UCM, RES, or persistence plane is needed.

The separate schema/composition branch remains separate and explicitly gated on:
- effect-trait split before effect-aware automatic scheduling;
- static plan-cost bounds;
- continuation currentness revalidation;
- `CAPABILITY_LEASE != CAPABILITY_GRANT`;
- compact-30 eligibility/derivation;
- legacy `memory.*` exit criterion;
- explicit bounded observe escape hatch;
- delayed/pressure-aware hedged reads;
- goal mode last.

No partial implementation of that branch is introduced here.

`CORE_RUNTIME_ARCHITECTURE_CONVERGED != FINAL_COMPOSITION_SCHEMA_COMPLETE`.

## 7A. Static dormant-crash gate

Whole-tree Ruff contained substantial pre-existing style/static debt, so this campaign did not equate formatting cleanliness with architecture. It did, however, treat `F821` undefined names as a release blocker because they can represent dormant executable crash paths.

Initial production `F821`: **53**.

The findings split into postponed annotation aliases and real dormant executable references, including missing `json`, `zipfile`, `SopError`, `_as_bool`, and `run_subprocess_envelope`. They were repaired surgically without broad reformatting.

Final production+test `F821`: **0**.
Runtime `compileall`: **PASS**.

A bounded second-order Ruff `B/F841` audit found 31 remaining findings, dominated by exception-chaining/style/unused witness variables; inspection did not reproduce another architecture/runtime defect. The repository still has broader pre-existing lint debt and this report does **not** claim full Ruff cleanliness.

`TESTS_GREEN != DORMANT_UNDEFINED_NAME_SAFE`.
`ARCHITECTURE_COMPLETE != ZERO_STYLE_DEBT`.

## 8. Live-promotion consequence

Live promotion remains **blocked until this clean-box repair is canonical-source qualified, published, and GitHub CI has passed on the published bytes**.

The live Desktop venv must also be rebuilt or otherwise restored to a declared runtime-only dependency state before restart, because earlier relative-path execution contaminated it with dev packages.

After those gates, the existing rollback-backed live promotion can resume with source/live parity, ICF-CS v1.2, 158-tool capability, 12-worker execution, scheduler/watcher, HUD/observability, and real async concurrency readback.

## 9. Claim ceiling

Earned at detached-candidate depth:
- hidden operator-environment dependency reproduced;
- undeclared Hypothesis dependency reproduced;
- Windows venv Job Object harness race localized;
- clean-box fixes implemented without weakening production containment;
- fresh declared-dependency venv passes serial and both parallel burns with zero inherited PCMMAD state;
- installed wheel imports and exposes the expected current Runtime surface.

Not yet earned at this report stage:
- canonical-source publication;
- GitHub Actions green on published bytes;
- live-vpn/runtime venv cleanup;
- live Runtime restart/promotion.
