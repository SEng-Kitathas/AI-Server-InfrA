from __future__ import annotations
import json,time
from pathlib import Path
import pytest
import supervisor.receiver_supervisor as m

class StopLoop(Exception): pass

def _run_one(monkeypatch,tmp_path,hold):
    stop=tmp_path/'hold.json';receipt=tmp_path/'receipt.json'
    if hold is not None:
        if isinstance(hold,str):stop.write_text(hold,encoding='utf-8')
        else:stop.write_text(json.dumps(hold),encoding='utf-8')
    calls=[]
    monkeypatch.setattr(m,'supervise_once',lambda **kwargs:calls.append(kwargs) or {})
    monkeypatch.setattr(m.time,'sleep',lambda _x:(_ for _ in ()).throw(StopLoop()))
    with pytest.raises(StopLoop):m.supervise_loop(health_url='x',task_name='T',receipt_path=receipt,interval_seconds=1,stop_path=stop,hold_max_age_seconds=60)
    return calls, json.loads(receipt.read_text()) if receipt.exists() else None

def test_loop_honors_valid_structured_hold(monkeypatch,tmp_path):
    now=time.time();calls,receipt=_run_one(monkeypatch,tmp_path,{'desired_state':'STOPPED','operator_id':'op','reason':'maintenance','expires_at_epoch':now+30})
    assert calls==[];assert receipt['action']=='MAINTENANCE_HOLD';assert receipt['operator_id']=='op'

@pytest.mark.parametrize('hold',[
    'not json',
    {'desired_state':'STOPPED','operator_id':'','reason':'x','expires_at_epoch':9999999999},
    {'desired_state':'STOPPED','operator_id':'op','reason':'x','expires_at_epoch':1},
    {'desired_state':'STOPPED','operator_id':'op','reason':'x','expires_at_epoch':9999999999},
])
def test_loop_ignores_invalid_expired_or_overlong_hold_and_reconciles_running(monkeypatch,tmp_path,hold):
    calls,_receipt=_run_one(monkeypatch,tmp_path,hold);assert len(calls)==1


def test_hold_activated_after_unhealthy_probe_but_before_trigger_suppresses_recovery(tmp_path):
    calls=[]
    state={'hold':False,'status':'RUNNING'}
    def hp(*_):
        state.update({'hold':True,'status':'VALID_HOLD','operator_id':'op','reason':'race','expires_at_epoch':time.time()+20})
        return False,'down'
    result=m.supervise_once(health_url='x',task_name='T',receipt_path=tmp_path/'r.json',health_probe=hp,trigger=lambda task:(calls.append(task) or True,'ok'),failure_state={'restart_events':[]},hold_check=lambda:dict(state),recovery_seconds=0)
    assert calls==[]
    assert result['action']=='MAINTENANCE_HOLD'
    assert result['operator_id']=='op'
