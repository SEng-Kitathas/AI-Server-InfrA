from __future__ import annotations

import json
import os
import secrets
import threading
import time
import urllib.error
import urllib.request
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_from_directory

try:
    import psutil
except ImportError:  # HUD remains usable when optional local process telemetry is unavailable.
    psutil = None

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
RECEIVER_BASE = os.environ.get("PCMMAD_RECEIVER_BASE", "http://127.0.0.1:5000").rstrip("/")
API_KEY = os.environ.get("GITHOME_API_KEY", "").strip()
HUD_HOST = os.environ.get("PCMMAD_HUD_HOST", "127.0.0.1")
HUD_PORT = int(os.environ.get("PCMMAD_HUD_PORT", "5090"))
BRIDGE_BASE = os.environ.get("PCMMAD_BROWSER_BRIDGE_BASE", "http://127.0.0.1:4471").rstrip("/")
HUD_TOKEN = secrets.token_urlsafe(32)
STATUS_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="pcmmad-hud-status")
TELEMETRY_HISTORY: deque[dict[str, Any]] = deque(maxlen=180)
TELEMETRY_LOCK = threading.Lock()
HUD_PROCESS_STARTED_AT = time.time()
HUD_PROCESS = psutil.Process(os.getpid()) if psutil is not None else None
if HUD_PROCESS is not None:
    HUD_PROCESS.cpu_percent(interval=None)

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


def _hud_process_snapshot() -> dict[str, Any]:
    if HUD_PROCESS is None:
        return {"available": False}
    try:
        with HUD_PROCESS.oneshot():
            mem = HUD_PROCESS.memory_info()
            full = HUD_PROCESS.memory_full_info()
            return {
                "available": True,
                "pid": HUD_PROCESS.pid,
                "uptime_seconds": round(max(0.0, time.time() - HUD_PROCESS_STARTED_AT), 3),
                "cpu_percent": round(float(HUD_PROCESS.cpu_percent(interval=None)), 3),
                "rss_bytes": mem.rss,
                "uss_bytes": getattr(full, "uss", None),
                "threads": HUD_PROCESS.num_threads(),
                "handles": HUD_PROCESS.num_handles() if hasattr(HUD_PROCESS, "num_handles") else None,
            }
    except Exception as exc:
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}


def _telemetry_alerts(execution: dict[str, Any], observed: dict[str, Any]) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []
    global_exec = execution.get("global") or {}
    scheduler = execution.get("scheduler_telemetry") or {}
    process = observed.get("process") or {}
    system = observed.get("system") or {}
    http = observed.get("http") or {}
    server = observed.get("server") or {}
    running = int(global_exec.get("running") or 0)
    limit = int(global_exec.get("global_limit") or 0)
    queued = int(global_exec.get("queued") or 0)
    if execution.get("unsupervised_jobs"):
        alerts.append({"severity": "critical", "code": "UNSUPERVISED_JOBS", "message": f"{len(execution['unsupervised_jobs'])} unsupervised execution record(s)"})
    if execution.get("corrupt_job_files"):
        alerts.append({"severity": "critical", "code": "CORRUPT_JOB_RECORDS", "message": f"{len(execution['corrupt_job_files'])} corrupt job record(s)"})
    if scheduler.get("last_error") or int(scheduler.get("last_tick_reconcile_errors") or 0) > 0:
        alerts.append({"severity": "critical", "code": "SCHEDULER_ERROR", "message": str(scheduler.get("last_error") or scheduler.get("last_reconcile_error") or "scheduler reconcile error")})
    if int(scheduler.get("watcher_errors") or 0) > 0 or scheduler.get("last_watcher_error"):
        alerts.append({"severity": "critical", "code": "WATCHER_ERROR", "message": str(scheduler.get("last_watcher_error") or f"watcher errors={scheduler.get('watcher_errors')}")})
    if limit > 0 and running / limit >= 0.90:
        alerts.append({"severity": "warning", "code": "EXECUTION_SATURATION", "message": f"execution workers {running}/{limit}"})
    if queued > 0:
        alerts.append({"severity": "warning", "code": "EXECUTION_QUEUE", "message": f"execution queue depth {queued}"})
    if int(server.get("queue_depth") or 0) > 0:
        alerts.append({"severity": "warning", "code": "HTTP_QUEUE", "message": f"HTTP queue depth {server.get('queue_depth')}"})
    if float(system.get("cpu_percent") or 0.0) >= 90.0:
        alerts.append({"severity": "warning", "code": "HOST_CPU", "message": f"host CPU {system.get('cpu_percent')}%"})
    if float(system.get("memory_percent") or 0.0) >= 90.0:
        alerts.append({"severity": "warning", "code": "HOST_MEMORY", "message": f"host memory {system.get('memory_percent')}%"})
    storage = system.get("storage") or {}
    storage_percent = float(storage.get("percent") or 0.0)
    storage_free = storage.get("free_bytes")
    critical_free = storage_free is not None and int(storage_free) < 10 * 1024**3
    warning_free = storage_free is not None and int(storage_free) < 25 * 1024**3
    if storage_percent >= 97.0 or critical_free:
        alerts.append({"severity": "critical", "code": "STORAGE_SPACE", "message": f"storage {storage_percent:.1f}% used / {int(storage_free or 0) / 1024**3:.1f} GiB free"})
    elif storage_percent >= 90.0 or warning_free:
        alerts.append({"severity": "warning", "code": "STORAGE_SPACE", "message": f"storage {storage_percent:.1f}% used / {int(storage_free or 0) / 1024**3:.1f} GiB free"})
    p95 = ((http.get("latency_ms") or {}).get("p95"))
    if p95 is not None and float(p95) >= 2000.0:
        alerts.append({"severity": "warning", "code": "HTTP_P95", "message": f"HTTP p95 {float(p95):.0f} ms"})
    if float(http.get("server_error_rate") or 0.0) > 0.0:
        alerts.append({"severity": "critical", "code": "HTTP_5XX", "message": f"HTTP 5xx rate {float(http.get('server_error_rate'))*100:.2f}%"})
    return alerts


