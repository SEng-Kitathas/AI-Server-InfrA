# Verification, derivation, and lineage reports

This directory is the repository's engineering evidence sidecar. Reports document what was tested, derived, attacked, qualified, or historically inherited; they do not outrank current source, current Runtime state, or explicit authority/promotion machinery.

For an outside evaluation, begin with [`../docs/EXTERNAL_EVALUATION.md`](../docs/EXTERNAL_EVALUATION.md).

## Current V30 evidence entrypoints

Read newest/current integrations before historical V28/V29 material:

- `V30_GOVERNANCE_ENFORCEMENT_DONOR_PRESSURE_2026-09-09.md` — governance contact + finite lawful-exhaustion donor pressure, native embodiment, hostile defects, qualification, and publication boundary.
- `V30_RUNTIME_OBSERVABILITY_HUD_2026-09-09.md` — Runtime telemetry and HUD projection work.
- `V30_ASYNC_12_WORKER_AND_SUBMITTED_RECOVERY_2026-09-09.md` — async capacity/source changes and submitted-job recovery.
- `V30_SKILL_DYNO_TELEMETRY_AND_GIT_TAXONOMY_2026-09-09.md` — Skill dyno pressure, telemetry, and Git taxonomy hardening.
- `V30_T0_2_REHYDRATION_DOGFOOD_RUNTIME_REPAIRS_2026-09-08.md` — rehydration dogfood and earned Runtime repairs.
- `V30_SERVER_HARDENING_AND_OPERATOR_COCKPIT_2026-09-08.md` — server hardening/operator cockpit campaign.
- `V30_WHOLE_RUNTIME_CONVERGENCE_2026-09-08.md` — whole-Runtime convergence evidence.
- `V30_BUILD_GOVERNANCE_CONTRACT.md` and `V30_COMMANDERS_INTENT_AND_WORKLIST.md` — build-governance/intent context; interpret historical sections against newer evidence.

## Evidence interpretation rules

```text
REPORT != RUNTIME AUTHORITY
SEARCH HIT != CLAIM SUPPORT
EXPECTED FAILURE != ANY FAILURE
FOCUSED GREEN != WHOLE-RUNTIME GREEN
GIT PUBLICATION != LIVE RUNTIME PROMOTION
DONOR MECHANICS QUALIFIED != DOCTRINE PROMOTED
```

Individual reports can contain machine-local paths and timestamps because they are truthful run evidence. Those paths are not deployment configuration.

## Historical release evidence

- `V29_REFACTOR_AUDIT.*` is the V29 human/machine promotion audit.
- `V29_RELEASE_VERIFICATION.json` is the V29 aggregate executable gate result.
- `source_review/` contains corpus inventory, hazard inventory, CSC comparison, and V28-to-V29 body differences.
- `lineage/` retains historical schemas/manifests and prior package evidence for provenance.

`PACKAGE_MANIFEST_V29.json`, `MANIFEST.sha256`, `VERSION`, and `RELEASE.json` describe the last packaged V29 release lineage. They are not a current V30 Git capability manifest.

## Current source-versus-release boundary

The V30 engineering source has continued beyond the V29 packaged release. At the governance publication frontier, source introspection registered 121 native tools and the complete Runtime qualification recorded 513 collected / 512 passed / 0 failed / 1 conditional skip.

Do not rewrite V29 release identity merely to make it look current: a new release identity must be earned through its own release/promotion process. External source evaluation should bind to the exact Git commit being tested.
