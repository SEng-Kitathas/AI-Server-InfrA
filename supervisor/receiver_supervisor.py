#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def probe(url: str, timeout: float, expected_schema_family: str | None = None, identity_url: str | None = None, minimum_capabilities: int = 1, expected_identity: dict[str,str] | None = None) -> tuple[bool, str | None]:
    try:
        api_key = str(os.environ.get("GITHOME_API_KEY") or "").strip()
        request = urllib.request.Request(url, headers={"X-GitHome-Key": api_key}) if api_key and str(url).lower().startswith(("http://", "https://")) else url
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if not (200 <= int(response.status) < 300): return False, f"HTTP {response.status}"
            raw=response.read(262144)
        try: body=json.loads(raw.decode("utf-8"))
        except Exception as exc:return False,f"INVALID_HEALTH_JSON: {type(exc).__name__}: {exc}"
        if not isinstance(body,dict):return False,"INVALID_HEALTH_SHAPE"
        if body.get("ok") is not True:return False,"CORE_NOT_OK"
        status=str(body.get("status") or "").lower()
        allowed_status={"ok","healthy","degraded"}
        if expected_schema_family and str(expected_schema_family).startswith("mvf.daemon-health."):allowed_status.add("starting")
        if status not in allowed_status:return False,f"CORE_STATUS:{status or 'missing'}"
        schema=str(body.get("schema_version") or body.get("schema") or "")
        daemon_health_family=bool(expected_schema_family and str(expected_schema_family).startswith("mvf.daemon-health."))
        # Receiver/core identity is verified by the dedicated identity endpoint when supplied.
        # Daemon deliberately self-identifies in /health and therefore must carry schema here.
        if expected_schema_family and not identity_url:
            if not schema:return False,"SCHEMA_IDENTITY_MISSING"
            if not schema.startswith(expected_schema_family):return False,f"SCHEMA_IDENTITY_MISMATCH:{schema}"
        if expected_identity:
            for key,expected in expected_identity.items():
                if str(body.get(key) or '') != str(expected):return False,f"HEALTH_IDENTITY_MISMATCH:{key}"
        if daemon_health_family:
            if not str(body.get('daemon_id') or '').strip():return False,"DAEMON_IDENTITY_MISSING"
            if not str(body.get('project_id') or '').strip():return False,"DAEMON_PROJECT_MISSING"
            if body.get('mutation_authority') is not False:return False,"DAEMON_AUTHORITY_SHAPE_INVALID"
        if identity_url:
            try:
                with urllib.request.urlopen(identity_url,timeout=timeout) as ir:
                    if not (200 <= int(ir.status) < 300):return False,f"IDENTITY_HTTP:{ir.status}"
                    ident=json.loads(ir.read(262144).decode("utf-8"))
            except Exception as exc:return False,f"IDENTITY_UNAVAILABLE:{type(exc).__name__}:{exc}"
            if not isinstance(ident,dict) or ident.get("ok") is not True:return False,"IDENTITY_INVALID"
            ischema=str(ident.get("schema_version") or "")
            if expected_schema_family and not ischema.startswith(expected_schema_family):return False,f"SCHEMA_INCOMPATIBLE:{ischema or 'missing'}"
            count=int(ident.get("capability_count") or 0)
            if count < minimum_capabilities:return False,f"CAPABILITY_FLOOR:{count}<{minimum_capabilities}"
            if not ident.get("catalog_digest"):return False,"CATALOG_IDENTITY_MISSING"
        return True,None
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def classify_readiness(*, service_ok: bool, service_detail: str | None, observed_catalog_digest: str | None = None, expected_catalog_digest: str | None = None) -> dict:
    if not service_ok:return {"service_ready":False,"deployment_current":False,"status":"SERVICE_NOT_READY","detail":service_detail}
    current=bool(expected_catalog_digest and observed_catalog_digest and expected_catalog_digest==observed_catalog_digest)
    return {"service_ready":True,"deployment_current":current,"status":"SERVICE_READY_DEPLOYMENT_CURRENT" if current else "SERVICE_READY_DEPLOYMENT_NOT_CURRENT","detail":service_detail}


