# AI-Server-InfrA / PCMMAD Laboratory Runtime

AI-Server-InfrA is the engineering repository for the PCMMAD Laboratory Runtime: a local-first, transport-independent runtime for durable project state, bounded execution, research, continuity, governance, verification, and operator control.

> **Current repository status (2026-09-10 rollover):** GitHub `main` mechanism frontier is `e1b2b8eddd92e8ad9159a548f9e6d6b2beb895f4` (`Add project-aware access logging`), tree `8fbded01e519a938ded1f2177378cd6693d788b7`. v11 schema authority remains `7e4c66a769884269d71babdb92217ba80eb66e74` with canonical SHA `ee62b261d6e5518b585faccd4af21a42d9b7bd6b3dc63f8af0e1242ef9fb9010`. Hosted clean-box CI for `e1b2b8e` is **not green yet**; run `34537723493` fails the full-suite step on Windows and Ubuntu. The loaded Desktop Runtime remains older and has not been implicitly promoted.

## Start here

If you are evaluating the project from outside the development thread, use these surfaces in order:

1. **This README** — product boundary, architecture, current status, and evaluation entrypoints.
2. [`docs/EXTERNAL_EVALUATION.md`](docs/EXTERNAL_EVALUATION.md) — reproducible source-evaluation path and claim ceilings.
3. [`docs/architecture/INVARIANTS.md`](docs/architecture/INVARIANTS.md) — architecture invariants.
4. [`docs/pcmmad_doctrine/PCMMAD_CANONICAL_RUNTIME_SPECIFICATION.md`](docs/pcmmad_doctrine/PCMMAD_CANONICAL_RUNTIME_SPECIFICATION.md) — Runtime doctrine.
5. [`reports/README.md`](reports/README.md) — evidence index and interpretation rules.
6. [`CURRENT_INGRESS.md`](CURRENT_INGRESS.md) — internal continuity/recovery ingress.
7. [`checkpoints/THREAD_ROLLOVER_CHECKPOINT_2026-09-10.md`](checkpoints/THREAD_ROLLOVER_CHECKPOINT_2026-09-10.md) — latest thread rollover/currentness checkpoint; fresh Git still outranks it.

## What this repository is

The Runtime owns machine truth that should survive any particular model, chat, UI, or transport:

- project and artifact state;
- append-oriented protocol/evidence history;
- bounded context and result retrieval;
- durable/asynchronous execution and supervision;
- project mutation authority and generation fencing;
- approval authority and capability-contract currentness;
- research and semantic tooling;
- continuity and rehydration;
- browser, filesystem, Git, transfer, SOP, doctrine, and verification capabilities;
- runtime observability and operator HUD telemetry;
- deterministic governance-contact and finite-exhaustion enforcement mechanics;
- Research Epistemic Shadow (RES) continuity policy: canonical truth states, visible addendum transitions, snapshot validation, materiality classification, and research-handoff currentness;
- User Continuity System (UCS/UCM) v1: 31 canonical `ucm.*` operations over the existing user-continuity ledger, with exact CAS/currentness, bounded hydration, identity/referent/decision/control/candidate semantics, private-safe migration, and strict authority firewalls;
- ICF-CS v1.2 fresh-instance orchestration that explicitly composes Current/ICF/SOP/Live/DTS/RES/UCM and requires owning-plane verification before consequence.

PCMMAD is the methodology. The Runtime is the durable state/capability plane. MCP/OpenAPI/CLI/HUD are projections over that plane. AI-side Skills/operating libraries compose Runtime capabilities; they do not become a second state, scheduler, approval, or authority plane.

Core laws:

```text
TRANSPORT IS NOT ARCHITECTURE AUTHORITY
MECHANISM LIVES WHERE STATE LIVES
EMERGENT CAPABILITY IS ALLOWED; EMERGENT AUTHORITY IS NOT
COMPOSITION BEFORE INVENTION
TOOL SUCCESS != TASK SUCCESS
GIT PUBLICATION != LIVE RUNTIME PROMOTION
```

## Current source surface

