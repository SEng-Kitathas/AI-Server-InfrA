# V30 A-041 — Certificate-Transparency-Style Merkle Protocol Receipts

Date: 2026-09-06
Status: **TECHNICALLY EARNED / PENDING GIT PUBLICATION**

## Trigger
The cross-domain raid packet proposed Certificate Transparency as a mechanism quarry for the protocol ledger: compact inclusion proofs and append-consistency proofs over an append-only history.

A-037 had already established the core authority boundary:
- `system/protocol/events.jsonl` is authoritative;
- derived state is rebuildable and non-authoritative;
- full ledger verification remains a recovery/audit backstop.

A-041 therefore targets proof-carrying evidence without creating a second ledger or replacing the existing event hash chain.

## Authority model
The authoritative source remains:
`system/protocol/events.jsonl`.

Merkle material is derived from the existing ordered `event_hash` sequence after full protocol-ledger verification.

Locked law:

`MERKLE_PROJECTION != LEDGER_AUTHORITY`

and:

`VALID_HISTORICAL_PROOF != CURRENT_STATE_PROOF`.

Missing Merkle state is not an authority failure; proof material can be rebuilt from the verified ledger.

## Merkle construction
Algorithm identifier:
`PCMMAD-CT-SHA256-V1`.

Construction is RFC6962-style domain separation over the already-authoritative protocol event hashes:
- leaf: `SHA256(0x00 || event_hash_bytes)`;
- interior node: `SHA256(0x01 || left || right)`;
- empty tree root: `SHA256("")`.

Tree shape uses the largest-power-of-two split used by Certificate Transparency tree hashing.

A-041 implements:
- Merkle root derivation;
- compact inclusion proofs;
- compact append-consistency proofs;
- pure inclusion verification;
- pure consistency verification;
- derived proof receipts bound to project, tree size, root, ledger head, event identity/hash, algorithm/version, and proof material.

## Native Runtime tools
Added three read-only protocol tools:
- `protocol.merkle.root`
- `protocol.merkle.inclusion`
- `protocol.merkle.consistency`

Protocol native tool count advances 12 -> 15.

These tools are read-only and explicitly declare:
- reads state;
- verifies hash chain;
- derives Merkle root/proof;
- non-initializing behavior.

They do not mutate the ledger or persist Merkle authority.

## Currentness hostile result
The first A-041 candidate unconditionally emitted:
`current_at_issue = true`.

That claim was attacked with a deterministic temp-ledger race:
1. read ledger snapshot;
2. verify that exact event list;
3. append one additional lawful event immediately after verification;
4. allow receipt generation to complete from the older verified snapshot.

Observed:
- receipt tree size: 2;
- actual ledger tree size by return: 3;
- receipt head != actual ledger head;
- receipt still claimed `current_at_issue=true`.

Therefore the Merkle math was valid while the currentness label was false.

The shared candidate was patched only after optimistic hash guards proved no concurrent edit had occurred.

Current receipt semantics:
- `verified_ledger_snapshot = true`;
- `currentness_claim = "not_asserted"`;
- `currentness_requires_head_match = true`.

Tool descriptions likewise refer to a **verified ledger snapshot**, not a linearly-current tree.

This preserves the key distinction:

`CRYPTOGRAPHIC_VALIDITY != CURRENTNESS`.

A proof remains valid for the bound historical tree; currentness requires comparing its bound `ledger_head_hash` / tree size against current authoritative state.

## Proof compactness
Pure 20,000-leaf measurement, leaf index / old size 12,345:
- inclusion proof hash count: **15**;
- consistency proof hash count: **16**;
- in-memory inclusion generation: ~30.551 ms;
- in-memory consistency generation: ~30.303 ms.

This earns compact proof transmission, not O(log n) server issuance.

Current receipt issuance intentionally:
1. reads authoritative ledger events;
2. verifies the full protocol hash chain;
3. derives the Merkle tree/proof from verified event hashes.

