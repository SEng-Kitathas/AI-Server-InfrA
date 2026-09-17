"""Transactional promotion of the Daemon(MVF) recovery runtime.

LIVE SOURCE PROMOTED != RECOVERY DAEMON RUNTIME PROMOTED.
This module makes that second promotion explicit, hash-fenced, rollback-capable,
and consequence-readback driven. It does not grant Daemon mutation authority.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable

WORKLOAD_TASK = "PCMMAD_V30_Daemon_SYSTEM"
SUPERVISOR_TASK = "PCMMAD_V30_DaemonSupervisor_SYSTEM"
EXCLUDED_PARTS = {".git", ".pytest_cache", ".heat_runtime", "__pycache__", "build"}


def _project_id() -> str:
    return str(os.environ.get("PCMMAD_DAEMON_PROJECT_ID") or "RECEIVER-LAB")


def _live_root() -> Path:
    raw = str(os.environ.get("LIVE_RECEIVER_ROOT") or "").strip()
    return Path(raw).resolve() if raw else Path(__file__).resolve().parents[2]


def _source_root() -> Path:
    return _live_root() / "mvf_resident"


def _recovery_root() -> Path:
    raw = str(os.environ.get("PCMMAD_RECOVERY_ROOT") or "").strip()
    if raw:
        return Path(raw).resolve()
    program_data = Path(str(os.environ.get("ProgramData") or r"C:\ProgramData"))
    return (program_data / "PCMMAD" / "Recovery").resolve()


def _target_root() -> Path:
    return _recovery_root() / "daemon_runtime" / "mvf_resident"


def _promotion_root() -> Path:
    return _recovery_root() / "daemon_runtime_promotions"


def _daemon_port() -> int:
    raw = str(os.environ.get("DAEMON_PORT") or "5015")
    value = int(raw)
    if value < 1 or value > 65535:
        raise ValueError("DAEMON_PORT_OUT_OF_RANGE")
    return value


def _excluded(root: Path, path: Path) -> bool:
    rel = path.relative_to(root)
    return any(part in EXCLUDED_PARTS or part.endswith(".egg-info") for part in rel.parts) or path.suffix == ".pyc"


def _tree_manifest(root: Path) -> dict[str, dict[str, Any]]:
    root = root.resolve()
    if not root.is_dir():
        return {}
    out: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or _excluded(root, path):
            continue
        rel = path.relative_to(root).as_posix()
        data = path.read_bytes()
        out[rel] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    return out


def _tree_digest(manifest: dict[str, dict[str, Any]]) -> str:
    raw = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _copy_tree(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    for rel in _tree_manifest(source):
        src = source / Path(rel)
        dst = destination / Path(rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    tmp_path = Path(tmp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    finally:
        tmp_path.unlink(missing_ok=True)


def _powershell() -> str:
    system_root = Path(str(os.environ.get("SystemRoot") or r"C:\Windows"))
    candidate = system_root / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    return str(candidate if candidate.exists() else Path("powershell.exe"))


def _ps(script: str, timeout: int = 20) -> str:
    proc = subprocess.run(
        [_powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"POWERSHELL_FAILED:{proc.returncode}:{proc.stderr.strip()[-1000:]}")
    return proc.stdout.strip()


def _listener_pids(port: int) -> list[int]:
    raw = _ps(f"@((Get-NetTCPConnection -State Listen -LocalPort {int(port)} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique)) | ConvertTo-Json -Compress")
    if not raw:
        return []
    parsed = json.loads(raw)
    values = parsed if isinstance(parsed, list) else [parsed]
    return sorted({int(value) for value in values if value is not None})


def _process_command_line(pid: int) -> str:
    raw = _ps(f"$p=Get-CimInstance Win32_Process -Filter 'ProcessId={int(pid)}' -ErrorAction SilentlyContinue; if($p){{$p.CommandLine}}")
    return str(raw or "")


def _stop_task(name: str) -> None:
    _ps(f"$t=Get-ScheduledTask -TaskName '{name}' -ErrorAction Stop; Stop-ScheduledTask -TaskName '{name}' -ErrorAction SilentlyContinue")


def _start_task(name: str) -> None:
    _ps(f"$t=Get-ScheduledTask -TaskName '{name}' -ErrorAction Stop; Start-ScheduledTask -TaskName '{name}'")


def _task_state(name: str) -> str:
    return _ps(f"[string](Get-ScheduledTask -TaskName '{name}' -ErrorAction Stop).State")


def _kill_pid(pid: int) -> None:
    _ps(f"Stop-Process -Id {int(pid)} -Force -ErrorAction Stop")


def _wait_port_closed(port: int, timeout_seconds: float = 6.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if not _listener_pids(port):
            return True
        time.sleep(0.25)
    return not _listener_pids(port)


def _health(port: int) -> dict[str, Any]:
    with urllib.request.urlopen(f"http://127.0.0.1:{int(port)}/health", timeout=2.0) as response:
        body = json.loads(response.read().decode("utf-8"))
    if not isinstance(body, dict):
        raise RuntimeError("DAEMON_HEALTH_NOT_OBJECT")
    return body


def _quiesce_daemon(port: int) -> dict[str, Any]:
    old = _listener_pids(port)
    _stop_task(SUPERVISOR_TASK)
    time.sleep(0.5)
    _stop_task(WORKLOAD_TASK)
    reaped: list[int] = []
    if not _wait_port_closed(port):
        for pid in _listener_pids(port):
            command_line = _process_command_line(pid).casefold()
            if "daemon_task_entry.py" not in command_line:
                raise RuntimeError(f"DAEMON_LISTENER_IDENTITY_MISMATCH:{pid}")
            _kill_pid(pid)
            reaped.append(pid)
        if not _wait_port_closed(port):
            raise RuntimeError("DAEMON_PORT_DID_NOT_QUIESCE")
    return {"old_listener_pids": old, "reaped_listener_pids": reaped, "port_closed": True}


def _start_and_verify_daemon(port: int) -> dict[str, Any]:
    _start_task(WORKLOAD_TASK)
    deadline = time.time() + 15.0
    last_error = ""
    body: dict[str, Any] | None = None
    listeners: list[int] = []
    while time.time() < deadline:
        listeners = _listener_pids(port)
        if listeners:
            try:
                body = _health(port)
                if (
                    body.get("ok") is True
                    and str(body.get("schema") or "").startswith("mvf.daemon-health.")
                    and str(body.get("daemon_id") or "") == "pcmmad-daemon"
                    and str(body.get("project_id") or "") == _project_id()
                ):
                    break
            except Exception as exc:
                last_error = f"{type(exc).__name__}:{exc}"
        time.sleep(0.25)
    if body is None or body.get("ok") is not True or not listeners:
        raise RuntimeError(f"DAEMON_HEALTH_NOT_READY:{last_error}")
    _start_task(SUPERVISOR_TASK)
    time.sleep(0.5)
    return {
        "new_listener_pids": listeners,
        "health_schema": str(body.get("schema") or ""),
        "daemon_id": str(body.get("daemon_id") or ""),
        "project_id": str(body.get("project_id") or ""),
        "workload_state": _task_state(WORKLOAD_TASK),
        "supervisor_state": _task_state(SUPERVISOR_TASK),
    }


def runtime_status(project_id: str) -> dict[str, Any]:
    if str(project_id) != _project_id():
        raise ValueError("DAEMON_PROJECT_ID_MISMATCH")
    source = _source_root().resolve()
    target = _target_root().resolve()
    source_manifest = _tree_manifest(source)
    target_manifest = _tree_manifest(target)
    if not source_manifest:
        raise FileNotFoundError(f"DAEMON_SOURCE_EMPTY_OR_MISSING:{source}")
    source_digest = _tree_digest(source_manifest)
    target_digest = _tree_digest(target_manifest) if target_manifest else None
    return {
        "ok": True,
        "project_id": project_id,
        "source_root": str(source),
        "target_root": str(target),
        "source_tree_sha256": source_digest,
        "target_tree_sha256": target_digest,
        "source_file_count": len(source_manifest),
        "target_file_count": len(target_manifest),
        "current": bool(target_manifest) and source_digest == target_digest,
        "port": _daemon_port(),
        "trust_claim": "tree_content_currentness_only",
    }


def promote_runtime(project_id: str, expected_source_tree_sha256: str) -> dict[str, Any]:
    before = runtime_status(project_id)
    expected = str(expected_source_tree_sha256 or "").strip().lower()
    if expected != before["source_tree_sha256"]:
        raise RuntimeError("DAEMON_SOURCE_TREE_CURRENTNESS_MISMATCH")
    if before["current"]:
        return {**before, "promoted": False, "already_current": True}
    source = Path(before["source_root"])
    target = Path(before["target_root"])
    promotion_root = _promotion_root()
    promotion_root.mkdir(parents=True, exist_ok=True)
    tx = promotion_root / uuid.uuid4().hex
    staged = tx / "staged" / "mvf_resident"
    backup = tx / "backup" / "mvf_resident"
    tx.mkdir(parents=True, exist_ok=False)
    _copy_tree(source, staged)
    staged_manifest = _tree_manifest(staged)
    staged_digest = _tree_digest(staged_manifest)
    if staged_digest != expected:
        shutil.rmtree(tx, ignore_errors=True)
        raise RuntimeError("DAEMON_STAGED_TREE_DIGEST_MISMATCH")
    port = int(before["port"])
    quiescence = _quiesce_daemon(port)
    target.parent.mkdir(parents=True, exist_ok=True)
    target_existed = target.exists()
    swapped = False
    try:
        if target_existed:
            backup.parent.mkdir(parents=True, exist_ok=True)
            os.replace(target, backup)
        os.replace(staged, target)
        swapped = True
        target_manifest = _tree_manifest(target)
        target_digest = _tree_digest(target_manifest)
        if target_digest != expected:
            raise RuntimeError("DAEMON_PROMOTED_TREE_DIGEST_MISMATCH")
        runtime = _start_and_verify_daemon(port)
    except Exception as exc:
        try:
            _stop_task(SUPERVISOR_TASK)
            _stop_task(WORKLOAD_TASK)
            _wait_port_closed(port)
        except Exception:
            pass
        if swapped and target.exists():
            shutil.rmtree(target, ignore_errors=True)
        if target_existed and backup.exists():
            os.replace(backup, target)
        try:
            runtime = _start_and_verify_daemon(port)
        except Exception as rollback_exc:
            raise RuntimeError(f"DAEMON_RUNTIME_PROMOTION_FAILED_AND_ROLLBACK_HEALTH_FAILED:{type(exc).__name__}:{exc};{type(rollback_exc).__name__}:{rollback_exc}") from exc
        raise RuntimeError(f"DAEMON_RUNTIME_PROMOTION_FAILED_ROLLED_BACK:{type(exc).__name__}:{exc}") from exc
    after = runtime_status(project_id)
    receipt = {
        "schema": "pcmmad.daemon-runtime-promotion.v1",
        "ok": True,
        "project_id": project_id,
        "promoted": True,
        "already_current": False,
        "source_tree_sha256": expected,
        "before_target_tree_sha256": before["target_tree_sha256"],
        "after_target_tree_sha256": after["target_tree_sha256"],
        "source_file_count": before["source_file_count"],
        "target_file_count": after["target_file_count"],
        "promotion_tx": str(tx),
        "backup_root": str(backup) if target_existed else None,
        "quiescence": quiescence,
        "runtime": runtime,
        "consequence_readback": {"tree_current": after["current"], "health_ok": True},
    }
    _atomic_json(tx / "receipt.json", receipt)
    return receipt


def register_daemon_runtime_tools(register_tool: Callable[..., Any], *, error_cls: type[Exception]) -> None:
    @register_tool(
        "control.daemon.runtime.status",
        "Compare the live Daemon(MVF) source tree with the installed Recovery daemon runtime using deterministic tree digests.",
        "low",
        category="control",
        mutating=False,
        side_effect_class="read",
        effect_traits=["source_currentness_check", "recovery_runtime_currentness", "does_not_grant_mutation_authority"],
        input_schema={"type":"object","properties":{"project_id":{"type":"string","minLength":1}},"required":["project_id"],"additionalProperties":False},
    )
    def tool_daemon_runtime_status(payload):
        try:
            return runtime_status(str(payload["project_id"]))
        except Exception as exc:
            raise error_cls("DAEMON_RUNTIME_STATUS_FAILED", f"{type(exc).__name__}: {exc}", 400) from exc

    @register_tool(
        "control.daemon.runtime.promote",
        "Transactionally promote the current live Daemon(MVF) source into the Recovery daemon runtime, with exact digest fencing, Daemon-only quiescence, rollback, restart, health validation, and supervision restoration.",
        "high",
        category="control",
        approval_required=True,
        mutating=True,
        side_effect_class="mutation",
        effect_traits=["durable_mutation", "hash_currentness_guarded", "quiesces_daemon_only", "rollback_capable", "restores_supervision", "exact_consequence_readback"],
        input_schema={"type":"object","properties":{"project_id":{"type":"string","minLength":1},"expected_source_tree_sha256":{"type":"string","minLength":64,"maxLength":64}},"required":["project_id","expected_source_tree_sha256"],"additionalProperties":False},
    )
    def tool_daemon_runtime_promote(payload):
        try:
            return promote_runtime(str(payload["project_id"]), str(payload["expected_source_tree_sha256"]))
        except Exception as exc:
            raise error_cls("DAEMON_RUNTIME_PROMOTION_FAILED", f"{type(exc).__name__}: {exc}", 500) from exc
