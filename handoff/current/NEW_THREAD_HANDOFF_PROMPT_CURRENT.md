Re-enter PCMMAD server work from GitHub/source truth, not historical handoff prose.

Fresh-read `git rev-parse HEAD`, `git status --short --branch`, and `git ls-remote origin refs/heads/main` first. Latest remote-verified source mechanism before the current-surface child is `0cc7894ffc766ac729c56d4abb8698bb3b6c78cb` / tree `ed939b1dbfd1dc570966c46f200618551b893503` (`Make Runtime clean-box reproducible`). v11 schema mechanism is `7e4c66a769884269d71babdb92217ba80eb66e74` / tree `967f108f235b4b42097f4b2d9d48ee61c591017c`. Current source is 158 native capabilities; v11.0 source successor has 8 Assistant-facing operations; v10.3 compatibility/import remains 30 operations. Current combined qualification is **890 collected / 888 passed / 2 skipped / 0 failed**; focused currentness+schema gate **128/128 PASS**; four-worker loadscope **888 passed / 2 skipped / 103 subtests**.

Read `handoff/current/SCHEMA_CURRENT.md` and `reports/V30_SCHEMA_V11_CURRENT_SURFACE_FINALIZATION_2026-09-10.md`. The schema branch has been explicitly triggered, built, qualified and source-published. Do not reopen it as locked/untriggered.

Production v11.0 currently has zero effect-truth, parallel-read and resume-replay witnesses; this conservative state is intentional. Goal-to-plan synthesis is deferred.

ICF-CS v1.2 is current at standard SHA `f966029496fd6e31a76a36a6e967db37ca2147acfa890a880426ae6a7fa79d92`. Use `continuity.ingress.rehydrate` for current fresh-instance orchestration.

Product-side ChatGPT Action installation and live Runtime promotion/restart are separate consequences.

Preserve `CAPABILITY_LEASE != CAPABILITY_GRANT`, `DECLARED_EFFECT_CLASS != VERIFIED_EFFECT_TRUTH`, `CONTINUATION != CURRENTNESS`, `LIVE_SHADOW != DTS != RES != UCM`, `SOURCE_SCHEMA_PUBLISHED != PRODUCT_SCHEMA_INSTALLED`, and `SOURCE_QUALIFIED != LIVE_PROMOTED`.
