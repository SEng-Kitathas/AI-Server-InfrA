from __future__ import annotations
import json,tempfile,hashlib
from pathlib import Path
from mvf_resident.lifecycle import ResidentLifecycle
from mvf_resident.resident import MVFResident,DutyContract
from mvf_resident.surfaces import REQUIRED_ACTIVE_SURFACES

class Fake:
    def call(self,name,payload): return {'ok':True}

def _handoff(root:Path):
    files={}
    for n in REQUIRED_ACTIVE_SURFACES:
        p=root/n;p.write_text(n,encoding='utf-8');b=p.read_bytes();files[n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    cp=files['THREAD_CONTINUITY_CHECKPOINT_2026-09-15.md']['sha256'];(root/'SNAPSHOT_MANIFEST_SHA256.json').write_text(json.dumps({'updated_at':'x','continuity_checkpoint_sha256':cp,'files':files}),encoding='utf-8')

def test_cycle_is_idempotent_for_identical_observations():
    with tempfile.TemporaryDirectory() as td:
        base=Path(td);h=base/'h';h.mkdir();_handoff(h);d=(DutyContract('a','s','c',(('x',{}),)),)
        with ResidentLifecycle(MVFResident(Fake(),now=lambda:'2026-09-15T00:00:00+00:00'),base/'state',h) as life:
            a=life.run_cycle(d);ec=a['evidence_count'];bg=a['biography_graph_digest'];b=life.run_cycle(d);assert b['evidence_count']==ec;assert b['biography_graph_digest']==bg;assert b['surface_audit']['status']=='CURRENT'

def test_surface_drift_becomes_deficit_without_mutation_authority():
    with tempfile.TemporaryDirectory() as td:
        base=Path(td);h=base/'h';h.mkdir();_handoff(h);(h/'LIVE_SHADOW.md').write_text('drift',encoding='utf-8');d=(DutyContract('a','s','c',(('x',{}),)),)
        with ResidentLifecycle(MVFResident(Fake(),now=lambda:'2026-09-15T00:00:00+00:00'),base/'state',h) as life:
            s=life.run_cycle(d);assert s['surface_audit']['status']=='STALE';assert 'deficit:continuity-active-surfaces' in s['deficits'];assert s['mutation_authority'] is False
