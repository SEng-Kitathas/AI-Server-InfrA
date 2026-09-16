# V30 WORKLOAD IDENTITY PROOF DERIVATION

Date: 2026-09-07
Status: QUALIFIED ENGINEERING CANDIDATE / PUBLICATION PENDING
Live promotion: NOT PART OF THIS CAMPAIGN

## Quarry

Cross-domain raid R13 (WireGuard/Tailscale / peer identity) asked the Runtime to authenticate a peer/workload rather than relying only on a replayable bearer request. The retained raid explicitly named peer auth, mTLS, and key rotation as candidate directions while warning not to silently break hosted GPT reachability.

Current-tree audit found:

- mandatory receiver API-key authentication;
- textual session/operator labels;
- fenced project mutation ownership;
- process/PID identity hardening;
- no stable workload/peer proof primitive at the HTTP authentication boundary.

The current hosted path does not expose verifiable client certificates to the Runtime, and the installed Runtime environment has no asymmetric crypto dependency. Pretending to have mTLS or public-key workload identity would therefore exceed evidence.

## Derived laws

- `BEARER_AUTHENTICATION != WORKLOAD_IDENTITY`.
- `WORKLOAD_PROOF != AUTHORIZATION_AUTHORITY`.
- `SIGNED_REQUEST != REPLAY_SAFE_REQUEST` unless a durable nonce witness exists.
- `PROOF_OF_POSSESSION_BINDS_EXACT_REQUEST`.
- `KEY_ROTATION_REQUIRES_KEY_IDENTITY`, not secret replacement under one unlabeled key.
- `OPTIONAL_IDENTITY_LAYER != HOSTED_REACHABILITY_BREAK`.
- `HMAC_WORKLOAD_PROOF != MTLS_OR_ASYMMETRIC_PEER_IDENTITY`.

## Embodiment

New stdlib-only module:

`workload_identity.py`

The existing `shared_core.require_valid_api_key()` remains the single HTTP auth chokepoint used by context, execution, lab, legacy, power, and transfer planes. R13 extends that chokepoint rather than scattering identity checks across route implementations.

### Compatibility boundary

The receiver API key remains mandatory in all modes. A workload proof can never substitute for an invalid/missing API key.

Workload identity mode is configured by `PCMMAD_WORKLOAD_IDENTITY_MODE`:

- `optional` (default): bearer-only callers continue to work; valid proof, when supplied, is verified;
- `required`: bearer-only HTTP requests are rejected until valid workload proof is also supplied;
- `off`: workload proof headers are rejected rather than silently ignored, preventing an identity illusion.

The default therefore preserves hosted GPT reachability unless an operator explicitly changes policy.

`capabilities()` advertises only `workload_identity_proof=true`. Configured workload IDs, key IDs, and secrets are not exposed through capability readback.

### Per-workload proof keys and rotation

`PCMMAD_WORKLOAD_KEYS_JSON` maps one workload ID to one or more key IDs and strict base64url secrets. Each decoded secret must be 32-128 bytes.

Multiple key IDs for one workload are accepted concurrently, creating an explicit rotation overlap window. Removing an old key ID from configuration revokes further proofs under that key. The proof receipt identifies the key ID but never returns the secret or signature.

### Exact request binding

Proof headers carry:

- workload ID;
- key ID;
- Unix timestamp;
- URL-safe nonce;
- HMAC-SHA256 signature.

The HMAC canonical message binds:

1. proof version `pcmmad-workload-proof-v1`;
2. workload ID;
3. key ID;
4. timestamp;
5. nonce;
6. HTTP method;
7. exact path + raw query string representation;
8. SHA-256 of the actual request body.

The maximum accepted clock skew is fixed at 300 seconds. Method, path/query, or body tampering invalidates the signature before nonce reservation.

### Durable replay witness

A valid proof reserves its nonce using atomic `O_CREAT|O_EXCL` under the Runtime temporary root (`TEMP_ROOT/workload_identity`) after signature verification and before the request continues.

The replay witness stores no secret or signature. It records:

- workload ID;
- key ID;
- proof timestamp / acceptance time;
- nonce SHA-256;
- HTTP method;
- target SHA-256;
- body SHA-256;
- canonical proof-message SHA-256.

A repeated nonce for the same workload/key fails with `WORKLOAD_IDENTITY_REPLAY`. Fixed 300-second replay buckets permit deterministic cleanup without a full historical directory scan on the request hot path.

Successful verification is attached to Flask request-local state as `g.pcmmad_workload_identity`, making the authenticated workload evidence available to later Runtime layers without promoting it into mutation/approval authority.

## Hostile evidence

`tests/test_workload_identity_proof.py` proves:

1. default optional mode preserves existing bearer-only hosted reachability;
2. a valid signed proof binds and exposes workload/key identity while persisting a non-secret replay witness;
3. the exact same signed request is rejected on replay;
4. invalid body signature does not consume the nonce, and the correctly bound request can subsequently succeed;
5. method and path/query are part of the signature;
6. stale and partial proofs fail closed;
7. two key IDs for one workload are accepted for rotation overlap;
8. proof cannot substitute for an invalid receiver API key;
9. malformed configured key material fails closed when proof is supplied;
10. `required` mode rejects bearer-only calls while `off` rejects supplied proof rather than silently ignoring it;
11. eight concurrent copies of the same signed proof yield exactly one acceptance and seven replay rejections, with exactly one durable witness.

Focused workload proof: **11/11 PASS**.
Broader workload/auth/direct-route/contract adjacency before the final witness extension: **33/33 PASS**; the final full suite includes the witness extension.
Full suite: **398 collected / 397 passed / 0 failed / 1 skipped**.
Changed/new Python compile: PASS.
CRLF-aware `git diff --check`: PASS.

## Claim ceiling

This campaign earns request-bound symmetric workload proof-of-possession and replay resistance. It does **not** claim:

- mTLS;
- asymmetric/public-key peer identity;
- hardware-backed identity;
- universal workload-proof enforcement (default remains optional);
- that workload identity itself grants mutation/approval authority;
- transport confidentiality beyond the existing HTTPS/public ingress setup.

`WORKLOAD_IDENTITY != FENCED_MUTATION_AUTHORITY` remains consistent with A-042. Downstream policy may use verified workload identity later, but this campaign does not silently promote it into authority.

No live Runtime promotion is part of this campaign. Live remains frozen on the previously promoted feature until whole-runtime convergence is complete.

## Sequencing

R13 is the final retained non-schema cross-domain raid in this campaign. R8 lease renewal and R11 caller-owned result cursors remain substantially embodied/retired by current-tree evidence.

Next work is whole-runtime convergence and OBE/Skills dogfood against the accumulated engineering feature set while live remains frozen. R10/final schema redesign remains LAST and untriggered pending whole-runtime convergence plus explicit user `hells yeah, ready`.
