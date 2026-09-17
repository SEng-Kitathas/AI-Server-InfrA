"""Plane-neutral CT-style Merkle primitives over ordered SHA-256 event hashes.

These primitives establish deterministic lineage/provenance proofs. They do not
assert external trust, signatures, hostile-storage resistance, or non-repudiation.
"""
from __future__ import annotations
import hashlib
from typing import Sequence

MERKLE_ALGORITHM = "PCMMAD-CT-SHA256-V1"
EMPTY_ROOT = hashlib.sha256(b"").digest()

def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()

def _hash_bytes(value: str) -> bytes:
    text = str(value or "").strip().lower()
    if len(text) != 64:
        raise ValueError("event/proof hash must be a 64-character SHA-256 hex digest")
    try:
        digest = bytes.fromhex(text)
    except ValueError as exc:
        raise ValueError("event/proof hash must be hexadecimal") from exc
    if len(digest) != 32:
        raise ValueError("digest must be 32 bytes")
    return digest

def merkle_leaf_hash(event_hash: str) -> bytes:
    return _sha256(b"\x00" + _hash_bytes(event_hash))

def merkle_node_hash(left: bytes, right: bytes) -> bytes:
    if len(left) != 32 or len(right) != 32:
        raise ValueError("Merkle node children must be 32-byte digests")
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
        return _inclusion_path(index, event_hashes[:k]) + [merkle_tree_hash_from_hashes(event_hashes[k:])]
    return _inclusion_path(index - k, event_hashes[k:]) + [merkle_tree_hash_from_hashes(event_hashes[:k])]

def inclusion_proof_hex(index: int, event_hashes: Sequence[str]) -> list[str]:
    return [item.hex() for item in _inclusion_path(index, event_hashes)]

def verify_inclusion_proof(*, event_hash: str, leaf_index: int, tree_size: int, proof: Sequence[str], expected_root: str) -> bool:
    if tree_size <= 0 or leaf_index < 0 or leaf_index >= tree_size:
        return False
    try:
        fn = leaf_index
        sn = tree_size - 1
        value = merkle_leaf_hash(event_hash)
        expected = _hash_bytes(expected_root)
        for item in proof:
            sibling = _hash_bytes(str(item))
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

def _consistency_subproof(old_size: int, event_hashes: Sequence[str], include_old_root: bool) -> list[bytes]:
    n = len(event_hashes)
    if old_size <= 0 or old_size > n:
        raise ValueError("old_size must satisfy 1 <= old_size <= tree_size")
    if old_size == n:
        return [] if include_old_root else [merkle_tree_hash_from_hashes(event_hashes)]
    k = _largest_power_of_two_less_than(n)
    if old_size <= k:
        return _consistency_subproof(old_size, event_hashes[:k], include_old_root) + [merkle_tree_hash_from_hashes(event_hashes[k:])]
    return _consistency_subproof(old_size - k, event_hashes[k:], False) + [merkle_tree_hash_from_hashes(event_hashes[:k])]

def consistency_proof_hex(old_size: int, event_hashes: Sequence[str]) -> list[str]:
    n = len(event_hashes)
    if old_size < 0 or old_size > n:
        raise ValueError("old_size must satisfy 0 <= old_size <= tree_size")
    if old_size in {0, n}:
        return []
    return [item.hex() for item in _consistency_subproof(old_size, event_hashes, True)]

def verify_consistency_proof(*, old_size: int, new_size: int, old_root: str, new_root: str, proof: Sequence[str]) -> bool:
    if old_size < 0 or new_size < 0 or old_size > new_size:
        return False
    try:
        old_b = _hash_bytes(old_root)
        new_b = _hash_bytes(new_root)
    except (TypeError, ValueError):
        return False
    if old_size == 0:
        if old_b != EMPTY_ROOT or len(proof) != 0:
            return False
        return new_b == EMPTY_ROOT if new_size == 0 else True
    if old_size == new_size:
        return len(proof) == 0 and old_b == new_b
    try:
        fn = old_size - 1
        sn = new_size - 1
        while (fn & 1) == 1:
            fn >>= 1
            sn >>= 1
        material = [_hash_bytes(str(item)) for item in proof]
        if fn == 0:
            fr = old_b
            sr = fr
        else:
            if not material:
                return False
            fr = material[0]
            sr = material[0]
            material = material[1:]
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
        return sn == 0 and fr == old_b and sr == new_b
    except (TypeError, ValueError):
        return False
