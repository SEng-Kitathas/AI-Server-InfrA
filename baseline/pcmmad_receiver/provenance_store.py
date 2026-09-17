"""Authoritative project provenance ledger and derived Merkle receipts.

PROVENANCE MERKLE != CRYPTOGRAPHIC TRUST. This ledger establishes deterministic
recorded lineage inside project state; it does not provide signatures, external
timestamp authority, non-repudiation, or hostile-storage guarantees.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any
from merkle_primitives import MERKLE_ALGORITHM, consistency_proof_hex, inclusion_proof_hex, merkle_root_hex, verify_consistency_proof, verify_inclusion_proof
from shared_core import append_jsonl, get_project_root, utc_now

SCHEMA = "pcmmad.project-provenance.v1"

def provenance_path_for(project_id: str, *, project_root: Path | None = None) -> Path:
    root = project_root if project_root is not None else get_project_root(project_id)
    return root / "system" / "provenance" / "events.jsonl"

def _canonical(obj: dict[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def _event_hash(payload: dict[str, Any]) -> str:
    body = dict(payload)
    body.pop("event_hash", None)
    return hashlib.sha256(_canonical(body)).hexdigest()

def read_events(project_id: str, *, project_root: Path | None = None) -> list[dict[str, Any]]:
    path = provenance_path_for(project_id, project_root=project_root)
    if not path.exists():
        return []
    events = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        raw = json.loads(line)
        if not isinstance(raw, dict):
            raise ValueError(f"provenance event {line_number} is not an object")
        events.append(raw)
    return events

def verify_events(project_id: str, events: list[dict[str, Any]] | None = None, *, project_root: Path | None = None) -> dict[str, Any]:
    events = read_events(project_id, project_root=project_root) if events is None else events
    failures = []
    previous_project = None
    surface_heads: dict[str, tuple[int, str]] = {}
    for index, event in enumerate(events, 1):
        surface_id = str(event.get("surface_id") or "")
        prior_sequence, prior_hash = surface_heads.get(surface_id, (0, ""))
        expected_surface_sequence = prior_sequence + 1
        expected_surface_previous = prior_hash or None
        checks = [
            (event.get("schema") == SCHEMA, "schema"),
            (event.get("project_sequence") == index, "project_sequence"),
            (event.get("previous_project_event_hash") == previous_project, "previous_project_event_hash"),
            (event.get("surface_sequence") == expected_surface_sequence, "surface_sequence"),
            (event.get("previous_surface_event_hash") == expected_surface_previous, "previous_surface_event_hash"),
            (event.get("event_hash") == _event_hash(event), "event_hash"),
        ]
        bad = [name for ok, name in checks if not ok]
        if bad:
            failures.append({"project_sequence": index, "failures": bad})
            continue
        previous_project = str(event["event_hash"])
        surface_heads[surface_id] = (expected_surface_sequence, previous_project)
    return {
        "ok": not failures,
        "project_id": project_id,
        "event_count": len(events),
        "project_head_hash": previous_project,
        "surface_heads": {k: {"surface_sequence": v[0], "event_hash": v[1]} for k, v in surface_heads.items()},
        "failures": failures,
    }

def find_event(project_id: str, *, commit_id: str | None = None, idempotency_key: str | None = None, project_root: Path | None = None) -> dict[str, Any] | None:
    for event in read_events(project_id, project_root=project_root):
        if commit_id and event.get("commit_id") == commit_id:
            return event
        if idempotency_key and event.get("idempotency_key") == idempotency_key:
            return event
    return None

def append_event(*, project_id: str, artifact_class: str, logical_name: str, operation: str, before_sha256: str | None, after_sha256: str, bytes_before: int | None, bytes_after: int, commit_id: str, idempotency_key: str, session_id: str, mutation_generation: int | None = None, project_root: Path | None = None) -> dict[str, Any]:
    existing = find_event(project_id, commit_id=commit_id, project_root=project_root)
    if existing is not None:
        if existing.get("idempotency_key") != idempotency_key or existing.get("after_sha256") != after_sha256:
            raise ValueError("provenance commit_id conflict")
        return existing
    events = read_events(project_id, project_root=project_root)
    verification = verify_events(project_id, events, project_root=project_root)
    if not verification["ok"]:
        raise ValueError(f"provenance ledger failed verification: {verification['failures']}")
    surface_id = f"{artifact_class}:{logical_name}"
    prior_surface = [event for event in events if event.get("surface_id") == surface_id]
    event = {
        "schema": SCHEMA,
        "project_id": project_id,
        "project_sequence": len(events) + 1,
        "surface_id": surface_id,
        "surface_sequence": len(prior_surface) + 1,
        "artifact_class": artifact_class,
        "logical_name": logical_name,
        "operation": operation,
        "before_sha256": before_sha256,
        "after_sha256": after_sha256,
        "bytes_before": bytes_before,
        "bytes_after": bytes_after,
        "previous_project_event_hash": events[-1]["event_hash"] if events else None,
        "previous_surface_event_hash": prior_surface[-1]["event_hash"] if prior_surface else None,
        "commit_id": commit_id,
        "idempotency_key": idempotency_key,
        "session_id": session_id,
        "mutation_generation": mutation_generation,
        "recorded_at": utc_now(),
    }
    event["event_hash"] = _event_hash(event)
    append_jsonl(provenance_path_for(project_id, project_root=project_root), event)
    return event

def project_root_receipt(project_id: str) -> dict[str, Any]:
    events = read_events(project_id)
    verification = verify_events(project_id, events)
    if not verification["ok"]:
        raise ValueError(f"provenance ledger failed verification: {verification['failures']}")
    hashes = [str(event["event_hash"]) for event in events]
    return {"ok": True, "receipt_type": "project_provenance_root", "project_id": project_id, "algorithm": MERKLE_ALGORITHM, "tree_size": len(events), "root_hash": merkle_root_hex(hashes), "ledger_head_hash": hashes[-1] if hashes else None, "verified_ledger_snapshot": True, "authoritative_source": "system/provenance/events.jsonl", "trust_claim": "recorded_lineage_only"}

def surface_root_receipt(project_id: str, surface_id: str) -> dict[str, Any]:
    events = read_events(project_id)
    verification = verify_events(project_id, events)
    if not verification["ok"]:
        raise ValueError(f"provenance ledger failed verification: {verification['failures']}")
    chosen = [event for event in events if event.get("surface_id") == surface_id]
    hashes = [str(event["event_hash"]) for event in chosen]
    return {"ok": True, "receipt_type": "surface_provenance_root", "project_id": project_id, "surface_id": surface_id, "algorithm": MERKLE_ALGORITHM, "tree_size": len(chosen), "root_hash": merkle_root_hex(hashes), "surface_head_hash": hashes[-1] if hashes else None, "verified_ledger_snapshot": True, "trust_claim": "recorded_lineage_only"}

def inclusion_receipt(project_id: str, project_sequence: int) -> dict[str, Any]:
    events = read_events(project_id)
    verification = verify_events(project_id, events)
    if not verification["ok"]:
        raise ValueError(f"provenance ledger failed verification: {verification['failures']}")
    if project_sequence < 1 or project_sequence > len(events):
        raise ValueError("project_sequence out of range")
    hashes = [str(event["event_hash"]) for event in events]
    event = events[project_sequence - 1]
    root = merkle_root_hex(hashes)
    proof = inclusion_proof_hex(project_sequence - 1, hashes)
    return {"ok": True, "receipt_type": "project_provenance_inclusion", "project_id": project_id, "project_sequence": project_sequence, "event_hash": event["event_hash"], "tree_size": len(events), "root_hash": root, "proof": proof, "verified": verify_inclusion_proof(event_hash=event["event_hash"], leaf_index=project_sequence - 1, tree_size=len(events), proof=proof, expected_root=root)}

def consistency_receipt(project_id: str, old_tree_size: int) -> dict[str, Any]:
    events = read_events(project_id)
    verification = verify_events(project_id, events)
    if not verification["ok"]:
        raise ValueError(f"provenance ledger failed verification: {verification['failures']}")
    hashes = [str(event["event_hash"]) for event in events]
    new_size = len(hashes)
    if old_tree_size < 0 or old_tree_size > new_size:
        raise ValueError("old_tree_size out of range")
    old_root = merkle_root_hex(hashes[:old_tree_size])
    new_root = merkle_root_hex(hashes)
    proof = consistency_proof_hex(old_tree_size, hashes)
    return {"ok": True, "receipt_type": "project_provenance_consistency", "project_id": project_id, "old_tree_size": old_tree_size, "new_tree_size": new_size, "old_root_hash": old_root, "new_root_hash": new_root, "proof": proof, "verified": verify_consistency_proof(old_size=old_tree_size, new_size=new_size, old_root=old_root, new_root=new_root, proof=proof)}
