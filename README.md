# AI-Server-InfrA / PCMMAD Laboratory Runtime

AI-Server-InfrA is the engineering repository for the PCMMAD Laboratory Runtime: a local-first, transport-independent runtime for durable project state, bounded execution, research, continuity, governance, verification, and operator control.

> **Current repository status (2026-09-09):** `main` is the V30 engineering frontier. The latest mechanism feature before this documentation refresh is `8714dd87d2092e0f4c66f261fcf5cee8b75a0798` (`Add native RES continuity enforcement`). The currently deployed Desktop Runtime is intentionally older and has **not** been implicitly promoted to this source frontier.

## Start here

If you are evaluating the project from outside the development thread, use these surfaces in order:

1. **This README** — product boundary, architecture, current status, and evaluation entrypoints.
2. [`docs/EXTERNAL_EVALUATION.md`](docs/EXTERNAL_EVALUATION.md) — reproducible source-evaluation path and claim ceilings.
3. [`docs/architecture/INVARIANTS.md`](docs/architecture/INVARIANTS.md) — architecture invariants.
4. [`docs/pcmmad_doctrine/PCMMAD_CANONICAL_RUNTIME_SPECIFICATION.md`](docs/pcmmad_doctrine/PCMMAD_CANONICAL_RUNTIME_SPECIFICATION.md) — Runtime doctrine.
5. [`reports/README.md`](reports/README.md) — evidence index and interpretation rules.
6. [`CURRENT_INGRESS.md`](CURRENT_INGRESS.md) — internal continuity/recovery ingress. This is useful for lineage, but is not required to understand or test the repository.

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
- Research Epistemic Shadow (RES) continuity policy: canonical truth states, visible addendum transitions, snapshot validation, materiality classification, and research-handoff currentness.

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

At the `8714dd8...` mechanism frontier, source introspection registers **126 native tools**. The tool namespace spans browser, project, protocol, lab/control, memory, SOP, execution, filesystem, transfer, Git, governance, doctrine, research, semantic, continuity, procedure, Python, verification, web, and ZIP capabilities.

The five governance tools remain:

- `governance.contacts.resolve`
- `governance.contacts.admit`
- `governance.exhaustion.enumerate`
- `governance.exhaustion.evaluate_table`
- `governance.exhaustion.compress_witnesses`

The new RES policy/projection tools are deliberately part of the existing `continuity` family:

- `continuity.res.addendum.validate`
- `continuity.res.addenda.project`
- `continuity.res.snapshot.validate`
- `continuity.res.materiality.classify`
- `continuity.res.handoff.readiness`

Both sets are authority-neutral/read-only enforcement mechanics. RES persistence still uses existing project/protocol/artifact machinery; no RES database, scheduler, daemon, transport family, or authority plane was introduced. `RES_CONTENT != GOVERNING_DOCTRINE`.

The compact imported Custom GPT action surface remains intentionally bounded at 30 operations; capability growth occurs behind the native Runtime catalog rather than by repeatedly widening the transport schema.

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
- Operating Library / Runtime boundary convergence without introducing a second scheduler or authority plane.

The detailed evidence and derivation records are indexed under [`reports/`](reports/README.md).

## Qualification status

For the RES integration at the current engineering frontier:

- dedicated RES policy/hostile suite: **43/43 PASS**;
- focused RES + context + protocol + authority + governance composition gate: **176 collected / 175 passed / 0 failed / 1 conditional skip**;
- full Runtime suite: **556 collected / 555 passed / 0 failed / 1 conditional skip**;
- real epoch-42 RES: **22/22 canonical sections VALID**, exact file SHA `24b0e9899a4388ad905746f897ad6dac20c8c1de9e2d3f7e63f612f6c416aec9`;
- native handoff smoke: **HANDOFF_READY -> stale after material claim -> HANDOFF_READY only after provenance-bound RES addendum**;
- 96-addendum projection: **62,418 bytes**, automatically retained server-side behind the existing bounded result-handle mechanism.

The earlier governance qualification remains in ancestry: 57/57 governance tests, 55/55 existing-composition discriminator, and the 4,096-case bounded lawful-exhaustion smoke. RES pressure also caught implementation-registration, hash-identity, event-coverage, and EOL/EOF defects before publication. See [`reports/V30_RES_COMPOSITION_AND_ENFORCEMENT_2026-09-09.md`](reports/V30_RES_COMPOSITION_AND_ENFORCEMENT_2026-09-09.md).

These are **source qualification claims**, not claims that the currently running Desktop Runtime has been reloaded to this source.

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
