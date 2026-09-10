# PCMMAD Laboratory Runtime invariants

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
10. **Continuity roles remain separate.** Live Shadow is bounded active state, Design Thread Stream is chronological forensic history, and Research Epistemic Shadow is the epistemic-learning surface. They are not collapsed into one ambiguous file.
11. **The GPT surface remains compact without reducing server power.** Exactly 30 imported operations route into a wider server-native surface of at least 87 tools.
12. **Execution is bounded and observable.** Queue, concurrency, timeout, output, registration, replay, and termination state are explicit.
13. **Optional sidecars fail cleanly.** Browser-bridge absence or failure cannot corrupt or falsely mark the receiver authority plane healthy.
14. **No promotion without final-artifact verification.** Route trace, protocol contracts, negative contracts, replay, concurrency, security, schema authority, package integrity, launcher audit, CSC finalization, and fresh ZIP verification govern release claims.
15. **RES history is append-oriented and authority-neutral.** Epistemic change is visible through addendum/promotion/demotion/supersession; consolidated RES snapshots are projections, not permission to rewrite history. `RES_CONTENT != GOVERNING_DOCTRINE`.
16. **Research handoff readiness is derived, not asserted.** A research-intensive handoff fails closed when the canonical RES snapshot is missing/invalid/stale, when registered bytes drift, or when a currentness-closing addendum is not bound to the latest material protocol event. `RES_HANDOFF_READY != PROJECT_MUTATION_AUTHORITY`.
17. **UCM is user continuity, not project/runtime/doctrine authority.** Canonical user continuity uses the existing append-only ledger with mandatory seq+hash CAS, explicit authority/currentness/verification components, bounded hydration, and `UCM != PROJECT_AUTHORITY / RUNTIME_TRUTH / DOCTRINE_AUTHORITY`.
18. **Fresh-instance applicability is explicit.** ICF-CS v1.2 requires a session mode and distinguishes `REQUIRED` from `NOT_APPLICABLE_WITH_BASIS`; Runtime SHALL NOT guess a UCM profile or silently equate missing state with non-applicability.
19. **Authority bytes, not labels, establish ICF currentness.** Fresh ingress binds the exact active ICF-CS v1.2 standard before RES/UCM hydration. `VERSION_LABEL != CURRENT_AUTHORITY_BYTES`.
20. **Unbounded selection does not authorize unbounded allocation.** Omitted context budget uses a finite default; explicit unbounded selection still caps individual reads to actual file size.
21. **Derived snapshots are caches, not history authority.** Canonical UCM retains bounded derived snapshot history while the append-only ledger remains authoritative.
22. **Path containment does not prove inode ownership.** Existing multiply-linked regular files are rejected before direct write consequences across project/filesystem/power/legacy surfaces.
23. **Fresh-ingress currentness is end-bound.** ICF, required RES and required UCM are reread/revalidated at the end of composed ingress; packet construction may not straddle authoritative heads silently.
24. **Canonical UCM JSON is finite UTF-8 and bounded.** NaN/Infinity, invalid surrogates, non-JSON types and excessive depth/node count fail before fingerprint/hash/append.
25. **Windows namespace identity outranks naïve strings.** Project/profile IDs and ZIP members reject device aliases, ADS/forbidden components, trailing-dot/space aliases and conflicting case identities.
26. **Atomic JSON publication tolerates transient Windows sharing violations without abandoning atomicity.** Bounded retry is permitted; in-place partial-write fallback is not.
27. **Transfer tickets bind file-object/content identity.** Import stage inode/link identity and export source inode/metadata/SHA currentness are verified across chunk/finalize boundaries.
