# Git Handoff Qualification — Current Candidate

Date: 2026-09-05
Status: QUALIFIED PRE-COMMIT CANDIDATE

## Purpose
Qualify the repository-contained ICF-CS recovery bundle before Git publication.

## Evidence
- handoff invariant regression: `tests/test_git_handoff_current.py`
- focused result: **6 / 6 PASS**
- full V30 suite after adding handoff bundle/test: **251 collected tests GREEN**
- existing conditional Windows symlink-privilege skip remains the only skip
- secret-like scan over `CURRENT_INGRESS.md`, `handoff/current/`, and updated Commander source: **NO SECRET-LIKE HITS**

## Handoff guarantees exercised
- snapshot manifest hashes every declared member
- required ICF authority/Frontier/Constraints/History surfaces are present
- root ingress uses qualified version-agnostic cold-start and conflict grammar
- Runtime↔OBE/Skills cross-thread meeting surfaces exist
- transport/runtime/Skill authority boundaries remain explicit
- long-running model-attention prohibition remains explicit
- snapshot claims recovery-mirror status, not live Runtime authority

## Claim ceiling
This proves the handoff bundle and test suite on the current pre-commit working-tree bytes. Git publication is not complete until commit, push, and independent remote-head readback succeed.

`GIT_PUBLICATION != LIVE_RUNTIME_PROMOTION`
`CURRENT_INGRESS_POINTER != CURRENT_STATE_PROOF`
