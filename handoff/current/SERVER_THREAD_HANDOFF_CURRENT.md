# Server Thread Handoff — Current

Status: **CURRENT ROLLOVER / CORE ARCHITECTURE CONVERGED / RELEASE GATES OPEN / LIVE UNCHANGED**

GitHub mechanism frontier: `e1b2b8eddd92e8ad9159a548f9e6d6b2beb895f4` / tree `8fbded01e519a938ded1f2177378cd6693d788b7` / parent `2753e87b9cc8f3309666ab479413306ba85e9b11`.
Schema mechanism: `7e4c66a769884269d71babdb92217ba80eb66e74`; canonical v11 SHA `ee62b261d6e5518b585faccd4af21a42d9b7bd6b3dc63f8af0e1242ef9fb9010`; **8 operations / 158 native capabilities**.
ICF-CS: v1.2 / `f966029496fd6e31a76a36a6e967db37ca2147acfa890a880426ae6a7fa79d92`.

Read first: `checkpoints/THREAD_ROLLOVER_CHECKPOINT_2026-09-10.md`, then `CURRENT_INGRESS.md` and `handoff/current/SCHEMA_CURRENT.md`.

Current release blocker: GitHub Actions run `34537723493` is red on both hosted OSes. Ubuntu exact current failure: `test_hot_scan_cost_is_independent_of_terminal_history_count` -> `38 != 50`. Windows still needs exact testcase readback if the next run remains red.

Published current source includes project-aware access logging (`[PROJECT] [job:SHORT] METHOD PATH STATUS latency`).

Local-only donor/work branches:
- adaptive mutation contention commit `12ccc208ec2e9183e3b280618f266211cc00179b` directly on `e1b2b8e`; not remote authority;
- schema-wire hardening WIP based on stale `f38c564`; reproduce/rebase before use.

Loaded Desktop Runtime remains older (observed compact 30-operation surface, global execution concurrency 8). Rebuild the contaminated live venv before final promotion.

Next: close hosted CI -> reconcile/publish adaptive guard if still green -> re-derive wire hardening -> final exact-Git live promotion/restart/readback.

`GIT_PUBLICATION != LIVE_RUNTIME_PROMOTION`
`SOURCE_SCHEMA_PUBLISHED != PRODUCT_SCHEMA_INSTALLED`
`LOCAL_GREEN != HOSTED_CLEANBOX_GREEN`
`SOURCE_QUALIFIED != LIVE_PROMOTED`
