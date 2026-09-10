# External Evaluation Guide

This is the shortest reproducible path for an evaluator outside the PCMMAD development threads.

## 1. Establish exact source identity

```bash
git rev-parse HEAD
git status --short --branch
git remote -v
```

Latest mechanism feature before the documentation refresh:
`7e4c66a769884269d71babdb92217ba80eb66e74`

Do not substitute a report/checkpoint/V29 package/live-process identity for Git source identity.

## 2. Authority and architecture split

```text
PCMMAD                         methodology/process
Runtime                        durable state/capability/enforcement mechanisms
ICF-CS                         continuity/process authority contract
MCP / OpenAPI / CLI / HUD      transport/presentation projections
Skills / operating libraries  composition intelligence
reports / donors               evidence, not automatic authority
handoff/current                Git-contained current/recovery carrier, not Runtime truth
```

Current ICF-CS v1.2 standard SHA: `f966029496fd6e31a76a36a6e967db37ca2147acfa890a880426ae6a7fa79d92`. Its carrier, activation receipt, detached qualification receipt, machine contract and fresh-instance contract are all under `handoff/current/`.

## 2A. Architecture-closure / effect metadata audit

Read `reports/V30_ARCHITECTURE_CLOSURE_EFFECT_TRAIT_TRUTH_AUDIT_2026-09-10.md` before interpreting `effect_traits` as machine guarantees. Current source has 204 distinct trait strings but only four generic Runtime consumers. Arbitrary descriptive traits are **not** scheduling/authorization truth.

The same audit confirms RES/UCM/DTS continuity separation is embodied independently of those trait strings, while compact-30 selection remains curated and legacy `memory.*` has no sunset clock. Those latter two belong to the separate schema/migration branch.

## 3. Source capability surface

Current source introspection: **158 native tools**.

Important current continuity capabilities:

```text
continuity.res.addendum.validate
continuity.res.addenda.project
continuity.res.snapshot.validate
continuity.res.materiality.classify
continuity.res.handoff.readiness
continuity.ingress.rehydrate
```

UCS/UCM v1 adds **31 `ucm.*` operations** in the existing `memory` family; eight legacy `memory.*` compatibility operations remain. Source schema v11.0 now exposes **8 Assistant-facing microkernel operations** over the 158-capability Runtime; v10.3 retains **30 operations** as a compatibility/import surface until product/live promotion.

No RES/UCM/ICF work created a second persistence engine, scheduler, daemon, or authority plane.

## 4. Reproduce source tests

Target Python: 3.12.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

