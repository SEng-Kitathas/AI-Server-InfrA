from __future__ import annotations
import json,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from supervisor.receiver_supervisor import probe

class Handler(BaseHTTPRequestHandler):
    payload={}
    def log_message(self,*args): return
    def do_GET(self):
        raw=json.dumps(type(self).payload).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)

def _probe(payload):
    Handler.payload=payload;server=ThreadingHTTPServer(('127.0.0.1',0),Handler);t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
    try:return probe(f'http://127.0.0.1:{server.server_address[1]}',1.0,'mvf.daemon-health.',expected_identity={'daemon_id':'d1','project_id':'P'})
    finally:server.shutdown();server.server_close();t.join(2)

def test_daemon_starting_is_valid_only_with_bound_identity_schema_and_no_effect_authority():
    ok,detail=_probe({'schema':'mvf.daemon-health.v1','ok':True,'status':'starting','daemon_id':'d1','project_id':'P','mutation_authority':False});assert ok,detail

def test_missing_schema_is_rejected_when_schema_family_expected():
    ok,detail=_probe({'ok':True,'status':'healthy','daemon_id':'d1','project_id':'P','mutation_authority':False});assert not ok and detail=='SCHEMA_IDENTITY_MISSING'

def test_wrong_daemon_identity_is_rejected():
    ok,detail=_probe({'schema':'mvf.daemon-health.v1','ok':True,'status':'healthy','daemon_id':'other','project_id':'P','mutation_authority':False});assert not ok and detail=='HEALTH_IDENTITY_MISMATCH:daemon_id'

def test_wrong_project_identity_is_rejected():
    ok,detail=_probe({'schema':'mvf.daemon-health.v1','ok':True,'status':'healthy','daemon_id':'d1','project_id':'Q','mutation_authority':False});assert not ok and detail=='HEALTH_IDENTITY_MISMATCH:project_id'

def test_daemon_health_claiming_effect_authority_is_rejected():
    ok,detail=_probe({'schema':'mvf.daemon-health.v1','ok':True,'status':'healthy','daemon_id':'d1','project_id':'P','mutation_authority':True});assert not ok and detail=='DAEMON_AUTHORITY_SHAPE_INVALID'
