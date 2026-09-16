from __future__ import annotations

import argparse, json, os, signal, sys, threading, time, importlib, ipaddress
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .daemon_bootstrap import rehydrate
from .daemon_plane import audit as audit_daemon_plane, paths as daemon_paths, atomic_json, service_lease, DaemonPlaneBusy
from .lifecycle import ResidentLifecycle
from .resident import MVFResident, LabToolsAdapter, default_receiver_lab_duties

class ReceiverLabDispatch:
    """Reconnectable bridge to Receiver native read tools. Body absence degrades senses, not Daemon process life."""
    def __init__(self, receiver_root: Path) -> None:
        self.receiver_root=Path(receiver_root).resolve();self.module=None;self._lock=threading.RLock()
    def _load(self):
        with self._lock:
            if self.module is not None:return self.module
            runtime=self.receiver_root/'baseline'/'pcmmad_receiver'
            if not runtime.exists():raise RuntimeError('RECEIVER_TOOL_SUBSTRATE_UNAVAILABLE')
            text=str(runtime)
            if text not in sys.path:sys.path.insert(0,text)
            try:self.module=importlib.import_module('lab_tools')
            except Exception as exc:raise RuntimeError(f'RECEIVER_TOOL_SUBSTRATE_IMPORT_FAILED:{type(exc).__name__}:{exc}') from exc
            return self.module
    def spec_lookup(self,name:str):
        try:return self._load()._TOOL_REGISTRY.get(name)
        except Exception:return None
    def __call__(self,name:str,payload:dict):
        return self._load().dispatch_tool(name,payload)
    def reset(self):
        with self._lock:self.module=None

