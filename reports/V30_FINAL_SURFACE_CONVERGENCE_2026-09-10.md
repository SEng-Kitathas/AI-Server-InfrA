# V30 Final Surface Convergence — 2026-09-10

Status: **LOCAL RELEASE-CANDIDATE QUALIFIED / GITHUB CI + LIVE PROMOTION PENDING**

Base GitHub head: `6d0e595063cc8bca698aa9b0551ad548a059a933`.

## User-visible defects closed in this candidate

### 1. Project access-log designator

The existing project-aware logger collapsed any project id beginning with `PCMMAD` to the visible tag `PCMMAD`. That erased the actual project distinction when every caller used PCMMAD Lab.

The tagger now treats PCMMAD as a laboratory namespace, not the attached project identity. Path-grounded project context still outranks the outer control-plane project id; when a project path is under a PCMMAD namespace, the attached project folder is used as the designator. Explicit `PCMMAD_PROJECT_LOG_ALIASES` remains the final operator override.

Examples:
- `PCMMAD_RECEIVER_LAB` -> `RECEIVER-LAB`;
- `.../projects/PCMMAD/HOSTILE_OS/src` -> `HOSTILE-OS`;
- Rahl/Forge/CFE known project designators remain supported.

Law: `CONTROL_PLANE_NAMESPACE != ATTACHED_PROJECT_IDENTITY`.

### 2. HUD embodiment

Current Git already contains the receiver-local three-wing Operations HUD, but the live Desktop install lacks the receiver-local `operator_hud` tree and therefore resolved to a legacy Rahl HUD fallback.

The legacy cross-project fallback has been removed. The operator plane now accepts only:
1. explicit `PCMMAD_HUD_SERVER` override, or
2. receiver-local `operator_hud/server.py`.

Missing receiver-local HUD now fails closed rather than silently serving another project's UI.

Tracked HUD/restart/hostile-suite launch paths are repo-relative rather than hard-coded to the historical V29 Desktop install.

Law: `MISSING_CURRENT_HUD != PERMISSION_TO_SERVE_LEGACY_PROJECT_UI`.

### 3. Custom GPT Actions OpenAPI importer compatibility

The canonical v11 eight-operation schema is valid OpenAPI 3.0.3 and passes both `openapi-spec-validator` and strict Prance `$ref` resolution, but the Custom GPT editor reported `Could not parse valid OpenAPI spec`.

A separate importer-conservative projection is now generated at:

`baseline/pcmmad_receiver/pcmmad_lab_action_schema_v11_0_actions_compat_8.json`

It keeps the same eight Runtime endpoints and authority/currentness semantics while removing importer-sensitive complexity from the client schema: no `$ref`, no `nullable`, no typeless any-value schemas, and no schema-valued `additionalProperties`. Canonical v11 remains server-side validation authority.

Generator:
`tools/generate_schema_v11_actions_compat.py`

Law: `CANONICAL_RUNTIME_SCHEMA != CLIENT_IMPORTER_COMPATIBILITY_PROFILE`.

### 4. Active release identity

Active package surfaces still declared `V29 Native Protocol Release Candidate` even though current Runtime engineering identity is V30 and GitHub source has materially advanced.

Candidate active identity is now:

`PCMMAD Laboratory Runtime V30 Release Candidate 1`

Version:
`30.0.0-rc1-laboratory-runtime`

V29 remains preserved as immutable lineage/baseline evidence rather than the outward active product identity.

Updated surfaces include `VERSION`, `RELEASE.json`, `pyproject.toml`, and `baseline/pcmmad_receiver/README_CURRENT.txt`.

Law: `RUNTIME_ENGINEERING_IDENTITY != HISTORICAL_PACKAGE_LINEAGE`.

## Qualification

Focused project-label/HUD/runtime-identity/v11-schema/package embedding gate: **PASS**.

Permanent regressions added for:
- attached PCMMAD project-folder designators;
- receiver-local HUD ownership and absence of legacy Rahl fallback;
- V30 active release identity;
- eight-operation Actions-compatible schema shape and deterministic generation.

Both OpenAPI artifacts pass:
- JSON parse;
- `openapi-spec-validator`;
- strict Prance resolution.

Canonical v11:
- paths: 8;
- bytes: 35,689;
- version: 11.0.0.

Actions-compatible v11:
- paths: 8;
- bytes: 23,633;
- version: 11.0.0-actions-compat.

Local sanitized qualification, excluding only `tests/test_execution_worker_restart_recovery.py` because this test is invalid under the outer PCMMAD Windows Job Object that hosts this control-plane execution:
- serial: **1,034 JUnit cases / 0 failures / 0 errors / 2 skips**;
- four-worker loadscope: **1,034 / 0 / 0 / 2**;
- four-worker worksteal: **1,034 / 0 / 0 / 2**.

The three worker-restart survival tests remain mandatory in GitHub Windows CI, which does not nest them inside the live server's execution Job Object.

## Promotion gate

Do not promote live until:
1. exact candidate is published to GitHub;
2. GitHub Windows and Ubuntu clean-box jobs are green;
3. Windows restart-survival tests pass in CI;
4. fresh GitHub clone is deployed into a V30-named live installation with a fresh runtime-only venv;
5. receiver-local HUD source/readback is proven;
6. live `runtime.identity`, capability count, v11 schema, execution capacity, HUD identity, and ngrok health are read back after restart.
