# WINDOWS JOB OBJECT RESOURCE ENVELOPE QUALIFICATION — 2026-09-07

Status: **QUALIFIED ENGINEERING CANDIDATE / GIT PUBLICATION PENDING / LIVE FROZEN**

## Baseline
- Current Git/remote `main`: recovery-only live-promotion handoff `85ae9b6c91616548fab9233e32c5a43471b33b65`.
- Last engineering/live Runtime feature: `4163606459324feaa31252b3c2a6d58d73aaff46`.
- Live Runtime remains on that feature by explicit user direction until the remaining server work is finished.

## Candidate identity
- 7 changed/new files.
- Inventory SHA-256: `ccf2f30301eff0182ea0eaa7ab745c427bde7ca06469b5af074090a7e05c0847`.
- Repo derivation: `reports/V30_WINDOWS_JOB_OBJECT_RESOURCE_ENVELOPE_DERIVATION.md`.

## Promoted candidate laws
- `RESOURCE_LIMIT_DECLARATION != RESOURCE_ENFORCEMENT`.
- `RESOURCE_ENVELOPE_CURRENTNESS_REQUIRES_KERNEL_READBACK`.
- `IDEMPOTENCY_KEY_BINDS_RESOURCE_BUDGET`.
- `JOB_OBJECT_RESOURCE_LIMITS_INCLUDE_PCMMAD_CONTROL_MEMBERS`.
- `KILL_ON_JOB_CLOSE_IS_ONE_LIMIT_FLAG_NOT_THE_WHOLE_LIMIT_STRUCTURE`.
- transport resource fields do not become Runtime policy authority.

## Embodiment
- Optional durable `resource_budget` per canonical async Job.
- Windows Job Object enforcement for per-process memory, aggregate Job memory, active process count, and CPU hard-cap percentage.
- Immediate kernel readback persisted as `applied_resource_envelope`; `resource_gate=pass` only after successful apply/readback.
- Active-process budget counts worker/control members plus user descendants; async minimum is 3.
- Resource budget is part of execution idempotency fingerprint.
- Non-empty budget fails closed on runtimes without Windows Job Object support.
- `set_kill_on_close()` preserves existing resource flags.
- Compact OpenAPI remains 30 operations and projects `ExecutionResourceBudget` / `ExecutionResourceEnvelope` without starting the final schema redesign.

## Evidence
- Direct kernel round-trip: 256 MiB/process, 512 MiB/job, 8 active members, 50% CPU hard cap — exact readback.
- Behavioral discriminator: Job Object active-process limit blocks descendant creation.
- Scheduler integration: kernel envelope applied/read back before ownership release/user execution; fresh named Job Object reopen matches durable state.
- Focused resource tests: 6/6 PASS.
- Resource + existing Job Object/ownership hostile cluster: 9/9 PASS.
- Resource + compact schema parity cluster: 23/23 PASS.
- Full suite: **376 collected / 375 passed / 0 failed / 1 skipped**.
- Changed/new Python compile: PASS.
- CRLF-aware `git diff --check`: PASS.

## Claim ceiling
- Active-process enforcement is behaviorally proven.
- Memory/CPU controls are proven as accepted native Job Object configuration plus kernel readback; long-duration memory-pressure and CPU-throttling soak behavior is not claimed.
- No live promotion is part of this publication.

## Sequencing
- Publish this as a dedicated engineering feature.
- Continue remaining cross-domain raids afterward.
- OBE/Skills may continue dogfood against the currently promoted live Runtime in parallel.
- Final schema redesign remains LAST/untriggered and still requires whole-runtime convergence plus explicit user `hells yeah, ready`.

## WINDOWS JOB OBJECT RESOURCE ENVELOPE — ENGINEERING PUBLISHED (2026-09-07)
- Engineering feature is **PUBLISHED / REMOTE-VERIFIED** at `0968ea5d9de36d766771c7930d9a0944a61ee546`; tree `810cc429067ff7e546fba732b1d0e5ec1d348c73`; subject `Enforce Windows Job Object resource budgets`.
- Qualification remains `376 collected / 375 passed / 0 failed / 1 skipped`; candidate inventory `ccf2f30301eff0182ea0eaa7ab745c427bde7ca06469b5af074090a7e05c0847`.
- Runtime now durably models and kernel-readbacks Job Object budgets for per-process memory, aggregate Job memory, active member count, and CPU hard cap; idempotency fingerprint binds the budget.
- Live Runtime intentionally remains at `4163606459324feaa31252b3c2a6d58d73aaff46`; **ENGINEERING_FEATURE_HEAD != LIVE_RUNTIME_FEATURE_HEAD** by explicit user direction. No live promotion occurred in this campaign.
- Next: audit remaining cross-domain raids R6/R8/R9/R11/R12/R13 against current-tree reality. R10/final schema remains LAST/untriggered.
