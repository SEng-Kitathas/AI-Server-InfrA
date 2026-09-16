from __future__ import annotations
import json,time,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import supervisor.receiver_supervisor as rs
from supervisor.ngrok_supervisor import probe_ngrok

class H(BaseHTTPRequestHandler):
    payload={}
    def log_message(self,*a): return
    def do_GET(self):
        raw=json.dumps(type(self).payload).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)

def _serve(payload):
    H.payload=payload;s=ThreadingHTTPServer(('127.0.0.1',0),H);t=threading.Thread(target=s.serve_forever,daemon=True);t.start();return s,t

def test_ngrok_probe_requires_expected_public_url_and_upstream():
    payload={'tunnels':[{'public_url':'https://x.example','config':{'addr':'http://127.0.0.1:5000'}}]};s,t=_serve(payload)
    try:
        url=f'http://127.0.0.1:{s.server_address[1]}/api/tunnels'
        assert probe_ngrok(url,1,'https://x.example','http://127.0.0.1:5000')==(True,None)
        assert probe_ngrok(url,1,'https://wrong.example','http://127.0.0.1:5000')[0] is False
        assert probe_ngrok(url,1,'https://x.example','http://127.0.0.1:5001')[0] is False
    finally:s.shutdown();s.server_close();t.join(2)

def test_restart_budget_survives_supervisor_process_restart(tmp_path):
    state={'restart_events':[],'state_status':'FRESH'};calls=[];now=time.time()
    probe=lambda *_:(False,'down');trigger=lambda task:(calls.append(task) or True,'ok')
    rs.supervise_once(health_url='x',task_name='T',receipt_path=tmp_path/'r1.json',health_probe=probe,trigger=trigger,recovery_seconds=0,poll_seconds=0,failure_state=state,max_restarts=2,restart_window_seconds=60,now_monotonic=lambda:now)
    rs.supervise_once(health_url='x',task_name='T',receipt_path=tmp_path/'r2.json',health_probe=probe,trigger=trigger,recovery_seconds=0,poll_seconds=0,failure_state=state,max_restarts=2,restart_window_seconds=60,now_monotonic=lambda:now+1)
    rs.save_failure_state(tmp_path/'failure.json',state)
    restored=rs.load_failure_state(tmp_path/'failure.json',max_restarts=2,restart_window_seconds=60)
    held=rs.supervise_once(health_url='x',task_name='T',receipt_path=tmp_path/'r3.json',health_probe=probe,trigger=trigger,recovery_seconds=0,poll_seconds=0,failure_state=restored,max_restarts=2,restart_window_seconds=60,now_monotonic=lambda:now+2)
    assert held['action']=='CRASH_LOOP_HOLD';assert len(calls)==2

def test_corrupt_restart_budget_fails_conservatively_but_bounded(tmp_path):
    path=tmp_path/'failure.json';path.write_text('{broken',encoding='utf-8');state=rs.load_failure_state(path,max_restarts=3,restart_window_seconds=60)
    assert state['state_status']=='CORRUPT_HOLD';assert len(state['restart_events'])==3
    held=rs.supervise_once(health_url='x',task_name='T',receipt_path=tmp_path/'r.json',health_probe=lambda *_:(False,'down'),trigger=lambda _:(True,'x'),failure_state=state,max_restarts=3,restart_window_seconds=60,now_monotonic=time.time)
    assert held['action']=='CRASH_LOOP_HOLD';assert held['crash_loop']['state_status']=='CORRUPT_HOLD'

def test_trigger_receipt_has_workload_neutral_family_and_exact_target(tmp_path):
    state={'restart_events':[]};seq=iter([(False,'down'),(True,None)])
    def hp(*_): return next(seq)
    r=rs.supervise_once(health_url='x',task_name='DAEMON_TASK',receipt_path=tmp_path/'r.json',health_probe=hp,trigger=lambda _:(True,'ok'),recovery_seconds=.01,poll_seconds=.001,failure_state=state,max_restarts=3,restart_window_seconds=60,now_monotonic=time.time)
    assert r['action_family']=='TRIGGER_CANONICAL_TASK';assert r['target_task']=='DAEMON_TASK'
