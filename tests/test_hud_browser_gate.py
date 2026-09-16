from __future__ import annotations
import importlib.util,json,tempfile
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];HUD_SERVER=ROOT/'operator_hud'/'server.py'
def load_hud(name):
    spec=importlib.util.spec_from_file_location(name,HUD_SERVER);m=importlib.util.module_from_spec(spec);assert spec and spec.loader;spec.loader.exec_module(m);return m
def receiver(path,method='GET',payload=None,timeout=5.0):
    if path=='/lab/tools':return 200,{'ok':True,'count':10}
    if path=='/lab/dispatch':return 200,{'ok':True,'result':{'sessions':[]}}
    return 200,{'ok':True}

def test_gate_mutation_requires_existing_hud_token_and_writes_atomic_state():
    hud=load_hud('pcmmad_hud_gate_auth');client=hud.app.test_client()
    with tempfile.TemporaryDirectory() as td:
        gate=Path(td)/'gate.json'
        with patch.object(hud,'BROWSER_GATE_FILE',gate),patch.object(hud,'bridge_request',return_value=(200,{'ok':True,'service':'pcmmad_browser_bridge','gate_state':'ARMED','armed':True,'playwright':True,'ready_for_browser_automation':True})):
            denied=client.post('/api/browser/gate',json={'state':'ARMED'},headers={'Host':f'127.0.0.1:{hud.HUD_PORT}'})
            assert denied.status_code==403 and denied.get_json()['error_code']=='HUD_TOKEN_REQUIRED'
            ok=client.post('/api/browser/gate',json={'state':'ARMED'},headers={'Host':f'127.0.0.1:{hud.HUD_PORT}','X-PCMMAD-HUD-Token':hud.HUD_TOKEN})
            assert ok.status_code==200 and ok.get_json()['state']=='ARMED'
            obj=json.loads(gate.read_text(encoding='utf-8'));assert obj['state']=='ARMED';assert obj['provenance']=='HUD_EXPLICIT_OPERATOR_TOGGLE'

def test_invalid_gate_state_is_rejected_without_write():
    hud=load_hud('pcmmad_hud_gate_invalid');client=hud.app.test_client()
    with tempfile.TemporaryDirectory() as td:
        gate=Path(td)/'gate.json'
        with patch.object(hud,'BROWSER_GATE_FILE',gate):
            r=client.post('/api/browser/gate',json={'state':'MAYBE'},headers={'Host':f'127.0.0.1:{hud.HUD_PORT}','X-PCMMAD-HUD-Token':hud.HUD_TOKEN})
            assert r.status_code==400;assert not gate.exists()

def test_status_normalizes_browser_gate_security_and_capability_state():
    hud=load_hud('pcmmad_hud_gate_status');client=hud.app.test_client();bridge={'ok':True,'service':'pcmmad_browser_bridge','gate_state':'BLOCKED','armed':False,'playwright':True,'browser_channel_available':True,'ready_for_browser_automation':False,'default_channel':'msedge'}
    with patch.object(hud,'receiver_request',side_effect=receiver),patch.object(hud,'bridge_request',return_value=(200,bridge)),patch.object(hud,'ngrok_request',return_value=(200,{'tunnels':[{'public_url':'https://x'}]})),patch.object(hud,'DAEMON_BASE',''):
        body=client.get('/api/status',headers={'Host':f'127.0.0.1:{hud.HUD_PORT}'}).get_json()
    b=body['browser_bridge'];assert b['ok'] is True;assert b['gate_state']=='BLOCKED';assert b['armed'] is False;assert b['playwright'] is True;assert b['browser_channel_available'] is True;assert b['ready_for_browser_automation'] is False;assert b['default_channel']=='msedge';assert body['readiness']['core_ready'] is True
