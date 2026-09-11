"""PCMMAD operator-plane supervisor.

Owns lifecycle discovery/control for the local Operations HUD. The HUD is a
receiver operator surface, not a research-project runtime dependency.
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

HUD_HOST = os.environ.get("PCMMAD_HUD_HOST", "127.0.0.1")
HUD_PORT = int(os.environ.get("PCMMAD_HUD_PORT", "5090"))
RUNTIME_ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT = RUNTIME_ROOT.parents[1]
RECEIVER_LOCAL_HUD = PACKAGE_ROOT / "operator_hud" / "server.py"


def _hud_server_candidates() -> list[tuple[Path, str]]:
    override = os.environ.get("PCMMAD_HUD_SERVER", "").strip()
    raw: list[tuple[Path, str]] = []
    if override:
        raw.append((Path(override).expanduser(), "env_override"))
    raw.append((RECEIVER_LOCAL_HUD, "receiver_local"))
    found: list[tuple[Path, str]] = []
    seen: set[str] = set()
    for path, source in raw:
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        key = str(resolved).casefold()
        if key in seen:
            continue
        seen.add(key)
        if resolved.is_file():
            found.append((resolved, source))
    return found


def resolve_hud_server() -> tuple[Path | None, str]:
    candidates = _hud_server_candidates()
    return candidates[0] if candidates else (None, "missing")


def _command_fingerprint(command_line: str) -> str:
    return hashlib.sha256(str(command_line or "").encode("utf-8")).hexdigest()


def _process_info(pid: int | None) -> dict[str, Any] | None:
    if os.name != "nt" or not pid:
        return None
    ps = (
        f"Get-CimInstance Win32_Process -Filter \"ProcessId = {int(pid)}\" "
        "-ErrorAction SilentlyContinue | "
        "Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine,CreationDate | "
        "ConvertTo-Json -Compress"
    )
    try:
        cp = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        raw = cp.stdout.strip()
        if cp.returncode != 0 or not raw:
            return None
        row = json.loads(raw)
        if not isinstance(row, dict):
            return None
        command = str(row.get("CommandLine") or "")
        return {
            "pid": int(row.get("ProcessId") or pid),
            "parent_pid": int(row.get("ParentProcessId") or 0) or None,
            "executable_path": str(row.get("ExecutablePath") or "") or None,
            "creation_date": str(row.get("CreationDate") or "") or None,
            "command_fingerprint": _command_fingerprint(command),
            "command_line": command,
        }
    except (OSError, subprocess.SubprocessError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _match_hud_server(command_line: str) -> tuple[Path | None, str | None]:
    folded = str(command_line or "").casefold()
    for path, source in _hud_server_candidates():
        if str(path).casefold() in folded:
            return path, source
    return None, None


def _public_process_identity(info: dict[str, Any] | None) -> dict[str, Any] | None:
    if not info:
        return None
    return {
        "pid": info.get("pid"),
        "parent_pid": info.get("parent_pid"),
        "executable_path": info.get("executable_path"),
        "creation_date": info.get("creation_date"),
        "command_fingerprint": info.get("command_fingerprint"),
    }


def _hud_process_identity(listener_pid: int | None) -> dict[str, Any]:
    listener = _process_info(listener_pid)
    if not listener:
        return {
            "recognized": False,
            "listener": None,
            "running_server_path": None,
            "running_server_source": None,
            "kill_root": None,
        }
    server_path, source = _match_hud_server(str(listener.get("command_line") or ""))
    recognized = server_path is not None
    kill_root = listener
    parent = _process_info(listener.get("parent_pid"))
    if recognized and parent:
        parent_path, _parent_source = _match_hud_server(str(parent.get("command_line") or ""))
        if parent_path is not None and parent_path == server_path:
            kill_root = parent
    return {
        "recognized": recognized,
        "listener": _public_process_identity(listener),
        "running_server_path": str(server_path) if server_path else None,
        "running_server_source": source,
        "kill_root": _public_process_identity(kill_root) if recognized else None,
    }


def _identity_matches(expected: dict[str, Any] | None) -> bool:
    if not expected or not expected.get("pid"):
        return False
    current = _process_info(int(expected["pid"]))
    if not current:
        return False
    return (
        current.get("creation_date") == expected.get("creation_date")
        and current.get("command_fingerprint") == expected.get("command_fingerprint")
    )


def _port_owner_pid(port: int = HUD_PORT) -> int | None:
    if os.name != "nt":
        return None
    ps = (
        f"(Get-NetTCPConnection -State Listen -LocalPort {int(port)} "
        "-ErrorAction SilentlyContinue | Select-Object -First 1).OwningProcess"
    )
    try:
        cp = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        value = cp.stdout.strip()
        return int(value) if value.isdigit() else None
    except Exception:
        return None


def _port_open(host: str = HUD_HOST, port: int = HUD_PORT, timeout: float = 0.25) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _http_meta(timeout: float = 1.0) -> tuple[bool, dict[str, Any] | None, str | None]:
    try:
        with urllib.request.urlopen(f"http://{HUD_HOST}:{HUD_PORT}/api/meta", timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return bool(resp.status == 200 and body.get("ok")), body, None
    except Exception as exc:
        return False, None, f"{type(exc).__name__}: {exc}"


def hud_status() -> dict[str, Any]:
    preferred, preferred_source = resolve_hud_server()
    listening = _port_open()
    listener_pid = _port_owner_pid() if listening else None
    identity = _hud_process_identity(listener_pid) if listening else {
        "recognized": False,
        "listener": None,
        "running_server_path": None,
        "running_server_source": None,
        "kill_root": None,
    }
    meta_ok, meta, error = _http_meta() if listening else (False, None, "not listening")
    meta_identity_ok = bool(
        meta_ok
        and isinstance(meta, dict)
        and str(meta.get("hud") or "").strip() == "PCMMAD Operations HUD"
    )
    healthy = bool(listening and meta_identity_ok)
    owned = bool(identity.get("recognized"))
    reason = None
    if listening and not owned:
        reason = "port is occupied by an unrecognized process; lifecycle control is refused"
    elif listening and owned and not healthy:
        reason = "recognized HUD process is present but /api/meta is unhealthy or identity-invalid"
    elif not listening:
        reason = "not listening"
    return {
        "ok": bool(healthy and owned),
        "healthy": healthy,
        "owned": owned,
        "host": HUD_HOST,
        "port": HUD_PORT,
        "listener_pid": listener_pid,
        "preferred_server_path": str(preferred) if preferred else None,
        "preferred_server_source": preferred_source,
        "running_server_path": identity.get("running_server_path"),
        "running_server_source": identity.get("running_server_source"),
        "process_identity": identity,
        "meta": meta,
        "error": error if not healthy else None,
        "reason": reason,
    }


def ensure_hud_running(*, wait_seconds: float = 8.0) -> dict[str, Any]:
    status = hud_status()
    if status["ok"]:
        return {**status, "action": "already_running"}
    server, source = resolve_hud_server()
    if server is None:
        raise FileNotFoundError("no PCMMAD HUD server implementation found")
    if _port_open():
        raise RuntimeError(f"HUD port {HUD_PORT} is occupied but /api/meta is unhealthy")

    env = os.environ.copy()
    env["PCMMAD_HUD_HOST"] = HUD_HOST
    env["PCMMAD_HUD_PORT"] = str(HUD_PORT)
    if not str(env.get("PCMMAD_RECEIVER_BASE") or "").strip():
        receiver_host = str(env.get("PCMMAD_BIND_HOST") or "127.0.0.1").strip() or "127.0.0.1"
        receiver_port = str(env.get("PCMMAD_BIND_PORT") or "5000").strip() or "5000"
        env["PCMMAD_RECEIVER_BASE"] = f"http://{receiver_host}:{receiver_port}"
    creationflags = 0
    if os.name == "nt":
        creationflags = int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)) | int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
    proc = subprocess.Popen(
        [sys.executable, str(server)],
        cwd=str(server.parent),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
        close_fds=True,
    )
    deadline = time.monotonic() + max(0.5, float(wait_seconds))
    last = None
    identity_mismatch = None
    while time.monotonic() < deadline:
        last = hud_status()
        if last["ok"]:
            running = str(last.get("running_server_path") or "")
            if running.casefold() != str(server.resolve()).casefold():
                identity_mismatch = (
                    "HUD start identity mismatch: a different recognized HUD implementation owns the port"
                )
                break
            return {
                **last,
                "action": "started",
                "launcher_pid": int(proc.pid),
                "server_source": source,
            }
        if proc.poll() is not None:
            break
        time.sleep(0.2)
    if proc.poll() is None:
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    check=False,
                )
            else:
                proc.kill()
        except Exception:
            pass
    if identity_mismatch:
        raise RuntimeError(identity_mismatch)
    raise RuntimeError(f"HUD start did not become healthy; launcher_pid={proc.pid}, last={last}")


def stop_hud(*, timeout_seconds: float = 8.0) -> dict[str, Any]:
    status = hud_status()
    pid = status.get("listener_pid")
    if not pid:
        return {"ok": True, "action": "already_stopped", "port": HUD_PORT}
    if os.name != "nt":
        raise RuntimeError("HUD stop is currently implemented only for Windows")
    if not status.get("owned"):
        raise RuntimeError(
            f"HUD_PROCESS_IDENTITY_MISMATCH: refusing to kill unrecognized listener PID {pid} on port {HUD_PORT}"
        )
    identity = status.get("process_identity") or {}
    listener_identity = identity.get("listener")
    kill_root = identity.get("kill_root") or listener_identity
    if not _identity_matches(listener_identity) or not _identity_matches(kill_root):
        raise RuntimeError(
            "HUD_PROCESS_IDENTITY_STALE: listener/kill-root identity changed before control action"
        )
    kill_pid = int(kill_root["pid"])
    cp = subprocess.run(
        ["taskkill", "/PID", str(kill_pid), "/T", "/F"],
        capture_output=True,
        text=True,
        timeout=max(2.0, float(timeout_seconds)),
        check=False,
    )
    deadline = time.monotonic() + max(0.5, float(timeout_seconds))
    last = None
    while time.monotonic() < deadline:
        if not _port_open():
            return {
                "ok": True,
                "action": "stopped",
                "listener_pid": int(pid),
                "stopped_root_pid": kill_pid,
                "process_identity": identity,
                "taskkill_rc": cp.returncode,
            }
        last = hud_status()
        # If another process acquired the port after our verified HUD exited, the
        # stop succeeded; do not attempt to kill the newcomer.
        if int(last.get("listener_pid") or 0) != int(pid) and not last.get("owned"):
            return {
                "ok": True,
                "action": "stopped_port_reoccupied",
                "listener_pid": int(pid),
                "stopped_root_pid": kill_pid,
                "new_listener": last,
                "taskkill_rc": cp.returncode,
            }
        time.sleep(0.2)
    raise RuntimeError(
        f"verified HUD process tree rooted at PID {kill_pid} did not release control of port {HUD_PORT}; last={last}"
    )


def restart_hud() -> dict[str, Any]:
    before = hud_status()
    stopped = stop_hud()
    started = ensure_hud_running()
    return {"ok": bool(started.get("ok")), "before": before, "stop": stopped, "after": started}
