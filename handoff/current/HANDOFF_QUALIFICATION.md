# Git Handoff Qualification — A-038 Publication Candidate

Date: 2026-09-06
Status: QUALIFIED FOR GIT COMMIT/PUSH

## Current step
A-038 deterministic execution lifecycle simulation / replay on-ramp.

## Qualification
- current survivor campaign: **100 / 100 seeds × 40 actions PASS**
- historical `pre_a034` scar discovered at seed 0
- vulnerable seed-0 failure envelope/trace replayed byte-identically twice
- same seed/current scheduler PASS with 3 injected reconcile faults + 2 PID recycle events
- focused execution/simulation cluster: **39 / 39 PASS**
- refreshed Git handoff regression: **6 / 6 PASS**
- complete V30 suite before mirror refresh: **289 collected tests GREEN**
- simulator SHA `98990c6024a3ab9defbbc1220e640f139490b2bdd54ae5a7048b0d85a3a8221a`
- A-038 test SHA `c61e0f6e6fc51f8d4fb8427c2438eb2cd44bd272eee2db4724c99f8758fb57ee`
- report SHA `5df52c77981f3b77ede86997df82eefcbd1005d2ebfa5eee6630fcec20ae2f1a`.

## Method promotion
`SCHEDULE_FAILURES_REQUIRE_SCHEDULE-LEVEL TESTS WHERE PRACTICAL`.

`A FAILURE SEED + DETERMINISTIC TRACE IS A STRONGER RECEIPT THAN AN UNREPLAYABLE FLAKE`.

## Next correctness discriminator
A-038 seed 0 exposes two recycled-PID aliases still active RUNNING in current legacy non-worker supervision. A-039 process-identity binding follows after publication.

## Publication boundary
Last remote-verified base:
`59b4b5e5d6339127e50e052827f27bc94a14c832`.

A final exact-candidate handoff + execution/simulation + complete-suite gate follows this file/manifest update with no repo mutation before commit.

## Claim ceiling
A-038 is bounded seeded search, not exhaustive formal verification. It does not virtualize full filesystem durability, real kernel Job Objects, whole-process receiver restart, arbitrary thread interleavings, disk faults, transport, or every timing boundary.

`GIT_PUBLICATION != LIVE_RUNTIME_PROMOTION`
