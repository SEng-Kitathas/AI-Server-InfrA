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

from merkle_primitives import (
    MERKLE_ALGORITHM,
    EMPTY_ROOT,
    consistency_proof_hex,
    inclusion_proof_hex,
    merkle_leaf_hash,
    merkle_node_hash,
    merkle_root_hex,
    merkle_tree_hash_from_hashes,
    verify_consistency_proof,
    verify_inclusion_proof,
)

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