def boot_recovery_classification(interrupted:dict | None) -> dict:
    """Classify persisted interrupted control state; never equate service restart with consequence reconciliation."""
    if not interrupted:return {"service_can_start":True,"control_state":"CLEAN","continuity_recoverable":True}
    status=str(interrupted.get("status") or "")
    if status in {"RELEASED","COMPLETED","RECONCILED_INVALID"}:return {"service_can_start":True,"control_state":"CLEAN","continuity_recoverable":True}
    if status=="ACTIVE" and not interrupted.get("lease_id"):
        return {"service_can_start":True,"control_state":"RECONCILIATION_REQUIRED","continuity_recoverable":False,"reason":"ACTIVE_AUTHORITY_WITHOUT_USABLE_LEASE"}
    if interrupted.get("consequence_active"):
        return {"service_can_start":True,"control_state":"INTERRUPTED_CONSEQUENCE_REVIEW","continuity_recoverable":False,"reason":"CONSEQUENCE_WAS_ACTIVE_AT_INTERRUPTION"}
    return {"service_can_start":True,"control_state":"UNKNOWN_INTERRUPTED_STATE","continuity_recoverable":False}


def hold_state(stop_path: Path | None, *, now_epoch: float | None = None, max_hold_seconds: float = 21600.0) -> dict:
    if stop_path is None or not stop_path.exists():return {"hold":False,"status":"RUNNING_DESIRED"}
    try:data=json.loads(stop_path.read_text(encoding="utf-8"))
    except Exception:return {"hold":False,"status":"INVALID_HOLD_IGNORED","reason":"UNPARSEABLE"}
    if not isinstance(data,dict) or data.get("desired_state")!="STOPPED":return {"hold":False,"status":"INVALID_HOLD_IGNORED","reason":"BAD_SHAPE"}
    expires=float(data.get("expires_at_epoch") or 0);now=time.time() if now_epoch is None else now_epoch
    if expires<=now:return {"hold":False,"status":"EXPIRED_HOLD_IGNORED"}
    if expires-now>max_hold_seconds:return {"hold":False,"status":"INVALID_HOLD_IGNORED","reason":"HOLD_EXCEEDS_MAXIMUM"}
    if not str(data.get("operator_id") or "").strip() or not str(data.get("reason") or "").strip():return {"hold":False,"status":"INVALID_HOLD_IGNORED","reason":"OPERATOR_REASON_REQUIRED"}
    return {"hold":True,"status":"MAINTENANCE_HOLD","operator_id":data["operator_id"],"reason":data["reason"],"expires_at_epoch":expires}


def trigger_task(task_name: str) -> tuple[bool, str]:
    proc = subprocess.run(["schtasks", "/Run", "/TN", task_name], text=True, capture_output=True, timeout=15)
    detail = (proc.stdout + "\n" + proc.stderr).strip()[-2000:]
    return proc.returncode == 0, detail


def _process_creation_100ns(pid:int)->int|None:
    if pid<=0:return None
    try:
        import ctypes
        from ctypes import wintypes
        h=ctypes.windll.kernel32.OpenProcess(0x1000,False,pid)
        if not h:return None
        creation=wintypes.FILETIME();exit_t=wintypes.FILETIME();kernel=wintypes.FILETIME();user=wintypes.FILETIME()
        ok=ctypes.windll.kernel32.GetProcessTimes(h,ctypes.byref(creation),ctypes.byref(exit_t),ctypes.byref(kernel),ctypes.byref(user));ctypes.windll.kernel32.CloseHandle(h)
        if not ok:return None
        return (int(creation.dwHighDateTime)<<32)|int(creation.dwLowDateTime)
    except Exception:return None

def acquire_singleton(lock_path: Path):
    """Exclusive supervisor lock bound to PID + process creation identity."""
    lock_path.parent.mkdir(parents=True,exist_ok=True);own_creation=_process_creation_100ns(os.getpid())
    for _ in range(2):
        try:
            fd=os.open(str(lock_path),os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,f"pid={os.getpid()}\ncreation_100ns={own_creation or 0}\nstarted={utc_now()}\n".encode());return fd
        except FileExistsError:
            try:
                rows=dict(x.split("=",1) for x in lock_path.read_text(encoding="utf-8",errors="ignore").splitlines() if "=" in x);pid=int(rows.get("pid","0"));recorded=int(rows.get("creation_100ns","0"))
            except Exception:return None
            if pid<=0 or recorded<=0:return None
            observed=_process_creation_100ns(pid)
            if observed is not None and recorded>0 and observed==recorded:return None
            # Dead PID, PID reuse, or legacy/unverifiable lock cannot permanently strand HA.
            try:lock_path.unlink()
            except OSError:return None
    return None

