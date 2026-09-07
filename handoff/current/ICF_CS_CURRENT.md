# PCMMAD Receiver Lab — ICF-CS Current Ingress

Status: CURRENT INGRESS POINTER — NAVIGATION, NOT STATE PROOF
Standard: Intent–Constraint–Frontier Continuity Standard — ICF-CS v1.1
Authority: qualified additive doctrine above sealed R4.4
Updated: 2026-09-07

`CURRENT_INGRESS_POINTER != CURRENT_STATE_PROOF`

## Qualified continuity authority

Exact current reusable standard:
`state/doctrine_snapshot/INTENT_CONSTRAINT_FRONTIER_CONTINUITY_STANDARD.md`
SHA-256 `62be845da364ae81f59b6320c9b34b136236bf5be8aa8036018da48efcb754f4`

Receipt-qualified v1.1 identities:
- machine descriptor SHA-256 `d67726aeb402c280770eeaf314068ed7a1330beb21167d9d6d9b7c4674425bb0`;
- qualification contract SHA-256 `7d20ed708adb4f7ee147b56da41deac77146b56fc85bd769be3a6d240b3e2029`;
- payload SHA-256 `f6f4ab2bafdb0ef2a7db1622a00462990baf980284d5b33827807caea1d41f63`;
- detached release receipt SHA-256 `418346ed6373887b5b924e71ca2bf4b83effad20b7269ab40607f5d2750b970c`;
- distribution SHA-256 `2bb57b24967f80fc5dcf028eece142150ce5d6a1356f12e13cda26951ae19fe7`.

ICF-CS v1.0 payload `51ed7f424dff7c67534f7e53e8a7c10ebd93bf33ea575eea49dc3f05c24a92a9`, standard `b22b6ba65992bf8e235df9acfb044da772282ae3820a1359af3b5309d1e1051b`, and machine contract `527e4fa0926449155a8aa548656b3debc5292262f8cfaab0ca3f0470e7771f5a` are historical/demoted evidence only. Historical v1.0 receipt/claim/machine artifacts remain preserved as lineage.

Current canonical SOP pointer:
`state/doctrine_snapshot/CURRENT_CANONICAL_SOP_POINTER.md`

Governance Contact local reconciliation sidecar:
`state/doctrine_snapshot/GOVERNANCE_CONTACT_V1_0_LOCAL_RECONCILIATION.md`

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

Current publication/worktree evidence at emergency rollover:
- current Git local/remote `main` `4c31f4cee2393650c090e49d585ae61b14879944` / tree `2efa45bc35463e45902395d2ddb5af4ace668ae6`; this is recovery-only publication;
- last published engineering feature A-041 `a97a00f67f3b79dbbe18e092d29b8971e588d4a2`;
- later Git commits are recovery-only;
- current A-042 worktree has **13** changed/new files and is not engineering-published; Git recovery mirror now contains all 13 byte-matching copies;
- all changed/new Python compile PASS; compact schema parses;
- A-042 focused test file **7/8 PASS**, with one unresolved active-lease compatibility-session semantics disagreement;
- complete dirty-tree suite **331 collected = 328 PASS / 2 FAIL / 1 skip**; second failure is compact-schema `RuntimeAuthorityEnvelope` vs `BoundApprovalAuthority` parity;
- current dirty-tree full suite NOT RUN / NOT CLAIMED;
- last published rollover checkpoint full suite 321 GREEN.

Active Frontier: A-042 project mutation ownership/exclusivity is exact 13-file dirty WIP, uncommitted/unqualified; Git recovery baseline is `4c31f4cee2393650c090e49d585ae61b14879944` while A-041 `a97a00f67f3b79dbbe18e092d29b8971e588d4a2` remains last engineering feature. Fresh 13/13 V2 hash readback and 331-test run reproduce exactly two contract discriminators. New thread begins RECOVERY/AUDIT and derives both before mutation.

Recovery ordering is binding:
`CURRENT -> ICF/COMMANDER -> EXACT GIT/WORKTREE -> LIVE RUNTIME WHEN RELEVANT -> WIP HASHES -> RECOVERY MIRROR -> CHAT NARRATIVE`.

The repo handoff mirror is navigation/recovery evidence, not current-state proof or a second durable truth plane.

`CHECKPOINT_PUBLICATION != A042_ENGINEERING_PUBLICATION`.
`WIP_SOURCE_PRESENT != QUALIFIED_SURVIVOR`.
`PY_COMPILE_PASS != A042_QUALIFIED`.
`CURRENT_INGRESS_POINTER != CURRENT_STATE_PROOF`.

## Rollover hardening — 2026-09-06

Observed recovery law:
`CHAT_VISIBLE_FRONTIER != PERSISTED_PROJECT_FRONTIER`.

