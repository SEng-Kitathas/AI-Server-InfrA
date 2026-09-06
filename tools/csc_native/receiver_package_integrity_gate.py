"""Require either a valid local V29 release manifest or a valid final release ZIP."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from receiver_resilience_common import ProbeResult, report_payload, write_report

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = PROJECT_ROOT / "reports" / "RECEIVER_PACKAGE_INTEGRITY_GATE_REPORT.json"
VERIFIER = PROJECT_ROOT / "tools" / "release_manifest.py"


def _probe() -> ProbeResult:
    package_value = os.environ.get("PCMMAD_RELEASE_PACKAGE", "").strip()
    command = [sys.executable, str(VERIFIER)]
    route = str(PROJECT_ROOT / "PACKAGE_MANIFEST_V29.json")
    if package_value:
        command.extend(["--zip", package_value])
        route = package_value
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    try:
        body = json.loads(completed.stdout)
    except json.JSONDecodeError:
        body = {"stdout": completed.stdout[-2000:], "stderr": completed.stderr[-2000:]}
    return ProbeResult(
        name="V29 release integrity",
        category="package",
        route=route,
        method="MANIFEST_OR_ZIP",
        status=200 if completed.returncode == 0 else 500,
        expected_statuses=[200],
        pass_=completed.returncode == 0,
        json_object=True,
        body_sample=body,
    )


def main() -> None:
    result = _probe()
    payload = report_payload(
        "receiver_package_integrity",
        "PROBE_DERIVE_VERIFY_EMBODY_RECURSE",
        [result],
    )
    write_report(REPORT_PATH, payload)


if __name__ == "__main__":
    main()
