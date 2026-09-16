from __future__ import annotations
import json,tempfile
from pathlib import Path
import pytest
import supervisor.receiver_supervisor as rs
from mvf_resident.daemon_service import DaemonService


def test_restart_budget_is_persisted_before_trigger_side_effect(tmp_path):
    failure=tmp_path/'failure.json';state={'restart_events':[]}
    def persist(st): rs.save_failure_state(failure,st)
    def trigger(_task):
        loaded=rs.load_failure_state(failure,max_restarts=3,restart_window_seconds=60)
        assert len(loaded['restart_events'])==1
        raise RuntimeError('simulated supervisor crash at trigger boundary')
    with pytest.raises(RuntimeError,match='trigger boundary'):
        rs.supervise_once(health_url='x',task_name='T',receipt_path=tmp_path/'r.json',health_probe=lambda *_:(False,'down'),trigger=trigger,failure_state=state,failure_state_persist=persist,max_restarts=3,restart_window_seconds=60,now_monotonic=rs.time.time)
    restored=rs.load_failure_state(failure,max_restarts=3,restart_window_seconds=60)
    assert len(restored['restart_events'])==1


def test_status_snapshot_bounds_pathological_error_and_compact_reason():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);svc=DaemonService(daemon_root=root/'daemon',handoff_dir=root,project_id='P',daemon_id='d1',dispatch=lambda *_:{'ok':True},interval_seconds=30)
        svc.last_error='E'*500000
        svc.last_cycle={'portfolio':{'compact':{'high_value_updates':[{'reason':'R'*500000}]}} ,'surface_audit':{'status':'CURRENT'}}
        raw=json.dumps(svc.status()).encode()
        assert len(raw)<20000
        assert 'truncated' in raw.decode()
        svc.close()


def test_events_contract_has_schema_identity_and_no_effect_authority():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);svc=DaemonService(daemon_root=root/'daemon',handoff_dir=root,project_id='P',daemon_id='d1',dispatch=lambda *_:{'ok':True},interval_seconds=30)
        try:
            svc._event('x',value=1)
            rows=svc.event_rows(limit=50);assert rows[0]['kind']=='x'
            body={'schema':'mvf.daemon-events.v1','ok':True,'daemon_id':'d1','project_id':'P','mutation_authority':False,'events':rows}
            import sys
            sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'baseline'/'pcmmad_receiver'))
            import lab_tools_daemon as d
            import os
            old_id=os.environ.get('PCMMAD_DAEMON_ID');old_p=os.environ.get('PCMMAD_DAEMON_PROJECT_ID');os.environ['PCMMAD_DAEMON_ID']='d1';os.environ['PCMMAD_DAEMON_PROJECT_ID']='P'
            try:assert d._validate('events',body) is body
            finally:
                if old_id is None:os.environ.pop('PCMMAD_DAEMON_ID',None)
                else:os.environ['PCMMAD_DAEMON_ID']=old_id
                if old_p is None:os.environ.pop('PCMMAD_DAEMON_PROJECT_ID',None)
                else:os.environ['PCMMAD_DAEMON_PROJECT_ID']=old_p
        finally:svc.close()