The saturated thread visibly resumed behind persisted project reality more than once. Canonical outer state was current, while the Git recovery mirror was also found stale at an A-041 pre-publication candidate. Full-thread/compaction is a suspected cause of the visible rollback, not proven exclusive cause.

Cold-start consequence ordering:
1. persisted Current/ICF/Commander;
2. exact Git/worktree readback;
3. live Runtime readback when relevant;
4. active WIP byte identity/claim ceiling;
5. Git recovery mirror;
6. visible chat narrative.

Dedicated current server rollover pointer:
`checkpoints/SERVER_THREAD_HANDOFF_CURRENT.md`.
## Emergency rollover hardening — 2026-09-07

The visual conversation rolled back behind persisted worktree state and a subsequent continuation attempt reached `this thread is full`. The previous recovery handoff was itself stale relative the newer A-042 integrated worktree.

New binding scars:
- `WIP_WORKTREE_BYTES != LAST_CHECKPOINT_SUMMARY`;
- `PERSISTED_CONTINUITY != CURRENT_WIP_BYTES`;
- `FRONTIER_CURRENTNESS_REQUIRES_GIT_WORKTREE_TEST_READBACK`;
- `THREAD_FULL_RECOVERY != CHAT_MEMORY_RECOVERY`;
- exact WIP byte inventory SHALL be mirrored at rollover when uncommitted consequence-bearing work exists.

The first emergency handoff preserved 11 files; that requirement is superseded for current Frontier recovery. The current handoff SHALL preserve all **13** A-042 WIP files byte-for-byte in a recovery-only namespace and state both current failing tests. It SHALL NOT stage active Runtime WIP into the recovery commit.
Final freeze supersession: the first emergency snapshot captured 11 A-042 files. Fresh status then showed 13 files because `execution_routes.py` and `power_routes.py` advanced concurrently. Current recovery freeze is V2 manifest `fad436518624dae080a1fb990a5097c9a0d1a55a7438aa43330f62499a6e9fe2` / ZIP `6bd6aba1a615ebcd90cd6691a62b09554e6e2af6252d8fca27453fc19a6f4a4b`; Git mirror now contains all 13 and handoff verifier is 11/11 PASS. Complete dirty tree is 331 collected / 328 PASS / 2 FAIL / 1 skip. This does not promote A-042.


Rollover completion: Git recovery mirror is sealed at `4c31f4cee2393650c090e49d585ae61b14879944`; A-042 active worktree was not staged. Fresh worktree/test readback still outranks the recovery mirror if WIP advances.


## Thread-full rollover currentness addendum — 2026-09-07 15:21 ET
- visible chat rolled back behind persisted project/worktree state; chat recency is not frontier authority;
- registered continuity hashes were also found behind some newer filesystem continuity bytes; timestamp arbitration is forbidden;
- current project/worktree/Git/tests were re-read and one coherent set is being re-registered;
- exact resume: `4c31f4cee2393650c090e49d585ae61b14879944` recovery baseline + 13-file A-042 WIP matching V2 `fad436518624dae080a1fb990a5097c9a0d1a55a7438aa43330f62499a6e9fe2` + 331 = 328 pass/2 fail/1 skip;
- Governance Contact locator present, activation token/ACTIVE receipt absent → NOT ACTIVE.

Cold-start conflict law:
`CURRENT STATE -> ICF-CS -> COMMANDER -> NEXT/DOCTRINE/REVISIT/TRACE -> LIVE -> DTS -> HANDOFF -> FRESH GIT/WORKTREE/TEST READBACK BEFORE MUTATION`.

If any surface materially disagrees:
`CONFLICT -> RECOVERY/AUDIT -> LOCALIZE -> REPAIR/SUPERSEDE -> REGISTER/READBACK -> RESUME`.


## A-042 frontier addendum — 2026-09-07

**Intent:** preserve one durable Runtime authority plane while making cross-client project mutation exclusive without blocking reads or creating a second scheduler/authority store.

**Constraints:** session text is not authority; generation fencing survives restart/takeover; long consequences outlive TTL safely; lease token is not readable from state; adapter authority stays separate from capability payload; Git publication != live promotion; Skills donor != Runtime authority; final schema redesign remains last.

**Frontier:** A-042 is a qualified 23-file engineering candidate, inventory `e2dcb52475bf5869b6f3ebc4561955e27ef52669291bb7e06aa96ca196b2f31e`, full suite `345 collected / 344 passed / 0 failed / 1 conditional skip`. Current Git still points to recovery commit `014dc68c954ab099c43118bd5072349fb93385d3` until the dedicated A-042 engineering publication is created and pushed.

**Next:** publish A-042, independently read remote HEAD, update post-push continuity, then re-derive the companion Skills A-001 stale-contract candidate.