At the `7e4c66a...` schema-mechanism frontier, source introspection registers **158 native capabilities**. Source schema successor **v11.0** exposes **8 Assistant-facing microkernel operations**; v10.3 remains the **30-operation compatibility/import surface** until separate product/live promotion.

Recent continuity/governance additions include:

- five governance contact/exhaustion tools;
- five RES policy/projection tools in the existing `continuity` family;
- **31 canonical `ucm.*` operations** in the existing `memory` family, while eight legacy `memory.*` compatibility tools remain;
- `continuity.ingress.rehydrate`, the current ICF-CS v1.2 fresh-instance orchestrator.

The active ICF-CS carrier is embedded under `handoff/current/`:

- current standard SHA `f966029496fd6e31a76a36a6e967db37ca2147acfa890a880426ae6a7fa79d92`;
- activation receipt SHA `893409f28ea181c60ca9e3681eb9a1a4d08fa279befac4d679d2cfdb958d7279`;
- detached qualification receipt SHA `59f66d7707508faa4015df86c728302961c0a13e2f4e8655425ce783248cbc7e`.

Core separation laws:

```text
LIVE_SHADOW != DTS != RES != UCM
RES_CONTENT != GOVERNING_DOCTRINE
UCM != PROJECT_AUTHORITY
UCM != RUNTIME_TRUTH
UCM != DOCTRINE_AUTHORITY
MISSING != NOT_APPLICABLE
SOURCE_QUALIFIED != LIVE_PROMOTED
```

The source remains one Runtime: UCM reuses the existing authoritative user-continuity ledger; RES reuses project/protocol/artifact/currentness/result machinery; ICF-CS ingress composes those planes rather than creating another database, scheduler, daemon, authority plane, or transport family.

## Recent engineering convergence

The current V30 source includes, among other work:

- project mutation ownership/exclusivity with generation fencing;
- expected capability-contract digest binding and stale-contract rejection;
- response-loss/idempotency hardening around consequence-bearing operations;
- Windows Job Object resource containment and workload identity work;
- T0.2 rehydration repairs and Git-grounding hardening;
- asynchronous scheduler capacity/recovery hardening;
- Runtime observability and operator HUD telemetry;
- native governance-contact and finite lawful-exhaustion mechanics;
- native RES continuity enforcement composed over existing project/protocol/artifact/currentness/result machinery;
- UCS/UCM v1 integration with 31 canonical operations, mandatory seq+hash CAS, bounded ten-surface ingress, private-safe importer, and bounded derived-snapshot retention;
- active ICF-CS v1.2 RES+UCM successor carrier and server-native fresh-instance ingress orchestration;
- Operating Library / Runtime boundary convergence without introducing a second scheduler or authority plane.

The detailed evidence and derivation records are indexed under [`reports/`](reports/README.md).

## Rollover release gate — 2026-09-10

Current GitHub head `e1b2b8e` is source-published but **hosted-CI red**. Ubuntu's current public failure is `test_hot_scan_cost_is_independent_of_terminal_history_count` (`38 != 50`); Windows still exposes only a suite-level full-suite failure. Prior local green does not override hosted clean-box red.

`LOCAL_GREEN != HOSTED_CLEANBOX_GREEN`

## Qualification status

At the current ICF-CS v1.2 / RES / UCM engineering frontier:

- ICF-CS v1.2 doctrine qualification: primary verifier PASS, meta-verifier PASS, **34/34 re-signed hostile mutants rejected**, deterministic double-seal/CRC/clean-extraction replay PASS;
- UCM canonical + hostile + legacy-memory + migration gate: **130/130 PASS**;
- UCM realistic private-scale synthetic: 716 canonical events, 7,172-byte core / 4,828-byte headroom; derived profile reduced from ~452 MB to ~3.98 MB while the append-only ledger remained authoritative;
- v1.2 fresh-instance ingress suite: **13/13 PASS**;
- handoff/currentness/ingress/budget gate: **37/37 PASS**;
- current combined source after clean-box + v11 current-surface reconciliation: **890 collected / 888 passed / 0 failed / 2 conditional/platform skips**;
- warfort-specific adversarial suite: **65 passed / 1 skipped / 17 property subtests passed**;
- v11 focused schema/package/compatibility gate: **127/127 PASS**;
- four-worker v11 mechanism burns (`loadscope` and `worksteal`): **876 passed / 2 skipped / 103 subtests passed** each;
- source native capability count: **158**;
- v11 schema: **8 operations / 33,844 bytes / SHA `ee62b261d6e5518b585faccd4af21a42d9b7bd6b3dc63f8af0e1242ef9fb9010`**;
- v10.3 compatibility schema retained: **30 operations / SHA `132dff5967d7b45278d63da11e4ab87a72bd3fbd0507af3b652ffd34ee88787f`**.

