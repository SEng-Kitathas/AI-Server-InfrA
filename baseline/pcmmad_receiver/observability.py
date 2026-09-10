"""Authenticated Runtime observability surface for HUD and machine scrapers.

The receiver owns telemetry truth. The HUD is a presentation projection over this
surface and must not rediscover receiver state by PID scraping or parallel heuristics.
"""

from __future__ import annotations

import importlib.metadata
import os
import shutil
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any

import psutil
from flask import Blueprint, Response, g, jsonify, request
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    GCCollector,
    Gauge,
    Histogram,
    PlatformCollector,
    ProcessCollector,
    generate_latest,
)

from .shared_core import require_valid_api_key

JsonObject = dict[str, Any]

observability_bp = Blueprint("observability", __name__, url_prefix="/observability")

_PROCESS = psutil.Process(os.getpid())
_PROCESS.cpu_percent(interval=None)
psutil.cpu_percent(interval=None)
_PROCESS_STARTED_AT = time.time()

_REGISTRY = CollectorRegistry(auto_describe=True)
ProcessCollector(registry=_REGISTRY)
PlatformCollector(registry=_REGISTRY)
GCCollector(registry=_REGISTRY)

_HTTP_REQUESTS = Counter(
    "pcmmad_http_requests_total",
    "Receiver HTTP requests by bounded Flask route, method, and status.",
    ("route", "method", "status"),
    registry=_REGISTRY,
)
_HTTP_DURATION = Histogram(
    "pcmmad_http_request_duration_seconds",
    "Receiver HTTP request duration by bounded Flask route and method.",
    ("route", "method"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
    registry=_REGISTRY,
)
_OBSERVATION_ERRORS = Counter(
    "pcmmad_observability_snapshot_errors_total",
    "Observability snapshot collection errors.",
    registry=_REGISTRY,
)

_GAUGES: dict[str, Gauge] = {}

def _gauge(name: str, description: str) -> Gauge:
    gauge = Gauge(name, description, registry=_REGISTRY)
    _GAUGES[name] = gauge
    return gauge

for _name, _description in (
    ("pcmmad_process_rss_bytes", "Receiver resident memory bytes."),
    ("pcmmad_process_uss_bytes", "Receiver unique-set memory bytes when available."),
    ("pcmmad_process_vms_bytes", "Receiver virtual memory bytes."),
    ("pcmmad_process_cpu_percent", "Receiver CPU utilization percent since previous sample."),
    ("pcmmad_process_threads", "Receiver process thread count."),
    ("pcmmad_process_handles", "Receiver Windows handle count when available."),
    ("pcmmad_process_open_files", "Receiver open-file count."),
    ("pcmmad_process_connections", "Receiver inet connection count."),
    ("pcmmad_process_children", "Receiver direct child-process count."),
    ("pcmmad_process_io_read_bytes", "Receiver cumulative IO read bytes."),
    ("pcmmad_process_io_write_bytes", "Receiver cumulative IO write bytes."),
    ("pcmmad_system_cpu_percent", "Host CPU utilization percent."),
    ("pcmmad_system_memory_percent", "Host physical-memory utilization percent."),
    ("pcmmad_system_memory_available_bytes", "Host available physical-memory bytes."),
    ("pcmmad_storage_free_bytes", "Free bytes on the volume containing PCMMAD_ROOT."),
    ("pcmmad_storage_percent", "Used percent on the volume containing PCMMAD_ROOT."),
    ("pcmmad_system_disk_read_bytes", "Host cumulative disk read bytes."),
    ("pcmmad_system_disk_write_bytes", "Host cumulative disk write bytes."),
    ("pcmmad_system_net_bytes_sent", "Host cumulative network bytes sent."),
    ("pcmmad_system_net_bytes_recv", "Host cumulative network bytes received."),
    ("pcmmad_http_server_worker_threads", "Configured/created HTTP worker threads when observable."),
    ("pcmmad_http_server_active_workers", "Currently active HTTP workers when observable."),
    ("pcmmad_http_server_queue_depth", "Current HTTP server task-queue depth when observable."),
    ("pcmmad_http_server_active_peak", "Peak active HTTP workers since process start."),
    ("pcmmad_http_server_queue_peak", "Peak HTTP task-queue depth since process start."),
    ("pcmmad_execution_running", "Canonical scheduler running-job count."),
    ("pcmmad_execution_queued", "Canonical scheduler queued-job count."),
    ("pcmmad_execution_worker_limit", "Loaded canonical scheduler global worker limit; 0 means unbounded."),
    ("pcmmad_execution_unsupervised_jobs", "Canonical scheduler unsupervised-job count."),
    ("pcmmad_execution_corrupt_job_files", "Canonical scheduler corrupt-job-record count."),
    ("pcmmad_execution_reconcile_errors", "Canonical scheduler cumulative reconcile errors."),
    ("pcmmad_execution_watcher_errors", "Canonical scheduler cumulative watcher errors."),
):
    _gauge(_name, _description)

_HTTP_SAMPLES: deque[tuple[float, float, int, str, str]] = deque(maxlen=10000)
_HTTP_SAMPLE_LOCK = threading.Lock()

_WAITRESS_SERVER: Any | None = None
_WAITRESS_LOCK = threading.Lock()
_WAITRESS_SAMPLER: threading.Thread | None = None
_WAITRESS_ACTIVE_PEAK = 0
_WAITRESS_QUEUE_PEAK = 0


def _version(package: str) -> str | None:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def dependency_snapshot() -> JsonObject:
    py_spy = shutil.which("py-spy")
    return {
        "psutil": _version("psutil"),
        "prometheus_client": _version("prometheus-client"),
        "waitress": _version("waitress"),
        "py_spy": _version("py-spy"),
        "py_spy_available": bool(py_spy),
    }


def _bounded_route() -> str:
    rule = getattr(request, "url_rule", None)
    if rule is not None and getattr(rule, "rule", None):
        return str(rule.rule)
    return "unmatched"


@observability_bp.before_app_request
def _observe_request_start() -> None:
    g.pcmmad_observability_started = time.perf_counter()


@observability_bp.after_app_request
def _observe_request_end(response):
    started = getattr(g, "pcmmad_observability_started", None)
    if started is None:
        return response
    elapsed = max(0.0, time.perf_counter() - float(started))
    route = _bounded_route()
    method = request.method.upper()
    status = int(response.status_code)
    _HTTP_REQUESTS.labels(route=route, method=method, status=str(status)).inc()
    _HTTP_DURATION.labels(route=route, method=method).observe(elapsed)
    with _HTTP_SAMPLE_LOCK:
        _HTTP_SAMPLES.append((time.time(), elapsed, status, route, method))
    return response


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def _http_summary(window_seconds: int = 300) -> JsonObject:
    cutoff = time.time() - window_seconds
    with _HTTP_SAMPLE_LOCK:
        rows = [row for row in _HTTP_SAMPLES if row[0] >= cutoff]
    durations_ms = [row[1] * 1000.0 for row in rows]
    client_errors = sum(1 for row in rows if 400 <= row[2] < 500)
    server_errors = sum(1 for row in rows if row[2] >= 500)
    count = len(rows)
    return {
        "window_seconds": window_seconds,
        "request_count": count,
        "requests_per_minute": round(count * 60.0 / window_seconds, 3),
        "client_error_count": client_errors,
        "server_error_count": server_errors,
        "client_error_rate": round(client_errors / count, 6) if count else 0.0,
        "server_error_rate": round(server_errors / count, 6) if count else 0.0,
        "latency_ms": {
            "p50": round(_percentile(durations_ms, 0.50) or 0.0, 3) if durations_ms else None,
            "p95": round(_percentile(durations_ms, 0.95) or 0.0, 3) if durations_ms else None,
            "p99": round(_percentile(durations_ms, 0.99) or 0.0, 3) if durations_ms else None,
            "max": round(max(durations_ms), 3) if durations_ms else None,
        },
    }


def _safe_call(fn, default=None):
    try:
        return fn()
    except (psutil.Error, OSError, AttributeError):
        return default


def _process_snapshot() -> JsonObject:
    with _PROCESS.oneshot():
        mem = _PROCESS.memory_info()
        full = _safe_call(_PROCESS.memory_full_info)
        cpu = _PROCESS.cpu_times()
        io = _safe_call(_PROCESS.io_counters)
        ctx = _safe_call(_PROCESS.num_ctx_switches)
        handles = _safe_call(_PROCESS.num_handles)
        open_files = _safe_call(lambda: len(_PROCESS.open_files()))
        connections = _safe_call(lambda: len(_PROCESS.net_connections(kind="inet")))
        children = _safe_call(lambda: len(_PROCESS.children(recursive=False)))
        threads = _PROCESS.num_threads()
        cpu_percent = _PROCESS.cpu_percent(interval=None)
    return {
        "pid": _PROCESS.pid,
        "uptime_seconds": round(max(0.0, time.time() - _PROCESS_STARTED_AT), 3),
        "rss_bytes": mem.rss,
        "uss_bytes": getattr(full, "uss", None) if full is not None else None,
        "vms_bytes": mem.vms,
        "cpu_percent": round(float(cpu_percent), 3),
        "cpu_user_seconds": round(float(cpu.user), 6),
        "cpu_system_seconds": round(float(cpu.system), 6),
        "threads": threads,
        "handles": handles,
        "open_files": open_files,
        "connections": connections,
        "children": children,
        "context_switches": {
            "voluntary": getattr(ctx, "voluntary", None) if ctx is not None else None,
            "involuntary": getattr(ctx, "involuntary", None) if ctx is not None else None,
        },
        "io": {
            "read_bytes": getattr(io, "read_bytes", None) if io is not None else None,
            "write_bytes": getattr(io, "write_bytes", None) if io is not None else None,
            "read_count": getattr(io, "read_count", None) if io is not None else None,
            "write_count": getattr(io, "write_count", None) if io is not None else None,
        },
    }


def _system_snapshot() -> JsonObject:
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_io_counters()
    net = psutil.net_io_counters()
    storage_root = Path(os.environ.get("PCMMAD_ROOT", str(Path.cwd()))).resolve()
    storage = _safe_call(lambda: psutil.disk_usage(str(storage_root)))
    return {
        "cpu_percent": round(float(psutil.cpu_percent(interval=None)), 3),
        "cpu_count_logical": psutil.cpu_count(logical=True),
        "cpu_count_physical": psutil.cpu_count(logical=False),
        "memory_total_bytes": vm.total,
        "memory_available_bytes": vm.available,
        "memory_percent": round(float(vm.percent), 3),
        "swap_total_bytes": swap.total,
        "swap_used_bytes": swap.used,
        "swap_percent": round(float(swap.percent), 3),
        "storage": {
            "root": str(storage_root),
            "total_bytes": getattr(storage, "total", None) if storage is not None else None,
            "used_bytes": getattr(storage, "used", None) if storage is not None else None,
            "free_bytes": getattr(storage, "free", None) if storage is not None else None,
            "percent": round(float(getattr(storage, "percent", 0.0)), 3) if storage is not None else None,
        },
        "disk": {
            "read_bytes": getattr(disk, "read_bytes", None) if disk is not None else None,
            "write_bytes": getattr(disk, "write_bytes", None) if disk is not None else None,
            "read_count": getattr(disk, "read_count", None) if disk is not None else None,
            "write_count": getattr(disk, "write_count", None) if disk is not None else None,
        },
        "network": {
            "bytes_sent": getattr(net, "bytes_sent", None) if net is not None else None,
            "bytes_recv": getattr(net, "bytes_recv", None) if net is not None else None,
            "packets_sent": getattr(net, "packets_sent", None) if net is not None else None,
            "packets_recv": getattr(net, "packets_recv", None) if net is not None else None,
            "errors_in": getattr(net, "errin", None) if net is not None else None,
            "errors_out": getattr(net, "errout", None) if net is not None else None,
            "drops_in": getattr(net, "dropin", None) if net is not None else None,
            "drops_out": getattr(net, "dropout", None) if net is not None else None,
        },
    }


def _waitress_values() -> tuple[int | None, int | None, int | None]:
    with _WAITRESS_LOCK:
        server = _WAITRESS_SERVER
    if server is None:
        return None, None, None
    dispatcher = getattr(server, "task_dispatcher", None)
    if dispatcher is None:
        return None, None, None
    queue_depth = len(getattr(dispatcher, "queue", ()) or ())
    active = int(getattr(dispatcher, "active_count", 0) or 0)
    worker_threads = len(getattr(dispatcher, "threads", ()) or ())
    return queue_depth, active, worker_threads


def _waitress_snapshot() -> JsonObject:
    queue_depth, active, worker_threads = _waitress_values()
    with _WAITRESS_LOCK:
        queue_peak = _WAITRESS_QUEUE_PEAK
        active_peak = _WAITRESS_ACTIVE_PEAK
        bound = _WAITRESS_SERVER is not None
    return {
        "implementation": "waitress" if bound else "embedded_or_flask_development",
        "instrumented": bound,
        "queue_depth": queue_depth,
        "active_workers": active,
        "worker_threads": worker_threads,
        "queue_peak": queue_peak if bound else None,
        "active_peak": active_peak if bound else None,
    }


def _set_gauge(name: str, value: Any) -> None:
    if value is None:
        return
    try:
        _GAUGES[name].set(float(value))
    except (TypeError, ValueError):
        return


def _refresh_gauges(process: JsonObject, system: JsonObject, server: JsonObject) -> None:
    _set_gauge("pcmmad_process_rss_bytes", process.get("rss_bytes"))
    _set_gauge("pcmmad_process_uss_bytes", process.get("uss_bytes"))
    _set_gauge("pcmmad_process_vms_bytes", process.get("vms_bytes"))
    _set_gauge("pcmmad_process_cpu_percent", process.get("cpu_percent"))
    _set_gauge("pcmmad_process_threads", process.get("threads"))
    _set_gauge("pcmmad_process_handles", process.get("handles"))
    _set_gauge("pcmmad_process_open_files", process.get("open_files"))
    _set_gauge("pcmmad_process_connections", process.get("connections"))
    _set_gauge("pcmmad_process_children", process.get("children"))
    _set_gauge("pcmmad_process_io_read_bytes", (process.get("io") or {}).get("read_bytes"))
    _set_gauge("pcmmad_process_io_write_bytes", (process.get("io") or {}).get("write_bytes"))
    _set_gauge("pcmmad_system_cpu_percent", system.get("cpu_percent"))
    _set_gauge("pcmmad_system_memory_percent", system.get("memory_percent"))
    _set_gauge("pcmmad_system_memory_available_bytes", system.get("memory_available_bytes"))
    _set_gauge("pcmmad_storage_free_bytes", (system.get("storage") or {}).get("free_bytes"))
    _set_gauge("pcmmad_storage_percent", (system.get("storage") or {}).get("percent"))
    _set_gauge("pcmmad_system_disk_read_bytes", (system.get("disk") or {}).get("read_bytes"))
    _set_gauge("pcmmad_system_disk_write_bytes", (system.get("disk") or {}).get("write_bytes"))
    _set_gauge("pcmmad_system_net_bytes_sent", (system.get("network") or {}).get("bytes_sent"))
    _set_gauge("pcmmad_system_net_bytes_recv", (system.get("network") or {}).get("bytes_recv"))
    _set_gauge("pcmmad_http_server_worker_threads", server.get("worker_threads"))
    _set_gauge("pcmmad_http_server_active_workers", server.get("active_workers"))
    _set_gauge("pcmmad_http_server_queue_depth", server.get("queue_depth"))
    _set_gauge("pcmmad_http_server_active_peak", server.get("active_peak"))
    _set_gauge("pcmmad_http_server_queue_peak", server.get("queue_peak"))


def _execution_snapshot() -> JsonObject:
    try:
        from .execution_routes import execution_readiness
        execution = execution_readiness()
    except Exception as exc:
        return {"status": "unavailable", "error": f"{type(exc).__name__}: {exc}"}
    global_state = execution.get("global") or {}
    scheduler = execution.get("scheduler_telemetry") or {}
    _set_gauge("pcmmad_execution_running", global_state.get("running") or 0)
    _set_gauge("pcmmad_execution_queued", global_state.get("queued") or 0)
    _set_gauge("pcmmad_execution_worker_limit", global_state.get("global_limit") or 0)
    _set_gauge("pcmmad_execution_unsupervised_jobs", len(execution.get("unsupervised_jobs") or []))
    _set_gauge("pcmmad_execution_corrupt_job_files", len(execution.get("corrupt_job_files") or []))
    _set_gauge("pcmmad_execution_reconcile_errors", scheduler.get("jobs_reconcile_errors") or 0)
    _set_gauge("pcmmad_execution_watcher_errors", scheduler.get("watcher_errors") or 0)
    return execution


def telemetry_snapshot() -> JsonObject:
    try:
        process = _process_snapshot()
        system = _system_snapshot()
        server = _waitress_snapshot()
        http = _http_summary()
        execution = _execution_snapshot()
        _refresh_gauges(process, system, server)
        return {
            "ok": True,
            "status": "available",
            "checked_at": time.time(),
            "basis": "receiver_owned_observability",
            "dependencies": dependency_snapshot(),
            "process": process,
            "system": system,
            "http": http,
            "server": server,
            "execution": execution,
        }
    except Exception as exc:  # telemetry failure must not crash the authority plane
        _OBSERVATION_ERRORS.inc()
        return {
            "ok": False,
            "status": "degraded",
            "checked_at": time.time(),
            "basis": "receiver_owned_observability",
            "error": f"{type(exc).__name__}: {exc}",
            "dependencies": dependency_snapshot(),
        }


def _require_auth():
    try:
        require_valid_api_key(request.headers)
    except PermissionError as exc:
        return jsonify({
            "ok": False,
            "error_code": "UNAUTHORIZED",
            "message": str(exc),
        }), 401
    return None


@observability_bp.get("/telemetry")
def observability_telemetry():
    denied = _require_auth()
    if denied is not None:
        return denied
    return jsonify(telemetry_snapshot())


@observability_bp.get("/metrics")
def observability_metrics():
    denied = _require_auth()
    if denied is not None:
        return denied
    telemetry_snapshot()
    return Response(generate_latest(_REGISTRY), content_type=CONTENT_TYPE_LATEST)


def _waitress_sampler() -> None:
    global _WAITRESS_ACTIVE_PEAK, _WAITRESS_QUEUE_PEAK
    while True:
        queue_depth, active, worker_threads = _waitress_values()
        if queue_depth is None or active is None:
            time.sleep(0.10)
            continue
        with _WAITRESS_LOCK:
            _WAITRESS_QUEUE_PEAK = max(_WAITRESS_QUEUE_PEAK, queue_depth)
            _WAITRESS_ACTIVE_PEAK = max(_WAITRESS_ACTIVE_PEAK, active)
            queue_peak = _WAITRESS_QUEUE_PEAK
            active_peak = _WAITRESS_ACTIVE_PEAK
        _set_gauge("pcmmad_http_server_queue_depth", queue_depth)
        _set_gauge("pcmmad_http_server_active_workers", active)
        _set_gauge("pcmmad_http_server_worker_threads", worker_threads)
        _set_gauge("pcmmad_http_server_queue_peak", queue_peak)
        _set_gauge("pcmmad_http_server_active_peak", active_peak)
        time.sleep(0.10)


def bind_waitress_server(server: Any) -> None:
    """Bind one running Waitress server for low-overhead saturation telemetry."""

    global _WAITRESS_SERVER, _WAITRESS_SAMPLER
    with _WAITRESS_LOCK:
        _WAITRESS_SERVER = server
        if _WAITRESS_SAMPLER is not None and _WAITRESS_SAMPLER.is_alive():
            return
        _WAITRESS_SAMPLER = threading.Thread(
            target=_waitress_sampler,
            name="pcmmad-observability-waitress-sampler",
            daemon=True,
        )
        _WAITRESS_SAMPLER.start()
