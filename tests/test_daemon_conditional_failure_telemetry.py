from __future__ import annotations
import hashlib,json,tempfile
from pathlib import Path
from mvf_resident.daemon_service import DaemonService
from mvf_resident.surfaces import REQUIRED_ACTIVE_SURFACES


def _handoff(root:Path):
    files={}
    for n in REQUIRED_ACTIVE_SURFACES:
        p=root/n;p.write_text(n,encoding='utf-8');b=p.read_bytes();files[n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    (root/'COMMANDERS_INTENT_CURRENT.md').write_text('Active parent campaign: GLOBAL INTERACTION WAR CAMPAIGN',encoding='utf-8');(root/'LIVE_SHADOW.md').write_text('Parent: GLOBAL INTERACTION WAR CAMPAIGN',encoding='utf-8');(root/'CURRENT_STATE.md').write_text('Active parent campaign: GLOBAL INTERACTION WAR CAMPAIGN',encoding='utf-8')
    for n in ('COMMANDERS_INTENT_CURRENT.md','LIVE_SHADOW.md','CURRENT_STATE.md'):
        b=(root/n).read_bytes();files[n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    cp=files['THREAD_CONTINUITY_CHECKPOINT_2026-09-15.md']['sha256'];(root/'SNAPSHOT_MANIFEST_SHA256.json').write_text(json.dumps({'updated_at':'2026-09-15T00:00:00+00:00','continuity_checkpoint_sha256':cp,'files':files}),encoding='utf-8')


def _healthy_dispatch(calls):
    def dispatch(name,payload):
        calls.append(name)
        if name=='machine.processes.list' and payload.get('name_filter')=='python':return {'ok':True,'processes':[{'name':'python.exe','command_line':r'C:\x\baseline\pcmmad_receiver\server.py'}]}
        if name=='machine.processes.list':return {'ok':True,'processes':[{'name':'ngrok.exe','command_line':'ngrok'}]}
        if name=='machine.scheduled_tasks.list':return {'ok':True,'scheduled_tasks':[{'task_name':'PCMMAD_V30_Receiver_SYSTEM'}]}
        if name=='git.repositories.list':return {'ok':True,'repositories':[{'root':'x'}]}
        if name=='machine.roots.list':return {'ok':True,'roots':['C:/']}
        if name=='continuity.convergence.inspect':return {'ok':True,'status':'current'}
        if name=='windows.failure_evidence.inspect':return {'ok':True,'security_signal_present':False,'causation_established':False,'mutation_authority':False}
        return {'ok':True}
    return dispatch

def test_healthy_cycle_does_not_poll_windows_failure_telemetry_and_surfaces_continuity_plan():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);h=b/'h';h.mkdir();_handoff(h);calls=[];svc=DaemonService(daemon_root=b/'daemon',handoff_dir=h,project_id='P',daemon_id='d1',dispatch=_healthy_dispatch(calls),interval_seconds=30)
        try:
            svc.cycle_once();assert 'windows.failure_evidence.inspect' not in calls;st=svc.status();assert st['failure_evidence'] is None;assert st['continuity_enforcement']['surfacing_plan']['selected'];assert st['continuity_enforcement']['handoff_ready'] is True
        finally:svc.close()

def test_noncurrent_cycle_invokes_failure_correlator_once_and_exposes_noncausal_packet():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);h=b/'h';h.mkdir();_handoff(h);calls=[]
        def dispatch(name,payload):
            calls.append(name)
            if name=='windows.failure_evidence.inspect':return {'ok':True,'security_signal_present':True,'causation_established':False,'defender_signals':[{'threat_id':1}],'mutation_authority':False}
            if name=='continuity.convergence.inspect':return {'ok':True,'status':'stale'}
            return {'ok':True}
        svc=DaemonService(daemon_root=b/'daemon',handoff_dir=h,project_id='P',daemon_id='d1',dispatch=dispatch,interval_seconds=30)
        try:
            svc.cycle_once();assert calls.count('windows.failure_evidence.inspect')==1;st=svc.status();assert st['failure_evidence']['security_signal_present'] is True;assert st['failure_evidence']['causation_established'] is False
        finally:svc.close()

def test_failure_telemetry_unavailable_does_not_abort_cognitive_cycle():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);h=b/'h';h.mkdir();_handoff(h)
        def dispatch(name,payload):
            if name=='windows.failure_evidence.inspect':raise RuntimeError('event channel unavailable')
            if name=='continuity.convergence.inspect':return {'ok':True,'status':'stale'}
            return {'ok':True}
        svc=DaemonService(daemon_root=b/'daemon',handoff_dir=h,project_id='P',daemon_id='d1',dispatch=dispatch,interval_seconds=30)
        try:
            result=svc.cycle_once();assert result['portfolio']['overall_status']!='CURRENT';assert svc.status()['failure_evidence']['status']=='UNKNOWN_INCOMPLETE';assert svc.status()['failure_evidence']['causation_established'] is False
        finally:svc.close()