Fresh-instance ingress now requires exact ICF-CS v1.2 bytes, explicit session applicability, required RES/UCM currentness, bounded project context, and a final owning-plane/live-readback gate before mutation.

These are **source qualification claims**. They do not claim that the loaded Desktop Runtime has been restarted to this source or that the private UCM instance has been imported.

## Substrate durability and package embedding

Current source closes the architecture-review defects found after the warfort campaign:

- session metadata uses atomic publication and cross-process serialization;
- session notes use a durable append-only journal, so note writes are O(1) with respect to prior note history;
- shared JSONL append is serialized, flushed and fsynced;
- Andon reports durable stop recording separately from session-pause projection;
- read observation is separated from reconciliation across mutation authority and execution projections;
- direct execution status/output/list and power wait no longer finalize jobs or advance queues during reads;
- response windows/corrupt-job diagnostics serialize correctly;
- the Runtime is installable/importable as `pcmmad_receiver` while legacy flat imports resolve to the same module/registry identity;
- all 178 internal imports are package-relative with zero bare internal imports;
- frozen A-042 recovery payloads moved byte-for-byte out of `handoff/current/wip` into `handoff/archive/`, leaving only a current locator.

```text
AUTHORITY_RIGOR != SUBSTRATE_RIGOR
STORAGE_SERIALIZATION != MUTATION_AUTHORITY
STOP_EVENT_RECORDED != SESSION_PAUSE_PROJECTED
OBSERVATION != RECONCILIATION
PACKAGE_IMPORT_WORKS != SINGLE_RUNTIME_IDENTITY
HISTORICAL_RECOVERY_EVIDENCE != CURRENT_WIP
```

See `reports/V30_SUBSTRATE_DURABILITY_AND_PACKAGE_EMBEDDING_2026-09-10.md`.

## Warfort hardening

The current source has been pressure-tested for consequence-boundary failures rather than only happy-path behavior. The warfort campaign added deterministic regression coverage for fresh-ingress TOCTOU, UCM crash/replay recovery, semantic ambiguity, Windows path/inode identity, hardlink escapes, canonical-JSON poison, Windows ZIP namespace aliases, atomic-replace contention, cross-process profile containment, and transfer stage/source object identity.

Key laws earned by reproduced failures:

```text
INGRESS_START_CURRENT != INGRESS_END_CURRENT
PATH_CONTAINMENT != INODE_OWNERSHIP
CANONICAL_JSON != PYTHON_JSON_PERMISSIVENESS
ZIP_MEMBER_STRING != WINDOWS_EXTRACTION_IDENTITY
ATOMIC_REPLACE != SINGLE_REPLACE_SYSCALL_ON_WINDOWS
PATH + SIZE + MTIME != FILE_CURRENTNESS
TRANSFER_STAGE_PATH != TRANSFER_STAGE_OBJECT_IDENTITY
```

See `reports/V30_WARFORT_BATTLE_HARDENING_2026-09-09.md`.

## Architecture closure and schema successor

A 2026-09-10 source-grounded audit against current Git confirms the **core Runtime architecture is converged at the current claim ceiling**. This means the durable state/authority/execution/continuity substrate has native homes and no currently reproduced defect requires another truth plane, scheduler, or authority system. The separately gated schema branch has now been explicitly triggered, built, qualified and source-published as v11.0.

