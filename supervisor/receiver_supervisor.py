#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def probe(url: str, timeout: float) -> tuple[bool, str | None]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= int(response.status) < 300, None
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def trigger_task(task_name: str) -> tuple[bool, str]:
    proc = subprocess.run(["schtasks", "/Run", "/TN", task_name], text=True, capture_output=True, timeout=15)
    detail = (proc.stdout + "\n" + proc.stderr).strip()[-2000:]
    return proc.returncode == 0, detail


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


def supervise_once(*, health_url: str, task_name: str, receipt_path: Path, timeout: float = 3.0, recovery_seconds: float = 20.0, poll_seconds: float = 1.0, trigger=trigger_task, health_probe=probe) -> dict:
    checked_at = utc_now()
    healthy, error = health_probe(health_url, timeout)
    receipt = {"schema":"pcmmad.receiver-supervisor.v1","checked_at":checked_at,"health_url":health_url,"task_name":task_name,"healthy_before":healthy,"probe_error_before":error,"action":"NONE","triggered":False,"healthy_after":healthy,"probe_error_after":error}
    if healthy:
        write_atomic(receipt_path, receipt)
        return receipt
    ok, detail = trigger(task_name)
    receipt["action"] = "TRIGGER_CANONICAL_RECEIVER_TASK"
    receipt["triggered"] = ok
    receipt["trigger_detail"] = detail
    deadline = time.monotonic() + recovery_seconds
    final_error = error
    while time.monotonic() < deadline:
        healthy, final_error = health_probe(health_url, timeout)
        if healthy:
            break
        time.sleep(poll_seconds)
    receipt["healthy_after"] = healthy
    receipt["probe_error_after"] = final_error
    receipt["completed_at"] = utc_now()
    write_atomic(receipt_path, receipt)
    return receipt


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--health-url", default="http://127.0.0.1:5090/api/health")
    parser.add_argument("--task-name", default="PCMMAD_V30_Receiver")
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--recovery-seconds", type=float, default=20.0)
    args=parser.parse_args()
    receipt=supervise_once(health_url=args.health_url,task_name=args.task_name,receipt_path=Path(args.receipt),recovery_seconds=args.recovery_seconds)
    print(json.dumps(receipt,sort_keys=True))
    return 0 if receipt.get("healthy_after") else 2

if __name__ == "__main__":
    raise SystemExit(main())
