from __future__ import annotations

import hashlib, json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

REQUIRED_ACTIVE_SURFACES = (
    "LIVE_SHADOW.md", "DESIGN_THREAD_STREAM.md", "CURRENT_STATE.md",
    "NEXT_STEPS.md", "DOCTRINE_SNAPSHOT.md", "TRACE_MATRIX.md",
    "REVISIT_LEDGER.md", "COMMANDERS_INTENT_CURRENT.md", "SERVER_THREAD_HANDOFF_CURRENT.md",
    "NEW_THREAD_HANDOFF_PROMPT_CURRENT.md", "THREAD_CONTINUITY_CHECKPOINT_2026-09-15.md",
)

@dataclass(frozen=True)
class SurfaceAuditResult:
    status: str
    manifest_updated_at: str | None
    missing: tuple[str,...]
    unmanifested: tuple[str,...]
    hash_mismatch: tuple[str,...]
    checkpoint_hash_match: bool
    mutation_authority: bool = False
    def to_dict(self) -> dict[str,Any]: return asdict(self)

def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def audit_continuity_surfaces(handoff_dir: Path, required: tuple[str,...]=REQUIRED_ACTIVE_SURFACES) -> SurfaceAuditResult:
    manifest_path=handoff_dir/"SNAPSHOT_MANIFEST_SHA256.json"
    if not manifest_path.exists():
        return SurfaceAuditResult("UNKNOWN_INCOMPLETE",None,(),("SNAPSHOT_MANIFEST_SHA256.json",),(),False)
    data=json.loads(manifest_path.read_text(encoding="utf-8")); entries=data.get("files",{})
    missing=[];unmanifested=[];mismatch=[]
    for name in required:
        p=handoff_dir/name
        if not p.exists(): missing.append(name); continue
        meta=entries.get(name)
        if not isinstance(meta,dict): unmanifested.append(name); continue
        if _sha(p)!=meta.get("sha256"): mismatch.append(name)
    cp=handoff_dir/"THREAD_CONTINUITY_CHECKPOINT_2026-09-15.md"
    checkpoint_match=bool(cp.exists() and data.get("continuity_checkpoint_sha256")==_sha(cp))
    if missing or unmanifested: status="UNKNOWN_INCOMPLETE"
    elif mismatch or not checkpoint_match: status="STALE"
    else: status="CURRENT"
    return SurfaceAuditResult(status,str(data.get("updated_at")) if data.get("updated_at") else None,tuple(missing),tuple(unmanifested),tuple(mismatch),checkpoint_match)
