from __future__ import annotations
import hashlib,json,tempfile,threading,urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from mvf_resident.daemon_service import DaemonService,_Handler
from mvf_resident.daemon_plane import paths,initialize
from mvf_resident.scar_intelligence import collect_scars,write_index
from mvf_resident.surfaces import REQUIRED_ACTIVE_SURFACES

def _handoff(root:Path):
    files={}
    for n in REQUIRED_ACTIVE_SURFACES:
        p=root/n;p.write_text(n,encoding='utf-8');b=p.read_bytes();files[n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    (root/'DOCTRINE_SNAPSHOT.md').write_text('`PRETTY DASHBOARD != COCKPIT`\n`LONG GLOBAL SUITE != SYNCHRONOUS EXECUTION.RUN WORKLOAD`\n',encoding='utf-8')
    b=(root/'DOCTRINE_SNAPSHOT.md').read_bytes();files['DOCTRINE_SNAPSHOT.md']={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    cp=files['THREAD_CONTINUITY_CHECKPOINT_2026-09-15.md']['sha256'];(root/'SNAPSHOT_MANIFEST_SHA256.json').write_text(json.dumps({'updated_at':'2026-09-15T00:00:00+00:00','continuity_checkpoint_sha256':cp,'files':files}),encoding='utf-8')

def _dispatch(name,payload):return {'ok':True}

def test_route_without_index_is_bounded_unavailable():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);h=b/'h';h.mkdir();_handoff(h);svc=DaemonService(daemon_root=b/'daemon',handoff_dir=h,project_id='P',daemon_id='d1',dispatch=_dispatch)
        try:
            result=svc.scar_route('hud cockpit',3);assert result['ok'] is False;assert result['status']=='index_unavailable';assert result['mutation_authority'] is False
        finally:svc.close()

def test_context_route_selects_hud_scar_and_preserves_non_authority():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);h=b/'h';h.mkdir();_handoff(h);root=b/'daemon';dp=initialize(root,daemon_id='d1',project_id='P');write_index(collect_scars(h),dp.scar_index);svc=DaemonService(daemon_root=root,handoff_dir=h,project_id='P',daemon_id='d1',dispatch=_dispatch)
        try:
            result=svc.scar_route('hud cockpit dashboard warning display',2);assert result['ok'] is True;assert result['daemon_id']=='d1';assert result['project_id']=='P';assert result['mutation_authority'] is False;assert any(x['expression']=='PRETTY DASHBOARD != COCKPIT' for x in result['routing']['selected'])
        finally:svc.close()

def test_http_scar_route_is_read_only_identity_bound():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);h=b/'h';h.mkdir();_handoff(h);root=b/'daemon';dp=initialize(root,daemon_id='d1',project_id='P');write_index(collect_scars(h),dp.scar_index);svc=DaemonService(daemon_root=root,handoff_dir=h,project_id='P',daemon_id='d1',dispatch=_dispatch);server=ThreadingHTTPServer(('127.0.0.1',0),_Handler);server.daemon_service=svc;t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{server.server_address[1]}/scars/route?context=hud%20cockpit&limit=1',timeout=2) as resp:body=json.loads(resp.read().decode())
            assert body['ok'] is True;assert body['daemon_id']=='d1';assert body['project_id']=='P';assert body['mutation_authority'] is False;assert len(body['routing']['selected'])<=1
        finally:server.shutdown();server.server_close();t.join(2);svc.close()
