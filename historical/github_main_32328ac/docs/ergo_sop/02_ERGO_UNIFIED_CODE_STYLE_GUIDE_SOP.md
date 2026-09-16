# 02 — ERGO Unified Code Style Guide SOP

## Purpose
This is the Ergo-Light-local code style guide derived from the recovered tri-doctrine stack and localized into engine work.

It is not fashion guidance.
It is the operational style baseline for load-bearing Ergo-Light code.

## Intent: code should preserve engine truth
Ergo-Light code should make the engine easier to reason about, not merely easier to type.

### Cognitive conservation
Prefer:
- small explicit modules
- low-parameter functions
- bounded nesting
- names that reveal engine/domain truth
- one coherent job per function where practical

### Typed boundary law
Prefer:
- dataclasses or explicit records for owned models
- TypedDict only at unavoidable boundary surfaces
- JSON only at hard boundaries
- no anonymous dict projection smear inside core runtime paths

### Failure locality law
Errors must remain explicit and local.
Forbidden:
- silent exception swallowing
- hidden no-op failure paths
- fake success surfaces

### Substrate sovereignty law
Engine truth must live in Ergo-Light-owned boundaries and models.
Dependencies and serialization formats are consumables, not architecture.

### Verification law
Prefer machine-checkable anchors:
- tests
- schema checks
- compile checks
- deterministic readback

### Session/world/runtime consequence
### Rust-core consequence
Prefer:
- small typed modules
- constructor-established invariants
- no unwrap/expect/todo/unimplemented/dbg in promotion-grade Rust core paths
- cargo fmt/clippy/test as mandatory CSC verification anchors

Ergo-Light runtime code should prefer:
- typed session/world/registry state
- command envelopes and delta packets as explicit records
- bootstrap snapshots/indexes only where the boundary requires them
- explicit host/join/session contracts rather than informal parameter soup

## Current active anti-pattern targets
- raw JSON outside approved boundary helpers
- `Any` where explicit shapes are realistically possible
- broad exceptions without boundary justification
- too-long functions that hide multiple jobs
- dict-smear across runtime layers
- stringly-typed mode/state machines where variants are possible
