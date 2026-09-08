"""Agent-safe adapter for the canonical PCMMAD restart controller.

This module does not implement restart semantics. It only schedules the single
canonical PowerShell convergence controller after returning an acknowledgement.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Callable

INSTALL_ROOT = Path(__file__).resolve().parents[2]
RESTART_SCRIPT = INSTALL_ROOT / "RESTART_RECEIVER_AND_NGROK.ps1"
RECEIPT_ROOT = Path(tempfile.gettempdir()) / "pcmmad_restart_receipts"


def _powershell() -> str:
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    candidate = Path(system_root) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    return str(candidate if candidate.exists() else Path("powershell.exe"))


def _receipt_path(request_id: str) -> Path:
    RECEIPT_ROOT.mkdir(parents=True, exist_ok=True)
    return RECEIPT_ROOT / f"inline_{request_id}.json"


def schedule_restart(delay_seconds: int = 2) -> dict[str, Any]:
    if not RESTART_SCRIPT.is_file():
        raise FileNotFoundError(f"restart controller missing: {RESTART_SCRIPT}")
    request_id = uuid.uuid4().hex
    receipt = _receipt_path(request_id)
    args = [
        _powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(RESTART_SCRIPT), "-Action", "Restart",
        "-PreDelaySeconds", str(max(1, min(int(delay_seconds), 30))),
        "-DelaySeconds", "1",
        "-ReceiptPath", str(receipt),
    ]
    creationflags = 0
    if os.name == "nt":
        creationflags = int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)) | int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
    proc = subprocess.Popen(
        args,
        cwd=str(INSTALL_ROOT),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        creationflags=creationflags,
    )
    return {
        "scheduled": True,
        "request_id": request_id,
        "controller_pid": int(proc.pid),
        "receipt_path": str(receipt),
        "controller": str(RESTART_SCRIPT),
        "semantic_note": "scheduled != permitted-by-intensity-guard != stopped != started != healthy; read restart receipt after reconnect",
    }


def latest_receipt() -> dict[str, Any]:
    RECEIPT_ROOT.mkdir(parents=True, exist_ok=True)
    files = sorted(RECEIPT_ROOT.glob("*.json"), key=lambda p: p.stat().st_mtime_ns, reverse=True)
    if not files:
        return {"found": False, "receipt_root": str(RECEIPT_ROOT)}
    path = files[0]
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return {"found": True, "path": str(path), "read_error": f"{type(exc).__name__}: {exc}"}
    return {"found": True, "path": str(path), "receipt": payload}


def register(register_tool: Callable[..., Any]) -> None:
    @register_tool(
        "control.receiver.restart",
        "Schedule one canonical PCMMAD receiver+ngrok convergent restart subject to the canonical restart-intensity guard. The call returns before shutdown; verify the restart receipt after reconnect for ready vs restart_intensity_blocked.",
        "medium",
        category="control",
        tags=["restart", "receiver", "ngrok", "self-restart", "receipt"],
        mutating=True,
    )
    def _restart(_payload: dict[str, Any]) -> dict[str, Any]:
        return schedule_restart(2)

    @register_tool(
        "control.receiver.restart.status",
        "Read the latest canonical PCMMAD restart receipt after reconnect.",
        "low",
        category="control",
        tags=["restart", "receipt", "status"],
        side_effect_class="read",
        effect_traits=["reads_receipt", "reads_service_state"],
    )
    def _status(_payload: dict[str, Any]) -> dict[str, Any]:
        return latest_receipt()
