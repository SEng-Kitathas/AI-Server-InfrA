# SERVER THREAD HANDOFF — CURRENT

Mode: BUILD-COMMIT with RECOVERY/AUDIT readback
Role: R5 Reality Pressure Engine + R1 publication auditor
Date: 2026-09-07

## Authority order
Persisted project + exact worktree + Git/remote + current tests > registered recovery mirror > chat narrative. Never restore older recovery bytes over newer WIP.

## Git baseline
Current pre-publication local+remote `main`: `014dc68c954ab099c43118bd5072349fb93385d3`. Last engineering feature A-041 `a97a00f67f3b79dbbe18e092d29b8971e588d4a2`. A-042 has no engineering commit yet.

## A-042 QUALIFIED 23-file engineering candidate
- 23 changed/new files; inventory `e2dcb52475bf5869b6f3ebc4561955e27ef52669291bb7e06aa96ca196b2f31e`.
- 22 changed/new Python compile PASS.
- compact schema parse PASS / 30 ops / `runtime-authority-envelope-v1`.
- CRLF-aware diff check PASS.
- full suite `345 collected / 344 passed / 0 failed / 1 conditional skip`.
- contracts: `SESSION_IDENTITY != FENCED_MUTATION_AUTHORITY`; `RuntimeAuthorityEnvelope` invocation authority; `NO AUTHORITY SMUGGLING THROUGH CAPABILITY ARGUMENTS`.
- core: state/consequence lock split, generation fence, token hash/redaction, durable worker non-secret binding, stale-takeover fence.
- chokepoints: native project/Git/protocol/state/SOP/execution + path filesystem/transfer + transfer cleanup + two-phase apoptosis/recovery.
- Git publication pending; live Runtime remains unpromoted.

## OBE/Skills bridge
`OBE_V30_HANDOFF_BUNDLE_2026-09-06.zip` came from a non-PCMMAD thread. Treat its 11-Skill portfolio as donor evidence. Runtime owns durable currentness/authority; Skills compose. A-001 expected-contract binding candidate is next only after A-042 publication.

## Final schema
Do not begin final schema redesign. It is LAST and requires whole-runtime convergence + explicit `hells yeah, ready`. Current compact-schema authority parity is not the final redesign.

## Immediate next
1. Register/read back this continuity set.
2. Refresh Git-contained `handoff/current` mirror and qualify it.
3. Create A-042 engineering commit.
4. Push `main`; independently `ls-remote` readback.
5. Update outer continuity with exact A-042 commit/tree.
6. Do not live-promote implicitly.

## A-042 ENGINEERING PUBLICATION — 2026-09-07
- A-042 `PROJECT MUTATION OWNERSHIP / EXCLUSIVITY` is **ENGINEERING-PUBLISHED / REMOTE-VERIFIED**.
- Commit: `df5cdd2f687c7da0ea9ac0b1abecb23579ae599c`
- Tree: `8ac51e5177e5a4edde449310c4566bab064eac04`
- Subject: `Add project mutation ownership exclusivity`
- `origin/main` independently resolves exactly to `df5cdd2f687c7da0ea9ac0b1abecb23579ae599c`.
- Post-push worktree: clean / `main...origin/main`.
- Pre-publication qualification remains `345 collected / 344 passed / 0 failed / 1 conditional skip`, with focused A-042 cluster 71/71 PASS and Git handoff verifier 11/11 PASS.
- This publication does **not** live-promote the Desktop Runtime. `GIT_PUBLICATION != LIVE_RUNTIME_PROMOTION`.
- The non-PCMMAD OBE/Skills A-001 stale-contract candidate is now the next Runtime/OBE discriminator and must be re-derived against this published Runtime; donor qualification alone grants no Runtime authority.
- Final schema redesign remains LAST and untriggered; whole-runtime convergence plus explicit user `hells yeah, ready` remains required.

## A-001 RUNTIME CONTRACT CURRENTNESS — QUALIFIED CANDIDATE (2026-09-07)
- Source donor: non-PCMMAD OBE/Skills stale-contract candidate; donor archive remains evidence, not authority.
- Re-derived against published A-042 Runtime commit `df5cdd2f687c7da0ea9ac0b1abecb23579ae599c`.
- Native contract: optional `expected_contract_digest`; exact current `ToolSpec.contract_digest` is compared immediately after native tool resolution.
- Mismatch: `409 CAPABILITY_CONTRACT_STALE` before router/provider work, schema/protocol work, approval issuance/consumption, mutation fencing, or handler effect.
- Malformed assertion: `400 BAD_EXPECTED_CONTRACT_DIGEST`.
- Legacy callers may omit the assertion; OBE/MCP may require it after capability discovery.
- HTTP `/lab/dispatch` and per-step `/lab/batch` propagate the assertion.
- Compact schema exposes the optional 64-hex assertion for both single and batch dispatch; authority model remains `runtime-authority-envelope-v1`; 30 operations remain unchanged.
- Qualification: focused A-001 + approval/MCP/result/schema adjacency `49/49 PASS`; changed Python compile PASS; full suite `352 collected / 351 passed / 0 failed / 1 conditional skip`; CRLF-aware `git diff --check` PASS.
- Status: **QUALIFIED ENGINEERING CANDIDATE / GIT PUBLICATION PENDING**.
- OBE/Skills 11-Skill interface remains **UNFROZEN** pending dogfood against the promoted Runtime interface.
- Final schema redesign remains LAST and untriggered; this compact schema field addition is adapter parity, not final schema redesign.

## A-001 ENGINEERING PUBLICATION — 2026-09-07
- A-001 Runtime contract currentness binding is **ENGINEERING-PUBLISHED / REMOTE-VERIFIED**.
- Commit: `a552af9957b99361c3aebf91c7abc65775e0ce43`
- Tree: `e51be9f7fb2f1e125b19d30e9da0e5324b661e4c`
- Subject: `Bind dispatch to expected capability contract`
- `origin/main` independently resolves exactly to `a552af9957b99361c3aebf91c7abc65775e0ce43`.
- Post-push worktree: clean / `main...origin/main`.
- Final qualification: `352 collected / 351 passed / 0 failed / 1 conditional skip`; focused A-001+continuity 18/18 PASS; broader A-001 adjacency 49/49 PASS; compile/schema/diff checks PASS.
- Runtime truth now includes optional `expected_contract_digest` with `409 CAPABILITY_CONTRACT_STALE` before authority/provider/handler consequence on mismatch.
- Legacy omission remains compatible.
- This publication does not freeze the OBE/Skills 11-Skill interface; real dogfood against this promoted Runtime remains the next integration discriminator.
- Final schema redesign remains LAST and untriggered; whole-runtime convergence plus explicit user `hells yeah, ready` is still required.
- `GIT_PUBLICATION != LIVE_RUNTIME_PROMOTION`.
