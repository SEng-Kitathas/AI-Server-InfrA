# Mutation Authority Semantic Correction

## Finding
The repeated diagnosis `ACTIVE + lease_id=null = impossible authority state` was wrong for current v2 mutation authority. `_public()` deliberately redacts the bearer token on observe/inspect/renew/release/error surfaces; only the successful acquire response discloses the newly minted bearer. Persisted ACTIVE records contain `lease_id_hash`, not plaintext lease_id. `_validate_record_shape` requires that hash for ACTIVE.

`inspect_lease()` already runs `_expire_if_needed()` under the transition guard, so current source correctly reconciles elapsed ACTIVE to EXPIRED. Live readback at 20:33Z confirmed generation 46 as EXPIRED.

Therefore: do NOT deploy a hotfix that exposes the bearer or treats redacted ACTIVE as corrupt. That would weaken security.

## Real seam
The API made redaction semantically ambiguous: `lease_id:null` looked indistinguishable from missing authority identity, and client/thread continuity can lose the one-time acquire bearer needed for renew/release. This is a client/authority-handoff usability seam, not persisted authority corruption.

## Minimal candidate correction
Public mutation records now add `lease_token_disclosed` and `authority_identity_present`. Acquire returns token + disclosed=true; ordinary observations keep token null + disclosed=false while reporting hashed authority identity present. No authority semantics changed.

## Qualification
New semantic warfort + existing project mutation authority + adaptive coordination: 24/24 PASS. A first qualification command referenced a nonexistent restart-survival filename and failed before tests; corrected command then passed.

## Next discriminator
Do not make renew tokenless. Instead compose with authenticated-principal/session work: a server-side session authority can retain/rotate the bearer binding without exposing it to generic observation, once higher-principal authentication exists. Until then, acquire bearer remains an explicit authority secret the client must preserve.

Earned laws: REDACTED AUTHORITY TOKEN != MISSING AUTHORITY IDENTITY. OBSERVABILITY SHOULD DISTINGUISH SECRET NONDISCLOSURE FROM ABSENCE. DO NOT REPAIR A SECURITY PROPERTY AS IF IT WERE CORRUPTION.