High-value focused gates:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_icf_cs_v12_ingress.py tests/test_icf_cs_rehydration.py tests/test_rehydrate_budget_strict.py tests/test_git_handoff_current.py
.\.venv\Scripts\python.exe -m pytest -q tests/test_ucm_v1_runtime.py tests/test_ucm_v1_runtime_hostile.py tests/test_ucm_private_migration.py tests/test_user_continuity_memory.py
.\.venv\Scripts\python.exe -m pytest -q tests/test_res_runtime.py tests/test_res_runtime_hostile.py
.\.venv\Scripts\python.exe -m pytest -q tests/test_governance_runtime.py tests/test_governance_runtime_hostile.py
```

Then run the entire suite. Current combined source qualification: **890 collected / 888 passed / 0 failed / 2 skips**.

## 5. Read current evidence in order

1. `reports/V30_SCHEMA_V11_CAPABILITY_MICROKERNEL_2026-09-10.md`
2. `reports/V30_SUBSTRATE_DURABILITY_AND_PACKAGE_EMBEDDING_2026-09-10.md`
2. `reports/V30_WARFORT_BATTLE_HARDENING_2026-09-09.md`
3. `reports/V30_ICF_CS_V1_2_FRESH_INSTANCE_INGRESS_2026-09-09.md`
4. `reports/V30_UCM_V1_RUNTIME_INTEGRATION_2026-09-09.md`
5. `reports/V30_RES_COMPOSITION_AND_ENFORCEMENT_2026-09-09.md`
6. `reports/V30_GOVERNANCE_ENFORCEMENT_DONOR_PRESSURE_2026-09-09.md`
7. `reports/V30_RUNTIME_OBSERVABILITY_HUD_2026-09-09.md`
8. `reports/V30_ASYNC_12_WORKER_AND_SUBMITTED_RECOVERY_2026-09-09.md`
9. `reports/V30_SKILL_DYNO_TELEMETRY_AND_GIT_TAXONOMY_2026-09-09.md`
10. `reports/V30_T0_2_REHYDRATION_DOGFOOD_RUNTIME_REPAIRS_2026-09-08.md`
11. `reports/V30_SERVER_HARDENING_AND_OPERATOR_COCKPIT_2026-09-08.md`
12. `reports/V30_WHOLE_RUNTIME_CONVERGENCE_2026-09-08.md`

## 6. Current qualification ceiling

Verified source evidence includes:

- ICF-CS v1.2 doctrine payload: primary verifier PASS, meta-verifier PASS, **34/34 re-signed hostile mutants rejected**, deterministic double-seal/CRC/clean-extraction PASS;
- Rahl activation closed at epoch 43;
- UCM focused Runtime gate: **130/130 PASS**;
- realistic private-scale synthetic UCM preserved 7,172-byte ingress while reducing derived profile storage from ~452 MB to ~3.98 MB;
- ICF-CS v1.2 ingress: **13/13 PASS**;
- handoff/currentness/ingress/budget: **37/37 PASS**;
- v11 focused schema/package/compatibility gate: **127/127 PASS**;
- full Runtime with v11 mechanism: **876 passed / 2 skipped / 0 failed**;
- substrate/package focused gate: **63 passed / 13 subtests**;
- warfort-specific adversarial suite: **65 passed / 1 skipped / 17 property subtests**;
- v11 mechanism four-worker `loadscope` and `worksteal`: **876 passed / 2 skipped / 103 subtests** each.

Important laws:

```text
LIVE_SHADOW != DTS != RES != UCM
RES_CONTENT != GOVERNING_DOCTRINE
UCM != PROJECT_AUTHORITY
UCM != RUNTIME_TRUTH
UCM != DOCTRINE_AUTHORITY
MISSING != NOT_APPLICABLE
VERSION_LABEL != CURRENT_AUTHORITY_BYTES
DESCRIPTIVE_CLASS != BEHAVIORAL_POLICY
APPEND_ONLY_HISTORY != UNBOUNDED_DERIVED_SNAPSHOT_HISTORY
DEFAULT_BUDGET_OMITTED != EXPLICIT_UNBOUNDED
UNBOUNDED_SELECTION_BUDGET != UNBOUNDED_SINGLE_READ_ALLOCATION
SEARCH_HIT != CLAIM_SUPPORT
SOURCE_QUALIFIED != LIVE_PROMOTED
PATH_CONTAINMENT != INODE_OWNERSHIP
CANONICAL_JSON != PYTHON_JSON_PERMISSIVENESS
ZIP_MEMBER_STRING != WINDOWS_EXTRACTION_IDENTITY
ATOMIC_REPLACE != SINGLE_REPLACE_SYSCALL_ON_WINDOWS
PATH + SIZE + MTIME != FILE_CURRENTNESS
TRANSFER_STAGE_PATH != TRANSFER_STAGE_OBJECT_IDENTITY
```

## 7. Source versus live deployment

Current Git source is **not** automatically the loaded Desktop Runtime. Last loaded-process readback still showed the older 8-worker process/router. No live reload is claimed here.

`GIT_PUBLICATION != PROCESS_RELOAD`

A live-deployment evaluator must independently inspect the running process after an explicitly authorized restart/promotion.

## 8. Open boundaries

- the actual private UCM instance is not in Git and has not been imported into the loaded Runtime; source contains a private-safe administrative verifier/importer;
- live Runtime reload/promotion remains separate;
- v11 schema successor is source-published; product-side ChatGPT Action installation and live Runtime promotion remain separate;
- current V30 engineering source has not been relabeled as a packaged V30 release.

## 9. Useful hostile targets

Attack stale ICF bytes, false session applicability, missing RES/UCM, UCM profile guessing, stale UCM head/snapshot, authority smuggling across RES/UCM/project/runtime/doctrine, generic update forging verification, bounded-core/headroom failure, private-import manifest/event tamper, derived snapshot amplification, context `MemoryError` under omitted/unbounded budgets, source/live identity confusion, stale capability contracts, mutation fencing, response-loss ambiguity, governance contact omission/currentness, and search/retrieval evidence laundering.

Report the exact commit, command, expected invariant, observed result, and retained artifact/result identity.
