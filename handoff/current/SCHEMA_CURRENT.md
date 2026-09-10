# PCMMAD Receiver — Current Assistant Schema Pointer

Status: **V11 SOURCE SUCCESSOR PUBLISHED / PRODUCT-SIDE INSTALLATION SEPARATE / LIVE V10.3 COMPATIBILITY RETAINED**

Current source schema successor:
`baseline/pcmmad_receiver/pcmmad_lab_action_schema_v11_0_capability_microkernel_8.json`

SHA-256: `ee62b261d6e5518b585faccd4af21a42d9b7bd6b3dc63f8af0e1242ef9fb9010`
Operations: **8**
Bytes: **33,844**

Mechanism feature: `7e4c66a769884269d71babdb92217ba80eb66e74`
Tree: `967f108f235b4b42097f4b2d9d48ee61c591017c`
Parent: `92010b57dfc275dd6f9753121cd8def98792ed41`
Canonical feature inventory SHA: `52571ba349a3de0fdca0c3a60d15c7780a7f1373289c31779762a1c673cf1cc7`

Current scheduler-effect profile:
`baseline/pcmmad_receiver/scheduler_effect_profile_v1.json`
SHA-256: `a7ee841edb47010978a13d884e899520c6bd6e22d2907a9ba4bbb169f8e58ce3`
Capabilities covered: **158**
Effect-truth verified: **0**
Parallel-read verified: **0**
Resume-replay verified: **0**

The production v11 profile is intentionally conservative: unwitnessed capabilities are `UNVERIFIED`, serial, recomposition-required, and charged worst-case static admission cost.

The eight Assistant-facing primitives are:
`orientCapabilities / invokeCapability / flowCapabilities / composePlan / executePlan / observeRuntime / resumeContinuation / transferData`.

Key laws:
`SCHEMA_OPERATION_COUNT != SERVER_CAPABILITY_COUNT`
`CAPABILITY_LEASE != CAPABILITY_GRANT`
`DESCRIPTIVE_EFFECT_TRAITS != SCHEDULER_AUTHORITY`
`DECLARED_EFFECT_CLASS != VERIFIED_EFFECT_TRUTH`
`CONTINUATION != CURRENTNESS`
`COMPACT_PLAN != UNBOUNDED_RESOLVED_ARGUMENTS`
`PLAN_VM != SECOND_JOB_SCHEDULER`

v10.3 compatibility remains present at:
`baseline/pcmmad_receiver/pcmmad_lab_action_schema_v10_3_pcmmad_native_protocol_compact_30_router.json`
SHA-256 `132dff5967d7b45278d63da11e4ab87a72bd3fbd0507af3b652ffd34ee88787f` / **30 operations**.

The currently loaded/product-installed surface has **not** been implicitly switched by source publication. Product-side ChatGPT Action configuration and live Runtime reload/promotion remain separate consequences.

`SOURCE_SCHEMA_PUBLISHED != PRODUCT_SCHEMA_INSTALLED`
`SOURCE_QUALIFIED != LIVE_PROMOTED`

## Rollover currentness — 2026-09-10

GitHub mechanism frontier `e1b2b8eddd92e8ad9159a548f9e6d6b2beb895f4` does **not** change the canonical v11 JSON/generator/schema runtime files from schema mechanism `7e4c66a`. Canonical SHA remains `ee62b261d6e5518b585faccd4af21a42d9b7bd6b3dc63f8af0e1242ef9fb9010`. Clean-box, transfer, telemetry and project-aware access-log repairs are schema-neutral.

A separate unpublished real-wire hardening donor would require documenting HTTP 413/415 and a 1 MiB `/lab/vnext/*` request ceiling if it is re-earned and promoted on current source. That donor is **not** current schema authority.
