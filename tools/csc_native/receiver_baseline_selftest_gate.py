"""Receiver baseline self-test gate for compile, hardening tests, and import probes."""

from __future__ import annotations
from typing import Any

import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Mapping

from strict_json_boundary import write_json_boundary


@dataclass(frozen=True)
class SelftestConfig:
    project_root: Path
    baseline_root: Path
    report_path: Path


IMPORT_PROBE_SCRIPT = """import json
import sys
from pathlib import Path

project_root = Path(sys.argv[1])
baseline_root = project_root / 'baseline'
package_root = baseline_root / 'pcmmad_receiver'
sys.path.insert(0, str(baseline_root))
sys.path.insert(0, str(package_root))

from pcmmad_receiver.app_factory import create_app
from pcmmad_receiver.lab_tools import list_tools, tool_lab_health
from pcmmad_receiver.server_hardening import (
    command_preflight,
    run_subprocess_envelope,
    safe_json_dumps,
)

app = create_app()
tools = list_tools()
health = tool_lab_health()
preflight = command_preflight(project_root, [sys.executable, '--version'], '.')
envelope = run_subprocess_envelope(
    [sys.executable, '-c', 'print("selftest")'],
    cwd=project_root,
    timeout_seconds=10,
    stdout_max_bytes=200,
    stderr_max_bytes=200,
)
encoded = safe_json_dumps({'path': package_root, 'tool_count': len(tools)})
result = {
    'ok': bool(health.get('ok')) and bool(preflight.get('ok')) and bool(envelope.get('ok')),
    'route_count': len(list(app.url_map.iter_rules())),
    'tool_count': len(tools),
    'health_ok': bool(health.get('ok')),
    'preflight_ok': bool(preflight.get('ok')),
    'envelope_ok': bool(envelope.get('ok')),
    'envelope': envelope,
    'encoded_has_path': 'pcmmad_receiver' in encoded,
}
sys.stdout.write(json.dumps(result, indent=2) + "\\n")
"""


def _run_command(name: str, command: list[str], cwd: Path) -> Mapping[str, Any]:
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    return {
        "name": name,
        "command": command,
        "return_code": completed.returncode,
        "ok": completed.returncode == 0,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }


def _run_import_probe(config: SelftestConfig) -> Mapping[str, Any]:
    completed = subprocess.run(
        [sys.executable, "-c", IMPORT_PROBE_SCRIPT, str(config.project_root)],
        cwd=str(config.project_root),
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    try:
        result: Mapping[str, Any] = json.loads(completed.stdout)
    except json.JSONDecodeError:
        result = {
            "ok": False,
            "error": "non-json import probe output",
            "stdout_tail": completed.stdout[-4000:],
        }
    result["return_code"] = completed.returncode
    result["stderr_tail"] = completed.stderr[-4000:]
    result["ok"] = bool(result.get("ok")) and completed.returncode == 0
    return result


def run_gate(config: SelftestConfig) -> Mapping[str, Any]:
    compile_result = _run_command(
        "baseline_compileall",
        [sys.executable, "-m", "compileall", str(config.baseline_root / "pcmmad_receiver")],
        config.project_root,
    )
    hardening_tests = _run_command(
        "server_hardening_tests",
        [sys.executable, "-m", "unittest", "tests.test_server_hardening"],
        config.project_root,
    )
    import_probe = _run_import_probe(config)
    clean = (
        bool(compile_result["ok"]) and bool(hardening_tests["ok"]) and bool(import_probe.get("ok"))
    )
    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "clean": clean,
        "baseline_root": str(config.baseline_root),
        "compile_result": compile_result,
        "hardening_tests": hardening_tests,
        "import_probe": import_probe,
    }
    write_json_boundary(config.report_path, report)
    return report


def main() -> None:
    project_root = Path.cwd()
    report = run_gate(
        SelftestConfig(
            project_root=project_root,
            baseline_root=project_root / "baseline",
            report_path=project_root / "reports" / "RECEIVER_BASELINE_SELFTEST_GATE_REPORT.json",
        )
    )
    sys.stdout.write(json.dumps(report, indent=2) + "\n")
    raise SystemExit(0 if report["clean"] else 1)


if __name__ == "__main__":
    main()
