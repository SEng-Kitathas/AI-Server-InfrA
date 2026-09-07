# A-042 Engineering Qualification — 2026-09-07

State: **QUALIFIED ENGINEERING CANDIDATE / PUBLICATION PENDING**

## Git baseline
- pre-publication HEAD/remote: `014dc68c954ab099c43118bd5072349fb93385d3`
- last engineering feature: A-041 `a97a00f67f3b79dbbe18e092d29b8971e588d4a2`

## Candidate seal
- files: 23 changed/new
- inventory SHA-256: `e2dcb52475bf5869b6f3ebc4561955e27ef52669291bb7e06aa96ca196b2f31e`
- changed/new Python: 22 / py_compile PASS
- compact schema: JSON PASS / 30 operations / `runtime-authority-envelope-v1`
- CRLF-aware `git diff --check`: PASS
- complete suite: `345 collected / 344 passed / 0 failed / 1 conditional skip`

## Contract survivors
- `SESSION_IDENTITY != FENCED_MUTATION_AUTHORITY`
- `LEASE_STATE_LOCK != MUTATION_CONSEQUENCE_LOCK`
- `NO AUTHORITY SMUGGLING THROUGH CAPABILITY ARGUMENTS`
- approval authority and project-mutation fencing are independent Runtime authority dimensions
- already-authorized expired same-generation Runtime follow-on may finish only before takeover; post-takeover generation is fenced

## Cross-thread convergence
The non-PCMMAD `OBE_V30_HANDOFF_BUNDLE_2026-09-06.zip` bundle is donor evidence only. A-001 is queued post-publication. Final schema redesign remains last and untriggered.

## Claim ceiling
This receipt qualifies the candidate bytes observed before Git commit. It is not a Git publication receipt and not a live Runtime promotion receipt. Commit/push/remote readback must independently confirm publication.