def write_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, sort_keys=True, indent=2)
            handle.write("\n")
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def supervise_once(*, health_url: str, task_name: str, receipt_path: Path, timeout: float = 3.0, recovery_seconds: float = 20.0, poll_seconds: float = 1.0, trigger=trigger_task, health_probe=probe, failure_state: dict | None = None, max_restarts: int = 3, restart_window_seconds: float = 300.0, now_monotonic=time.time, expected_schema_family: str | None = None, expected_identity: dict[str,str] | None = None, hold_check:Callable[[],dict]|None=None, receipt_action:str='TRIGGER_CANONICAL_RECEIVER_TASK', failure_state_persist:Callable[[dict],None]|None=None) -> dict:
    checked_at = utc_now()
    try: healthy, error = health_probe(health_url, timeout, expected_schema_family, None, 1, expected_identity)
    except TypeError: healthy, error = health_probe(health_url, timeout)
    receipt = {"schema":"pcmmad.receiver-supervisor.v1","checked_at":checked_at,"health_url":health_url,"task_name":task_name,"healthy_before":healthy,"probe_error_before":error,"action":"NONE","triggered":False,"healthy_after":healthy,"probe_error_after":error}
    if healthy:
        write_atomic(receipt_path, receipt)
        return receipt
    if hold_check is not None:
        hs=hold_check()
        if hs.get("hold"):
            receipt.update({"desired_state":"STOPPED","action":"MAINTENANCE_HOLD","triggered":False,"healthy_after":False,"hold_status":hs.get("status"),"operator_id":hs.get("operator_id"),"reason":hs.get("reason"),"expires_at_epoch":hs.get("expires_at_epoch")});write_atomic(receipt_path,receipt);return receipt
    if failure_state is not None:
        now=now_monotonic();events=[float(x) for x in failure_state.get("restart_events",[]) if now-float(x)<=restart_window_seconds];failure_state["restart_events"]=events
        if len(events)>=max_restarts:
            receipt["action"]="CRASH_LOOP_HOLD";receipt["triggered"]=False;receipt["healthy_after"]=False;receipt["crash_loop"]={"events":len(events),"window_seconds":restart_window_seconds,"max_restarts":max_restarts,"state_status":failure_state.get("state_status")};write_atomic(receipt_path,receipt);return receipt
        events.append(now);failure_state["restart_events"]=events
        if failure_state_persist is not None:failure_state_persist(failure_state)
    ok, detail = trigger(task_name)
    receipt["action"] = receipt_action
    receipt["action_family"] = "TRIGGER_CANONICAL_TASK"
    receipt["target_task"] = task_name
    receipt["triggered"] = ok
    receipt["trigger_detail"] = detail
    deadline = time.monotonic() + recovery_seconds
    final_error = error
    while time.monotonic() < deadline:
        try: healthy, final_error = health_probe(health_url, timeout, expected_schema_family, None, 1, expected_identity)
        except TypeError: healthy, final_error = health_probe(health_url, timeout)
        if healthy:
            break
        time.sleep(poll_seconds)
    receipt["healthy_after"] = healthy
    receipt["probe_error_after"] = final_error
    receipt["completed_at"] = utc_now()
    write_atomic(receipt_path, receipt)
    return receipt


def load_failure_state(path: Path | None, *, max_restarts:int, restart_window_seconds:float) -> dict:
    if path is None or not path.exists(): return {"restart_events":[],"state_status":"FRESH"}
    now=time.time()
    try:
        raw=json.loads(path.read_text(encoding="utf-8-sig"));events=[float(x) for x in raw.get("restart_events",[])]
        if any(x<0 or x>now+60 for x in events): raise ValueError("restart event outside sane epoch range")
        events=[x for x in events if now-x<=restart_window_seconds]
        return {"restart_events":events,"state_status":"RESTORED"}
    except Exception:
        # Corrupt safety state must not silently erase the restart budget. Hold for one window, then self-recover.
        return {"restart_events":[now]*max_restarts,"state_status":"CORRUPT_HOLD"}

def save_failure_state(path: Path | None, state: dict) -> None:
    if path is None:return
    write_atomic(path,{"schema":"pcmmad.supervisor-failure-state.v1","updated_at":utc_now(),"restart_events":[float(x) for x in state.get("restart_events",[])],"state_status":state.get("state_status")})

