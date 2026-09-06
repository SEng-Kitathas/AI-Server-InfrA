"""Runs the receiver resilience gate suite."""

from __future__ import annotations

from subprocess import run as run_process
import tempfile
import sys
from pathlib import Path

from typing import TypedDict

from strict_json_boundary import render_json_boundary, write_json_boundary

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = PROJECT_ROOT / "reports" / "RECEIVER_RESILIENCE_GATE_SUITE_REPORT.json"


class GateRunResult(TypedDict):
    gate: str
    returncode: int
    pass_: bool
    stdout_tail: str
    stderr_tail: str


GATES = (
    "receiver_negative_contract_trace_gate.py",
    "receiver_stateful_replay_gate.py",
    "receiver_security_boundary_gate.py",
    "receiver_browser_bridge_resilience_gate.py",
    "receiver_package_integrity_gate.py",
    "receiver_live_parity_gate.py",
    "receiver_concurrency_trace_gate.py",
)


def _run_gate(name: str) -> GateRunResult:
    """Run one gate without PIPE handles that can be inherited by execution descendants."""

    path = Path(__file__).resolve().parent / name
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as stdout, tempfile.TemporaryFile(
        mode="w+t", encoding="utf-8"
    ) as stderr:
        proc = run_process(
            [sys.executable, str(path)],
            cwd=PROJECT_ROOT,
            stdout=stdout,
            stderr=stderr,
            text=True,
            timeout=240,
            check=False,
        )
        stdout.seek(0)
        stderr.seek(0)
        stdout_text = stdout.read()
        stderr_text = stderr.read()
    return {
        "gate": name,
        "returncode": proc.returncode,
        "pass_": proc.returncode == 0,
        "stdout_tail": stdout_text[-4000:],
        "stderr_tail": stderr_text[-4000:],
    }


def main() -> None:
    results = [_run_gate(name) for name in GATES]
    failures = [result for result in results if not result["pass_"]]
    payload = {
        "clean": not failures,
        "gate_count": len(results),
        "failure_count": len(failures),
        "failures": failures,
        "results": results,
    }
    write_json_boundary(REPORT_PATH, payload)
    sys.stdout.write(
        render_json_boundary({"report": str(REPORT_PATH), "clean": payload["clean"]}) + "\n"
    )
    if not payload["clean"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