Therefore current server-side issuance remains O(history) in ledger verification/tree derivation. This is acceptable for the first authority-first read surface and avoids a second persisted truth plane.

Claim ceiling:

`LOGARITHMIC_PROOF_SIZE != LOGARITHMIC_PROOF_ISSUANCE_COST`.

A future derived Merkle frontier/cache may be justified by measured read pressure, but it must remain rebuildable and currentness-bound.

## Hostile / independent checks
`tests/test_protocol_merkle.py` covers:
- inclusion verification for every leaf over unbalanced tree sizes 1..32;
- inclusion tampering and wrong-position rejection;
- consistency proof verification for every prefix over small trees;
- expected RFC6962-style proof shapes for selected seven-leaf prefixes;
- Merkle root cross-check against an independently iterative frontier construction over sizes 0..256;
- empty-tree consistency edge cases;
- historical inclusion proof remains valid only for its bound old tree;
- 20,000-leaf proof hash counts remain logarithmic;
- wrong old root, new root, and proof rejection;
- real protocol-ledger integration with root/inclusion/consistency receipts;
- authoritative-ledger tamper refusal;
- verified-read / concurrent-append race proving currentness is not asserted.

## Multi-tab concurrency scar discovered during A-041 recovery
This thread recovered while another project tab/thread was actively mutating the same repo.

Observed sequence:
- this thread had just pushed A-039 at `d887213...`;
- direct Git read later showed A-040 had independently advanced HEAD to `486eee4a...`;
- A-041 files were modified at 19:55-19:56 ET by the other writer;
- this thread had meanwhile registered A-039 post-push outer continuity, temporarily regressing the bounded Frontier below already-published A-040.

The canonical outer planes were repaired back to the exact A-040 post-push hashes before A-041 work continued.

This is direct evidence for a separate project-level coordination seam:

`THREAD_LOCAL_DISCIPLINE != PROJECT_MUTATION_EXCLUSIVITY`.

A future project mutation lease / ownership protocol should prevent two tabs from concurrently owning the same Git/continuity mutation frontier. This is **not** bundled into A-041 code.

## Verification
Initial shared A-041 candidate:
- targeted Merkle + protocol runtime: **19/19 PASS**;
- complete suite: **317 GREEN**;
- candidate hashes stable before/after both runs.

After currentness-race repair:
- targeted Merkle + protocol runtime: **20/20 PASS**;
- complete V30 suite: **318 collected tests GREEN**;
- existing conditional Windows symlink-privilege skip only;
- candidate hashes stable before/after qualification.

Current file identities:
- `baseline/pcmmad_receiver/lab_tools_protocol.py`
  - SHA-256 `a5fb00ae7fe315cd834b3fc328e26673a95a4276d7b514386c66ad9f73ff16e4`
- `baseline/pcmmad_receiver/protocol_merkle.py`
  - SHA-256 `9227dda0b661a42607e2c8d2d278a726bf4e11d7b9489724ace5a448bebdde90`
- `tests/test_protocol_runtime.py`
  - SHA-256 `51432fd3b0d444fedc3f24c2cc733a44317af46d0f2357bddbc1009e355e0926`
- `tests/test_protocol_merkle.py`
  - SHA-256 `8f7a6d37e9a4ac1dd7ce4306f74e4ccca99883c4d4766e4461ba58dabd88c669`.

## Claim ceiling / next
A-041 earns derived CT-style Merkle proof receipts over the verified protocol ledger.

It does not:
- replace or weaken the protocol hash chain;
- create persistent Merkle authority;
- make proof issuance O(log n);
- create linearizable currentness across multi-process writers;
- solve project multi-tab mutation ownership;
- add protocol/lab mutation idempotency;
- add Windows Job Object resource caps.

After A-041 Git publication, the raid queue may proceed to idempotency / Job Object resource envelope, while project-level mutation ownership should be added as a high-priority coordination seam because the race was directly observed rather than hypothetical.