class DaemonService:
    def __init__(self, *, daemon_root: Path, handoff_dir: Path | None, project_id: str, daemon_id: str, dispatch, interval_seconds: float = 15.0, event_limit: int = 500, handoff_resolver=None) -> None:
        self.daemon_root=daemon_root;self.handoff_dir=handoff_dir;self.handoff_resolver=handoff_resolver;self.project_id=project_id;self.daemon_id=daemon_id;self.interval=max(1.0,float(interval_seconds))
        self.dispatch=dispatch;self.lifecycle=None;self._lifecycle_thread_id=None;self._service_lease_ctx=None;self._last_transition_signature=None
        self.events=deque(maxlen=max(10,int(event_limit)));self._lock=threading.RLock();self.observability_error=None;self._load_persisted_events() ;self._stop=threading.Event();self._thread:threading.Thread|None=None
        self.started_at=time.time();self.started_monotonic=time.monotonic();self.last_cycle_at:float|None=None;self.last_cycle_monotonic:float|None=None;self.last_cycle:dict[str,Any]|None=None;self.last_failure_evidence:dict[str,Any]|None=None;self.last_error:str|None=None;self.cycle_count=0
    @staticmethod
    def _bounded(value, *, max_string:int=2048, max_items:int=64):
        if isinstance(value,str): return value if len(value)<=max_string else value[:max_string]+'...[truncated]'
        if isinstance(value,dict): return {str(k):DaemonService._bounded(v,max_string=max_string,max_items=max_items) for k,v in list(value.items())[:max_items]}
        if isinstance(value,(list,tuple)): return [DaemonService._bounded(v,max_string=max_string,max_items=max_items) for v in list(value)[:max_items]]
        return value

    def _load_persisted_events(self):
        p=daemon_paths(self.daemon_root).status_timeline
        if not p.exists(): return
        try:
            with p.open('rb') as h:
                h.seek(0,os.SEEK_END);size=h.tell();h.seek(max(0,size-262144));raw=h.read()
            for line in raw.splitlines()[-self.events.maxlen:]:
                try:self.events.appendleft(json.loads(line.decode('utf-8')))
                except Exception:continue
        except Exception: return

    def close(self):
        stopped=self.stop()
        life=self.lifecycle
        if stopped is not False and life is not None and (self._thread is None or not self._thread.is_alive()) and self._lifecycle_thread_id==threading.get_ident():
            life.close();self.lifecycle=None;self._lifecycle_thread_id=None
        return stopped
    def _append_timeline(self,row:dict[str,Any]) -> None:
        p=daemon_paths(self.daemon_root);p.status_timeline.parent.mkdir(parents=True,exist_ok=True)
        if p.status_timeline.exists() and p.status_timeline.stat().st_size>4*1024*1024:
            rotated=p.status_timeline.with_name('timeline.1.jsonl');rotated.unlink(missing_ok=True);os.replace(p.status_timeline,rotated)
        with p.status_timeline.open('a',encoding='utf-8',newline='\n') as h:
            h.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n');h.flush();os.fsync(h.fileno())

    def _event(self,kind:str,**data):
        data=self._bounded(data);row={'ts':time.time(),'kind':kind,**data}
        if kind in {'cycle_completed','cycle_failed'}:
            sig=json.dumps({'kind':kind,**data},sort_keys=True,separators=(',',':'))
            if sig==self._last_transition_signature:
                return row
            self._last_transition_signature=sig
        with self._lock:self.events.appendleft(row)
        try:
            self._append_timeline(row)
            if isinstance(self.observability_error,str) and self.observability_error.startswith('timeline:'):self.observability_error=None
        except Exception as exc:
            self.observability_error=f'timeline:{type(exc).__name__}:{exc}'
        return row
    def _ensure_lifecycle(self):
        tid=threading.get_ident()
        if self.lifecycle is None:
            self.lifecycle=ResidentLifecycle.from_daemon_plane(MVFResident(LabToolsAdapter(self.dispatch)),self.daemon_root,self.handoff_dir,daemon_id=self.daemon_id,project_id=self.project_id,handoff_resolver=self.handoff_resolver)
            self._lifecycle_thread_id=tid
        elif self._lifecycle_thread_id!=tid:
            raise RuntimeError('DAEMON_LIFECYCLE_THREAD_MISMATCH')
        return self.lifecycle

    def cycle_once(self):
        try:
            life=self._ensure_lifecycle();result=life.run_cycle(default_receiver_lab_duties(self.project_id));now=time.time();mono=time.monotonic()
            noncurrent=[d for d in result['portfolio']['duties'] if d.get('status')!='CURRENT']
            failure_evidence=None
            if noncurrent:
                try: failure_evidence=self.dispatch('windows.failure_evidence.inspect',{'lookback_hours':1,'text_filter':'PCMMAD','limit':30})
                except Exception as exc: failure_evidence={'ok':False,'status':'UNKNOWN_INCOMPLETE','error':str(self._bounded(f'{type(exc).__name__}: {exc}')),'causation_established':False,'mutation_authority':False}
            with self._lock:self.last_cycle=result;self.last_failure_evidence=failure_evidence;self.last_cycle_at=now;self.last_cycle_monotonic=mono;self.last_error=None;self.cycle_count+=1
            self._event('cycle_completed',overall_status=result['portfolio']['overall_status'],surface_status=result['surface_audit']['status'],decisions_required=result['portfolio']['decisions_required'],failure_evidence_present=bool(failure_evidence));self._persist_status()
            return result
        except Exception as exc:
            with self._lock:self.last_error=str(self._bounded(f'{type(exc).__name__}: {exc}'))
            self._event('cycle_failed',error=self.last_error);self._persist_status();raise
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
        if self._service_lease_ctx is None:
            deadline=time.monotonic()+2.0;ctx=None
            while True:
                ctx=service_lease(self.daemon_root,blocking=False)
                try:ctx.__enter__();break
                except DaemonPlaneBusy:
                    if time.monotonic()>=deadline:raise
                    time.sleep(.05)
            self._service_lease_ctx=ctx
        try:
            self._stop.clear();self._thread=threading.Thread(target=self._loop,name='MVFDaemonInitiative',daemon=True);self._thread.start()
        except Exception:
            ctx=self._service_lease_ctx;self._service_lease_ctx=None
            if ctx is not None:ctx.__exit__(None,None,None)
            raise
    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():self._thread.join(timeout=max(2.0,self.interval+1.0))
        if self._thread and self._thread.is_alive():
            return False
        ctx=self._service_lease_ctx;self._service_lease_ctx=None
        if ctx is not None:ctx.__exit__(None,None,None)
        return True
    def health(self):
        plane=audit_daemon_plane(self.daemon_root);now_mono=time.monotonic();age=None if self.last_cycle_monotonic is None else max(0.0,now_mono-self.last_cycle_monotonic)
        uptime=max(0.0,now_mono-self.started_monotonic);grace=max(self.interval*3,30.0);initiative_alive=self._thread is not None and self._thread.is_alive();first_cycle_ok=(self.last_cycle_monotonic is not None) or uptime<=grace
        healthy=plane.status=='CURRENT' and self.last_error is None and initiative_alive and first_cycle_ok and (age is None or age <= grace)
        status='starting' if healthy and self.last_cycle_at is None else ('degraded' if healthy and self.observability_error else ('healthy' if healthy else ('stalled' if initiative_alive and self.last_cycle_at is None else 'degraded')))
        return {'schema':'mvf.daemon-health.v1','ok':healthy,'status':status,'daemon_id':self.daemon_id,'project_id':self.project_id,'plane_status':plane.status,'initiative_alive':bool(self._thread and self._thread.is_alive()),'last_cycle_age_seconds':age,'last_error':self.last_error,'observability_error':self.observability_error,'mutation_authority':False}
    def _status_snapshot(self):
        with self._lock:
            compact=(self.last_cycle or {}).get('portfolio',{}).get('compact') if self.last_cycle else None
            continuity=(self.last_cycle or {}).get('continuity_enforcement') if self.last_cycle else None
            return self._bounded({'schema':'mvf.daemon-status.v1','daemon_id':self.daemon_id,'project_id':self.project_id,'started_at_epoch':self.started_at,'cycle_count':self.cycle_count,'last_cycle_at_epoch':self.last_cycle_at,'last_error':self.last_error,'compact':compact,'surface_status':(self.last_cycle or {}).get('surface_audit',{}).get('status') if self.last_cycle else None,'continuity_enforcement':continuity,'failure_evidence':self.last_failure_evidence,'observability_error':self.observability_error,'mutation_authority':False})
    def _persist_status(self):
        try:
            atomic_json(daemon_paths(self.daemon_root).status_current,self._status_snapshot())
            if isinstance(self.observability_error,str) and self.observability_error.startswith('status:'):self.observability_error=None
        except Exception as exc:
            self.observability_error=f'status:{type(exc).__name__}:{exc}'
    def status(self):
        return self._status_snapshot()
    def event_rows(self,limit:int|None=None):
        with self._lock:
            rows=list(self.events)
        return rows if limit is None else rows[:max(0,int(limit))]