Current effect metadata is intentionally **not** a generic scheduling algebra: the 158-tool registry contains 204 distinct `effect_traits` strings (133 single-use), but only four currently alter Runtime behavior: `project_mutation_fenced`, `idempotent_replay_while_unacked`, `exact_offset_required`, and `requires_chunk_hash`. Other traits may describe properties independently enforced by mechanisms/tests, but the trait declaration itself is not proof.

```text
CORE_RUNTIME_ARCHITECTURE_CONVERGED != FINAL_COMPOSITION_SCHEMA_COMPLETE
TRAIT_DECLARED != PROPERTY_HELD_BY_TYPE_SYSTEM
DESCRIPTIVE_EFFECT != SCHEDULING_AUTHORITY
COMPACT_COUNT_CORRECT != COMPACT_MEMBERSHIP_DERIVED
```

v11 closes the schema-side gates conservatively: server-side dataflow lands first; leases are explicitly non-authoritative; compose is deterministic and statically cost-admitted; continuations do not manufacture currentness; and automatic parallel/replay behavior requires separate exact-digest effect-truth + optimization witnesses. Production v11.0 intentionally has zero effect-truth, parallel-read and resume-replay witnesses. Goal-to-plan synthesis remains deferred. The eight legacy `memory.*` compatibility operations still share the same UCM store and retain their separate sunset question.

See [`reports/V30_ARCHITECTURE_CLOSURE_EFFECT_TRAIT_TRUTH_AUDIT_2026-09-10.md`](reports/V30_ARCHITECTURE_CLOSURE_EFFECT_TRAIT_TRUTH_AUDIT_2026-09-10.md).

## Reproduce the source evaluation

Python 3.12 is the primary target.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

For the canonical Windows command surface used by the packaged receiver:

```powershell
.\PCMMAD.ps1 -Action Setup
.\PCMMAD.ps1 -Action Verify
.\PCMMAD.ps1 -Action Start -NoNgrok
.\PCMMAD.ps1 -Action Status
```

Do not put credentials in this repository. Runtime secrets are supplied through the environment.

See [`docs/EXTERNAL_EVALUATION.md`](docs/EXTERNAL_EVALUATION.md) for focused tests, source-vs-live interpretation, evidence navigation, and known boundaries.

## Repository map

| Path | Purpose |
|---|---|
| `baseline/pcmmad_receiver/` | Canonical Runtime source body |
| `tests/` | Runtime regression, hostile, authority, boundedness, and integration contracts |
| `operator_hud/` | Operator HUD projection |
| `tools/csc_native/` | CSC/release/security/resilience verification gates |
| `system/constraint_pipeline/` | Claim/finalizer constraint pipeline |
| `docs/` | Architecture, doctrine, protocol, evaluation, and operating guidance |
| `reports/` | Engineering evidence, derivations, audits, and lineage |
| `handoff/current/` | Git-contained continuity/recovery mirror; not Runtime authority |
| `design_donors/` | Design donor material; donor provenance does not grant authority |

## Release identity versus engineering identity

`VERSION`, `RELEASE.json`, and the V29 package manifest identify the last packaged V29 release candidate lineage. They are intentionally **not** being rewritten to pretend that the current V30 engineering source has already been packaged or live-promoted.

Therefore:

```text
CURRENT GIT MAIN = V30 ENGINEERING SOURCE
V29 RELEASE METADATA = LAST PACKAGED RELEASE IDENTITY
CURRENT LIVE DESKTOP PROCESS != CURRENT GIT MAIN
```

An evaluator should test the checked-out source directly and should not infer current source capability counts from the older V29 release metadata.

## Safety and authority boundary

The project deliberately separates read capability, execution capability, mutation authority, approval authority, transport projection, and doctrine/promotion authority. A successful tool call is not evidence of broader authority. Research output and donor material are non-authoritative until separately admitted through the appropriate verification/promotion path.

For architecture and promotion constraints, continue with [`docs/architecture/INVARIANTS.md`](docs/architecture/INVARIANTS.md) and [`docs/verification/RELEASE_CONTRACT.md`](docs/verification/RELEASE_CONTRACT.md).
