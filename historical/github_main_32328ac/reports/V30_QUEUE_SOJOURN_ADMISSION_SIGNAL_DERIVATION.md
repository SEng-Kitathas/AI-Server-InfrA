# V30 QUEUE SOJOURN ADMISSION SIGNAL DERIVATION

Date: 2026-09-07
Status: QUALIFIED ENGINEERING CANDIDATE / PUBLICATION PENDING
Live promotion: NOT PART OF THIS CAMPAIGN

## Quarry

Cross-domain raid R9 (CoDel) proposed that queue sojourn time is more decision-useful than queue depth and suggested retry-after / oldest-queued-age admission semantics.

Current V30 already measured `oldest_queued_age_seconds` in aggregate execution readiness, but queue-full rejection only returned capacity/depth. The caller receiving `EXECUTION_OVER_CAPACITY` therefore lacked the measured wait-pressure signal already available to the Runtime.

The Runtime does not currently maintain a trustworthy observed service-time model. Deriving a numeric Retry-After from queue depth alone would manufacture precision.

## Derived laws

- `QUEUE_DEPTH != QUEUE_SOJOURN`.
- `MEASURED_WAIT_PRESSURE != SERVICE_TIME_FORECAST`.
- `NO_SERVICE_TIME_MODEL => NO_NUMERIC_RETRY_ETA`.
- `ADMISSION_REJECTION_SHOULD_CARRY_THE_PRESSURE_SIGNAL_THAT_JUSTIFIED_IT`.

## Embodiment

`CapacitySnapshot` now includes:
- `oldest_queued_age_seconds`;
- `oldest_project_queued_age_seconds`.

The admission capacity path now uses:
- one existing managed-aware running census;
- one queue census that simultaneously computes global/project queue counts and oldest queue ages.

This replaces the prior capacity snapshot's separate global/project running scans plus separate global/project queue scans.

When the queue is full, `EXECUTION_OVER_CAPACITY` now carries:
- serializable `capacity` including measured global/project oldest queue ages;
- `queue_sojourn` with the same explicit pressure values;
- `retry_after_seconds: null`;
- `retry_after_basis: not_claimed_without_observed_service-time_model`.

No CoDel dropping algorithm, target delay, or fabricated ETA is introduced.

## Evidence

`tests/test_execution_queue_sojourn.py` proves:
1. queue census measures global and project oldest queued age correctly while ignoring running jobs;
2. capacity snapshot uses exactly one running census and one queue census;
3. queue-full rejection exposes measured sojourn and explicitly does not invent a numeric retry ETA.

Focused queue/admission/scheduler cluster: 12/12 PASS.
Full suite: **379 collected / 378 passed / 0 failed / 1 skipped**.
Changed/new Python compile: PASS.
CRLF-aware `git diff --check`: PASS.

## Claim ceiling

This campaign makes queue pressure more observable and admission rejection more decision-useful. It does not implement CoDel active queue management, estimate completion time, or claim a service-time forecast.

## Sequencing

Live Runtime remains frozen on the previously promoted feature until remaining server campaigns finish. Continue remaining raids R6/R12/R13 and verify R8/R11 retirement against current reality. R10/final schema remains LAST and untriggered.
