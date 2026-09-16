# Maintenance / Agent-Server Warfort Campaign

Standing rule: choose the sharpest discriminator at every branch. OARR attacks mechanisms and interactions, not only code. Local clone is sacrificial sandbox.

## W1 — Can maintenance survive receiver unavailability without duplicating authority semantics?
NARROW PASS. `tools/pcmmad_maintenance_supervisor.py` is an out-of-process CLI importing the exact same `maintenance_plane` module. It has no subprocess/shell/arbitrary file-write implementation and requires explicit operator/reason/token/generation. Process-level suite 4/4; combined maintenance 10/10.

Evidence ceiling: this proves independence from receiver HTTP/router process, not yet independence from the receiver Python package/source tree. If package/source corruption prevents importing `maintenance_plane`, supervisor also fails.

## W2 — Fresh agent <-> candidate server protocol emulation
Candidate catalog 175. Fresh explicit orient over 9 mixed capabilities returned all 9; zero opaque schemas; lease survived JSON round-trip; returned contract digests matched registry; stale contract failed closed; maintenance.status dispatched successfully. PASS.

Scar: first stale-contract assertion expected wording containing STALE/digest, but actual structured semantic surfaced as `capability contract changed after client discovery`. Harness was too text-specific; expectation was corrected to the existing semantic, not server behavior.

## Sharpest next discriminator
Kill/corrupt the receiver import path itself in a sacrificial copied environment while leaving only the maintenance supervisor bundle. If maintenance still depends on importing receiver package internals, it is not a true repair root. Derive the minimum sealed maintenance core shared by receiver and supervisor without code duplication: a tiny dependency-light module/package whose identity/hash is verified by both. Then attack version skew: receiver maintenance wrapper at version N, supervisor core at N-1/N+1 must fail compatibility rather than silently repair with mismatched semantics.

## W3 — Receiver package/source loss attack
FAIL as predicted by the evidence ceiling. Copying only the supervisor CLI into an isolated temp directory and invoking `--help` fails immediately with `ModuleNotFoundError: pcmmad_receiver`. Therefore out-of-process != independent repair root. The current supervisor is only HTTP/router-independent.

Earned invariant: OUT-OF-PROCESS != OUT-OF-FAILURE-DOMAIN. A repair root must not share the import/package failure domain of the component it repairs.

Next: derive a sealed dependency-light maintenance core/bundle with no receiver-package imports, and make both receiver wrapper and supervisor consume that same core identity. Version/hash skew must fail closed.
