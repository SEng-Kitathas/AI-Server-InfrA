from __future__ import annotations
import importlib.util,sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('hud_server_projection_test',ROOT/'operator_hud/server.py');hud=importlib.util.module_from_spec(spec);spec.loader.exec_module(hud)

def test_status_projects_browser_sessions_from_receiver_dispatch():
    def receiver(path,**kw):
        if path=='/lab/health':return 200,{'ok':True,'status':'ready'}
        if path=='/observability/telemetry':return 200,{'ok':True}
        if path=='/lab/dispatch':return 200,{'ok':True,'result':{'sessions':[{'session_id':'S1'}]}}
        raise AssertionError(path)
    with patch.object(hud,'receiver_request',side_effect=receiver),patch.object(hud,'bridge_request',return_value=(200,{'ok':True,'sessions':1})):
        with hud.app.test_client() as c:data=c.get('/api/status').get_json()
    assert [x['session_id'] for x in data['browser_sessions']]==['S1']

def test_status_does_not_fake_zero_sessions_when_bridge_unobservable():
    def receiver(path,**kw):
        if path=='/lab/health':return 200,{'ok':True,'status':'ready'}
        if path=='/observability/telemetry':return 200,{'ok':True}
        raise AssertionError(path)
    hud.app.config['TESTING']=True
    with patch.object(hud,'receiver_request',side_effect=receiver),patch.object(hud,'bridge_request',return_value=(503,{'ok':False,'error':'down'})):
        with hud.app.test_client() as c:data=c.get('/api/status').get_json()
    assert data['browser_sessions']==[];assert data['browser_bridge']['ok'] is False

def test_dispatch_updates_live_activity_journal():
    with hud.EVENT_LOCK:hud.EVENTS.clear()
    with patch.object(hud,'receiver_request',return_value=(200,{'ok':True,'result':{'x':1}})):
        with hud.app.test_client() as c:
            r=c.post('/api/dispatch',json={'tool_name':'lab.health','payload':{}},headers={'X-PCMMAD-HUD-Token':hud.HUD_TOKEN});assert r.status_code==200
            status=c.get('/api/status').get_json()
    kinds=[x.get('kind') for x in status['events']]
    assert 'dispatch_started' in kinds and 'dispatch_completed' in kinds
