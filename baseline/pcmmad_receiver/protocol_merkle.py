"""Derived CT-style Merkle proofs for the authoritative PCMMAD protocol ledger.

The JSONL protocol ledger remains authoritative.  This module derives ordered
Merkle roots and compact inclusion/append-consistency proofs from the existing
event_hash sequence.  Missing derived proof state is never authority failure:
proof material can always be rebuilt from verified ledger events.
"""

from __future__ import annotations

import hashlib
from typing import Any, Iterable, Sequence

from protocol_models import ProtocolEvent
from protocol_store import ProtocolLedgerError, read_events, verify_events

MERKLE_ALGORITHM = "PCMMAD-CT-SHA256-V1"
EMPTY_ROOT = hashlib.sha256(b"").digest()


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def _event_hash_bytes(event_hash: str) -> bytes:
    text = str(event_hash or "").strip().lower()
    if len(text) != 64:
        raise ValueError("event_hash must be a 64-character SHA-256 hex digest")
    try:
        return bytes.fromhex(text)
    except ValueError as exc:
        raise ValueError("event_hash must be hexadecimal") from exc


def _digest_hex_bytes(value: str) -> bytes:
    text = str(value or "").strip().lower()
    if len(text) != 64:
        raise ValueError("Merkle root/proof digest must be a 64-character SHA-256 hex digest")
    try:
        digest = bytes.fromhex(text)
    except ValueError as exc:
        raise ValueError("Merkle root/proof digest must be hexadecimal") from exc
    if len(digest) != 32:
        raise ValueError("Merkle digest must be 32 bytes")
    return digest


def merkle_leaf_hash(event_hash: str) -> bytes:
    """RFC6962-style domain-separated leaf over the existing event hash."""
    return _sha256(b"\x00" + _event_hash_bytes(event_hash))


def merkle_node_hash(left: bytes, right: bytes) -> bytes:
    if len(left) != 32 or len(right) != 32:
        raise ValueError("Merkle node children must be 32-byte SHA-256 digests")
    return _sha256(b"\x01" + left + right)


def _largest_power_of_two_less_than(n: int) -> int:
    if n < 2:
        raise ValueError("n must be >= 2")
    return 1 << ((n - 1).bit_length() - 1)


def merkle_tree_hash_from_hashes(event_hashes: Sequence[str]) -> bytes:
    n = len(event_hashes)
    if n == 0:
        return EMPTY_ROOT
    if n == 1:
        return merkle_leaf_hash(event_hashes[0])
    k = _largest_power_of_two_less_than(n)
    return merkle_node_hash(
        merkle_tree_hash_from_hashes(event_hashes[:k]),
        merkle_tree_hash_from_hashes(event_hashes[k:]),
    )


def merkle_root_hex(event_hashes: Sequence[str]) -> str:
    return merkle_tree_hash_from_hashes(event_hashes).hex()


def _inclusion_path(index: int, event_hashes: Sequence[str]) -> list[bytes]:
    n = len(event_hashes)
    if index < 0 or index >= n:
        raise IndexError("leaf index out of range")
    if n == 1:
        return []
    k = _largest_power_of_two_less_than(n)
    if index < k:
        return _inclusion_path(index, event_hashes[:k]) + [
            merkle_tree_hash_from_hashes(event_hashes[k:])
        ]
    return _inclusion_path(index - k, event_hashes[k:]) + [
        merkle_tree_hash_from_hashes(event_hashes[:k])
    ]


def inclusion_proof_hex(index: int, event_hashes: Sequence[str]) -> list[str]:
    return [item.hex() for item in _inclusion_path(index, event_hashes)]


def verify_inclusion_proof(
    *,
    event_hash: str,
    leaf_index: int,
    tree_size: int,
    proof: Sequence[str],
    expected_root: str,
) -> bool:
    if tree_size <= 0 or leaf_index < 0 or leaf_index >= tree_size:
        return False
    try:
        fn = leaf_index
        sn = tree_size - 1
        value = merkle_leaf_hash(event_hash)
        expected = _digest_hex_bytes(expected_root)
        for item in proof:
            sibling = _digest_hex_bytes(str(item))
            if (fn & 1) == 1 or fn == sn:
                value = merkle_node_hash(sibling, value)
                while fn != 0 and (fn & 1) == 0:
                    fn >>= 1
                    sn >>= 1
            else:
                value = merkle_node_hash(value, sibling)
            fn >>= 1
            sn >>= 1
        return sn == 0 and value == expected
    except (TypeError, ValueError):
        return False


def _consistency_subproof(
    old_size: int, event_hashes: Sequence[str], include_old_root: bool
) -> list[bytes]:
    n = len(event_hashes)
    if old_size <= 0 or old_size > n:
        raise ValueError("old_size must satisfy 1 <= old_size <= tree_size")
    if old_size == n:
        return [] if include_old_root else [merkle_tree_hash_from_hashes(event_hashes)]
    k = _largest_power_of_two_less_than(n)
    if old_size <= k:
        return _consistency_subproof(old_size, event_hashes[:k], include_old_root) + [
            merkle_tree_hash_from_hashes(event_hashes[k:])
        ]
    return _consistency_subproof(old_size - k, event_hashes[k:], False) + [
        merkle_tree_hash_from_hashes(event_hashes[:k])
    ]


def consistency_proof_hex(old_size: int, event_hashes: Sequence[str]) -> list[str]:
    n = len(event_hashes)
    if old_size < 0 or old_size > n:
        raise ValueError("old_size must satisfy 0 <= old_size <= tree_size")
    if old_size in {0, n}:
        return []
    return [item.hex() for item in _consistency_subproof(old_size, event_hashes, True)]


