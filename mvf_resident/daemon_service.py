from __future__ import annotations

import argparse, json, os, signal, sys, threading, time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .daemon_bootstrap import rehydrate
from .daemon_plane import audit as audit_daemon_plane, paths as daemon_paths, atomic_json
from .lifecycle import ResidentLifecycle
from .resident import MVFResident, LabToolsAdapter, default_receiver_lab_duties

class DaemonService:
    def __init__(self, *, daemon_root: Path, handoff_dir: Path, project_id: str, daemon_id: str, dispatch, interval_seconds: float = 15.0, event_limit: int = 500) -> None:
        self.daemon_root=daemon_root;self.handoff_dir=handoff_dir;self.project_id=project_id;self.daemon_id=daemon_id;self.interval=max(1.0,float(interval_seconds))
        self.dispatch=dispatch;self.lifecycle=None;self._lifecycle_thread_id=None
        self.events=deque(maxlen=max(10,int(event_limit)));self._lock=threading.RLock();self._stop=threading.Event();self._thread:threading.Thread|None=None
        self.started_at=time.time();self.last_cycle_at:float|None=None;self.last_cycle:dict[str,Any]|None=None;self.last_error:str|None=None;self.cycle_count=0
    def close(self):
        self.stop()
    def _event(self,kind:str,**data):
        row={'ts':time.time(),'kind':kind,**data}
        with self._lock:self.events.appendleft(row)
        p=daemon_paths(self.daemon_root);p.status_timeline.parent.mkdir(parents=True,exist_ok=True)
        with p.status_timeline.open('a',encoding='utf-8',newline='\n') as h:
            h.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n');h.flush();os.fsync(h.fileno())
        return row
    def _ensure_lifecycle(self):
        tid=threading.get_ident()
        if self.lifecycle is None:
            self.lifecycle=ResidentLifecycle.from_daemon_plane(MVFResident(LabToolsAdapter(self.dispatch)),self.daemon_root,self.handoff_dir,daemon_id=self.daemon_id,project_id=self.project_id)
            self._lifecycle_thread_id=tid
        elif self._lifecycle_thread_id!=tid:
            raise RuntimeError('DAEMON_LIFECYCLE_THREAD_MISMATCH')
        return self.lifecycle

    def cycle_once(self):
        try:
            life=self._ensure_lifecycle();result=life.run_cycle(default_receiver_lab_duties(self.project_id));now=time.time()
            with self._lock:self.last_cycle=result;self.last_cycle_at=now;self.last_error=None;self.cycle_count+=1
            self._event('cycle_completed',overall_status=result['portfolio']['overall_status'],surface_status=result['surface_audit']['status'],decisions_required=result['portfolio']['decisions_required'])
            return result
        except Exception as exc:
            with self._lock:self.last_error=f'{type(exc).__name__}: {exc}'
            self._event('cycle_failed',error=self.last_error);raise
    def _loop(self):
        self._event('initiative_loop_started',interval_seconds=self.interval)
        try:
            while not self._stop.is_set():
                started=time.monotonic()
                try:self.cycle_once()
                except Exception:pass
                delay=max(0.0,self.interval-(time.monotonic()-started));self._stop.wait(delay)
        finally:
            life=self.lifecycle
            if life is not None and self._lifecycle_thread_id==threading.get_ident():
                life.close();self.lifecycle=None;self._lifecycle_thread_id=None
            self._event('initiative_loop_stopped')
    def start(self):
        if self._thread and self._thread.is_alive():return
        self._stop.clear();self._thread=threading.Thread(target=self._loop,name='MVFDaemonInitiative',daemon=True);self._thread.start()
    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():self._thread.join(timeout=max(2.0,self.interval+1.0))
    def health(self):
        plane=audit_daemon_plane(self.daemon_root);age=None if self.last_cycle_at is None else max(0.0,time.time()-self.last_cycle_at)
        healthy=plane.status=='CURRENT' and self.last_error is None and self._thread is not None and self._thread.is_alive() and (age is None or age <= max(self.interval*3,30.0))
        return {'schema':'mvf.daemon-health.v1','ok':healthy,'status':'healthy' if healthy else 'degraded','daemon_id':self.daemon_id,'project_id':self.project_id,'plane_status':plane.status,'initiative_alive':bool(self._thread and self._thread.is_alive()),'last_cycle_age_seconds':age,'last_error':self.last_error,'mutation_authority':False}
    def status(self):
        with self._lock:
            compact=(self.last_cycle or {}).get('portfolio',{}).get('compact') if self.last_cycle else None
            row={'schema':'mvf.daemon-status.v1','daemon_id':self.daemon_id,'project_id':self.project_id,'started_at_epoch':self.started_at,'cycle_count':self.cycle_count,'last_cycle_at_epoch':self.last_cycle_at,'last_error':self.last_error,'compact':compact,'surface_status':(self.last_cycle or {}).get('surface_audit',{}).get('status') if self.last_cycle else None,'mutation_authority':False}
        try:atomic_json(daemon_paths(self.daemon_root).status_current,row)
        except Exception:pass
        return row
    def event_rows(self):
        with self._lock:return list(self.events)

class _Handler(BaseHTTPRequestHandler):
    server_version='MVFDaemon/1'
    def log_message(self,*args):return
    def _send(self,code:int,obj:Any):
        raw=json.dumps(obj,sort_keys=True,separators=(',',':')).encode('utf-8');self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        svc=self.server.daemon_service
        if self.path=='/health':self._send(200 if svc.health()['ok'] else 503,svc.health());return
        if self.path=='/status':self._send(200,svc.status());return
        if self.path=='/events':self._send(200,{'ok':True,'events':svc.event_rows()});return
        self._send(404,{'ok':False,'error':'NOT_FOUND'})

def serve(service:DaemonService,host:str='127.0.0.1',port:int=5015):
    httpd=ThreadingHTTPServer((host,int(port)),_Handler);httpd.daemon_service=service;service.start()
    stop=threading.Event()
    def _stop(*_):stop.set();threading.Thread(target=httpd.shutdown,daemon=True).start()
    for sig in (signal.SIGINT,signal.SIGTERM):
        try:signal.signal(sig,_stop)
        except Exception:pass
    try:httpd.serve_forever(poll_interval=0.5)
    finally:service.close();httpd.server_close()

def main(argv=None):
    ap=argparse.ArgumentParser();ap.add_argument('--daemon-root',required=True);ap.add_argument('--handoff-dir',required=True);ap.add_argument('--project-id',default='RECEIVER-LAB');ap.add_argument('--daemon-id',default='pcmmad-daemon');ap.add_argument('--receiver-root',required=True);ap.add_argument('--host',default='127.0.0.1');ap.add_argument('--port',type=int,default=5015);ap.add_argument('--interval-seconds',type=float,default=15.0);args=ap.parse_args(argv)
    receiver_root=Path(args.receiver_root).resolve();sys.path.insert(0,str(receiver_root/'baseline'/'pcmmad_receiver'));import lab_tools
    root=Path(args.daemon_root);
    if root.exists():rehydrate(root,expected_daemon_id=args.daemon_id,expected_project_id=args.project_id)
    svc=DaemonService(daemon_root=root,handoff_dir=Path(args.handoff_dir),project_id=args.project_id,daemon_id=args.daemon_id,dispatch=lab_tools.dispatch_tool,interval_seconds=args.interval_seconds)
    serve(svc,args.host,args.port);return 0

if __name__=='__main__':raise SystemExit(main())
