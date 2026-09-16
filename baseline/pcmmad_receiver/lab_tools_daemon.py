from __future__ import annotations
import json, os, urllib.request, urllib.error
from collections.abc import Callable, MutableMapping
from typing import Any
JsonObject=MutableMapping[str,Any]
Registrar=Callable[...,Any]

def _base(): return str(os.environ.get('PCMMAD_DAEMON_URL') or 'http://127.0.0.1:5015').rstrip('/')
def _get(path:str,timeout:float=2.0):
    try:
        with urllib.request.urlopen(_base()+path,timeout=timeout) as r:
            body=json.loads(r.read(262144).decode('utf-8'));body['_http_status']=int(r.status);return body
    except urllib.error.HTTPError as exc:
        raw=exc.read(262144)
        try: body=json.loads(raw.decode('utf-8'))
        except Exception: raise
        if not isinstance(body,dict): raise
        body['_http_status']=int(exc.code);return body

def _validate(kind:str,body:JsonObject)->JsonObject:
    expected_daemon=str(os.environ.get('PCMMAD_DAEMON_ID') or 'pcmmad-daemon')
    expected_project=str(os.environ.get('PCMMAD_DAEMON_PROJECT_ID') or 'RECEIVER-LAB')
    schema=str(body.get('schema') or body.get('schema_version') or '')
    expected_schema={'health':'mvf.daemon-health.','status':'mvf.daemon-status.','events':'mvf.daemon-events.'}.get(kind)
    if expected_schema and not schema.startswith(expected_schema): raise RuntimeError(f'DAEMON_SCHEMA_IDENTITY_MISMATCH:{kind}:{schema or "missing"}')
    if kind in {'health','status','events'}:
        if str(body.get('daemon_id') or '')!=expected_daemon: raise RuntimeError('DAEMON_IDENTITY_MISMATCH')
        if str(body.get('project_id') or '')!=expected_project: raise RuntimeError('DAEMON_PROJECT_MISMATCH')
        if body.get('mutation_authority') is not False: raise RuntimeError('DAEMON_AUTHORITY_SHAPE_INVALID')
    if kind=='events' and (body.get('ok') is not True or not isinstance(body.get('events'),list)): raise RuntimeError('DAEMON_EVENTS_SHAPE_INVALID')
    return body

def register_daemon_tools(register_tool:Registrar,*,error_cls:type[Exception])->None:
    common=dict(danger_tier='low',category='daemon',approval_required=False,mutating=False,side_effect_class='read',effect_traits=['local_daemon_read','does_not_grant_mutation_authority'],input_schema={'type':'object','properties':{},'additionalProperties':False})
    @register_tool('daemon.health','Read current Daemon health from the local resident service.',**common)
    def daemon_health(payload:JsonObject)->JsonObject:
        try:return _validate('health',_get('/health'))
        except Exception as exc: raise error_cls('DAEMON_UNAVAILABLE',f'{type(exc).__name__}: {exc}',503)
    @register_tool('daemon.status','Read compact current Daemon status.',**common)
    def daemon_status(payload:JsonObject)->JsonObject:
        try:return _validate('status',_get('/status'))
        except Exception as exc: raise error_cls('DAEMON_UNAVAILABLE',f'{type(exc).__name__}: {exc}',503)
    @register_tool('daemon.events','Read bounded recent Daemon events.',**common)
    def daemon_events(payload:JsonObject)->JsonObject:
        try:return _validate('events',_get('/events'))
        except Exception as exc: raise error_cls('DAEMON_UNAVAILABLE',f'{type(exc).__name__}: {exc}',503)
