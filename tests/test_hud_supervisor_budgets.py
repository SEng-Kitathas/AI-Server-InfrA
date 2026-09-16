from __future__ import annotations
import importlib.util,json,tempfile,time
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];HUD_SERVER=ROOT/'operator_hud'/'server.py'
def load_hud(name):
    spec=importlib.util.spec_from_file_location(name,HUD_SERVER);m=importlib.util.module_from_spec(spec);assert spec and spec.loader;spec.loader.exec_module(m);return m

def test_missing_recovery_estate_is_neutral_standby():
    hud=load_hud('pcmmad_budget_missing')
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)/'missing'
        with patch.object(hud,'RECOVERY_ROOT',root):b=hud.supervisor_budgets()
    assert b['summary']['status']=='STANDBY';assert b['mutation_authority'] is False;assert all(x['state_status']=='MISSING' for x in b['workloads'].values())

def test_restart_events_are_windowed_and_remaining_budget_is_explicit():
    hud=load_hud('pcmmad_budget_events')
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);now=time.time();(root/'receiver_supervisor.failure_state.json').write_text(json.dumps({'state_status':'RESTORED','restart_events':[now-10,now-20,now-900]}),encoding='utf-8')
        with patch.object(hud,'RECOVERY_ROOT',root),patch.object(hud.time,'time',return_value=now):b=hud.supervisor_budgets()
    r=b['workloads']['receiver'];assert r['restart_events']==2;assert r['remaining']==1;assert b['summary']['status']=='AVAILABLE';assert b['summary']['remaining']==1

def test_corrupt_failure_state_is_fail_closed_as_zero_budget():
    hud=load_hud('pcmmad_budget_corrupt')
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);(root/'ngrok_supervisor.failure_state.json').write_text('{bad',encoding='utf-8')
        with patch.object(hud,'RECOVERY_ROOT',root):b=hud.supervisor_budgets()
    n=b['workloads']['ngrok'];assert n['state_status']=='CORRUPT_HOLD';assert n['remaining']==0;assert b['summary']['status']=='CORRUPT_HOLD'

def test_valid_maintenance_hold_overrides_available_budget():
    hud=load_hud('pcmmad_budget_hold')
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);now=time.time();(root/'daemon_supervisor.failure_state.json').write_text(json.dumps({'state_status':'RESTORED','restart_events':[]}),encoding='utf-8');(root/'daemon_supervisor.maintenance_hold').write_text(json.dumps({'desired_state':'STOPPED','expires_at_epoch':now+300,'operator_id':'op','reason':'maintenance'}),encoding='utf-8')
        with patch.object(hud,'RECOVERY_ROOT',root),patch.object(hud.time,'time',return_value=now):b=hud.supervisor_budgets()
    d=b['workloads']['daemon'];assert d['hold']['hold'] is True;assert d['hold']['status']=='MAINTENANCE_HOLD';assert b['summary']['status']=='MAINTENANCE_HOLD'