def _telemetry_projection(receiver_health: dict[str, Any], observed: dict[str, Any], *, observed_ok: bool) -> dict[str, Any]:
    execution = receiver_health.get("execution_readiness") or observed.get("execution") or {}
    global_exec = execution.get("global") or {}
    scheduler = execution.get("scheduler_telemetry") or {}
    process = observed.get("process") or {}
    system = observed.get("system") or {}
    http = observed.get("http") or {}
    server = observed.get("server") or {}
    running = int(global_exec.get("running") or 0)
    limit = int(global_exec.get("global_limit") or 0)
    sample = {
        "ts": time.time(),
        "running": running,
        "capacity": limit,
        "queued": int(global_exec.get("queued") or 0),
        "worker_utilization": round(running / limit, 6) if limit > 0 else None,
        "cpu_percent": process.get("cpu_percent"),
        "host_cpu_percent": system.get("cpu_percent"),
        "rss_bytes": process.get("rss_bytes"),
        "uss_bytes": process.get("uss_bytes"),
        "handles": process.get("handles"),
        "threads": process.get("threads"),
        "host_memory_percent": system.get("memory_percent"),
        "storage_free_bytes": (system.get("storage") or {}).get("free_bytes"),
        "storage_percent": (system.get("storage") or {}).get("percent"),
        "http_p95_ms": (http.get("latency_ms") or {}).get("p95"),
        "http_rpm": http.get("requests_per_minute"),
        "http_5xx_rate": http.get("server_error_rate"),
        "http_queue": server.get("queue_depth"),
        "http_active": server.get("active_workers"),
    }
    with TELEMETRY_LOCK:
        TELEMETRY_HISTORY.append(sample)
        history = list(TELEMETRY_HISTORY)[-60:]
    alerts = _telemetry_alerts(execution, observed)
    severity = "critical" if any(a["severity"] == "critical" for a in alerts) else "warning" if alerts else "nominal"
    return {
        "ok": bool(observed_ok),
        "status": observed.get("status") if observed_ok else "unavailable",
        "basis": "hud_projection_over_receiver_owned_observability",
        "severity": severity,
        "execution": execution,
        "background_batch_executor": receiver_health.get("background_batch_executor") or {},
        "process": process,
        "system": system,
        "http": http,
        "server": server,
        "dependencies": observed.get("dependencies") or {},
        "alerts": alerts,
        "history": history,
        "scheduler": {
            "thread_alive": bool(execution.get("scheduler_thread_alive")),
            "last_error": scheduler.get("last_error"),
            "reconcile_errors": int(scheduler.get("jobs_reconcile_errors") or 0),
            "last_tick_reconcile_errors": int(scheduler.get("last_tick_reconcile_errors") or 0),
            "watcher_alive": bool(scheduler.get("watcher_alive")),
            "watcher_errors": int(scheduler.get("watcher_errors") or 0),
            "unsupervised_jobs": len(execution.get("unsupervised_jobs") or []),
            "corrupt_job_files": len(execution.get("corrupt_job_files") or []),
        },
    }


