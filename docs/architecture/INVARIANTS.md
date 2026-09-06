# PCMMAD Receiver V29 invariants

## Global cycle

Every promoted change follows **PROBE → DERIVE → VERIFY → EMBODY → RECURSE** at function, module, subsystem, and release scales.

## Load-bearing invariants

1. **Required route families fail hard.** Optional route families may degrade, but degradation is explicit in boot and health evidence.
2. **Authentication is mandatory and singular.** `GITHOME_API_KEY` is the authority source; `X-GitHome-Key` is compared in constant time; no key is embedded in code, reports, launchers, or schemas.
3. **Read does not mutate.** Inspection and result retrieval do not create project layouts or write state.
4. **Project paths remain inside project roots.** General filesystem access is mount-governed; archive extraction rejects traversal, drive/UNC paths, normalized collisions, links, and special entries.
5. **Mutation is explicit and mode-aware.** Artifact class, operation, project identity, approval policy, protocol mode, mutation domain, and result evidence are structured boundaries rather than prose conventions.
6. **Protocol history is append-only and verifiable.** `events.jsonl` is authoritative, sequence and previous hashes are monotonic, event hashes commit to canonical bodies, and `state.json` is only a rebuildable projection.
7. **Sealed identity cannot be silently rewritten.** A sealed artifact requires a digest; changed content requires a new identity and explicit lineage.
8. **Evidence pressure is proportionate.** Ratification thresholds scale with `STANDARD`, `ELEVATED`, and `CRITICAL` rigor; duplicate, failed, or expired evidence cannot satisfy the gate.
9. **Waivers remain visible and bounded.** Waivers require identity, scope, reason, doctrine basis, owner, status, optional future expiry, and affected-claim lineage. Inactive or expired waivers cannot authorize promotion.
10. **Continuity roles remain separate.** Bounded active state and chronological forensic stream are not collapsed into one ambiguous file.
11. **The GPT surface remains compact without reducing server power.** Exactly 30 imported operations route into a wider server-native surface of at least 87 tools.
12. **Execution is bounded and observable.** Queue, concurrency, timeout, output, registration, replay, and termination state are explicit.
13. **Optional sidecars fail cleanly.** Browser-bridge absence or failure cannot corrupt or falsely mark the receiver authority plane healthy.
14. **No promotion without final-artifact verification.** Route trace, protocol contracts, negative contracts, replay, concurrency, security, schema authority, package integrity, launcher audit, CSC finalization, and fresh ZIP verification govern release claims.
