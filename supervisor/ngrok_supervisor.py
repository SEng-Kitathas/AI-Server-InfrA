#!/usr/bin/env python3
from __future__ import annotations

import argparse,json,urllib.request
from pathlib import Path

try:
    from .receiver_supervisor import acquire_singleton, supervise_loop
except ImportError:
    from receiver_supervisor import acquire_singleton, supervise_loop

def probe_ngrok(url:str, timeout:float, expected_public_url:str|None=None, expected_upstream:str|None=None) -> tuple[bool,str|None]:
    try:
        with urllib.request.urlopen(url,timeout=timeout) as response:
            body=json.loads(response.read(262144).decode('utf-8'))
        tunnels=body.get('tunnels') if isinstance(body,dict) else None
        if not isinstance(tunnels,list) or not tunnels:return False,'NGROK_TUNNELS_MISSING'
        matches=[]
        for tunnel in tunnels:
            if not isinstance(tunnel,dict):continue
            if expected_public_url and str(tunnel.get('public_url') or '')!=str(expected_public_url):continue
            if expected_upstream and str((tunnel.get('config') or {}).get('addr') or '')!=str(expected_upstream):continue
            matches.append(tunnel)
        if not matches:return False,'NGROK_TUNNEL_IDENTITY_MISMATCH'
        return True,None
    except Exception as exc:
        return False,f'{type(exc).__name__}: {exc}'

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--health-url',default='http://127.0.0.1:4040/api/tunnels');ap.add_argument('--expected-public-url',required=True);ap.add_argument('--expected-upstream',default='http://127.0.0.1:5000');ap.add_argument('--task-name',default='PCMMAD_V30_Ngrok_SYSTEM');ap.add_argument('--receipt',required=True);ap.add_argument('--stop-file');ap.add_argument('--lock-file',required=True);ap.add_argument('--failure-state-file');ap.add_argument('--interval-seconds',type=float,default=10.0);ap.add_argument('--recovery-seconds',type=float,default=20.0);ap.add_argument('--max-restarts',type=int,default=3);ap.add_argument('--restart-window-seconds',type=float,default=300.0);ap.add_argument('--hold-max-age-seconds',type=float,default=7200.0);args=ap.parse_args()
    fd=acquire_singleton(Path(args.lock_file))
    if fd is None:return 73
    hp=lambda url,timeout,*_args:probe_ngrok(url,timeout,args.expected_public_url,args.expected_upstream)
    return supervise_loop(health_url=args.health_url,task_name=args.task_name,receipt_path=Path(args.receipt),interval_seconds=max(1,args.interval_seconds),recovery_seconds=args.recovery_seconds,stop_path=Path(args.stop_file) if args.stop_file else None,max_restarts=max(1,args.max_restarts),restart_window_seconds=max(10,args.restart_window_seconds),hold_max_age_seconds=max(60,args.hold_max_age_seconds),expected_schema_family=None,expected_identity=None,failure_state_path=Path(args.failure_state_file) if args.failure_state_file else None,health_probe=hp,receipt_action='TRIGGER_CANONICAL_NGROK_TASK')

if __name__=='__main__':raise SystemExit(main())
