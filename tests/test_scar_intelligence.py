from __future__ import annotations
import hashlib,json,tempfile
from pathlib import Path
from mvf_resident.scar_intelligence import collect_scars,refresh_index,route_scars
from mvf_resident.lifecycle import ResidentLifecycle
from mvf_resident.resident import MVFResident,DutyContract
from mvf_resident.surfaces import REQUIRED_ACTIVE_SURFACES
from mvf_resident.daemon_plane import paths

class Fake:
    def call(self,name,payload): return {'ok':True}

def _handoff(root:Path):
    files={}
    for n in REQUIRED_ACTIVE_SURFACES:
        p=root/n;p.write_text(n,encoding='utf-8');b=p.read_bytes();files[n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    (root/'DOCTRINE_SNAPSHOT.md').write_text('''# Runtime scars\n- `LOCAL OPTIMUM != GLOBAL FUNCTIONALITY`\n- `VENV PYTHON REDIRECTOR != STABLE WINDOWS PROCESS-CONTROL BOUNDARY`\n## EARNED execution\n- `LONG GLOBAL SUITE != SYNCHRONOUS EXECUTION.RUN WORKLOAD`\n- `OPTIONAL PLANE DEGRADED != CORE FAILURE`\n''',encoding='utf-8')
    (root/'COMMANDERS_INTENT_CURRENT.md').write_text('''# Intent\nParent: HUD COCKPIT WAR CAMPAIGN\n- `LOCAL OPTIMUM != GLOBAL FUNCTIONALITY`\n- `PRETTY DASHBOARD != COCKPIT`\n''',encoding='utf-8')
    (root/'LIVE_SHADOW.md').write_text('Parent: HUD COCKPIT WAR CAMPAIGN',encoding='utf-8')
    (root/'CURRENT_STATE.md').write_text('Parent: HUD COCKPIT WAR CAMPAIGN',encoding='utf-8')
    for n in ('DOCTRINE_SNAPSHOT.md','COMMANDERS_INTENT_CURRENT.md','LIVE_SHADOW.md','CURRENT_STATE.md'):
        b=(root/n).read_bytes();files[n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    cp=files['THREAD_CONTINUITY_CHECKPOINT_2026-09-15.md']['sha256'];(root/'SNAPSHOT_MANIFEST_SHA256.json').write_text(json.dumps({'updated_at':'2026-09-15T00:00:00+00:00','continuity_checkpoint_sha256':cp,'files':files}),encoding='utf-8')

def test_duplicate_expression_dedupes_semantically_but_preserves_source_occurrences():
    with tempfile.TemporaryDirectory() as td:
        h=Path(td);_handoff(h);idx=collect_scars(h);rows=[x for x in idx['scars'] if x['expression']=='LOCAL OPTIMUM != GLOBAL FUNCTIONALITY'];assert len(rows)==1;assert rows[0]['occurrence_count']==2;assert {o['source'] for o in rows[0]['occurrences']}=={'active_handoff:DOCTRINE_SNAPSHOT.md','active_handoff:COMMANDERS_INTENT_CURRENT.md'}

def test_collection_never_promotes_derived_index_authority_and_only_records_explicit_provenance():
    with tempfile.TemporaryDirectory() as td:
        h=Path(td);_handoff(h);idx=collect_scars(h);assert idx['authority']=='DERIVED_INDEX_ONLY';earned=next(x for x in idx['scars'] if x['expression']=='LONG GLOBAL SUITE != SYNCHRONOUS EXECUTION.RUN WORKLOAD');assert earned['authority']=='DERIVED_INDEX_ONLY';assert earned['provenance_observations'].get('EARNED')==1

def test_semantic_router_surfaces_execution_scars_for_execution_failure_not_pretty_dashboard():
    with tempfile.TemporaryDirectory() as td:
        h=Path(td);_handoff(h);idx=collect_scars(h);route=route_scars(idx,'execution worker python process timeout restart failure',limit=3);expr=[x['expression'] for x in route['selected']];assert any('VENV PYTHON REDIRECTOR' in x or 'LONG GLOBAL SUITE' in x for x in expr);assert 'PRETTY DASHBOARD != COCKPIT' not in expr;assert route['ritual_dump_avoided'] is True

def test_hud_context_routes_cockpit_scar():
    with tempfile.TemporaryDirectory() as td:
        h=Path(td);_handoff(h);idx=collect_scars(h);route=route_scars(idx,'hud cockpit dashboard warning display operator',limit=3);assert any(x['expression']=='PRETTY DASHBOARD != COCKPIT' for x in route['selected'])

def test_refresh_is_hash_driven_and_new_scar_appears_after_source_change():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);h=b/'h';h.mkdir();_handoff(h);out=b/'index.json';a=refresh_index(h,out);assert a['changed'] is True;b1=refresh_index(h,out);assert b1['changed'] is False
        p=h/'DOCTRINE_SNAPSHOT.md';p.write_text(p.read_text()+"\n- `READINESS != PROCESS EXISTENCE`\n",encoding='utf-8');c=refresh_index(h,out);assert c['changed'] is True;assert any(x['expression']=='READINESS != PROCESS EXISTENCE' for x in c['scars'])

def test_lifecycle_writes_durable_index_and_bounded_applicable_packet():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);h=b/'h';h.mkdir();_handoff(h);root=b/'daemon';life=ResidentLifecycle.from_daemon_plane(MVFResident(Fake(),now=lambda:'2026-09-15T00:00:00+00:00'),root,h,daemon_id='d1',project_id='P')
        try:
            state=life.run_cycle((DutyContract('hud-cockpit','hud display','maintain cockpit dashboard warning display operator',(('x',{}),)),));packet=state['scar_intelligence'];assert packet['scar_count']>=4;assert len(packet['applicable'])<=7;assert packet['authority']=='DERIVED_ROUTING_ONLY';assert paths(root).scar_index.exists();assert any('COCKPIT' in x['expression'] for x in packet['applicable'])
        finally:life.close()


