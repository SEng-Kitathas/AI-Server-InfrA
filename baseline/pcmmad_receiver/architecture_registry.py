from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .protocol_models import ProtocolEventKind
from .protocol_store import read_events

JsonObject = dict[str, Any]


@dataclass(frozen=True)
class ArtifactRegistryDeps:
    resolve_target: Any
    commits_ledger_path_for: Any
    sha256_file: Any


def _lineage(project_id: str, artifact_class: str, logical_name: str, dep: ArtifactRegistryDeps) -> list[JsonObject]:
    path = dep.commits_ledger_path_for(project_id)
    rows: list[JsonObject] = []
    if not path.is_file():
        return rows
    import json
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("artifact_class") == artifact_class and row.get("logical_name") == logical_name:
            rows.append(row)
    return rows


def _protocol_rows(project_id: str, path_rel: str) -> list[JsonObject]:
    rows: list[JsonObject] = []
    for event in read_events(project_id):
        if event.event_kind is not ProtocolEventKind.ARTIFACT_REGISTERED:
            continue
        if str(event.payload.get("path") or "").replace("\\", "/") != path_rel.replace("\\", "/"):
            continue
        rows.append({
            "sequence": event.sequence,
            "artifact_id": event.payload.get("artifact_id"),
            "artifact_class": event.payload.get("artifact_class"),
            "sha256": event.payload.get("sha256"),
            "time": event.time,
        })
    return rows


def inspect_artifact(project_id: str, artifact_class: str, logical_name: str, dep: ArtifactRegistryDeps) -> JsonObject:
    target = dep.resolve_target(project_id, artifact_class, logical_name)
    exists = target.is_file()
    current_sha = dep.sha256_file(target) if exists else None
    lineage = _lineage(project_id, artifact_class, logical_name, dep)
    latest_lineage = lineage[-1] if lineage else None
    latest_registered_sha = latest_lineage.get("sha256") if latest_lineage else None
    try:
        project_root = target.parents[0]
        # resolve_target paths are always under the project root; protocol paths are canonical relative strings.
        from .shared_core import get_project_root
        project_root = get_project_root(project_id).resolve()
        rel = str(target.resolve().relative_to(project_root)).replace("\\", "/")
    except Exception:
        rel = logical_name.replace("\\", "/")
    protocol = _protocol_rows(project_id, rel)
    protocol_current = [row for row in protocol if row.get("sha256") == current_sha]
    protocol_classes = sorted({str(row.get("artifact_class")) for row in protocol if row.get("artifact_class")})

    if not exists:
        status = "MISSING"
    elif latest_registered_sha is None:
        status = "LOCAL_UNREGISTERED"
    elif latest_registered_sha != current_sha:
        status = "LINEAGE_STALE"
    else:
        status = "CURRENT"

    repairs: list[str] = []
    if status in {"LOCAL_UNREGISTERED", "LINEAGE_STALE"}:
        repairs.append("continuity.artifact.adopt")
    if protocol and not protocol_current:
        repairs.append("protocol.artifact.register")

    return {
        "schema": "pcmmad.architecture-artifact-registry.v1",
        "project_id": project_id,
        "artifact": {"artifact_class": artifact_class, "logical_name": logical_name, "path": str(target), "relative_path": rel},
        "authority": {"file_bytes": "filesystem", "lineage": "commit_ledger", "protocol": "protocol_event_ledger"},
        "filesystem": {"exists": exists, "sha256": current_sha, "bytes": target.stat().st_size if exists else None},
        "lineage": {
            "depth": len(lineage),
            "generation": int(latest_lineage.get("generation") or len(lineage)) if latest_lineage else 0,
            "latest_registered_sha256": latest_registered_sha,
            "current": bool(current_sha is not None and latest_registered_sha == current_sha),
        },
        "protocol": {
            "registrations": len(protocol),
            "classes": protocol_classes,
            "latest_sequence": protocol[-1]["sequence"] if protocol else None,
            "current_registration_sequences": [row["sequence"] for row in protocol_current],
            "current": bool(protocol_current) if protocol else None,
        },
        "status": status,
        "repair_capabilities": repairs,
    }
