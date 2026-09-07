"""Durable one-job execution actuator for the canonical PCMMAD scheduler.

This module is intentionally NOT a scheduler. It cannot admit, queue, replay, or
promote jobs. It executes exactly one scheduler-authored request and writes
heartbeat/completion receipts that survive receiver-process restarts.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

HEARTBEAT_INTERVAL_SECONDS = 0.20


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), delete=False) as handle:
        handle.write(encoded)
        handle.write("\n")
        temp_path = Path(handle.name)
    # Windows can transiently deny replacement while a concurrent reader has the
    # destination open without delete sharing. Preserve atomicity and retry the
    # rename briefly rather than misclassifying a telemetry collision as job failure.
    deadline = time.monotonic() + 1.0
    delay = 0.005
    while True:
        try:
            os.replace(temp_path, path)
            break
        except PermissionError:
            if time.monotonic() >= deadline:
                temp_path.unlink(missing_ok=True)
                raise
            time.sleep(delay)
            delay = min(delay * 1.8, 0.05)


def _load_request(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("worker request must be a JSON object")
    required = (
        "job_id",
        "worker_token",
        "command",
        "cwd",
        "stdout_path",
        "stderr_path",
        "heartbeat_path",
        "completion_path",
        "cancel_path",
        "ownership_release_path",
    )
    for key in required:
        if key not in raw:
            raise ValueError(f"worker request missing {key}")
    command = raw["command"]
    if not isinstance(command, list) or not command or not all(isinstance(x, str) and x for x in command):
        raise ValueError("worker request command must be a non-empty string array")
    return raw


def _kill_process_tree(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
                check=False,
            )
        except Exception:
            proc.kill()
    else:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            proc.kill()


def _receipt_base(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": str(request["job_id"]),
        "worker_token": str(request["worker_token"]),
        "worker_pid": os.getpid(),
    }


def _heartbeat(request: dict[str, Any], *, state: str, child_pid: int | None, started_at: str) -> None:
    payload = {
        **_receipt_base(request),
        "state": state,
        "child_pid": child_pid,
        "started_at": started_at,
        "heartbeat_at": _utc_now(),
    }
    _atomic_json(Path(str(request["heartbeat_path"])), payload)


def _completion(
    request: dict[str, Any],
    *,
    state: str,
    return_code: int,
    child_pid: int | None,
    started_at: str,
    reason: str | None = None,
) -> None:
    payload = {
        **_receipt_base(request),
        "state": state,
        "return_code": int(return_code),
        "child_pid": child_pid,
        "started_at": started_at,
        "finished_at": _utc_now(),
        "reason": reason,
    }
    _atomic_json(Path(str(request["completion_path"])), payload)


def _child_options(request: dict[str, Any]) -> dict[str, Any]:
    env = os.environ.copy()
    for key, value in dict(request.get("env_allowlist") or {}).items():
        if isinstance(key, str) and isinstance(value, str):
            env[key] = value
    options: dict[str, Any] = {
        "cwd": str(request["cwd"]),
        "stdin": subprocess.DEVNULL,
        "shell": False,
        "env": env,
    }
    if os.name == "nt":
        options["creationflags"] = int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
    else:
        options["start_new_session"] = True
    return options


def _open_ownership_anchor(request: dict[str, Any]):
    job_object_name = str(request.get("job_object_name") or "").strip()
    if os.name != "nt" or not job_object_name:
        return None
    import windows_job_object as wjo
    return wjo.open_named_job(job_object_name, terminate=False)


def _wait_for_ownership_release(
    request: dict[str, Any], *, started_at: str, cancel_path: Path, timeout_seconds: float = 8.0
) -> str:
    release_path = Path(str(request["ownership_release_path"]))
    deadline = time.monotonic() + max(0.5, float(timeout_seconds))
    while time.monotonic() < deadline:
        if cancel_path.exists():
            return "cancelled"
        if release_path.is_file():
            try:
                payload = json.loads(release_path.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                payload = None
            if (
                isinstance(payload, dict)
                and str(payload.get("job_id") or "") == str(request["job_id"])
                and str(payload.get("worker_token") or "") == str(request["worker_token"])
                and payload.get("permit_spawn") is True
            ):
                return "released"
        _heartbeat(request, state="OWNERSHIP_READY", child_pid=None, started_at=started_at)
        time.sleep(0.05)
    return "timeout"


def _project_mutation_context(request: dict[str, Any]):
    binding = request.get("project_mutation_binding")
    if not isinstance(binding, dict):
        from contextlib import nullcontext
        return nullcontext()
    project_id = str(request.get("project_id") or "").strip()
    if not project_id:
        raise ValueError("bound execution worker request missing project_id")
    from project_mutation_authority import runtime_bound_mutation_guard
    return runtime_bound_mutation_guard(project_id, binding)


def run_request(request_path: Path) -> int:
    request = _load_request(request_path)
    heartbeat_path = Path(str(request["heartbeat_path"]))
    completion_path = Path(str(request["completion_path"]))
    cancel_path = Path(str(request["cancel_path"]))
    stdout_path = Path(str(request["stdout_path"]))
    stderr_path = Path(str(request["stderr_path"]))
    timeout_seconds = request.get("timeout_seconds")
    timeout_seconds = None if timeout_seconds in (None, 0, -1) else float(timeout_seconds)

    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    started_at = _utc_now()
    proc: subprocess.Popen[bytes] | None = None
    ownership_anchor = None
    try:
        ownership_anchor = _open_ownership_anchor(request)
        _heartbeat(
            request,
            state="OWNERSHIP_READY" if ownership_anchor is not None else "WORKER_STARTING",
            child_pid=None,
            started_at=started_at,
        )
        if ownership_anchor is not None:
            outcome = _wait_for_ownership_release(
                request, started_at=started_at, cancel_path=cancel_path, timeout_seconds=8.0
            )
            if outcome == "cancelled":
                _completion(
                    request, state="TERMINATED", return_code=-9, child_pid=None,
                    started_at=started_at, reason="CANCEL_BEFORE_SPAWN",
                )
                _heartbeat(request, state="TERMINATED", child_pid=None, started_at=started_at)
                return 0
            if outcome != "released":
                raise RuntimeError("OWNERSHIP_HANDSHAKE_TIMEOUT")

        with _project_mutation_context(request):
            with stdout_path.open("wb") as out_f, stderr_path.open("wb") as err_f:
                options = _child_options(request)
                options["stdout"] = out_f
                options["stderr"] = err_f
                proc = subprocess.Popen(list(request["command"]), **options)
                child_pid = int(proc.pid)
                _heartbeat(request, state="RUNNING", child_pid=child_pid, started_at=started_at)
                start_monotonic = time.monotonic()

                while True:
                    return_code = proc.poll()
                    if return_code is not None:
                        state = "COMPLETED" if return_code == 0 else "FAILED"
                        _completion(
                            request,
                            state=state,
                            return_code=int(return_code),
                            child_pid=child_pid,
                            started_at=started_at,
                            reason=None if return_code == 0 else "NONZERO_EXIT",
                        )
                        _heartbeat(request, state=state, child_pid=child_pid, started_at=started_at)
                        return int(return_code)

                    if cancel_path.exists():
                        _kill_process_tree(proc)
                        proc.wait(timeout=10)
                        _completion(
                            request,
                            state="TERMINATED",
                            return_code=-9,
                            child_pid=child_pid,
                            started_at=started_at,
                            reason="CANCEL_REQUEST",
                        )
                        _heartbeat(request, state="TERMINATED", child_pid=child_pid, started_at=started_at)
                        return 0

                    if timeout_seconds is not None and (time.monotonic() - start_monotonic) > timeout_seconds:
                        _kill_process_tree(proc)
                        proc.wait(timeout=10)
                        _completion(
                            request,
                            state="TIMED_OUT",
                            return_code=-9,
                            child_pid=child_pid,
                            started_at=started_at,
                            reason="TIMEOUT",
                        )
                        _heartbeat(request, state="TIMED_OUT", child_pid=child_pid, started_at=started_at)
                        return 0

                    _heartbeat(request, state="RUNNING", child_pid=child_pid, started_at=started_at)
                    time.sleep(HEARTBEAT_INTERVAL_SECONDS)
    except Exception as exc:
        if proc is not None and proc.poll() is None:
            _kill_process_tree(proc)
        _completion(
            request,
            state="WORKER_FAILED",
            return_code=-1,
            child_pid=int(proc.pid) if proc is not None else None,
            started_at=started_at,
            reason=f"{type(exc).__name__}: {exc}",
        )
        _heartbeat(
            request,
            state="WORKER_FAILED",
            child_pid=int(proc.pid) if proc is not None else None,
            started_at=started_at,
        )
        return 1
    finally:
        if ownership_anchor is not None:
            try:
                ownership_anchor.close()
            except Exception:
                pass


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: execution_worker.py <worker_request.json>", file=sys.stderr)
        return 2
    return run_request(Path(args[0]).resolve())


if __name__ == "__main__":
    raise SystemExit(main())
