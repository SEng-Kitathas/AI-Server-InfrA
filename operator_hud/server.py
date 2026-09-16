from __future__ import annotations

import json
import os
import secrets
import threading
import time
import urllib.error
import urllib.request
import urllib.parse
import uuid
from collections import deque
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_from_directory

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
RECEIVER_BASE = os.environ.get("PCMMAD_RECEIVER_BASE", "http://127.0.0.1:5000").rstrip("/")
API_KEY = os.environ.get("GITHOME_API_KEY", "").strip()
HUD_HOST = os.environ.get("PCMMAD_HUD_HOST", "127.0.0.1")
HUD_PORT = int(os.environ.get("PCMMAD_HUD_PORT", "5090"))
BRIDGE_BASE = os.environ.get("PCMMAD_BROWSER_BRIDGE_BASE", "http://127.0.0.1:4471").rstrip("/")
DAEMON_BASE = os.environ.get("PCMMAD_DAEMON_URL", "").strip().rstrip("/")
DAEMON_ID = os.environ.get("PCMMAD_DAEMON_ID", "pcmmad-daemon").strip()
DAEMON_PROJECT_ID = os.environ.get("PCMMAD_DAEMON_PROJECT_ID", "RECEIVER-LAB").strip()
NGROK_API_BASE = os.environ.get("PCMMAD_NGROK_API_BASE", "http://127.0.0.1:4040").strip().rstrip("/")
BROWSER_GATE_FILE = Path(os.environ.get("PCMMAD_BROWSER_BRIDGE_GATE_FILE", str(Path(os.environ.get("PROGRAMDATA", str(ROOT / "runtime"))) / "PCMMAD" / "Recovery" / "browser_bridge_gate.json")))
RECOVERY_ROOT = Path(os.environ.get("PCMMAD_RECOVERY_ROOT", str(Path(os.environ.get("PROGRAMDATA", str(ROOT / "runtime"))) / "PCMMAD" / "Recovery")))
HUD_TOKEN = secrets.token_urlsafe(32)

app = Flask(__name__, static_folder=str(STATIC), static_url_path="/static")
# DNS-rebinding boundary: only exact loopback identities are trusted.
# Some lawful in-process/test and local HTTP clients omit the Host port; accept
# that representation without widening to arbitrary hostnames or wrong ports.
TRUSTED_HOSTS = {
    "127.0.0.1",
    "localhost",
    "[::1]",
    f"127.0.0.1:{HUD_PORT}",
    f"localhost:{HUD_PORT}",
    f"[::1]:{HUD_PORT}",
}


@app.before_request
def _reject_untrusted_host():
    host = request.host.lower()
    if host not in {h.lower() for h in TRUSTED_HOSTS}:
        return jsonify({
            "ok": False,
            "error_code": "HUD_HOST_REJECTED",
            "message": "untrusted Host header rejected by localhost control surface",
        }), 421
    return None
EVENTS: deque[dict[str, Any]] = deque(maxlen=250)
EVENT_LOCK = threading.Lock()
JOURNAL_PATH = ROOT / "runtime" / "hud_events.jsonl"
JOURNAL_STATE: dict[str, Any] = {
    "ok": True,
    "load_integrity_ok": True,
    "write_ok": True,
    "loaded_rows": 0,
    "malformed_rows_skipped": 0,
    "write_failures": 0,
    "load_error": None,
    "write_error": None,
    "last_write_ts": None,
}


def _refresh_journal_ok() -> None:
    JOURNAL_STATE["ok"] = bool(JOURNAL_STATE.get("load_integrity_ok")) and bool(JOURNAL_STATE.get("write_ok"))


