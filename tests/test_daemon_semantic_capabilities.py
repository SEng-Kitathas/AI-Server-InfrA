from __future__ import annotations
import sys
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"baseline"/"pcmmad_receiver"
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
if str(BASE) not in sys.path: sys.path.insert(0,str(BASE))

from mvf_resident.daemon_service import DaemonService

class FakeDispatch:
    def __call__(self,name,payload):
        if name=='project.files.read': return {'ok':True,'content':'sample','file':{'path':payload['path']}}
        if name=='continuity.convergence.inspect': return {'status':'converged','current_sha256':'a','latest_registered_sha256':'a'}
        if name=='project.provenance.status': return {'ok':True,'event_count':1,'project_head_hash':'h'}
        if name=='project.provenance.root': return {'ok':True,'tree_size':1,'root_hash':'r'}
        raise RuntimeError(name)

def service(tmp_path):
    return DaemonService(daemon_root=tmp_path/'daemon',handoff_dir=tmp_path/'handoff',project_id='RECEIVER-LAB',daemon_id='pcmmad-daemon',dispatch=FakeDispatch(),interval_seconds=999)

def test_resident_context_drift_impact_and_handoff_are_read_only(tmp_path):
    svc=service(tmp_path)
    capsule=svc.context_capsule(context='receiver restart continuity')
    assert capsule['schema']=='mvf.daemon-context-capsule.v1' and capsule['mutation_authority'] is False
    assert len(capsule['surfaces'])==2
    drift=svc.continuity_drift()
    assert drift['status']=='current' and drift['drift']==[] and drift['mutation_authority'] is False
    impact=svc.semantic_impact(context='restart receiver continuity and git publish')
    assert 'runtime_recovery' in impact['affected_planes'] and 'continuity' in impact['affected_planes'] and 'source_control' in impact['affected_planes']
    assert impact['advisory_only'] is True and impact['mutation_authority'] is False
    handoff=svc.handoff_capsule()
    assert handoff['schema']=='mvf.daemon-handoff-capsule.v1' and handoff['mutation_authority'] is False

def test_receiver_daemon_adapters_register_semantic_tools():
    import lab_tools_daemon as ltd
    handlers={}
    class E(Exception):
        def __init__(self,code,message,status): self.code=code;self.message=message;self.status=status
    def register(name,*args,**kwargs):
        def deco(fn): handlers[name]=fn; return fn
        return deco
    ltd.register_daemon_tools(register,error_cls=E)
    assert {'daemon.context.capsule','daemon.continuity.drift','daemon.semantic.impact','daemon.handoff.capsule'} <= set(handlers)
    with patch.object(ltd,'_get',return_value={'schema':'mvf.daemon-semantic-impact.v1','ok':True,'daemon_id':'pcmmad-daemon','project_id':'RECEIVER-LAB','mutation_authority':False}):
        out=handlers['daemon.semantic.impact']({'context':'restart receiver'})
        assert out['mutation_authority'] is False

class EnvelopeDispatch(FakeDispatch):
    def __call__(self,name,payload):
        inner=super().__call__(name,payload)
        return {
            'ok':True,
            'tool':name,
            'danger_tier':'low',
            'policy_mode':'strict',
            'approved':False,
            'time':'2026-09-17T00:00:00+00:00',
            'result':inner,
        }


def test_resident_unwraps_receiver_tool_envelope_before_reasoning(tmp_path):
    svc=DaemonService(
        daemon_root=tmp_path/'daemon',
        handoff_dir=tmp_path/'handoff',
        project_id='RECEIVER-LAB',
        daemon_id='pcmmad-daemon',
        dispatch=EnvelopeDispatch(),
        interval_seconds=999,
    )
    capsule=svc.context_capsule(context='continuity drift')
    convergence=capsule['surfaces'][0]['convergence']
    assert convergence['result']['status']=='converged'
    assert convergence['receiver_envelope']['tool']=='continuity.convergence.inspect'
    provenance=capsule['provenance']
    assert provenance['result']['ok'] is True
    drift=svc.continuity_drift()
    assert drift['status']=='current'
    assert drift['drift']==[]