def verify_consistency_proof(
    *,
    old_size: int,
    new_size: int,
    old_root: str,
    new_root: str,
    proof: Sequence[str],
) -> bool:
    if old_size < 0 or new_size < 0 or old_size > new_size:
        return False
    try:
        old_root_bytes = _digest_hex_bytes(old_root)
        new_root_bytes = _digest_hex_bytes(new_root)
    except (TypeError, ValueError):
        return False
    old_root = old_root_bytes.hex()
    new_root = new_root_bytes.hex()
    if old_size == 0:
        if old_root_bytes != EMPTY_ROOT or len(proof) != 0:
            return False
        if new_size == 0:
            return new_root_bytes == EMPTY_ROOT
        # The empty tree is a prefix of every non-empty tree.  A zero-length
        # consistency proof cannot independently authenticate the new root; it
        # only proves the empty-prefix relation, so root syntax is the remaining
        # verifier obligation here.
        return True
    if old_size == new_size:
        return len(proof) == 0 and old_root_bytes == new_root_bytes
    try:
        fn = old_size - 1
        sn = new_size - 1
        while (fn & 1) == 1:
            fn >>= 1
            sn >>= 1

        material = [_digest_hex_bytes(str(item)) for item in proof]

        if fn == 0:
            fr = bytes.fromhex(old_root)
            sr = fr
        else:
            if not material:
                return False
            fr = material[0]
            sr = material[0]
            material = material[1:]

        if len(fr) != 32:
            return False

        for sibling in material:
            if sn == 0:
                return False
            if (fn & 1) == 1 or fn == sn:
                fr = merkle_node_hash(sibling, fr)
                sr = merkle_node_hash(sibling, sr)
                while fn != 0 and (fn & 1) == 0:
                    fn >>= 1
                    sn >>= 1
            else:
                sr = merkle_node_hash(sr, sibling)
            fn >>= 1
            sn >>= 1

        return sn == 0 and fr.hex() == old_root and sr.hex() == new_root
    except (TypeError, ValueError):
        return False


def _verified_events(project_id: str) -> list[ProtocolEvent]:
    events = read_events(project_id)
    verification = verify_events(project_id, events)
    if not verification["ok"]:
        raise ProtocolLedgerError(
            f"protocol ledger failed verification: {verification['failures']}"
        )
    return events


def merkle_root_receipt(project_id: str) -> dict[str, Any]:
    events = _verified_events(project_id)
    hashes = [event.event_hash for event in events]
    return {
        "ok": True,
        "receipt_type": "protocol_merkle_root",
        "project_id": project_id,
        "algorithm": MERKLE_ALGORITHM,
        "tree_size": len(events),
        "root_hash": merkle_root_hex(hashes),
        "ledger_head_hash": events[-1].event_hash if events else None,
        "verified_ledger_snapshot": True,
        "currentness_claim": "not_asserted",
        "currentness_requires_head_match": True,
        "authoritative_source": "system/protocol/events.jsonl",
        "projection_authority": "derived_rebuildable",
    }


def merkle_inclusion_receipt(project_id: str, sequence: int) -> dict[str, Any]:
    events = _verified_events(project_id)
    if sequence < 1 or sequence > len(events):
        raise ValueError(f"sequence must be between 1 and {len(events)}")
    hashes = [event.event_hash for event in events]
    event = events[sequence - 1]
    root = merkle_root_hex(hashes)
    proof = inclusion_proof_hex(sequence - 1, hashes)
    return {
        "ok": True,
        "receipt_type": "protocol_merkle_inclusion",
        "project_id": project_id,
        "algorithm": MERKLE_ALGORITHM,
        "tree_size": len(events),
        "root_hash": root,
        "ledger_head_hash": events[-1].event_hash if events else None,
        "sequence": sequence,
        "leaf_index": sequence - 1,
        "event_id": event.event_id,
        "event_hash": event.event_hash,
        "proof": proof,
        "proof_hash_count": len(proof),
        "verified": verify_inclusion_proof(
            event_hash=event.event_hash,
            leaf_index=sequence - 1,
            tree_size=len(events),
            proof=proof,
            expected_root=root,
        ),
        "verified_ledger_snapshot": True,
        "currentness_claim": "not_asserted",
        "currentness_requires_head_match": True,
        "authoritative_source": "system/protocol/events.jsonl",
        "projection_authority": "derived_rebuildable",
    }


def merkle_consistency_receipt(project_id: str, old_size: int) -> dict[str, Any]:
    events = _verified_events(project_id)
    new_size = len(events)
    if old_size < 0 or old_size > new_size:
        raise ValueError(f"old_size must be between 0 and {new_size}")
    hashes = [event.event_hash for event in events]
    old_root = merkle_root_hex(hashes[:old_size])
    new_root = merkle_root_hex(hashes)
    proof = consistency_proof_hex(old_size, hashes)
    return {
        "ok": True,
        "receipt_type": "protocol_merkle_consistency",
        "project_id": project_id,
        "algorithm": MERKLE_ALGORITHM,
        "old_tree_size": old_size,
        "old_root_hash": old_root,
        "new_tree_size": new_size,
        "new_root_hash": new_root,
        "ledger_head_hash": events[-1].event_hash if events else None,
        "proof": proof,
        "proof_hash_count": len(proof),
        "verified": verify_consistency_proof(
            old_size=old_size,
            new_size=new_size,
            old_root=old_root,
            new_root=new_root,
            proof=proof,
        ),
        "verified_ledger_snapshot": True,
        "currentness_claim": "not_asserted",
        "currentness_requires_head_match": True,
        "authoritative_source": "system/protocol/events.jsonl",
        "projection_authority": "derived_rebuildable",
    }