def supervise_loop(*, health_url: str, task_name: str, receipt_path: Path, interval_seconds: float = 10.0, timeout: float = 3.0, recovery_seconds: float = 20.0, stop_path: Path | None = None, max_restarts: int = 3, restart_window_seconds: float = 300.0, hold_max_age_seconds: float = 7200.0, expected_schema_family: str | None = None, expected_identity:dict[str,str]|None=None, failure_state_path:Path|None=None, health_probe:Callable[...,tuple[bool,str|None]]=probe, receipt_action:str='TRIGGER_CANONICAL_RECEIVER_TASK') -> int:
    """Continuously reconcile RUNNING desired state. A stop file changes desired state; killing a process does not."""
    failure_state=load_failure_state(failure_state_path,max_restarts=max_restarts,restart_window_seconds=restart_window_seconds)
    while True:
        hs=hold_state(stop_path,max_hold_seconds=hold_max_age_seconds)
        if hs.get("hold"):
            receipt={"schema":"pcmmad.receiver-supervisor.v1","checked_at":utc_now(),"desired_state":"STOPPED","action":"MAINTENANCE_HOLD","healthy_after":False,"hold_status":hs.get("status"),"operator_id":hs.get("operator_id"),"reason":hs.get("reason"),"expires_at_epoch":hs.get("expires_at_epoch")}
            write_atomic(receipt_path,receipt);time.sleep(interval_seconds);continue
        supervise_once(health_url=health_url,task_name=task_name,receipt_path=receipt_path,timeout=timeout,recovery_seconds=recovery_seconds,failure_state=failure_state,max_restarts=max_restarts,restart_window_seconds=restart_window_seconds,expected_schema_family=expected_schema_family,expected_identity=expected_identity,health_probe=health_probe,hold_check=(lambda:hold_state(stop_path,max_hold_seconds=hold_max_age_seconds)),receipt_action=receipt_action,failure_state_persist=(lambda st:save_failure_state(failure_state_path,st)))
        save_failure_state(failure_state_path,failure_state)
        time.sleep(interval_seconds)

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--health-url", default="http://127.0.0.1:5000/health")
    parser.add_argument("--task-name", default="PCMMAD_V30_Receiver")
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--recovery-seconds", type=float, default=20.0)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--interval-seconds", type=float, default=10.0)
    parser.add_argument("--stop-file")
    parser.add_argument("--max-restarts",type=int,default=3)
    parser.add_argument("--restart-window-seconds",type=float,default=300.0)
    parser.add_argument("--hold-max-age-seconds",type=float,default=7200.0)
    parser.add_argument("--lock-file")
    parser.add_argument("--expected-schema-family",default="11.")
    parser.add_argument("--expected-daemon-id")
    parser.add_argument("--expected-project-id")
    parser.add_argument("--failure-state-file")
    parser.add_argument("--receipt-action",default="TRIGGER_CANONICAL_RECEIVER_TASK")
    args=parser.parse_args()
    lock_fd=None
    if args.daemon and args.lock_file:
        lock_fd=acquire_singleton(Path(args.lock_file))
        if lock_fd is None:return 73
    if args.daemon:
        expected_identity={};
        if args.expected_daemon_id:expected_identity['daemon_id']=args.expected_daemon_id
        if args.expected_project_id:expected_identity['project_id']=args.expected_project_id
        return supervise_loop(health_url=args.health_url,task_name=args.task_name,receipt_path=Path(args.receipt),interval_seconds=max(1.0,args.interval_seconds),recovery_seconds=args.recovery_seconds,stop_path=Path(args.stop_file) if args.stop_file else None,max_restarts=max(1,args.max_restarts),restart_window_seconds=max(10.0,args.restart_window_seconds),hold_max_age_seconds=max(60.0,args.hold_max_age_seconds),expected_schema_family=args.expected_schema_family,expected_identity=expected_identity or None,failure_state_path=Path(args.failure_state_file) if args.failure_state_file else None,receipt_action=args.receipt_action)
    receipt=supervise_once(health_url=args.health_url,task_name=args.task_name,receipt_path=Path(args.receipt),recovery_seconds=args.recovery_seconds)
    print(json.dumps(receipt,sort_keys=True))
    return 0 if receipt.get("healthy_after") else 2

if __name__ == "__main__":
    raise SystemExit(main())
