# Append-Only Protocol
_Version: 2026-03-31k_

## Purpose
This file defines how the corpus SHALL emulate append-only behavior.
Its lab function is to preserve history.
Its control function is to make silent rewriting feel structurally wrong.

## Core rule
The corpus SHALL be treated as append-only in spirit and in workflow.

This means:
- existing sealed artifacts SHALL NOT be silently rewritten
- new discoveries SHOULD be appended as new artifacts
- changed interpretations SHALL be recorded as supersession, replay, demotion, or maintenance entries
- provenance files SHALL be regenerated after any intentional corpus update

## Allowed mutation
Direct mutation MAY occur during active drafting before a package is sealed.

Once a package is sealed:
- change by addition when possible
- if replacement is unavoidable, record:
  - what changed
  - why it changed
  - what prior artifact it supersedes
  - what risk the replacement introduces

## Minimum append-only discipline
1. Add a new artifact or note rather than deleting an old one
   - alphanumeric insertion points MAY be used when a new control artifact must sit between two existing traversal nodes
2. Update the trace matrix / revisit ledger / maintenance note as needed
3. If footer metadata changed, update the file tail and the ledger's `default_read_next_file` field together
4. Recompute `manifest-sha256.txt`
5. Recompute `92 CORPUS_CHAIN_LEDGER.csv`
6. Recompute `93 CORPUS_MERKLE_ROOT.txt`
7. Record the package version bump

## SHALL NOT rules
- SHALL NOT silently rewrite baseline doctrine
- SHALL NOT silently rewrite evidence history
- SHALL NOT silently remove contradictions from the record
- SHALL NOT treat a new summary as permission to erase prior uncertainty

## Honesty clause
This archive does not create magical immutability.
It creates disciplined provenance pressure.
Trustworthiness depends on whether the operator and model obey the protocol.

---
## Provenance tail
- Artifact ID: `90 SHALL_READ_APPEND_ONLY_PROTOCOL_BEFORE_MUTATING_CORPUS.md`
- Artifact class: `append_only_protocol`
- Authority scope: `mutation discipline and append-only behavior`
- Default read-next file: `91 SHALL_VERIFY_CHAIN_LEDGER_BEFORE_TRUSTING_CORPUS.md`
- Verify with: `91 SHALL_VERIFY_CHAIN_LEDGER_BEFORE_TRUSTING_CORPUS.md`, `92 CORPUS_CHAIN_LEDGER.csv`, `93 CORPUS_MERKLE_ROOT.txt`
- Mutation rule: `visible replacement + version bump + provenance regeneration`
- This artifact SHALL NOT be treated as authoritative in isolation.
