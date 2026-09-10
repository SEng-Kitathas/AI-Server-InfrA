# V30 Cross-Platform Clean-Box Remaining-Failures Repair — 2026-09-10

Status: **DETACHED CANDIDATE QUALIFIED / GITHUB CI PENDING**

Base GitHub main: `f38c564c486b03278ba9f10dbc87aa4b1c9c07d1`.

## Reproduced review findings

The current GitHub Actions clean-box workflow is red on both Windows and Ubuntu at the full-suite step. Local Windows sanitized execution did not reproduce the reported eight failures, so the remaining clusters were treated as platform-sensitive until mechanism inspection resolved them.

### Transfer identity

Current transfer file-object identity used `st_dev`, `st_ino`, and `st_nlink`. This is insufficient as a cross-platform generation witness because POSIX filesystems may rapidly reuse an inode after unlink/recreate. A content-identical replacement can therefore masquerade as the original object.

Repair: transfer identity now also binds `st_ctime_ns`, and `st_birthtime_ns` where available. Source/stage identity comparisons require the change-generation witness in addition to device/inode. This preserves the existing hardlink guard and closes inode-reuse substitution.

`INODE_NUMBER != FILE_OBJECT_GENERATION`.

### Observability failure isolation

`telemetry_snapshot()` previously wrapped process/system/server/http/execution collectors in one catch-all. One platform-specific collector failure collapsed the entire response to a degraded envelope without normal RED/USE sections, producing downstream `KeyError: 'http'` and related failures.

Repair: collectors are independently isolated. A failed section returns a typed degraded fallback plus `section_errors`; unrelated process/system/http/server/execution sections remain present. Gauge-refresh failure is also isolated.

`ONE_COLLECTOR_FAILURE != TOTAL_TELEMETRY_ERASURE`.

### Hot-scan cost test

The active/queued iterators already scan only the active partition. The hot-scan benchmark could nevertheless include one-time execution-store layout/migration preparation because the fixture reset layout readiness and did not explicitly warm the store before measuring scan cost.

Repair: the test now calls `_ensure_execution_store_layout()` before the measured steady-state scan. Production hot iterators are unchanged.

`MIGRATION_COST != STEADY_STATE_HOT_SCAN_COST`.

## Added regression pressure

Observability tests now deliberately fail the process collector and the HTTP collector independently and require all unrelated RED/USE sections to remain structurally present.

## Detached qualification

Targeted observability/telemetry/hot-scan/transfer cluster: **35/35 PASS**.

Full sanitized Windows clean-box candidate:
- serial: **995 JUnit cases / 0 failures / 0 errors / 2 skips**;
- four-worker loadscope: **995 / 0 / 0 / 2**;
- four-worker worksteal: **995 / 0 / 0 / 2**.

GitHub Ubuntu remains the cross-platform oracle for the inode-reuse repair because no WSL/Docker Linux execution environment is available locally.

## Claim ceiling

Earned locally:
- transfer object identity no longer relies on inode number alone;
- telemetry is section-failure isolated;
- hot-scan benchmark measures the intended warmed steady state;
- full Windows clean-box serial/parallel suite remains green.

Not yet earned:
- GitHub Windows CI green on published bytes;
- GitHub Ubuntu CI green on published bytes;
- live Runtime promotion.

## Hosted CI exact-failure diagnosis — run 34533978802

A permanent CI diagnostic layer was added so unauthenticated/public Actions metadata exposes failing testcase names and traceback tails through check annotations, while JUnit is retained as an artifact. Runtime fingerprinting also records Python/pip/platform/checkout identity.

GitHub run `34533978802` at diagnostic commit `529345e26751acba239c946ac57b3bdfdb17aec3` exposed the exact Ubuntu failures under Python **3.12.14**:

1. `test_export_same_size_same_mtime_content_change_is_detected` — mechanism detected the change but error wording lost the `source changed` contract phrase;
2. `test_happy_import_finalizes_atomically_after_full_hash` — POSIX ctime changed after an authorized chunk write, so creation-time identity was incorrectly reused as the current stage witness;
3. `test_destination_change_after_overwrite_ticket_creation_blocks_finalize` — same stale stage-generation witness masked the intended destination-currentness check;
4. `test_observe_validates_lease_plan_and_capability` — schema-v11 temp root teardown raced process-global scheduler activity;
5. `test_goal_is_sealed_metadata_but_does_not_synthesize_or_change_execution_shape` — same scheduler/temp-root ownership race;
6. `test_telemetry_is_authenticated_and_contains_red_use_fields` — one platform collector degraded, making `ok=false` even though section-isolated RED/USE fields remained present;
7. `test_current_seed_replays_byte_identical_result` — deterministic lifecycle simulator did not quiesce the real process-global scheduler and also imported `execution_routes` through an order-dependent top-level path;
8. `test_capabilities_expose_policy_while_telemetry_exposes_live_wait_mode` — test conflated platform watcher support with an explicitly injected alive watcher object.

The Windows hosted job exposed only a suite-level failure before the diagnostic emitter was enhanced. The emitter now reports suite/collection failures plus retained pytest output tails as public annotations.

## CI-proven repair set

- import stage keeps immutable `stage_identity_at_create` for provenance and mutable `stage_identity_current` for authorized-write generation tracking; the current witness advances only after fsynced chunk writes;
- export identity errors preserve both `source changed` and `source identity` semantics;
- schema-v11 fixture explicitly shuts down the process-global execution scheduler before temporary-root ownership and before cleanup;
- lifecycle simulator shuts down the global scheduler before virtualizing state and imports Runtime modules through the `pcmmad_receiver` package namespace;
- watcher tests distinguish `watcher_supported` from an injected live `watcher_active` object;
- telemetry tests require RED/USE structural continuity under section degradation rather than requiring every optional platform collector to be healthy;
- CI diagnostics retain pytest output and emit suite-level annotations.

Local sanitized verification on the repaired bytes:
- exact eight Ubuntu failures: **8/8 PASS**;
- full serial: **995 JUnit cases / 0 failures / 0 errors / 2 skips**;
- four-worker loadscope: **995 / 0 / 0 / 2**;
- four-worker worksteal: **995 / 0 / 0 / 2**.

`DETERMINISTIC_SIMULATION != LIVE_BACKGROUND_SCHEDULER_INTERLEAVING`.
`PLATFORM_SUPPORT != INJECTED_WATCHER_LIVENESS`.
`AUTHORIZED_STAGE_WRITE_ADVANCES_GENERATION_WITNESS`.
