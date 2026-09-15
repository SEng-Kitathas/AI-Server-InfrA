from __future__ import annotations
import hashlib,json,tempfile
from pathlib import Path
from mvf_resident.surfaces import audit_continuity_surfaces, REQUIRED_ACTIVE_SURFACES

def _build(root: Path):
    files={}
    for n in REQUIRED_ACTIVE_SURFACES:
        p=root/n;p.write_text(n,encoding='utf-8');b=p.read_bytes();files[n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    cp=files['THREAD_CONTINUITY_CHECKPOINT_2026-09-15.md']['sha256']
    (root/'SNAPSHOT_MANIFEST_SHA256.json').write_text(json.dumps({'updated_at':'2026-09-15T00:00:00+00:00','continuity_checkpoint_sha256':cp,'files':files}),encoding='utf-8')

def test_surface_audit_current_when_manifest_matches():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);_build(root);r=audit_continuity_surfaces(root);assert r.status=='CURRENT';assert r.mutation_authority is False

def test_surface_audit_detects_hash_drift():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);_build(root);(root/'LIVE_SHADOW.md').write_text('changed',encoding='utf-8');r=audit_continuity_surfaces(root);assert r.status=='STALE';assert 'LIVE_SHADOW.md' in r.hash_mismatch

def test_surface_audit_detects_missing_and_unmanifested():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);_build(root);(root/'NEXT_STEPS.md').unlink();m=json.loads((root/'SNAPSHOT_MANIFEST_SHA256.json').read_text());m['files'].pop('TRACE_MATRIX.md');(root/'SNAPSHOT_MANIFEST_SHA256.json').write_text(json.dumps(m),encoding='utf-8');r=audit_continuity_surfaces(root);assert r.status=='UNKNOWN_INCOMPLETE';assert 'NEXT_STEPS.md' in r.missing;assert 'TRACE_MATRIX.md' in r.unmanifested
