"""
Singularity Works — Forge HUD Server v2.0
Production cockpit backend: WebSocket live stream, file watcher, event log,
project scope awareness. Claude Code is the harness. You are the commander.

Endpoints:
  GET  /api/health               — server status
  GET  /api/version              — forge capability manifest
  POST /api/analyze              — manual forge run on submitted code
  POST /api/analyze_file         — forge run on a specific file path
  POST /api/project              — set active project directory
  GET  /api/project              — get active project state
  GET  /api/events               — MCP event ring buffer (last N)
  GET  /api/commit_log           — commit gate history

WebSocket (Socket.IO):
  Client receives: forge_event, file_analyzed, project_state, status
  Client emits:    set_project, analyze_request, clear_events
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
import threading
from collections import deque
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_OK = True
except ImportError:
    WATCHDOG_OK = False

app = Flask(__name__)
app.config["SECRET_KEY"] = "sw-forge-hud-2025"
CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ── Constants ──────────────────────────────────────────────────────────────────
FORGE_VERSION = "1.29"
MAX_EVENTS     = 500
MAX_COMMIT_LOG = 100
WATCH_EXTENSIONS = {".py", ".js", ".ts", ".go", ".rs", ".java", ".c", ".cpp",
                    ".rb", ".php", ".cs", ".swift", ".kt", ".sh"}

# ── Ring buffers ───────────────────────────────────────────────────────────────
event_log:   deque[dict] = deque(maxlen=MAX_EVENTS)
commit_log:  deque[dict] = deque(maxlen=MAX_COMMIT_LOG)
_log_lock = threading.Lock()

# ── Project state ──────────────────────────────────────────────────────────────
@dataclass
class ProjectState:
    root:         Optional[str] = None
    active_file:  Optional[str] = None
    active_code:  Optional[str] = None
    last_result:  Optional[dict] = None
    file_results: dict = field(default_factory=dict)   # path → last result
    watcher:      Optional[object] = field(default=None, repr=False)

project = ProjectState()
_project_lock = threading.Lock()

# ── Event helpers ──────────────────────────────────────────────────────────────
def _ts() -> str:
    return time.strftime("%H:%M:%S")

def _push_event(kind: str, payload: dict) -> None:
    evt = {"ts": _ts(), "kind": kind, **payload}
    with _log_lock:
        event_log.append(evt)
    socketio.emit("forge_event", evt)

def _push_commit(result: dict, path: str) -> None:
    entry = {
        "ts": _ts(),
        "path": Path(path).name if path else "?",
        "assurance": result.get("assurance", "?"),
        "tier": (result.get("starmap_topology") or {}).get("trust_tier", "?"),
        "gate_pass": result.get("gate_pass", 0),
        "gate_fail": result.get("gate_fail", 0),
        "blobs": (result.get("lbe_result") or {}).get("blob_count", 0),
    }
    with _log_lock:
        commit_log.appendleft(entry)
    socketio.emit("commit_log_update", entry)

# ── Forge runner ───────────────────────────────────────────────────────────────
_configs = Path(__file__).parent / "configs"

def _run_forge(code: str, requirement: str, tags: list[str],
               source_path: str = "<input>") -> dict:
    """Run the full forge pipeline. Returns a serializable result dict."""
    import tempfile, shutil
    from singularity_works.orchestration import Orchestrator
    from singularity_works.models import Requirement, RunContext
    from singularity_works.facts import FactBus

    _push_event("forge_start", {
        "msg": f"Analysis started — {Path(source_path).name}",
        "path": source_path,
    })

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        shutil.copytree(str(_configs), str(tmp_path / "configs"))
        orc = Orchestrator(tmp_path / "evidence.jsonl")
        orc.facts = FactBus()

        t0 = time.perf_counter()

        _push_event("gate_phase", {"msg": "Running gate fabric…"})
        r = orc.run(
            RunContext("hud-analysis", "qa", "hud", {}),
            Requirement("REQ-HUD", requirement, tags=tags),
            code,
        )
        elapsed = round((time.perf_counter() - t0) * 1000, 1)

        hud_snapshot = getattr(r, "hud_snapshot", None)
        if hud_snapshot is None:
            try:
                from dataclasses import asdict as _dc_asdict
                from singularity_works.hud import snapshot_from_run_result as _snapshot_from_run_result
                hud_snapshot = _dc_asdict(_snapshot_from_run_result(r, orc))
            except Exception:
                hud_snapshot = None

    # ── Serialize gate results ─────────────────────────────────────────────
    gate_results = []
    for gr in r.gate_summary.results:
        findings = []
        for fn in gr.findings[:3]:
            findings.append({
                "message": fn.message,
                "line": fn.evidence.get("line", 0) if hasattr(fn, "evidence") else 0,
            })
        gate_results.append({
            "gate_id": gr.gate_id,
            "status": gr.status,
            "findings": findings,
        })

    g_pass = sum(1 for g in gate_results if g["status"] == "pass")
    g_fail = sum(1 for g in gate_results if g["status"] == "fail")
    g_warn = sum(1 for g in gate_results if g["status"] == "warn")

    assurance = r.assurance.status
    _push_event("gate_done", {
        "msg": f"Gates: {g_pass}✓ {g_warn}⚠ {g_fail}✗ | assurance: {assurance.upper()}",
        "assurance": assurance,
        "gate_pass": g_pass, "gate_fail": g_fail, "gate_warn": g_warn,
    })

    # ── Escalation / LBE ──────────────────────────────────────────────────
    escalated = bool(r.escalation_decision and r.escalation_decision.get("route_to_lbe"))
    if escalated:
        _push_event("lbe_phase", {
            "msg": "Escalated → LBE Universal Reasoner running…",
            "reason": r.escalation_decision.get("triggers", []),
        })

    # ── LBE result ────────────────────────────────────────────────────────
    lbe = r.lbe_result
    if lbe:
        blob_count = lbe.get("blob_count", 0)
        verdict = lbe.get("verdict", "")
        _push_event("lbe_done", {
            "msg": f"LBE: {blob_count} blob(s) — {verdict[:60]}",
            "blob_count": blob_count,
            "highest_risk": lbe.get("highest_risk", 0),
        })

    # ── Blueprint ─────────────────────────────────────────────────────────
    bp = r.lbe_blueprint
    if bp:
        _push_event("blueprint_ready", {
            "msg": f"Blueprint: 🔴{bp.get('red_paths',0)} 🟡{bp.get('yellow_paths',0)} "
                   f"🟢{bp.get('green_paths',0)} 🟣{bp.get('purple_paths',0)}",
        })

    # ── StarMap ───────────────────────────────────────────────────────────
    sm = r.starmap_topology or {}
    tier = sm.get("trust_tier", "?")
    fiedler = sm.get("fiedler_value", 0) or 0
    _push_event("starmap_ready", {
        "msg": f"StarMap: tier={tier} | λ₂={fiedler:.3f}",
        "trust_tier": tier,
        "fiedler_value": fiedler,
    })

    # ── Monitors ──────────────────────────────────────────────────────────
    monitor_events = []
    for ev in r.monitor_events:
        monitor_events.append({"monitor_id": ev.monitor_id, "status": ev.status})
        if ev.status == "fail":
            _push_event("monitor_fail", {
                "msg": f"Monitor FAIL: {ev.monitor_id}",
                "monitor_id": ev.monitor_id,
            })

    _push_event("forge_done", {
        "msg": f"Done — {elapsed}ms | {assurance.upper()} | tier={tier}",
        "elapsed_ms": elapsed,
        "assurance": assurance,
    })

    result = {
        "elapsed_ms":          elapsed,
        "source_path":         source_path,
        "assurance":           assurance,
        "escalated":           escalated,
        "escalation_decision": r.escalation_decision,
        "gate_results":        gate_results,
        "gate_pass":           g_pass,
        "gate_fail":           g_fail,
        "gate_warn":           g_warn,
        "hud_snapshot":        hud_snapshot,
        "lbe_result":          lbe,
        "lbe_blueprint":       bp,
        "starmap_topology":    sm,
        "monitor_events":      monitor_events,
    }

    # Push annotations for center panel
    socketio.emit("file_analyzed", {
        "path": source_path,
        "result": result,
    })

    return result


# ── File watcher ───────────────────────────────────────────────────────────────
class ForgeFileWatcher(FileSystemEventHandler):
    """Watches project directory. Auto-runs forge on any supported file change."""

    def __init__(self, root: str):
        self.root = root
        self._debounce: dict[str, float] = {}
        self._debounce_lock = threading.Lock()

    def on_modified(self, event):
        if event.is_directory:
            return
        path = event.src_path
        ext = Path(path).suffix.lower()
        if ext not in WATCH_EXTENSIONS:
            return
        # Debounce: 1.5s per file
        now = time.time()
        with self._debounce_lock:
            last = self._debounce.get(path, 0)
            if now - last < 1.5:
                return
            self._debounce[path] = now

        _push_event("file_change", {
            "msg": f"File changed: {Path(path).relative_to(self.root)}",
            "path": path,
        })
        threading.Thread(target=self._analyze, args=(path,), daemon=True).start()

    def _analyze(self, path: str) -> None:
        try:
            code = Path(path).read_text(encoding="utf-8", errors="replace")
            result = _run_forge(
                code=code,
                requirement="Security and correctness analysis.",
                tags=["security", "correctness"],
                source_path=path,
            )
            with _project_lock:
                project.active_file = path
                project.active_code = code
                project.last_result = result
                project.file_results[path] = result
            _push_commit(result, path)
            socketio.emit("project_state", _project_snapshot())
        except Exception as e:
            _push_event("error", {"msg": f"Watcher error on {Path(path).name}: {e}"})


def _start_watcher(root: str) -> None:
    if not WATCHDOG_OK:
        _push_event("warn", {"msg": "watchdog not available — file watching disabled"})
        return
    # Stop existing watcher
    with _project_lock:
        if project.watcher:
            try:
                project.watcher.stop()
                project.watcher.join(timeout=2)
            except Exception:
                pass
    observer = Observer()
    handler = ForgeFileWatcher(root)
    observer.schedule(handler, root, recursive=True)
    observer.start()
    with _project_lock:
        project.watcher = observer
    _push_event("watcher_start", {"msg": f"Watching: {root}"})


# ── Snapshot helper ────────────────────────────────────────────────────────────
def _project_snapshot() -> dict:
    with _project_lock:
        return {
            "root":        project.root,
            "active_file": project.active_file,
            "last_result": project.last_result,
            "file_count":  len(project.file_results),
        }


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "version": FORGE_VERSION,
        "forge": "Singularity Works",
        "watchdog": WATCHDOG_OK,
        "project_root": project.root,
    })


@app.route("/api/version")
def version():
    return jsonify({
        "forge_version":  FORGE_VERSION,
        "gate_count":     53,
        "mcp_tools":      8,
        "lbe_engines":    ["python_ast", "universal", "generic"],
        "starmap":        True,
        "blueprint":      True,
        "file_watcher":   WATCHDOG_OK,
        "websocket":      True,
    })


@app.route("/api/analyze", methods=["POST"])
def analyze():
    data        = request.get_json(force=True)
    code        = data.get("code", "").strip()
    requirement = data.get("requirement", "Security analysis.").strip()
    tags        = data.get("tags", ["security"])
    source_path = data.get("path", "<input>")
    if not code:
        return jsonify({"error": "code is required"}), 400
    try:
        result = _run_forge(code, requirement, tags, source_path)
        with _project_lock:
            project.active_code = code
            project.last_result = result
            if source_path != "<input>":
                project.active_file = source_path
                project.file_results[source_path] = result
        _push_commit(result, source_path)
        return jsonify(result)
    except Exception as e:
        _push_event("error", {"msg": str(e)})
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/analyze_file", methods=["POST"])
def analyze_file():
    data = request.get_json(force=True)
    path = data.get("path", "").strip()
    requirement = data.get("requirement", "Security analysis.").strip()
    if not path:
        return jsonify({"error": "path is required"}), 400
    try:
        code = Path(path).read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return jsonify({"error": f"Cannot read {path}: {e}"}), 400
    try:
        result = _run_forge(code, requirement, ["security", "correctness"], path)
        with _project_lock:
            project.active_file = path
            project.active_code = code
            project.last_result = result
            project.file_results[path] = result
        _push_commit(result, path)
        socketio.emit("project_state", _project_snapshot())
        return jsonify(result)
    except Exception as e:
        _push_event("error", {"msg": str(e)})
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/project", methods=["GET"])
def get_project():
    return jsonify(_project_snapshot())


@app.route("/api/project", methods=["POST"])
def set_project():
    data = request.get_json(force=True)
    root = data.get("root", "").strip()
    if not root or not Path(root).is_dir():
        return jsonify({"error": f"Invalid directory: {root}"}), 400
    with _project_lock:
        project.root = root
        project.file_results.clear()
        project.active_file = None
        project.active_code = None
        project.last_result = None
    _start_watcher(root)
    socketio.emit("project_state", _project_snapshot())
    return jsonify({"ok": True, "root": root})


@app.route("/api/events")
def get_events():
    n = int(request.args.get("n", 100))
    with _log_lock:
        events = list(event_log)[-n:]
    return jsonify(events)


@app.route("/api/commit_log")
def get_commit_log():
    with _log_lock:
        log = list(commit_log)
    return jsonify(log)


# ── Socket.IO handlers ─────────────────────────────────────────────────────────

@socketio.on("connect")
def on_connect():
    emit("status", {
        "msg": "Forge HUD connected",
        "version": FORGE_VERSION,
        "project": _project_snapshot(),
    })
    # Replay last 50 events to new client
    with _log_lock:
        replay = list(event_log)[-50:]
    for evt in replay:
        emit("forge_event", evt)


@socketio.on("set_project")
def on_set_project(data):
    root = (data or {}).get("root", "").strip()
    if root and Path(root).is_dir():
        with _project_lock:
            project.root = root
            project.file_results.clear()
        _start_watcher(root)
        emit("project_state", _project_snapshot(), broadcast=True)


@socketio.on("analyze_request")
def on_analyze_request(data):
    code        = (data or {}).get("code", "").strip()
    requirement = (data or {}).get("requirement", "Security analysis.")
    path        = (data or {}).get("path", "<input>")
    if not code:
        emit("forge_event", {"ts": _ts(), "kind": "error", "msg": "No code provided"})
        return
    def _run():
        try:
            result = _run_forge(code, requirement, ["security", "correctness"], path)
            with _project_lock:
                project.active_code = code
                project.last_result = result
            _push_commit(result, path)
        except Exception as e:
            _push_event("error", {"msg": str(e)})
    threading.Thread(target=_run, daemon=True).start()


@socketio.on("clear_events")
def on_clear_events(_data=None):
    with _log_lock:
        event_log.clear()
    emit("events_cleared", {}, broadcast=True)


# ── Entry ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Forge HUD Server v2.0 — http://localhost:5173")
    print(f"  watchdog: {'✓' if WATCHDOG_OK else '✗ (install watchdog for file watching)'}")
    socketio.run(app, host="0.0.0.0", port=5173, debug=False, allow_unsafe_werkzeug=True)
