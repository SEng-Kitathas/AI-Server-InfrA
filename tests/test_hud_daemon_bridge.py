from __future__ import annotations
import importlib.util
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
HUD_SERVER=ROOT/'operator_hud'/'server.py'

def load_hud(name='pcmmad_test_hud_daemon_bridge'):
    spec=importlib.util.spec_from_file_location(name,HUD_SERVER);module=importlib.util.module_from_spec(spec);assert spec and spec.loader;spec.loader.exec_module(module);return module

def _receiver(path,method='GET',payload=None,timeout=5.0):
    if path=='/lab/tools':return 200,{'ok':True,'count':10}
    if path=='/lab/dispatch':return 200,{'ok':True,'result':{'sessions':[]}}
    return 200,{'ok':True}

def test_daemon_not_configured_is_neutral_and_does_not_affect_core_readiness():
    hud=load_hud('pcmmad_test_hud_daemon_absent');client=hud.app.test_client()
    with patch.object(hud,'DAEMON_BASE',''),patch.object(hud,'receiver_request',side_effect=_receiver),patch.object(hud,'bridge_request',return_value=(200,{'ok':True})),patch.object(hud,'ngrok_request',return_value=(200,{'tunnels':[{'public_url':'https://x'}]})):
        res=client.get('/api/status',headers={'Host':f'127.0.0.1:{hud.HUD_PORT}'})
    body=res.get_json();assert res.status_code==200;assert body['readiness']['core_ready'] is True;assert body['daemon']['configured'] is False;assert body['scar_intelligence'] is None

def test_valid_daemon_status_passes_bounded_scar_packet_without_becoming_core_requirement():
    hud=load_hud('pcmmad_test_hud_daemon_present');client=hud.app.test_client();scar={'applicable':[{'expression':'PRETTY DASHBOARD != COCKPIT','reason':'tag:hud','occurrence_count':2}],'authority':'DERIVED_ROUTING_ONLY'}
    daemon={'schema':'mvf.daemon-status.v1','daemon_id':'pcmmad-daemon','project_id':'RECEIVER-LAB','mutation_authority':False,'scar_intelligence':{'applicable':[{'expression':'resident unrelated'}]}}
    with patch.object(hud,'DAEMON_BASE','http://127.0.0.1:5015'),patch.object(hud,'receiver_request',side_effect=_receiver),patch.object(hud,'bridge_request',return_value=(200,{'ok':True})),patch.object(hud,'daemon_request',return_value=(200,daemon)),patch.object(hud,'daemon_scar_route',return_value=(200,{'ok':True,'daemon_id':'pcmmad-daemon','project_id':'RECEIVER-LAB','mutation_authority':False,'routing':{'selected':scar['applicable']},'source_deficits':[{'source_id':'pending-global','status':'REGISTERED_ATTACHMENT_IDENTITY_PENDING_MATERIALIZATION'}]})),patch.object(hud,'ngrok_request',return_value=(200,{'tunnels':[{'public_url':'https://x'}]})):
        body=client.get('/api/status',headers={'Host':f'127.0.0.1:{hud.HUD_PORT}'}).get_json()
    assert body['readiness']['core_ready'] is True;assert body['daemon']['ok'] is True;assert body['daemon']['required_for_core'] is False;assert body['scar_intelligence']['applicable']==scar['applicable'];assert body['scar_intelligence']['source_deficits'][0]['source_id']=='pending-global';assert body['scar_intelligence']['authority']=='DERIVED_ROUTING_ONLY';assert 'hud cockpit normal operation' in body['scar_intelligence']['context']

def test_foreign_or_authority_shaped_daemon_status_is_not_promoted_into_cockpit_scar_packet():
    hud=load_hud('pcmmad_test_hud_daemon_invalid');client=hud.app.test_client();bad={'schema':'mvf.daemon-status.v1','daemon_id':'foreign-daemon','project_id':'RECEIVER-LAB','mutation_authority':False,'scar_intelligence':{'applicable':[{'expression':'bad'}]}}
    with patch.object(hud,'DAEMON_BASE','http://127.0.0.1:5015'),patch.object(hud,'receiver_request',side_effect=_receiver),patch.object(hud,'bridge_request',return_value=(200,{'ok':True})),patch.object(hud,'daemon_request',return_value=(200,bad)),patch.object(hud,'ngrok_request',return_value=(200,{'tunnels':[{'public_url':'https://x'}]})),patch.object(hud,'daemon_scar_route') as route:
        body=client.get('/api/status',headers={'Host':f'127.0.0.1:{hud.HUD_PORT}'}).get_json()
    assert body['daemon']['configured'] is True;assert body['daemon']['ok'] is False;assert body['scar_intelligence'] is None;route.assert_not_called()


def test_receiver_down_requests_recovery_specific_scar_context():
    hud=load_hud('pcmmad_test_hud_daemon_receiver_down');client=hud.app.test_client();daemon={'schema':'mvf.daemon-status.v1','daemon_id':'pcmmad-daemon','project_id':'RECEIVER-LAB','mutation_authority':False}
    def receiver(path,method='GET',payload=None,timeout=5.0):
        if path=='/lab/tools':return 502,{'ok':False}
        return 503,{'ok':False}
    routed={'ok':True,'daemon_id':'pcmmad-daemon','project_id':'RECEIVER-LAB','mutation_authority':False,'routing':{'selected':[{'expression':'LOCAL OPTIMUM != GLOBAL FUNCTIONALITY'}]}}
    with patch.object(hud,'DAEMON_BASE','http://127.0.0.1:5015'),patch.object(hud,'receiver_request',side_effect=receiver),patch.object(hud,'bridge_request',return_value=(200,{'ok':True})),patch.object(hud,'daemon_request',return_value=(200,daemon)),patch.object(hud,'ngrok_request',return_value=(200,{'tunnels':[{'public_url':'https://x'}]})),patch.object(hud,'daemon_scar_route',return_value=(200,routed)) as route:
        body=client.get('/api/status',headers={'Host':f'127.0.0.1:{hud.HUD_PORT}'}).get_json()
    context=route.call_args.args[0];assert 'receiver unavailable' in context;assert 'transport online' in context;assert 'windows defender' in context;assert body['scar_intelligence']['applicable'][0]['expression']=='LOCAL OPTIMUM != GLOBAL FUNCTIONALITY'
