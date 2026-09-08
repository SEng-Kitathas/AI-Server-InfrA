# WORKLOAD IDENTITY PROOF QUALIFICATION — 2026-09-07

Status: **QUALIFIED ENGINEERING CANDIDATE / GIT PUBLICATION PENDING / LIVE FROZEN**

## Baseline
- Current Git/remote engineering `main`: R12 continuity convergence `b5cf1b9628ef1ff6f3fbec2f215b1d014a9ab32a`.
- Live Runtime remains `4163606459324feaa31252b3c2a6d58d73aaff46` by explicit user direction.
- R12 post-publication continuity is included in this registration transition.

## Candidate identity
- 4 changed/new engineering files.
- Inventory SHA-256: `523d113d9069e209d767c0444a2ad1296a35b07bdd786e0bd4faf9897301e2fb`.
- Derivation: `reports/V30_WORKLOAD_IDENTITY_PROOF_DERIVATION.md`.

## Earned laws
- `BEARER_AUTHENTICATION != WORKLOAD_IDENTITY`.
- `WORKLOAD_PROOF != AUTHORIZATION_AUTHORITY`.
- `SIGNED_REQUEST != REPLAY_SAFE_REQUEST` without durable nonce witness.
- `PROOF_OF_POSSESSION_BINDS_EXACT_REQUEST`.
- `KEY_ROTATION_REQUIRES_KEY_IDENTITY`.
- `OPTIONAL_IDENTITY_LAYER != HOSTED_REACHABILITY_BREAK`.
- `HMAC_WORKLOAD_PROOF != MTLS_OR_ASYMMETRIC_PEER_IDENTITY`.

## Embodiment
- The existing mandatory `X-GitHome-Key` remains the outer compatibility boundary and cannot be replaced by workload proof.
- `PCMMAD_WORKLOAD_IDENTITY_MODE`: `optional` default, explicit `required`, or `off`.
- Default optional mode preserves bearer-only hosted GPT reachability.
- `PCMMAD_WORKLOAD_KEYS_JSON` maps workload IDs to one or more key IDs with strict base64url 32-128 byte secrets; multiple key IDs support rotation overlap.
- HMAC-SHA256 proof binds proof version, workload ID, key ID, timestamp, nonce, HTTP method, exact path/query, and actual request-body SHA-256.
- Fixed freshness window: +/-300 seconds.
- Valid proof atomically reserves a durable nonce witness under `TEMP_ROOT/workload_identity`; replay fails.
- Durable witness contains workload/key identity and non-secret request-binding hashes, never secret/signature.
- Verified receipt is available request-locally as `g.pcmmad_workload_identity`; this does not grant project mutation or approval authority.
- `capabilities()` exposes only `workload_identity_proof=true`, not configured identities/key IDs/secrets.

## Evidence
- Focused workload identity hostile tests: **11/11 PASS**.
- Broader workload/auth/direct-route/contract adjacency before final witness extension: **33/33 PASS**; final full suite includes the witness extension.
- Concurrency discriminator: 8 concurrent copies of one signed proof -> exactly 1 acceptance / 7 replay rejections / 1 durable witness.
- Full suite: **398 collected / 397 passed / 0 failed / 1 skipped**.
- Changed/new Python compile: PASS.
- CRLF-aware `git diff --check`: PASS.

## Claim ceiling / sequencing
- This earns symmetric request-bound workload proof-of-possession and replay resistance.
- It does not claim mTLS, asymmetric/public-key identity, hardware identity, universal proof enforcement, or workload-derived mutation authority.
- No live promotion occurs.
- R13 is the final retained non-schema cross-domain raid. R8/R11 remain substantially embodied/retired.
- Next is whole-runtime convergence + OBE/Skills dogfood against accumulated engineering features while live remains frozen.
- R10/final schema redesign remains LAST/untriggered and still requires whole-runtime convergence plus explicit user `hells yeah, ready`.

## WORKLOAD IDENTITY PROOF — ENGINEERING PUBLISHED (2026-09-07)
- Engineering feature **PUBLISHED / REMOTE-VERIFIED** at `ee8ec16000f1d90eb60d034259f85f3b8b5148e1`; tree `0b20eed8220015d26b8315094f5009e2942120f7`; subject `Add replay-safe workload identity proof`.
- Final exact candidate inventory `523d113d9069e209d767c0444a2ad1296a35b07bdd786e0bd4faf9897301e2fb`; qualification `398 collected / 397 passed / 0 failed / 1 skipped`; focused workload proof `11/11 PASS`.
- Mandatory receiver bearer key remains required; optional request-bound workload proof adds identity/replay evidence without silently breaking hosted GPT reachability.
- HMAC proof binds workload/key/timestamp/nonce/method/path-query/body hash; durable atomic nonce witness makes replay fail closed; multiple key IDs support rotation overlap.
- `WORKLOAD_IDENTITY != FENCED_MUTATION_AUTHORITY`; proof is request identity evidence only. Claim ceiling remains symmetric proof-of-possession, not mTLS/asymmetric/hardware identity.
- Live Runtime remains frozen at `4163606459324feaa31252b3c2a6d58d73aaff46`; no live promotion occurred.
- **Retained non-schema cross-domain raid set is now closed.** R8/R11 are substantially embodied/retired; R6/R7/R9/R12/R13 are engineering-published.
- Next: whole-runtime convergence + OBE/Skills dogfood against accumulated engineering features while live remains frozen. R10/final schema remains LAST/untriggered and still requires explicit user `hells yeah, ready`.
