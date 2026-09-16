from __future__ import annotations
import hashlib, importlib, json, sys, tempfile, time
from pathlib import Path
from mvf_resident.daemon_service import DaemonService, ReceiverLabDispatch
from mvf_resident.resident import MVFResident, LabToolsAdapter, default_receiver_lab_duties
from mvf_resident.surfaces import REQUIRED_ACTIVE_SURFACES

def _handoff(root:Path):
    files={}
    for n in REQUIRED_ACTIVE_SURFACES:
        p=root/n;p.write_text(n,encoding='utf-8');b=p.read_bytes();files[n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    cp=files['THREAD_CONTINUITY_CHECKPOINT_2026-09-15.md']['sha256'];(root/'SNAPSHOT_MANIFEST_SHA256.json').write_text(json.dumps({'updated_at':'x','continuity_checkpoint_sha256':cp,'files':files}),encoding='utf-8')

def test_missing_receiver_tool_substrate_yields_unknown_not_false_violation_and_daemon_stays_process_healthy():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);h=b/'h';h.mkdir();_handoff(h);dispatch=ReceiverLabDispatch(b/'missing_receiver');svc=DaemonService(daemon_root=b/'daemon',handoff_dir=h,project_id='P',daemon_id='d1',dispatch=dispatch,interval_seconds=1)
        try:
            svc.start();deadline=time.time()+4
            while svc.cycle_count<1 and time.time()<deadline:time.sleep(.05)
            assert svc.cycle_count>=1
            assert svc.health()['ok'] is True
            statuses={d['duty_id']:d['status'] for d in svc.last_cycle['portfolio']['duties']}
            assert statuses['receiver-currentness-ha']=='UNKNOWN_INCOMPLETE'
            assert statuses['repository-topology-currentness']=='UNKNOWN_INCOMPLETE'
        finally:svc.close()

def test_receiver_dispatch_retries_after_substrate_appears():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);receiver=b/'receiver';dispatch=ReceiverLabDispatch(receiver)
        assert dispatch.spec_lookup('x') is None
        runtime=receiver/'baseline'/'pcmmad_receiver';runtime.mkdir(parents=True)
        (runtime/'lab_tools.py').write_text("from types import SimpleNamespace\n_TOOL_REGISTRY={'x':SimpleNamespace(mutating=False,side_effect_class='read')}\ndef dispatch_tool(name,payload): return {'ok':True,'result':{'value':1}}\n",encoding='utf-8')
        old=sys.modules.pop('lab_tools',None);importlib.invalidate_caches()
        try:
            spec=dispatch.spec_lookup('x');assert spec is not None;assert dispatch('x',{})['ok'] is True
        finally:
            sys.modules.pop('lab_tools',None)
            if old is not None:sys.modules['lab_tools']=old
