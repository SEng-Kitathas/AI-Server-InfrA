# Changelog

## V30 engineering main — 2026-09-09 (unpackaged / not implicitly live-promoted)

- 2026-09-10 schema v11: after the effect-trait/current-surface audit confirmed core Runtime convergence, the explicitly triggered schema campaign produced an 8-operation capability microkernel over 158 native capabilities with server-side dataflow, closed conservative effect truth, static plan cost, continuation currentness, and retained v10.3 compatibility.
Current `main` has advanced substantially beyond the V29 packaged release candidate. Major published engineering work includes:

- project mutation ownership/exclusivity and generation fencing;
- expected capability-contract digest binding with stale-contract rejection before consequence;
- idempotency/response-loss hardening and explicit retry semantics;
- Windows Job Object resource containment, workload identity, execution lifecycle, and recovery work;
- T0.2 project rehydration and Git-grounding repairs;
- async scheduler capacity and submitted-job recovery hardening;
- Runtime observability and operator HUD telemetry;
- Operating Library / Runtime boundary convergence without creating a duplicate state/scheduler/authority plane;
- native governance-contact resolution/admission and finite lawful-exhaustion/evaluation/witness mechanics;
- native Research Epistemic Shadow continuity enforcement composed over existing project/protocol/artifact/currentness/result machinery, without a new RES database, daemon, capability family, or authority plane;
- UCS/UCM v1 integration with 31 canonical operations over the existing user-continuity ledger, mandatory seq+hash CAS, exact authority/currentness components, identity/referent/decision/control/candidate semantics, bounded ingress, and private-safe migration;
- bounded canonical UCM derived-snapshot retention after private-scale pressure exposed ~452 MB amplification from a ~1.49 MB authoritative ledger;
- ICF-CS v1.2 activation carrier and `continuity.ingress.rehydrate` fresh-instance orchestration across Live/DTS/RES/UCM with explicit applicability and owning-plane verification;
- context-engine boundedness repair separating omitted default budget from explicit unbounded selection and capping single-file allocation to actual file size;
- warfort consequence-boundary hardening across ICF/RES/UCM TOCTOU, UCM replay recovery, Windows namespace/inode identity, hardlinks, canonical JSON poison, ZIP extraction aliases, atomic replace contention, profile containment, and transfer file-object/content currentness;
- substrate durability and package embedding: durable/serialized session state, O(1) note journals, Andon consequence/projection separation, observation-vs-reconciliation cleanup, installable single-identity package imports, direct execution wire serialization repairs, and exact-byte A-042 historical archive relocation;
- hostile governance pressure that exposed and repaired incomplete-contact re-signing and over-broad local-file recheck boundaries;
- hostile RES pressure covering canonical truth states, append/supersession currentness, provenance/evidence, 22-section snapshot shape, material-change cadence, handoff staleness, and the RES-to-doctrine authority firewall.

At schema mechanism frontier `7e4c66a769884269d71babdb92217ba80eb66e74`, source introspection remains **158 native capabilities**. Source schema v11.0 exposes **8 Assistant-facing operations** while v10.3 remains a **30-operation compatibility/import surface**. Current combined source qualification is **890 collected / 888 passed / 0 failed / 2 skips**; focused v11 schema/package compatibility is **127/127 PASS**; four-worker loadscope/worksteal each pass at **876 passed / 2 skipped / 103 subtests**. ICF-CS v1.2 remains active continuity/process doctrine; product-side schema installation and live Runtime promotion remain separate.

This section describes the engineering repository, **not a new packaged release identity**. `VERSION` and `RELEASE.json` continue to identify the last packaged V29 release candidate until a separate release/promotion process earns a successor.

See `docs/EXTERNAL_EVALUATION.md` and `reports/README.md` for the current evaluation path and evidence index.

## V29.0.0-rc1 — Native PCMMAD Protocol

- Deep-cross-referenced the surviving receiver, V28 parity anchor, unified standards, complete doctrine archive, and main/alternate CSC dumps.
- Preserved the 49-route and 30-operation contracts and all 75 V28 server-native tools.
- Added 12 server-native PCMMAD protocol tools for 87 total without expanding the Custom GPT action budget.
- Added typed modes, rigor, objective, constraint, continuity, claim, evidence, artifact, promotion, and waiver records.
- Added append-only, fsynced JSONL protocol ledgers with sequence/hash-chain verification and rebuildable snapshots.
- Added compatibility-aware discourse/build/promotion mode enforcement with `off`, `advisory`, and `strict` policy modes.
- Added evidence status, verifier identity, observation/expiry timestamps, distinctness, and proportionate verified-evidence thresholds.
- Added sealed artifact identity, scoped expiring waiver discipline, and append-only promotion/demotion lineage.
- Added source authority, corpus inventory, cross-reference, native protocol, migration, and release-contract documentation.
- Promoted the compact Custom GPT schema to v10.3 while retaining exactly 30 unique operations.
- Expanded the regression suite to 40 passing tests while retaining every prior test.
- Added a 49-route/87-tool/12-protocol-tool/30-operation runtime surface contract.
- Moved historical schemas and prior package manifests out of the live runtime into explicit lineage folders.
- Removed inherited test environments, bytecode, cached gate roots, stale run debris, and machine-local secret surfaces from the release body.

## V28.0.0 — PDVER Recovery Refactor

- Preserved 49 routes, 75 tools, and the compact 30-operation GPT surface.
- Replaced raw host/port parsing with typed runtime configuration and explicit invalid-state rejection.
- Reworked application assembly around explicit required/optional blueprint and runtime-start specifications.
- Fixed failure-report interface drift while preserving hard failure for required route families.
- Switched API-key validation to constant-time comparison.
- Hardened ZIP extraction against POSIX traversal, Windows backslash traversal, drive/UNC paths, normalized collisions, links, and special entries; extraction writes validated targets directly.
- Repaired route/security/browser verification fixtures so they test configured roots and dynamic sidecar ports instead of stale machine assumptions.
- Added the canonical `PCMMAD.ps1` command surface and made browser startup use the project virtual environment.
- Promoted schema v10.2 while preserving exactly 30 unique operations.
- Added release identity, lineage, invariants, migration, verification contract, and final manifest surfaces.
