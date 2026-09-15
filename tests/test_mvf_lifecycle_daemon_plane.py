from __future__ import annotations
import tempfile, json, hashlib
from pathlib import Path
from mvf_resident.lifecycle import ResidentLifecycle
from mvf_resident.resident import MVFResident, DutyContract
from mvf_resident.surfaces import REQUIRED_ACTIVE_SURFACES
from mvf_resident.daemon_plane import audit, paths

class Fake:
    def call(self,name,payload): return {'ok':True}

def _handoff(root:Path):
    files={}
    for n in REQUIRED_ACTIVE_SURFACES:
        p=root/n;p.write_text(n,encoding='utf-8');b=p.read_bytes();files[n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    cp=files['THREAD_CONTINUITY_CHECKPOINT_2026-09-15.md']['sha256'];(root/'SNAPSHOT_MANIFEST_SHA256.json').write_text(json.dumps({'updated_at':'x','continuity_checkpoint_sha256':cp,'files':files}),encoding='utf-8')

def test_resident_lifecycle_uses_qualified_daemon_plane_storage():
    with tempfile.TemporaryDirectory() as td:
        base=Path(td);h=base/'h';h.mkdir();_handoff(h);root=base/'daemon'
        life=ResidentLifecycle.from_daemon_plane(MVFResident(Fake(),now=lambda:'2026-09-15T00:00:00+00:00'),root,h,daemon_id='d1',project_id='P')
        try:
            out=life.run_cycle((DutyContract('a','s','c',(('x',{}),)),))
            p=paths(root);assert life.governance.ledger.path == p.evidence_db if hasattr(life.governance.ledger,'path') else p.evidence_db.exists()
            assert p.biography_db.exists();assert json.loads(p.current_state.read_text())['state']['schema']=='mvf.resident-current-state.v1';assert audit(root).status=='CURRENT';assert out['mutation_authority'] is False
        finally: life.close()
