# External Hostile Evidence Receipt — Execution Plane Teardown — 2026-09-05

Status: **ADMITTED AS HOSTILE EVIDENCE / NOT AUTOMATIC ARCHITECTURE AUTHORITY**

Source: user-supplied teardown + benchmark/repro/patch attachments in the saturated project thread.

## Exact attachment identities

| Attachment | Bytes | SHA-256 |
|---|---:|---|
| `EXECUTION PLANE TEARDOWN.md` | 12,339 | `89dd7999e868a9c70769019b755cb7add60448d8f9e7c8c503c12248d25bd699` |
| `execution scheduler hotpath.diff` | 3,710 | `3302d6551b9d727b8282e7bef430fbc6a3c647a937b7e57a774127bbbd1aef45` |
| `repro scheduler starvation.py` | 1,923 | `c24b999554db6bf8d805b57066f589725c8e1df90ca29b0e9389866b7fb29845` |
| `bench admission lock.py` | 1,439 | `0617b048a4dae1c6c4012f012d47332cf46cbb215e091c6d1e1dcf93bf27d935` |

The attachments were read in full before the campaign split was derived. Their exact bytes are identified above; this receipt preserves the load-bearing claims even if chat-local attachment access is unavailable in a future thread.

## Hostile claims admitted for reproduction

1. **Admission read amplification under the process-global lock.** `_drain_queue_locked` calls `_can_start_now` per queued candidate; `_capacity_snapshot` performs four lifetime-tree scans; unbounded drain + `continue` at saturation produces O(queued × lifetime-jobs) reads while starting nothing.
2. **Poison-record scheduler starvation.** A malformed/dead RUNNING record with invalid/empty log paths can throw during reconciliation and abort the tick before `_drain_queue` forever.
3. **Lifetime-job scheduler duty-cycle growth.** Flat execution storage and no retention make scheduler cost depend on historical job count rather than active work.
4. **Structural candidate:** partition durable execution state into active/terminal directories and move records atomically on terminal transition so hot scans are O(active).
5. **Retention candidate:** slow-path retention for terminal history after hot-path partitioning.
6. **Drain-bound candidate:** default drain work should not be unbounded beyond useful capacity.
7. **Serving-model audit:** public ngrok-facing Werkzeug development server may be an inappropriate production serving boundary; evaluate a bounded production WSGI server separately.
8. **Legacy PID-reuse audit:** bare PID liveness on the legacy path may disagree with the worker-capsule creation-time identity model on Windows.
9. **Multi-receiver admission audit:** `_ADMISSION_LOCK` is process-local; simultaneous receivers sharing a job store could over-admit.

## Campaign split / authority ceiling

Do **not** merge the supplied 86-line patch wholesale. It combines at least two distinct failure classes.

Current ordered campaign:
- **A-033:** admission hotpath read amplification only;
- **A-034:** poison-record isolation and read-path failure excerpt separation;
- **A-035:** active/terminal durable-store partition;
- **A-036:** retention / bounded drain after partition semantics;
- separate serving-model / legacy PID-reuse / multi-receiver ownership audits.

Each item must be reproduced against current V30, derived from current semantics, hostile-tested, full-suite qualified, continuity-updated, committed, pushed, and remote-read before the next mutation.

## A-033 reproduction result on current V30

Before A-033 mutation, synthetic saturation with 40 terminal + 8 RUNNING + 12 QUEUED records produced:
- 0 jobs started;
- 12 `_capacity_snapshot` calls;
- 49 job-tree walks = 1 candidate scan + 4 × 12 candidate capacity scans;
- 2,940 job-file loads;
- 0.554 s end-to-end on the operator Windows host, already exceeding the configured 0.25 s scheduler interval.

This independently reproduced the mechanism claimed by the external teardown.
