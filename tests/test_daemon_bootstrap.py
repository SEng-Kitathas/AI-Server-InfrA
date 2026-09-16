from __future__ import annotations

import hashlib, json, tempfile
from pathlib import Path
import pytest

from mvf_resident.daemon_bootstrap import rehydrate
from mvf_resident.daemon_plane import DaemonPlaneCorrupt, initialize, paths
from mvf_resident.lifecycle import ResidentLifecycle
from mvf_resident.resident import MVFResident, DutyContract
from mvf_resident.surfaces import REQUIRED_ACTIVE_SURFACES

class Fake:
    def call(self,name,payload): return {'ok':True}

def _handoff(root:Path):
    files={}
    for n in REQUIRED_ACTIVE_SURFACES:
        p=root/n;p.write_text(n,encoding='utf-8');b=p.read_bytes();files[n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    cp=files['THREAD_CONTINUITY_CHECKPOINT_2026-09-15.md']['sha256'];(root/'SNAPSHOT_MANIFEST_SHA256.json').write_text(json.dumps({'updated_at':'x','continuity_checkpoint_sha256':cp,'files':files}),encoding='utf-8')

def _sha_tree(root:Path):
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}

def test_bootstrap_rehydrates_existing_plane_read_only():
    with tempfile.TemporaryDirectory() as td:
        base=Path(td);h=base/'h';h.mkdir();_handoff(h);root=base/'daemon'
        life=ResidentLifecycle.from_daemon_plane(MVFResident(Fake(),now=lambda:'2026-09-15T00:00:00+00:00'),root,h,daemon_id='d1',project_id='P')
        try: life.run_cycle((DutyContract('a','s','c',(('x',{}),)),))
        finally: life.close()
        before=_sha_tree(root);state=rehydrate(root,expected_daemon_id='d1',expected_project_id='P');after=_sha_tree(root)
        assert before==after
        assert state.daemon_id=='d1' and state.project_id=='P'
        assert state.generation==1
        assert state.evidence_count>=2
        assert state.biography_event_count>=2
        assert state.authority=='COGNITIVE_PLANE_ONLY' and state.mutation_authority is False
        assert state.current_state['schema']=='mvf.resident-current-state.v1'

def test_bootstrap_refuses_missing_plane_without_initializing_it():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)/'daemon'
        with pytest.raises(DaemonPlaneCorrupt,match='NOT_CURRENT'): rehydrate(root)
        assert not root.exists()

def test_bootstrap_refuses_identity_and_project_mismatch():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)/'daemon';initialize(root,daemon_id='d1',project_id='P')
        with pytest.raises(DaemonPlaneCorrupt,match='IDENTITY_MISMATCH'): rehydrate(root,expected_daemon_id='d2')
        with pytest.raises(DaemonPlaneCorrupt,match='PROJECT_MISMATCH'): rehydrate(root,expected_project_id='Q')

def test_bootstrap_refuses_authority_identity_tamper():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)/'daemon';p=initialize(root,daemon_id='d1',project_id='P');obj=json.loads(p.identity.read_text());obj['authority']='EFFECT';p.identity.write_text(json.dumps(obj),encoding='utf-8')
        with pytest.raises(DaemonPlaneCorrupt,match='AUTHORITY_IDENTITY_INVALID'): rehydrate(root)

def test_bootstrap_refuses_current_state_daemon_identity_mismatch():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)/'daemon';p=initialize(root,daemon_id='d1',project_id='P');obj=json.loads(p.current_state.read_text());obj['daemon_id']='other';p.current_state.write_text(json.dumps(obj),encoding='utf-8')
        with pytest.raises(DaemonPlaneCorrupt,match='CURRENT_STATE_DAEMON_IDENTITY_MISMATCH'): rehydrate(root)