def _load_journal() -> None:
    JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not JOURNAL_PATH.is_file():
        JOURNAL_STATE.update(load_integrity_ok=True, write_ok=True, loaded_rows=0, malformed_rows_skipped=0, load_error=None, write_error=None)
        _refresh_journal_ok()
        return
    rows: list[dict[str, Any]] = []
    malformed = 0
    try:
        for line in JOURNAL_PATH.read_text(encoding="utf-8").splitlines()[-250:]:
            try:
                row = json.loads(line)
                if isinstance(row, dict): rows.append(row)
                else: malformed += 1
            except Exception:
                malformed += 1
    except Exception as exc:
        JOURNAL_STATE.update(load_integrity_ok=False, loaded_rows=0, malformed_rows_skipped=0, load_error=f"{type(exc).__name__}: {exc}")
        _refresh_journal_ok()
        return
    with EVENT_LOCK:
        EVENTS.clear()
        for row in rows: EVENTS.appendleft(row)
    load_error = None if malformed == 0 else f"{malformed} malformed journal row(s) skipped during load"
    JOURNAL_STATE.update(load_integrity_ok=(malformed == 0), loaded_rows=len(rows), malformed_rows_skipped=malformed, load_error=load_error)
    _refresh_journal_ok()


def _event(kind: str, **data: Any) -> None:
    row = {"ts": time.time(), "kind": kind, **data}
    with EVENT_LOCK:
        EVENTS.appendleft(row)
        try:
            JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
            with JOURNAL_PATH.open("a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
                f.flush()
                os.fsync(f.fileno())
            JOURNAL_STATE.update(write_ok=True, write_error=None, last_write_ts=row["ts"])
        except Exception as exc:
            JOURNAL_STATE["write_ok"] = False
            JOURNAL_STATE["write_failures"] = int(JOURNAL_STATE.get("write_failures", 0)) + 1
            JOURNAL_STATE["write_error"] = f"{type(exc).__name__}: {exc}"
        _refresh_journal_ok()


_load_journal()

def _require_hud_token():
    origin = request.headers.get("Origin")
    if origin:
        allowed_origins = {f"http://{request.host}", f"https://{request.host}"}
        if origin not in allowed_origins:
            _event("hud_origin_rejected", remote_addr=request.remote_addr, path=request.path, origin=origin)
            return jsonify({
                "ok": False,
                "error_code": "HUD_ORIGIN_REJECTED",
                "message": "cross-origin HUD mutation request rejected",
            }), 403
    supplied = request.headers.get("X-PCMMAD-HUD-Token", "")
    if not supplied or not secrets.compare_digest(supplied, HUD_TOKEN):
        _event("hud_token_rejected", remote_addr=request.remote_addr, path=request.path)
        return jsonify({
            "ok": False,
            "error_code": "HUD_TOKEN_REQUIRED",
            "message": "valid per-process HUD capability token required for this POST",
        }), 403
    return None


def _json_file(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():return None,None
    try:
        obj=json.loads(path.read_text(encoding="utf-8-sig"));return (obj if isinstance(obj,dict) else None),None
    except Exception as exc:return None,f"{type(exc).__name__}: {exc}"

def _hold_file_state(path: Path, *, now_epoch: float) -> dict[str, Any]:
    obj,error=_json_file(path)
    if obj is None:return {"hold":False,"status":"MISSING" if error is None else "INVALID_HOLD","error":error}
    try:
        if obj.get("desired_state")!="STOPPED":return {"hold":False,"status":"INVALID_HOLD","reason":"BAD_SHAPE"}
        expires=float(obj.get("expires_at_epoch") or 0)
        if expires<=now_epoch:return {"hold":False,"status":"EXPIRED_HOLD"}
        return {"hold":True,"status":"MAINTENANCE_HOLD","expires_at_epoch":expires,"operator_id":obj.get("operator_id"),"reason":obj.get("reason")}
    except Exception as exc:return {"hold":False,"status":"INVALID_HOLD","error":f"{type(exc).__name__}: {exc}"}

def _supervisor_budget(name: str, prefix: str, *, now_epoch: float, max_restarts: int = 3, window_seconds: float = 300.0) -> dict[str, Any]:
    failure_path=RECOVERY_ROOT/f"{prefix}.failure_state.json";receipt_path=RECOVERY_ROOT/f"{prefix}_receipt.json";hold_path=RECOVERY_ROOT/f"{prefix}.maintenance_hold"
    failure,error=_json_file(failure_path);receipt,receipt_error=_json_file(receipt_path);hold=_hold_file_state(hold_path,now_epoch=now_epoch)
    if failure is None:
        return {"name":name,"installed":RECOVERY_ROOT.exists(),"state_status":"MISSING" if error is None else "CORRUPT_HOLD","restart_events":0,"max_restarts":max_restarts,"remaining":max_restarts if error is None else 0,"window_seconds":window_seconds,"hold":hold,"receipt_action":receipt.get("action") if receipt else None,"failure_error":error,"receipt_error":receipt_error}
    raw=failure.get("restart_events") or [];events=[]
    for value in raw:
        try:
            epoch=float(value)
            if 0<=now_epoch-epoch<=window_seconds:events.append(epoch)
        except Exception:continue
    state=str(failure.get("state_status") or "RESTORED");remaining=max(0,max_restarts-len(events))
    if state=="CORRUPT_HOLD":remaining=0
    return {"name":name,"installed":True,"state_status":state,"restart_events":len(events),"max_restarts":max_restarts,"remaining":remaining,"window_seconds":window_seconds,"hold":hold,"receipt_action":receipt.get("action") if receipt else None,"failure_error":error,"receipt_error":receipt_error}

def supervisor_budgets() -> dict[str, Any]:
    now_epoch=time.time();rows={
        "receiver":_supervisor_budget("Receiver","receiver_supervisor",now_epoch=now_epoch),
        "ngrok":_supervisor_budget("ngrok","ngrok_supervisor",now_epoch=now_epoch),
        "daemon":_supervisor_budget("Daemon","daemon_supervisor",now_epoch=now_epoch),
        "browser":_supervisor_budget("Browser Bridge","browser_bridge_supervisor",now_epoch=now_epoch),
    }
    active=[x for x in rows.values() if x["state_status"]!="MISSING" or x["hold"].get("hold")]
    if not active:summary={"status":"STANDBY","remaining":None,"max_restarts":3}
    elif any(x["hold"].get("hold") for x in active):summary={"status":"MAINTENANCE_HOLD","remaining":min(x["remaining"] for x in active),"max_restarts":3}
    elif any(x["state_status"]=="CORRUPT_HOLD" for x in active):summary={"status":"CORRUPT_HOLD","remaining":0,"max_restarts":3}
    elif any(x["remaining"]<=0 for x in active):summary={"status":"EXHAUSTED","remaining":0,"max_restarts":3}
    else:summary={"status":"AVAILABLE","remaining":min(x["remaining"] for x in active),"max_restarts":3}
    return {"schema":"pcmmad.ha-budget.v1","recovery_root":str(RECOVERY_ROOT),"summary":summary,"workloads":rows,"mutation_authority":False}


def receiver_request(path: str, *, method: str = "GET", payload: dict[str, Any] | None = None, timeout: float = 8.0) -> tuple[int, Any]:
    if not API_KEY:
        return 503, {"ok": False, "error_code": "HUD_NO_API_KEY", "message": "GITHOME_API_KEY is not available to the HUD process"}
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        RECEIVER_BASE + path,
        data=body,
        method=method,
        headers={"X-GitHome-Key": API_KEY, "Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw.decode("utf-8")) if raw else {"ok": True}
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try: data = json.loads(raw.decode("utf-8"))
        except Exception: data = {"ok": False, "error_code": "UPSTREAM_HTTP_ERROR", "message": raw.decode("utf-8", errors="replace")}
        return exc.code, data
    except Exception as exc:
        return 502, {"ok": False, "error_code": "HUD_UPSTREAM_UNAVAILABLE", "message": f"{type(exc).__name__}: {exc}"}


def bridge_request(path: str, *, method: str = "GET", payload: dict[str, Any] | None = None, timeout: float = 3.0) -> tuple[int, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(BRIDGE_BASE + path, data=body, method=method, headers={"Content-Type":"application/json","Accept":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw=resp.read()
            return resp.status, json.loads(raw.decode("utf-8")) if raw else {"ok": True}
    except urllib.error.HTTPError as exc:
        raw=exc.read()
        try: data=json.loads(raw.decode("utf-8"))
        except Exception: data={"ok":False,"message":raw.decode("utf-8",errors="replace")}
        return exc.code,data
    except Exception as exc:
        return 502,{"ok":False,"error":f"{type(exc).__name__}: {exc}"}


def daemon_request(path: str, *, timeout: float = 1.5) -> tuple[int, Any]:
    if not DAEMON_BASE:
        return 0,{"ok":False,"configured":False,"status":"not_configured","mutation_authority":False}
    req=urllib.request.Request(DAEMON_BASE+path,method="GET",headers={"Accept":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as resp:
            raw=resp.read(262144);return resp.status,json.loads(raw.decode("utf-8")) if raw else {"ok":True}
    except urllib.error.HTTPError as exc:
        raw=exc.read(262144)
        try:data=json.loads(raw.decode("utf-8"))
        except Exception:data={"ok":False,"error":raw.decode("utf-8",errors="replace")}
        return exc.code,data
    except Exception as exc:
        return 502,{"ok":False,"configured":True,"status":"unavailable","error":f"{type(exc).__name__}: {exc}","mutation_authority":False}


def daemon_scar_route(context: str, *, timeout: float=1.0) -> tuple[int, Any]:
    if not DAEMON_BASE:
        return 0,{"ok":False,"status":"not_configured","routing":{"selected":[]},"mutation_authority":False}
    query=urllib.parse.urlencode({"context":str(context)[:2000],"limit":3})
    req=urllib.request.Request(DAEMON_BASE+"/scars/route?"+query,method="GET",headers={"Accept":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as resp:
            raw=resp.read(262144);return resp.status,json.loads(raw.decode("utf-8")) if raw else {}
    except urllib.error.HTTPError as exc:
        raw=exc.read(262144)
        try:data=json.loads(raw.decode("utf-8"))
        except Exception:data={"ok":False,"error":raw.decode("utf-8",errors="replace")}
        return exc.code,data
    except Exception as exc:
        return 502,{"ok":False,"status":"unavailable","error":f"{type(exc).__name__}: {exc}","routing":{"selected":[]},"mutation_authority":False}


def ngrok_request(path: str="/api/tunnels", *, timeout: float=1.0) -> tuple[int, Any]:
    if not NGROK_API_BASE:
        return 0,{"ok":False,"configured":False,"status":"not_configured"}
    req=urllib.request.Request(NGROK_API_BASE+path,method="GET",headers={"Accept":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as resp:
            raw=resp.read(262144);return resp.status,json.loads(raw.decode("utf-8")) if raw else {}
    except Exception as exc:
        return 502,{"ok":False,"configured":True,"error":f"{type(exc).__name__}: {exc}"}


@app.after_request
def no_cache(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; "
        "form-action 'self'; base-uri 'none'; object-src 'none'"
    )
    if request.path == "/" or request.path.startswith("/static/") or request.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store, max-age=0"
        resp.headers["Pragma"] = "no-cache"
    return resp



@app.get("/")
def index(): return send_from_directory(STATIC, "index.html")


def _readiness_payload(*, receiver_ok: bool, browser_bridge_ok: bool, journal_ok: bool) -> dict[str, Any]:
    required = {"hud": True, "receiver": bool(receiver_ok), "journal": bool(journal_ok)}
    optional = {"browser_bridge": bool(browser_bridge_ok)}
    core_ready = all(required.values())
    optional_degraded = [name for name, ok in optional.items() if not ok]
    if core_ready and not optional_degraded:
        status = "ready"
    elif core_ready:
        status = "ready_optional_degraded"
    elif any(required.values()):
        status = "degraded"
    else:
        status = "down"
    return {
        "status": status,
        "core_ready": core_ready,
        "required": required,
        "optional": optional,
        "optional_degraded": optional_degraded,
        "basis": "hud_presentation_over_live_upstream_evidence",
    }


@app.get("/api/status")
def api_status():
    t0=time.time()
    receiver_code, receiver_data = receiver_request("/lab/tools", timeout=1.5)
    receiver_ok = receiver_code == 200 and bool(receiver_data.get("ok"))
    bridge_code, bridge_data = bridge_request("/health", timeout=1.5)
    bridge_ok = bridge_code == 200 and bool(bridge_data.get("ok"))
    daemon_code,daemon_data=daemon_request("/status",timeout=1.0)
    daemon_configured=bool(DAEMON_BASE)
    daemon_ok=daemon_configured and daemon_code==200 and isinstance(daemon_data,dict) and str(daemon_data.get("schema") or "").startswith("mvf.daemon-status.") and daemon_data.get("mutation_authority") is False and str(daemon_data.get("daemon_id") or "")==DAEMON_ID and str(daemon_data.get("project_id") or "")==DAEMON_PROJECT_ID
    ngrok_code,ngrok_data=ngrok_request(timeout=1.0)
    tunnels=ngrok_data.get("tunnels",[]) if isinstance(ngrok_data,dict) else []
    ngrok_ok=ngrok_code==200 and isinstance(tunnels,list) and len(tunnels)>0
    scar_route_data=None
    if daemon_ok:
        if not receiver_ok:scar_context=f"hud cockpit receiver unavailable transport {'online' if ngrok_ok else 'down'} recovery supervisor windows defender"
        elif not bool(JOURNAL_STATE.get('ok')):scar_context="hud cockpit journal evidence degraded consequence readback"
        elif not bridge_ok:scar_context="hud cockpit optional browser degraded core ready"
        else:scar_context="hud cockpit normal operation situational awareness"
        route_code,route_data=daemon_scar_route(scar_context,timeout=1.0)
        if route_code==200 and isinstance(route_data,dict) and route_data.get('ok') and str(route_data.get('daemon_id') or '')==DAEMON_ID and str(route_data.get('project_id') or '')==DAEMON_PROJECT_ID and route_data.get('mutation_authority') is False:
            selected=(route_data.get('routing') or {}).get('selected') or []
            scar_route_data={'applicable':selected[:3],'source_deficits':(route_data.get('source_deficits') or [])[:12],'authority':'DERIVED_ROUTING_ONLY','context':scar_context}
    sessions=[]
    # Session inventory is routed through the receiver. Do not wait on that
    # path when receiver health has already failed merely because bridge health
    # itself is green.
    if bridge_ok and receiver_ok:
        s_code,s_data=receiver_request("/lab/dispatch",method="POST",payload={"tool_name":"browser.sessions.list","payload":{}},timeout=2.5)
        if s_code==200 and s_data.get("ok"):
            sessions=s_data.get("result",{}).get("sessions",[]) or []
    with EVENT_LOCK:
        events=list(EVENTS)[:40]
    journal = {**JOURNAL_STATE, "path": str(JOURNAL_PATH), "memory_rows": len(EVENTS)}
    readiness = _readiness_payload(
        receiver_ok=receiver_ok,
        browser_bridge_ok=bridge_ok,
        journal_ok=bool(journal.get("ok")),
    )
    return jsonify({
        "ok": True,
        "checked_at": time.time(),
        "latency_ms": round((time.time()-t0)*1000,1),
        "hud": {"ok": True, "host": HUD_HOST, "port": HUD_PORT, "api_key_exposed_to_browser": False},
        "receiver": {"ok": receiver_ok, "http_status": receiver_code, "tool_count": receiver_data.get("count") if receiver_ok else None, "error": None if receiver_ok else receiver_data},
        "browser_bridge": {"ok": bridge_ok, "http_status": bridge_code, "detail": bridge_data, "required_for_core": False, "gate_state": str(bridge_data.get("gate_state") or "UNKNOWN") if isinstance(bridge_data,dict) else "UNKNOWN", "armed": bool(bridge_data.get("armed")) if isinstance(bridge_data,dict) else False, "ready_for_browser_automation": bool(bridge_data.get("ready_for_browser_automation")) if isinstance(bridge_data,dict) else False, "playwright": bool(bridge_data.get("playwright")) if isinstance(bridge_data,dict) else False, "browser_channel_available": bool(bridge_data.get("browser_channel_available")) if isinstance(bridge_data,dict) else False, "default_channel": bridge_data.get("default_channel") if isinstance(bridge_data,dict) else None},
        "daemon": {"configured": daemon_configured, "ok": daemon_ok, "http_status": daemon_code if daemon_configured else None, "status": daemon_data if daemon_configured else None, "required_for_core": False},
        "ngrok": {"configured": bool(NGROK_API_BASE), "ok": ngrok_ok, "http_status": ngrok_code, "tunnel_count": len(tunnels) if isinstance(tunnels,list) else 0, "public_urls": [str(x.get("public_url")) for x in tunnels[:4] if isinstance(x,dict) and x.get("public_url")], "required_for_core": False},
        "scar_intelligence": scar_route_data,
        "failure_evidence": daemon_data.get("failure_evidence") if daemon_ok and isinstance(daemon_data,dict) else None,
        "supervisor_budgets": supervisor_budgets(),
        "readiness": readiness,
        "browser_sessions": sessions,
        "journal": journal,
        "events": events,
    })


@app.get("/api/health")
def api_health(): return api_status()


@app.get("/api/tools")
def api_tools():
    code,data=receiver_request("/lab/tools",timeout=2.0)
    return jsonify(data),code


@app.get("/api/mounts")
def api_mounts():
    code,data=receiver_request("/lab/mounts",timeout=3.0)
    return jsonify(data),code


@app.get("/api/events")
def api_events():
    with EVENT_LOCK: rows=list(EVENTS)
    return jsonify({"ok":True,"journal":{**JOURNAL_STATE,"path":str(JOURNAL_PATH)},"events":rows})


@app.post("/api/browser/gate")
def api_browser_gate():
    rejected=_require_hud_token()
    if rejected is not None:return rejected
    body=request.get_json(silent=True) or {};desired=str(body.get("state") or "").upper().strip()
    if desired not in {"ARMED","BLOCKED"}:return jsonify({"ok":False,"error_code":"BROWSER_GATE_STATE_INVALID","message":"state must be ARMED or BLOCKED"}),400
    try:
        BROWSER_GATE_FILE.parent.mkdir(parents=True,exist_ok=True)
        obj={"schema":"pcmmad.browser-bridge-gate.v1","state":desired,"changed_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"provenance":"HUD_EXPLICIT_OPERATOR_TOGGLE"}
        tmp=BROWSER_GATE_FILE.with_suffix(BROWSER_GATE_FILE.suffix+".tmp");tmp.write_text(json.dumps(obj,sort_keys=True)+"\n",encoding="utf-8");os.replace(tmp,BROWSER_GATE_FILE)
        _event("browser_gate_changed",state=desired,path=str(BROWSER_GATE_FILE))
        code,health=bridge_request("/health",timeout=2.0)
        return jsonify({"ok":True,"state":desired,"gate_file":str(BROWSER_GATE_FILE),"bridge_http_status":code,"bridge_health":health})
    except Exception as exc:
        _event("browser_gate_change_failed",state=desired,error=f"{type(exc).__name__}: {exc}")
        return jsonify({"ok":False,"error_code":"BROWSER_GATE_WRITE_FAILED","message":f"{type(exc).__name__}: {exc}"}),500


@app.post("/api/dispatch")
def api_dispatch():
    denied = _require_hud_token()
    if denied is not None: return denied
    body=request.get_json(force=True,silent=False)
    if not isinstance(body,dict):
        return jsonify({"ok":False,"error_code":"BAD_REQUEST","message":"dispatch body must be an object"}),400
    tool_name=str(body.get("tool_name","")).strip()
    payload=body.get("payload") or {}
    authority=body.get("authority") or {}
    expected_contract_digest=body.get("expected_contract_digest")
    request_id=str(body.get("request_id","")).strip() or f"hud-{int(time.time()*1000)}"
    dispatch_id=uuid.uuid4().hex
    if not tool_name:
        return jsonify({"ok":False,"error_code":"BAD_REQUEST","message":"tool_name is required","request_id":request_id}),400
    if not isinstance(payload,dict):
        return jsonify({"ok":False,"error_code":"BAD_REQUEST","message":"payload must be an object","request_id":request_id}),400
    if not isinstance(authority,dict):
        return jsonify({"ok":False,"error_code":"BAD_REQUEST","message":"authority must be an object","request_id":request_id}),400
    if expected_contract_digest is not None and not isinstance(expected_contract_digest,str):
        return jsonify({"ok":False,"error_code":"BAD_REQUEST","message":"expected_contract_digest must be a string","request_id":request_id}),400
    if bool(body.get("approve",False)):
        return jsonify({
            "ok":False,
            "error_code":"HUD_LEGACY_APPROVAL_DISABLED",
            "message":"HUD no longer manufactures approval authority; request a runtime approval challenge, then confirm its exact handle",
            "request_id":request_id,
        }),409
    payload=dict(payload)
    # Embedded authority is never forwarded from the browser payload plane.
    payload.pop("approval",None); payload.pop("approval_handle",None); payload.pop("authority",None)
    authority=dict(authority)
    authority.pop("legacy_approval",None); authority.pop("approval",None)
    receiver_body={"tool_name":tool_name,"payload":payload}
    if authority:
        receiver_body["authority"]=authority
    if expected_contract_digest is not None:
        receiver_body["expected_contract_digest"]=expected_contract_digest
    _event(
        "dispatch_started",
        dispatch_id=dispatch_id,
        request_id=request_id,
        tool_name=tool_name,
        approval_handle=authority.get("approval_handle"),
    )
    started=time.time()
    code,data=receiver_request("/lab/dispatch",method="POST",payload=receiver_body,timeout=30.0)
    elapsed=round((time.time()-started)*1000,1)
    if isinstance(data,dict):
        data.setdefault("request_id",request_id)
        data.setdefault("dispatch_id",dispatch_id)
        data.setdefault("hud_elapsed_ms",elapsed)
    _event(
        "dispatch_completed",
        dispatch_id=dispatch_id,
        request_id=request_id,
        tool_name=tool_name,
        approval_handle=authority.get("approval_handle"),
        http_status=code,
        ok=bool(data.get("ok")) if isinstance(data,dict) else False,
        elapsed_ms=elapsed,
        error_code=data.get("error_code") if isinstance(data,dict) else None,
    )
    return jsonify(data),code


@app.post("/api/batch")
def api_batch():
    denied = _require_hud_token()
    if denied is not None: return denied
    body=request.get_json(force=True,silent=False)
    if not isinstance(body,dict):
        return jsonify({"ok":False,"error_code":"BAD_REQUEST","message":"batch body must be an object"}),400
    steps=body.get("steps")
    if not isinstance(steps,list) or not steps:
        return jsonify({"ok":False,"error_code":"BAD_REQUEST","message":"steps must be a non-empty array"}),400

    # Batch must not become an alternate approval surface. Strip all nested
    # approval metadata and classify every step against the live receiver
    # catalog. If the catalog cannot be read, fail closed.
    cat_code,cat=receiver_request("/lab/tools",timeout=2.0)
    if cat_code!=200 or not isinstance(cat,dict) or not cat.get("ok"):
        return jsonify({"ok":False,"error_code":"HUD_BATCH_CLASSIFICATION_UNAVAILABLE","message":"cannot safely classify batch approval requirements"}),503
    by_name={str(t.get("name")):t for t in cat.get("tools",[]) if isinstance(t,dict)}
    clean_steps=[]; gated=[]
    for idx,step in enumerate(steps):
        if not isinstance(step,dict):
            return jsonify({"ok":False,"error_code":"BAD_REQUEST","message":f"step {idx} must be an object"}),400
        tool_name=str(step.get("tool_name","")).strip()
        payload=step.get("payload") or {}
        if not isinstance(payload,dict):
            return jsonify({"ok":False,"error_code":"BAD_REQUEST","message":f"step {idx} payload must be an object"}),400
        payload=dict(payload); payload.pop("approval",None); payload.pop("approval_handle",None); payload.pop("authority",None)
        spec=by_name.get(tool_name)
        if spec is None:
            return jsonify({
                "ok":False,
                "error_code":"HUD_BATCH_TOOL_UNKNOWN",
                "message":f"cannot safely classify unknown batch tool: {tool_name}",
                "index":idx,
                "tool_name":tool_name,
            }),409
        if bool(spec.get("effective_approval_required",spec.get("approval_required",False))):
            gated.append({
                "index":idx,
                "tool_name":tool_name,
                "danger_tier":spec.get("danger_tier"),
                "effective_approval_required":True,
                "contract_digest":spec.get("contract_digest"),
            })
        clean=dict(step); clean.pop("authority",None); clean["payload"]=payload; clean_steps.append(clean)
    if gated:
        _event("batch_rejected_approval",batch_id=uuid.uuid4().hex,gated_steps=gated,step_count=len(clean_steps))
        return jsonify({
            "ok":False,
            "error_code":"HUD_BATCH_APPROVAL_REQUIRED",
            "message":"batch contains approval-gated tools; use explicit per-dispatch approval until a batch approval surface exists",
            "gated_steps":gated,
        }),403

    batch_id=uuid.uuid4().hex
    request_id=str(body.get("request_id","")).strip() or f"hud-batch-{int(time.time()*1000)}"
    clean_body=dict(body); clean_body["steps"]=clean_steps
    _event("batch_started",batch_id=batch_id,request_id=request_id,step_count=len(clean_steps))
    started=time.time()
    code,data=receiver_request("/lab/batch",method="POST",payload=clean_body,timeout=30.0)
    elapsed=round((time.time()-started)*1000,1)
    if isinstance(data,dict):
        data.setdefault("batch_id",batch_id); data.setdefault("request_id",request_id); data.setdefault("hud_elapsed_ms",elapsed)
    _event("batch_completed",batch_id=batch_id,request_id=request_id,step_count=len(clean_steps),http_status=code,ok=bool(data.get("ok")) if isinstance(data,dict) else False,elapsed_ms=elapsed,error_code=data.get("error_code") if isinstance(data,dict) else None)
    return jsonify(data),code


@app.post("/api/results/get")
def api_results_get():
    denied = _require_hud_token()
    if denied is not None: return denied
    body=request.get_json(force=True,silent=False)
    code,data=receiver_request("/lab/results/get",method="POST",payload=body)
    return jsonify(data),code


@app.get("/api/meta")
def api_meta():
    return jsonify({"ok":True,"hud":"PCMMAD Operations HUD","receiver_base":RECEIVER_BASE,"api_key_available":bool(API_KEY),"api_key_exposed_to_browser":False,"hud_token":HUD_TOKEN,"hud_token_scope":"local UI POST capability; rotates on HUD process restart","approval_model":"runtime-issued target/argument/contract-bound challenge; HUD confirms exact single-use handle","ui_version":"ops-hud-20260905-bound-approval"})


if __name__ == "__main__":
    app.run(host=HUD_HOST,port=HUD_PORT,debug=False,threaded=True,use_reloader=False)