class _Handler(BaseHTTPRequestHandler):
    server_version='MVFDaemon/1'
    def log_message(self,*args):return
    def _send(self,code:int,obj:Any):
        raw=json.dumps(obj,sort_keys=True,separators=(',',':')).encode('utf-8');self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        svc=self.server.daemon_service
        if self.path=='/health':
            snapshot=svc.health();self._send(200 if snapshot['ok'] else 503,snapshot);return
        if self.path=='/status':self._send(200,svc.status());return
        if self.path=='/events':self._send(200,{'schema':'mvf.daemon-events.v1','ok':True,'daemon_id':svc.daemon_id,'project_id':svc.project_id,'mutation_authority':False,'events':svc.event_rows(limit=50)});return
        self._send(404,{'ok':False,'error':'NOT_FOUND'})

def _validate_bind_host(host:str) -> None:
    if str(host).casefold()=='localhost': return
    try:
        if ipaddress.ip_address(str(host)).is_loopback:return
    except ValueError:pass
    raise ValueError('DAEMON_BIND_MUST_BE_LOOPBACK')

def serve(service:DaemonService,host:str='127.0.0.1',port:int=5015):
    _validate_bind_host(host)
    httpd=ThreadingHTTPServer((host,int(port)),_Handler);httpd.daemon_service=service;service.start()
    stop=threading.Event()
    def _stop(*_):stop.set();threading.Thread(target=httpd.shutdown,daemon=True).start()
    for sig in (signal.SIGINT,signal.SIGTERM):
        try:signal.signal(sig,_stop)
        except Exception:pass
    try:httpd.serve_forever(poll_interval=0.5)
    finally:service.close();httpd.server_close()

def main(argv=None):
    ap=argparse.ArgumentParser();ap.add_argument('--daemon-root',required=True);ap.add_argument('--handoff-dir');ap.add_argument('--handoff-root');ap.add_argument('--project-id',default='RECEIVER-LAB');ap.add_argument('--daemon-id',default='pcmmad-daemon');ap.add_argument('--receiver-root',required=True);ap.add_argument('--host-lock');ap.add_argument('--host',default='127.0.0.1');ap.add_argument('--port',type=int,default=5015);ap.add_argument('--interval-seconds',type=float,default=15.0);args=ap.parse_args(argv)
    receiver_root=Path(args.receiver_root).resolve();dispatch=ReceiverLabDispatch(receiver_root)
    if not args.handoff_dir and not args.handoff_root:ap.error('one of --handoff-dir or --handoff-root is required')
    handoff_resolver=None;handoff_dir=Path(args.handoff_dir) if args.handoff_dir else None
    if args.handoff_root:
        from .project_handoff import resolve as resolve_project_handoff
        handoff_root=Path(args.handoff_root);handoff_resolver=lambda:resolve_project_handoff(handoff_root)
        handoff_resolver()
    root=Path(args.daemon_root);
    if root.exists():rehydrate(root,expected_daemon_id=args.daemon_id,expected_project_id=args.project_id)
    svc=DaemonService(daemon_root=root,handoff_dir=handoff_dir,project_id=args.project_id,daemon_id=args.daemon_id,dispatch=dispatch,interval_seconds=args.interval_seconds,handoff_resolver=handoff_resolver)
    if args.host_lock:
        from .daemon_plane import plane_lock
        with plane_lock(Path(args.host_lock),blocking=False): serve(svc,args.host,args.port)
    else: serve(svc,args.host,args.port)
    return 0

if __name__=='__main__':raise SystemExit(main())
