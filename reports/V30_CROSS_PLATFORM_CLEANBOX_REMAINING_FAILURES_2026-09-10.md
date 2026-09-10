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
