# PCMMAD Receiver Lab — ICF-CS Current Ingress

Status: CURRENT INGRESS POINTER — NAVIGATION, NOT STATE PROOF
Standard: Intent–Constraint–Frontier Continuity Standard — ICF-CS v1.0
Authority: qualified additive doctrine above sealed R4.4
Updated: 2026-09-05

`CURRENT_INGRESS_POINTER != CURRENT_STATE_PROOF`

## Qualified continuity authority

Exact qualified standard:
`state/doctrine_snapshot/INTENT_CONSTRAINT_FRONTIER_CONTINUITY_STANDARD.md`
SHA-256 `b22b6ba65992bf8e235df9acfb044da772282ae3820a1359af3b5309d1e1051b`

Machine contract:
`state/doctrine_snapshot/ICF_CS_V1_0_MACHINE.json`
SHA-256 `527e4fa0926449155a8aa548656b3debc5292262f8cfaab0ca3f0470e7771f5a`

Claim ceiling:
`state/doctrine_snapshot/ICF_CS_CLAIM_CEILING.md`
SHA-256 `079a523d017438cfd9057d5bfe78b4bf47e4550c20fc9bbd3840cbf6d66f245a`

Current canonical SOP pointer:
`state/doctrine_snapshot/CURRENT_CANONICAL_SOP_POINTER.md`

External qualification receipt:
`checkpoints/ICF_CS_ADDENDUM_QUALIFICATION_RECEIPT.md`

Qualified overlay outer ZIP SHA-256:
`51ed7f424dff7c67534f7e53e8a7c10ebd93bf33ea575eea49dc3f05c24a92a9`

## ICF-CS authority separation

**DIRECTION != CONSTRAINTS != FRONTIER != HISTORY**

For this project:

### Frontier
- `state/current/CURRENT_STATE.md`
- `state/next_steps/NEXT_STEPS.md`

Frontier carries verified current state, provisional/blocking/deferred state, and immediate next actions. It is high-churn and requires fresh evidence.

### Intent
- `checkpoints/COMMANDERS_INTENT_CURRENT.md`

Intent carries governing engineering direction and success boundaries. Authorized project direction is not automatically factual truth.

### Constraints
- `state/doctrine_snapshot/DOCTRINE_SNAPSHOT.md`
- `state/revisit_ledger/REVISIT_LEDGER.md`
- `state/trace_matrix/TRACE_MATRIX.md`
- current canonical SOP surfaces above.

Constraints carry load-bearing decisions, authority ceilings, sequencing laws, scars, claim ceilings, and evidence lineage.

### History / recovery lineage
- `continuity/live_shadow/LIVE_SHADOW.md`
- `continuity/design_thread_stream/DESIGN_THREAD_STREAM.md`
- historical checkpoints/reports/donors when explicitly relevant.

History is recoverable and necessary, but it is not automatic current authority.

## Binding cold-start grammar

Use the qualified version-agnostic sequence:

`CURRENT STATE -> ICF-CS -> CURRENT CANONICAL SOP + NEXT/DOCTRINE/REVISIT/TRACE -> LIVE SHADOW -> DTS -> LIVE READBACK BEFORE MUTATION`

Operationally for this project:
1. read Current State;
2. read this ICF ingress plus the exact qualified ICF standard;
3. read `CURRENT_CANONICAL_SOP_POINTER.md`, Commander’s Intent, Next Steps, Doctrine, Revisit, and Trace;
4. read Live Shadow;
5. read the Design Thread Stream tail;
6. perform fresh consequence-bearing local/runtime readback before mutation.

Missing surfaces must be reported as missing. Do not reconstruct them from memory, donor material, or convenient historical prose.

## Conflict grammar

If material surfaces disagree:

`CONFLICT -> RECOVERY/AUDIT -> LOCALIZE -> REPAIR/SUPERSEDE -> READBACK -> RESUME`

Do not select a winner by polish, filename, timestamp, recency, or convenience.

## Binding non-equivalences

- `HISTORICAL_HANDOFF != CURRENT_INGRESS`
- `DONOR != AUTHORITY`
- `RECENT_TIMESTAMP != CURRENT_AUTHORITY`
- `STALE_GREEN != CURRENT_EVIDENCE`
- `CURRENT_INGRESS_POINTER != CURRENT_STATE_PROOF`
- `EXPECTED_LABEL != PROMPT_CONTENT`
- `BENCHMARK_ITEM != DOCTRINE_AUTHORITY`
- `FORMAT_FAILURE != SEMANTIC_FAILURE`
- `SEMANTIC_AGREEMENT != AUTHORITY_FIDELITY`
- `AUTHORIZED_GOVERNING_INTENT != FACTUAL_TRUTH`
- `CONTINUITY_MAP != CURRENT_STATE_EVIDENCE`
- `REMEMBERED_SUMMARY != SOURCE_CONTACT`
- `SUMMARY_FIDELITY != SOURCE_COMPLETENESS`.

## Current V30 rehydration embodiment

The V30 working-tree context engine seeds current authority surfaces before topic evidence and excludes transient internal noise by default.

Current seeded classes:
- state.current
- continuity.icf_standard
- continuity.intent
- state.next_steps
- state.doctrine_snapshot
- state.revisit_ledger
- state.trace_matrix
- continuity.live_shadow
- continuity.design_thread_stream.

Index-cache currentness binds to canonical path + size + high-resolution modification time rather than TTL alone.

This is a project implementation of ICF-CS, not a substitute for the qualified standard itself.

## Current verification ceiling

Current V30 working-tree evidence:
- **100 native tools / 16 families**;
- native effects, availability/currentness core, bound authority, bounded result retrieval, plugin currentness, MCP availability projection, and HUD availability/readiness presentation are earned;
- final HUD+projection currentness cluster **32/32 PASS**;
- complete V30 suite **245 collected tests GREEN**, existing conditional Windows symlink-privilege skip only.

A-030 HUD presentation laws:
- explicit selected-tool native availability probe only; no hidden/catalog-wide scan;
- ephemeral probe row must match current capability `contract_digest`;
- browser bridge optional degradation does not collapse core readiness;
- HUD readiness is presentation, not Runtime availability authority.

Current Git evidence before this handoff snapshot mutation:
- local/remote `main` exact at `f63f31f7f2ae89f9253d21609a1d431df29e0a69`;
- tree `6dbdc6fa9a42531ae0252b634cfd3f8e0d749ba3`;
- working tree clean;
- complete V30 suite 245 collected tests GREEN.

Git-contained ICF-CS recovery mirror publication is COMPLETE:
- commit/local/remote `cc2802f6d0a0ea24fe036aad9bdb6abfde925566`;
- tree `b93f7973a3c29c6f6ddfcbc88df9405e0c61d095`;
- remote `CURRENT_INGRESS.md` readback PASS;
- handoff focused 6/6 PASS; full suite 251 GREEN.

Active Frontier: A-033 admission hotpath is locally earned (execution 19/19; full 264 GREEN) and must be Git-published/remote-read before A-034 poison-record scheduler isolation begins.

The repo handoff mirror is navigation/recovery evidence, not current-state proof or a second durable truth plane.

`CURRENT_INGRESS_POINTER != CURRENT_STATE_PROOF`, `STALE_GREEN != CURRENT_EVIDENCE`, and `GIT_PUBLICATION != LIVE_RUNTIME_PROMOTION` remain binding.
