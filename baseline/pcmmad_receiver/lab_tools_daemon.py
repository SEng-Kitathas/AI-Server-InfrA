from __future__ import annotations
import json, os, urllib.request
from collections.abc import Callable, MutableMapping
from typing import Any
JsonObject=MutableMapping[str,Any]
Registrar=Callable[...,Any]

def _base(): return str(os.environ.get('PCMMAD_DAEMON_URL') or 'http://127.0.0.1:5015').rstrip('/')
def _get(path:str,timeout:float=2.0):
    with urllib.request.urlopen(_base()+path,timeout=timeout) as r:
        return json.loads(r.read(262144).decode('utf-8'))

def register_daemon_tools(register_tool:Registrar,*,error_cls:type[Exception])->None:
    common=dict(danger_tier='low',category='daemon',approval_required=False,mutating=False,side_effect_class='read',effect_traits=['local_daemon_read','does_not_grant_mutation_authority'],input_schema={'type':'object','properties':{},'additionalProperties':False})
    @register_tool('daemon.health','Read current Daemon health from the local resident service.',**common)
    def daemon_health(payload:JsonObject)->JsonObject:
        try:return _get('/health')
        except Exception as exc: raise error_cls('DAEMON_UNAVAILABLE',f'{type(exc).__name__}: {exc}',503)
    @register_tool('daemon.status','Read compact current Daemon status.',**common)
    def daemon_status(payload:JsonObject)->JsonObject:
        try:return _get('/status')
        except Exception as exc: raise error_cls('DAEMON_UNAVAILABLE',f'{type(exc).__name__}: {exc}',503)
    @register_tool('daemon.events','Read bounded recent Daemon events.',**common)
    def daemon_events(payload:JsonObject)->JsonObject:
        try:return _get('/events')
        except Exception as exc: raise error_cls('DAEMON_UNAVAILABLE',f'{type(exc).__name__}: {exc}',503)