def _readiness_payload(*, receiver_ok: bool, browser_bridge_ok: bool, journal_ok: bool, observability_ok: bool) -> dict[str, Any]:
    required = {"hud": True, "receiver": bool(receiver_ok), "journal": bool(journal_ok)}
    optional = {"browser_bridge": bool(browser_bridge_ok), "observability": bool(observability_ok)}
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
    t0 = time.time()
    health_future = STATUS_POOL.submit(receiver_request, "/lab/health", timeout=1.5)
    telemetry_future = STATUS_POOL.submit(receiver_request, "/observability/telemetry", timeout=1.5)
    bridge_future = STATUS_POOL.submit(bridge_request, "/health", timeout=1.5)
    receiver_code, receiver_data = health_future.result()
    telemetry_code, telemetry_data = telemetry_future.result()
    bridge_code, bridge_data = bridge_future.result()
    receiver_ok = receiver_code == 200 and isinstance(receiver_data, dict) and bool(receiver_data.get("ok"))
    observability_ok = telemetry_code == 200 and isinstance(telemetry_data, dict) and bool(telemetry_data.get("ok"))
    bridge_ok = bridge_code == 200 and isinstance(bridge_data, dict) and bool(bridge_data.get("ok"))
    sessions = []
    # Session inventory is routed through the receiver. Do not wait on that
    # path when receiver health has already failed merely because bridge health
    # itself is green.
    if bridge_ok and receiver_ok:
        s_code, s_data = receiver_request(
            "/lab/dispatch",
            method="POST",
            payload={"tool_name": "browser.sessions.list", "payload": {}},
            timeout=2.5,
        )
        if s_code == 200 and s_data.get("ok"):
            sessions = s_data.get("result", {}).get("sessions", []) or []
    with EVENT_LOCK:
        events = list(EVENTS)[:40]
    journal = {**JOURNAL_STATE, "path": str(JOURNAL_PATH), "memory_rows": len(EVENTS)}
    readiness = _readiness_payload(
        receiver_ok=receiver_ok,
        browser_bridge_ok=bridge_ok,
        journal_ok=bool(journal.get("ok")),
        observability_ok=observability_ok,
    )
    telemetry = _telemetry_projection(
        receiver_data if receiver_ok else {},
        telemetry_data if observability_ok else {},
        observed_ok=observability_ok,
    )
    return jsonify({
        "ok": True,
        "checked_at": time.time(),
        "latency_ms": round((time.time() - t0) * 1000, 1),
        "hud": {
            "ok": True,
            "host": HUD_HOST,
            "port": HUD_PORT,
            "api_key_exposed_to_browser": False,
            "process": _hud_process_snapshot(),
        },
        "receiver": {
            "ok": receiver_ok,
            "http_status": receiver_code,
            "status": receiver_data.get("status") if receiver_ok else None,
            "tool_count": receiver_data.get("tool_count") if receiver_ok else None,
            "error": None if receiver_ok else receiver_data,
        },
        "browser_bridge": {
            "ok": bridge_ok,
            "http_status": bridge_code,
            "detail": bridge_data,
            "required_for_core": False,
        },
        "observability": {
            "ok": observability_ok,
            "http_status": telemetry_code,
            "required_for_core": False,
            "error": None if observability_ok else telemetry_data,
        },
        "readiness": readiness,
        "telemetry": telemetry,
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
    request_id=str(body.get("request_id","")).strip() or f"hud-{int(time.time()*1000)}"
    dispatch_id=uuid.uuid4().hex
    if not tool_name:
        return jsonify({"ok":False,"error_code":"BAD_REQUEST","message":"tool_name is required","request_id":request_id}),400
    if not isinstance(payload,dict):
        return jsonify({"ok":False,"error_code":"BAD_REQUEST","message":"payload must be an object","request_id":request_id}),400
    if not isinstance(authority,dict):
        return jsonify({"ok":False,"error_code":"BAD_REQUEST","message":"authority must be an object","request_id":request_id}),400
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
    return jsonify({"ok":True,"hud":"PCMMAD Operations HUD","receiver_base":RECEIVER_BASE,"api_key_available":bool(API_KEY),"api_key_exposed_to_browser":False,"hud_token":HUD_TOKEN,"hud_token_scope":"local UI POST capability; rotates on HUD process restart","approval_model":"runtime-issued target/argument/contract-bound challenge; HUD confirms exact single-use handle","ui_version":"ops-hud-20260909-observability-v1","telemetry_model":"receiver-owned RED+USE+scheduler projection"})


if __name__ == "__main__":
    try:
        from waitress import serve
    except ImportError as exc:
        print(f"[PCMMAD HUD] Waitress unavailable; Flask fallback: {exc}", flush=True)
        app.run(host=HUD_HOST, port=HUD_PORT, debug=False, threaded=True, use_reloader=False)
    else:
        hud_threads = max(4, int(os.environ.get("PCMMAD_HUD_HTTP_THREADS", "8")))
        print(f"[PCMMAD HUD] waitress threads={hud_threads} bind={HUD_HOST}:{HUD_PORT}", flush=True)
        serve(app, host=HUD_HOST, port=HUD_PORT, threads=hud_threads, channel_timeout=120, cleanup_interval=10, asyncore_use_poll=True)
