from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'baseline'/'pcmmad_receiver'))
import browser_bridge_service as bridge

def _client(gate:Path):
    bridge.GATE_FILE=gate;bridge.SESSIONS.clear();return bridge.app.test_client()

def test_missing_gate_is_fail_closed_but_health_is_readable():
    with tempfile.TemporaryDirectory() as td:
        c=_client(Path(td)/'gate.json');bridge.PW=object()
        h=c.get('/health').get_json();assert h['ok'] is True;assert h['gate_state']=='BLOCKED';assert h['armed'] is False;assert h['ready_for_browser_automation'] is False
        r=c.post('/session/start',json={'headless':True});assert r.status_code==423;assert r.get_json()['error_code']=='BROWSER_BRIDGE_BLOCKED'

def test_bom_armed_gate_is_accepted_and_health_separates_security_from_capability():
    with tempfile.TemporaryDirectory() as td:
        gate=Path(td)/'gate.json';gate.write_text(json.dumps({'state':'ARMED','provenance':'EXPLICIT_OPERATOR_TOGGLE'}),encoding='utf-8-sig');c=_client(gate)
        bridge.PW=None
        with patch.object(bridge,'_browser_channel',return_value='msedge'),patch.object(bridge,'_browser_channel_available',return_value=True):h=c.get('/health').get_json()
        assert h['armed'] is True;assert h['playwright'] is False;assert h['browser_channel_available'] is True;assert h['ready_for_browser_automation'] is False
        bridge.PW=object()
        with patch.object(bridge,'_browser_channel',return_value='msedge'),patch.object(bridge,'_browser_channel_available',return_value=True):h=c.get('/health').get_json()
        assert h['armed'] is True;assert h['playwright'] is True;assert h['browser_channel_available'] is True;assert h['ready_for_browser_automation'] is True

def test_malformed_gate_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        gate=Path(td)/'gate.json';gate.write_text('{bad',encoding='utf-8');c=_client(gate);bridge.PW=object();h=c.get('/health').get_json();assert h['gate_state']=='BLOCKED';assert h['armed'] is False;assert h['gate_reason'].startswith('invalid_gate:')

def test_cleanup_and_observation_routes_remain_available_while_blocked():
    with tempfile.TemporaryDirectory() as td:
        c=_client(Path(td)/'missing.json');bridge.PW=object()
        assert c.get('/sessions').status_code==200
        assert c.post('/pages/list',json={'session_id':'missing'}).status_code!=423
        assert c.post('/content',json={'session_id':'missing'}).status_code!=423
        assert c.post('/text',json={'session_id':'missing'}).status_code!=423
        assert c.post('/session/stop',json={'session_id':'missing'}).status_code!=423
        assert c.post('/navigate',json={'session_id':'missing','url':'about:blank'}).status_code==423

def test_armed_route_reaches_session_logic():
    with tempfile.TemporaryDirectory() as td:
        gate=Path(td)/'gate.json';gate.write_text(json.dumps({'state':'ARMED'}),encoding='utf-8');c=_client(gate);bridge.PW=object()
        def fake_start(*args,**kwargs):
            bridge.SESSIONS['br-test']={'session_id':'br-test','context':object(),'page_index':0,'created_at':0.0};return 'br-test'
        with patch.object(bridge,'_start_launched_session',side_effect=fake_start),patch.object(bridge,'_maybe_open_start_url',return_value=None),patch.object(bridge,'_pages',return_value=[]):
            r=c.post('/session/start',json={'headless':True});assert r.status_code==200;assert r.get_json()['session_id']=='br-test'


def test_armed_with_missing_browser_channel_is_not_ready():
    with tempfile.TemporaryDirectory() as td:
        gate=Path(td)/'gate.json';gate.write_text(json.dumps({'state':'ARMED'}),encoding='utf-8');c=_client(gate);bridge.PW=object()
        with patch.object(bridge,'_browser_channel',return_value='msedge'),patch.object(bridge,'_browser_channel_available',return_value=False):h=c.get('/health').get_json()
        assert h['armed'] is True;assert h['playwright'] is True;assert h['browser_channel_available'] is False;assert h['ready_for_browser_automation'] is False
