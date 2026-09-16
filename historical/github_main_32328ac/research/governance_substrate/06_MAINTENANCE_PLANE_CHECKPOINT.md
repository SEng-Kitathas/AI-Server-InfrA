# Maintenance Plane Checkpoint

## Trigger scar
Generation 34 persisted ACTIVE with lease_id=null after the client lost/failed to preserve the bearer token. Normal renew/release could not operate it; acquire remained blocked until expiry. At 02:40Z normal acquire lawfully advanced to generation 35 after expiry.

## Earned laws
- NORMAL SECURITY MUST NOT MAKE THE SYSTEM UNREPAIRABLE.
- AUTHORITY STATUS != AUTHORITY USABILITY.
- ACTIVE AUTHORITY MUST BE OPERABLE OR LAWFULLY RECONCILABLE.
- REPAIR IMPOSSIBLE AUTHORITY; DO NOT INVENT MISSING AUTHORITY.
- MAINTENANCE AUTHORITY != PROJECT MUTATION AUTHORITY.

## Candidate embodiment
Separate bounded maintenance authority with independent generation/token/operator/reason/expiry/integrity; maintenance.status/acquire/release; authority.reconcile only for recognized ACTIVE+null-lease impossible state; canonical target path binding; generation preservation; append-only before/after receipt; refusal to rewrite healthy authority.

## Qualification
Maintenance focused 6/6 PASS. Combined maintenance/agent-contract/qualification-lifecycle 35/35 PASS. Full suite PASS with normal 2 skips; compileall and diff-check PASS. Candidate catalog 175. Effect profile rebuilt/current: 175 capabilities, 3 effect-truth/parallel/resume witnesses.

## Evidence ceiling / next discriminator
This maintenance plane still lives inside the receiver source. It solves repair while receiver routing/execution is alive, but does not yet satisfy the stronger out-of-process repair requirement when the receiver itself cannot start. Next architectural discriminator: extract the minimal authority reconciliation/service lifecycle subset into the existing out-of-process supervisor without duplicating authority semantics.
