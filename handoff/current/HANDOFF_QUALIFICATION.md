# Git Handoff Qualification — A-033 Publication Candidate

Date: 2026-09-05
Status: QUALIFIED FOR GIT COMMIT/PUSH

## Current step
A-033 execution admission hotpath read-amplification repair.

## Reproduction
Before mutation, current V30 saturated 60-record drain produced:
- 49 tree walks
- 2,940 job-file loads
- 12 per-candidate capacity snapshots
- 0 starts
- 0.554 s.

Current A-033 candidate produces:
- 2 tree walks
- 120 loads
- zero per-candidate capacity calls
- zero queued-record reads at global saturation
- 0.231 s.

500-history/50-queued Windows split:
- candidate discovery 2.226 s outside admission lock
- admission-lock hold 0.049 s.

## Qualification
- execution cluster: **19 / 19 PASS**
- refreshed Git handoff regression: **6 / 6 PASS**
- complete V30 suite before mirror refresh: **264 collected tests GREEN**
- `execution_routes.py` SHA `2cea76cd1b24291f1ef5d929fedbf02f6102b3bc0e2927cedc5db2a367d0a02e`
- A-033 test SHA `fd2ed0b73c413d88dc8083797d623504da5bca435b7a0063c9d1d8b1ba56efb8`.

## Hostile evidence
External teardown receipt:
`reports/hostile_inputs/EXECUTION_PLANE_TEARDOWN_2026-09-05_RECEIPT.md`.

## Publication boundary
Last remote-verified base before this step:
`a3d84199e2673b87c4d7d246bf591bb3dbefdd63`.

A final exact-candidate handoff + execution + full-suite gate follows this file/manifest update, with no repo mutation before commit.

## Claim ceiling
A-033 fixes repeated capacity scans under the process-global admission lock. It does not fix flat lifetime-tree discovery/census, poison-record isolation, retention, serving model, legacy PID identity, or multi-receiver ownership.

Git publication is incomplete until commit, push, and independent remote-head readback succeed.

`GIT_PUBLICATION != LIVE_RUNTIME_PROMOTION`
`CURRENT_INGRESS_POINTER != CURRENT_STATE_PROOF`
