from __future__ import annotations
import hashlib,json,sys,tempfile
from pathlib import Path
import pytest
import mvf_resident.lifecycle as lifecycle_mod
from mvf_resident.daemon_plane import paths
from mvf_resident.daemon_service import _validate_bind_host
from mvf_resident.lifecycle import ResidentLifecycle
from mvf_resident.resident import MVFResident,DutyContract
from mvf_resident.surfaces import REQUIRED_ACTIVE_SURFACES

ROOT=Path(__file__).resolve().parents[1]

class Fake:
    def call(self,name,payload): return {'ok':True}

def _handoff(root):
    files={}
    for n in REQUIRED_ACTIVE_SURFACES:
        p=root/n;p.write_text(n,encoding='utf-8');b=p.read_bytes();files[n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    cp=files['THREAD_CONTINUITY_CHECKPOINT_2026-09-15.md']['sha256'];(root/'SNAPSHOT_MANIFEST_SHA256.json').write_text(json.dumps({'updated_at':'x','continuity_checkpoint_sha256':cp,'files':files}),encoding='utf-8')

def test_partial_cycle_crash_after_evidence_before_state_converges_idempotently(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);h=b/'h';h.mkdir();_handoff(h);root=b/'daemon';duty=(DutyContract('a','s','c',(('x',{}),)),)
        real=lifecycle_mod.daemon_write_current_unlocked;calls={'n':0}
        def fail_once(root,state):
            calls['n']+=1
            if calls['n']==1: raise OSError('simulated disk failure before current-state replace')
            return real(root,state)
        monkeypatch.setattr(lifecycle_mod,'daemon_write_current_unlocked',fail_once)
        life=ResidentLifecycle.from_daemon_plane(MVFResident(Fake(),now=lambda:'2026-09-15T00:00:00+00:00'),root,h,daemon_id='d1',project_id='P')
        with pytest.raises(OSError): life.run_cycle(duty)
        evidence_after_failure=len(life.governance.ledger.list());bio_after_failure=life.biography.graph_digest();life.close()
        life2=ResidentLifecycle.from_daemon_plane(MVFResident(Fake(),now=lambda:'2026-09-15T00:01:00+00:00'),root,h,daemon_id='d1',project_id='P')
        try:
            state=life2.run_cycle(duty);assert state['evidence_count']==evidence_after_failure;assert state['biography_graph_digest']==bio_after_failure
        finally:life2.close()

def test_daemon_bind_rejects_non_loopback_interfaces():
    _validate_bind_host('127.0.0.1');_validate_bind_host('::1');_validate_bind_host('localhost')
    for host in ('0.0.0.0','192.168.1.10','example.com'):
        with pytest.raises(ValueError,match='LOOPBACK'): _validate_bind_host(host)

def test_native_daemon_validation_rejects_foreign_identity_and_effect_authority(monkeypatch):
    sys.path.insert(0,str(ROOT/'baseline'/'pcmmad_receiver'));import lab_tools_daemon as d
    monkeypatch.setenv('PCMMAD_DAEMON_ID','d1');monkeypatch.setenv('PCMMAD_DAEMON_PROJECT_ID','P')
    good={'schema':'mvf.daemon-health.v1','daemon_id':'d1','project_id':'P','mutation_authority':False,'ok':True,'status':'healthy'};assert d._validate('health',good) is good
    with pytest.raises(RuntimeError,match='IDENTITY'):d._validate('health',{**good,'daemon_id':'other'})
    with pytest.raises(RuntimeError,match='PROJECT'):d._validate('health',{**good,'project_id':'Q'})
    with pytest.raises(RuntimeError,match='AUTHORITY'):d._validate('health',{**good,'mutation_authority':True})
    with pytest.raises(RuntimeError,match='SCHEMA'):d._validate('health',{**good,'schema':'foreign.v1'})

def test_installer_contains_daemon_port_collision_guard():
    text=(ROOT/'supervisor'/'install_unattended_recovery.ps1').read_text(encoding='utf-8')
    assert 'DAEMON_PORT_COLLIDES_WITH_RECEIVER_OR_HUD' in text
    assert "PCMMAD_DAEMON_ID" in text and "PCMMAD_DAEMON_PROJECT_ID" in text
