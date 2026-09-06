# PCMMAD source authority and conflict resolution

PCMMAD Receiver is the product and runtime. External project labels in source archives do not become PCMMAD namespaces.

## Authority order

1. `PCMMAD_CANONICAL_RUNTIME_SPECIFICATION.md` governs PCMMAD runtime method, modes, state classes, adjudication, artifacts, and promotion.
2. `docs/ergo_foundations/UNIFIED_CODE_STANDARDS_AGNOSTIC_2026-04-11.md` governs implementation-facing invariants and verification quality.
3. `docs/csc_sop/` governs audit, anti-pattern inversion, promotion, freshness, holonic review, and unreliable execution planes.
4. `spec/PCMMAD_RECEIVER_V29_NATIVE_PROTOCOL_SPEC.md` binds those laws to this receiver release.
5. Historical archives, Forge-specific documents, run reports, and alternate CSC trees are evidence sources. They do not override the PCMMAD-native contract merely because they are newer or more verbose.

## Conflict rules

- Verified runtime truth outranks prose claims.
- PCMMAD-native terminology outranks source-project terminology inside executable code and public interfaces.
- Explicit invariants and typed records outrank duplicated conventions.
- The append-only event ledger outranks its derived snapshot.
- A verified prior capability remains preserved unless a replacement proves parity or the release records an intentional removal.
- Source-specific corpus and extension mechanisms are imported only when their invariant generalizes to PCMMAD Receiver.