def test_specific_condition_scar_beats_more_frequent_broad_scar():
    with tempfile.TemporaryDirectory() as td:
        h=Path(td);_handoff(h)
        # Make the broad scar more frequent on purpose. Frequency must not outrank specificity.
        p=h/'COMMANDERS_INTENT_CURRENT.md';p.write_text(p.read_text()+"\n`LOCAL OPTIMUM != GLOBAL FUNCTIONALITY`\n`LOCAL OPTIMUM != GLOBAL FUNCTIONALITY`\n",encoding='utf-8')
        idx=collect_scars(h);route=route_scars(idx,'hud cockpit optional browser degraded core ready',limit=3)
        assert route['selected'][0]['expression']=='OPTIONAL PLANE DEGRADED != CORE FAILURE'
        assert 'expression:' in route['selected'][0]['reason']
        assert route['selected'][0]['best_occurrence'] is not None

def test_consolidated_ledger_section_headings_preserve_provenance_classes():
    with tempfile.TemporaryDirectory() as td:
        h=Path(td);f=h/'ledger.md'
        f.write_text("# Ledger\n## §3 — EARNED SCARS — class EARNED\n### 3.1 Verification and evidence\n`RECORDED_PASS != REPRODUCIBLE_PASS`\n### 3.2 Replay\n`IDENTITY_REPLAY != PROPERTY_REPLAY`\n## §5 — CSC — class PROPOSED\n### Tier 0\n`DECLARED != BOUND`\n## §6 — DONOR SET — class DONOR\n### Industry set\n`Redundancy != Availability`\n",encoding='utf-8')
        idx=collect_scars(h);prov={x['expression']:x['provenance_observations'] for x in idx['scars']}
        assert prov['RECORDED_PASS != REPRODUCIBLE_PASS']=={'EARNED':1}
        assert prov['IDENTITY_REPLAY != PROPERTY_REPLAY']=={'EARNED':1}
        assert prov['DECLARED != BOUND']=={'PROPOSED':1}
        assert prov['Redundancy != Availability']=={'DONOR':1}

def test_multi_source_semantic_dedupe_preserves_source_plane_and_registry_deficit():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);active=b/'active';external=b/'scar_sources';active.mkdir();external.mkdir();_handoff(active)
        (external/'gathering.md').write_text('## EARNED local copy\n`LOCAL OPTIMUM != GLOBAL FUNCTIONALITY`\n',encoding='utf-8')
        registry={'schema':'pcmmad.scar-source-registry.v1','sources':[{'source_id':'pending-global','filename':'missing.md','sha256':'0'*64,'source_class':'GATHERING','authority':'NONE_FROM_COMPILATION','evidence_ceiling':['CONSOLIDATION != CANON'],'status':'REGISTERED_ATTACHMENT_IDENTITY_PENDING_MATERIALIZATION'}]}
        (external/'SOURCE_REGISTRY.json').write_text(json.dumps(registry),encoding='utf-8')
        idx=collect_scars([active,external]);scar=next(x for x in idx['scars'] if x['expression']=='LOCAL OPTIMUM != GLOBAL FUNCTIONALITY')
        assert scar['source_plane_observations'].get('active_handoff',0)>=1
        assert scar['source_plane_observations'].get('scar_sources',0)==1
        assert {o['source_plane'] for o in scar['occurrences']} >= {'active_handoff','scar_sources'}
        assert idx['source_deficits'][0]['source_id']=='pending-global'
        assert idx['source_deficits'][0]['status']=='REGISTERED_ATTACHMENT_IDENTITY_PENDING_MATERIALIZATION'

def test_current_duty_semantics_route_scars_before_failure():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);h=b/'h';h.mkdir();_handoff(h);root=b/'daemon'
        life=ResidentLifecycle.from_daemon_plane(MVFResident(Fake(),now=lambda:'2026-09-15T00:00:00+00:00'),root,h,daemon_id='d1',project_id='P')
        try:
            state=life.run_cycle((DutyContract('hud-cockpit','hud cockpit display','maintain cockpit dashboard warning display operator',(('x',{}),)),))
            assert state['portfolio']['overall_status']=='CURRENT'
            assert any('COCKPIT' in x['expression'] for x in state['scar_intelligence']['applicable'])
        finally:life.close()
