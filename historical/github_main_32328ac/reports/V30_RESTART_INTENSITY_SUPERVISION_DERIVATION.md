# V30 RESTART INTENSITY SUPERVISION DERIVATION

Date: 2026-09-07
Status: QUALIFIED ENGINEERING CANDIDATE / PUBLICATION PENDING
Live promotion: NOT PART OF THIS CAMPAIGN

## Quarry

Cross-domain raid R6 (Erlang/OTP supervisors) proposed restart-intensity budgets and crash-loop protection. Current-tree falsification found no restart window, restart count, cooldown, backoff, or crash-loop state in the canonical receiver+ngrok restart path.

The Runtime already had a canonical PowerShell convergence controller and a governed `control.receiver.restart` adapter, but each approved call could schedule another restart regardless of recent restart history. Per-call approval therefore constrained who could request a restart, not how frequently the service could be restarted.

## Derived laws

- `APPROVAL_GRANTED != RESTART_INTENSITY_PERMITTED`.
- `SUPERVISION_POLICY != TRANSPORT_ARGUMENTS`.
- `CRASH_LOOP_GUARD_REQUIRES_DURABLE_CROSS_PROCESS_HISTORY`.
- `RESTART_RESERVATION_PRECEDES_RESTART_CONSEQUENCE`.
- `FORCED_RECOVERY != COOLDOWN_RESET`.
- `CUSTOM_RECEIPT_PATH != FRESH_RESTART_BUDGET`.

## Canonical policy

The restart controller now owns one fixed service-level policy:

- window: 300 seconds;
- maximum allowed Start/Restart reservations in-window: 3;
- cooldown after the next over-intensity request: 600 seconds.

These values are not caller-controlled command-line transport parameters. The only bypass is explicit `-ForceRestart`, intended for operator recovery.

`Stop` and `Status` are not restart attempts and do not consume the budget.

## Durable supervision state

Restart intensity state lives beside the canonical restart receipts under `%TEMP%\\pcmmad_restart_receipts`, independent of any custom receipt destination. A caller cannot obtain a fresh restart budget merely by choosing another `-ReceiptPath`.

State schema: `pcmmad.restart-intensity.v1`.

Each Start/Restart controller acquires an exclusive cross-process file lock, loads the durable state, prunes attempts outside the fixed window, evaluates cooldown/intensity, and—when allowed—persists the new reservation before any stop/start consequence.

Malformed JSON, wrong/missing state schema, malformed attempt timestamps, malformed cooldown timestamps, and lock acquisition failure fail closed.

Blocked requests:

- do not stop receiver/ngrok processes;
- do not add another restart attempt;
- write terminal receipt stage `restart_intensity_blocked`;
- report reason `restart_intensity_exceeded` or `cooldown_active`;
- exit with code 75.

Forced recovery:

- is explicit in the receipt (`forced=true`);
- records the forced reservation;
- does not clear an existing cooldown.

A `-RestartIntensityReservationOnly` controller mode exists for supervision reservation/testing without stop/start consequence. It is intentionally named reservation-only because it mutates the restart budget.

## Adapter truth

`restart_control.py` remains an adapter over the canonical controller. Its schedule response now states:

`scheduled != permitted-by-intensity-guard != stopped != started != healthy`

The post-reconnect restart receipt remains authoritative for whether a scheduled restart converged, was intensity-blocked, or failed.

## Hostile evidence

`tests/test_restart_intensity_supervision.py` proves with separate Windows PowerShell processes:

1. three reservations are allowed in the canonical five-minute window;
2. the fourth request is blocked and starts a ten-minute cooldown;
3. subsequent requests during cooldown remain blocked without consuming another slot;
4. explicit force is allowed, recorded, and does not clear cooldown;
5. an expired historical attempt is pruned;
6. corrupted canonical intensity state fails closed before any restart consequence;
7. six concurrent controller processes serialize through one cross-process lock: exactly three reserve and three are blocked, with durable state containing exactly three attempts.

Focused restart/control/contract adjacency: **20/20 PASS**.
Full suite: **383 collected / 382 passed / 0 failed / 1 skipped**.
Changed/new Python compile: PASS.
PowerShell parser: PASS.
CRLF-aware `git diff --check`: PASS.

## Claim ceiling

This campaign prevents restart storms through the canonical PCMMAD receiver+ngrok restart controller. It does not claim control over an unrelated external OS service manager or a privileged operator who edits/deletes local supervision state directly.

No live Runtime promotion or live restart is part of this campaign. The live Runtime remains frozen on the previously promoted engineering feature until remaining server campaigns converge.

## Sequencing

After publication, continue current-tree audits of R12 continuity divergence/convergence and R13 compaction safety. R8 and R11 remain retired/substantially embodied by current Runtime behavior. R10/final schema remains LAST and untriggered pending whole-runtime convergence plus explicit user `hells yeah, ready`.
