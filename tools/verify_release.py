"""Aggregate the PCMMAD V29 release contract from executable anchors and gate reports."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from release_manifest import verify_manifest

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "V29_RELEASE_VERIFICATION.json"
CSC_OUTPUT = ROOT / "data" / "csc_v29"
SOURCE_AUDIT = ROOT / "reports" / "source_review" / "V29_SOURCE_CORPUS_INVENTORY.json"
SCHEMA = ROOT / "baseline" / "pcmmad_receiver" / "pcmmad_lab_action_schema_v10_3_pcmmad_native_protocol_compact_30_router.json"

GATE_REPORTS = (
    "RECEIVER_BASELINE_SELFTEST_GATE_REPORT.json",
    "RECEIVER_SCHEMA_AUTHORITY_GATE_REPORT.json",
    "SEMANTIC_FOOTGUN_DATAFLOW_GATE_REPORT.json",
    "RECEIVER_FULL_ROUTE_TRACE_GATE_REPORT.json",
    "RECEIVER_NEGATIVE_CONTRACT_TRACE_GATE_REPORT.json",
    "RECEIVER_STATEFUL_REPLAY_GATE_REPORT.json",
    "RECEIVER_SECURITY_BOUNDARY_GATE_REPORT.json",
    "RECEIVER_BROWSER_BRIDGE_RESILIENCE_GATE_REPORT.json",
    "RECEIVER_PACKAGE_INTEGRITY_GATE_REPORT.json",
    "RECEIVER_LIVE_PARITY_GATE_REPORT.json",
    "RECEIVER_CONCURRENCY_TRACE_GATE_REPORT.json",
    "RECEIVER_LAUNCHER_SCRIPT_AUDIT_REPORT.json",
    "PCMMAD_RUNTIME_SURFACE_CONTRACT.json",
)


def _isolated_env() -> dict[str, str]:
    env = os.environ.copy()
    root = Path(tempfile.mkdtemp(prefix="pcmmad_release_verify_"))
    env.setdefault("PCMMAD_ROOT", str(root / "root"))
    env.setdefault("PCMMAD_PROJECTS_ROOT", str(root / "root" / "projects"))
    env.setdefault("PCMMAD_SYSTEM_ROOT", str(root / "root" / "system"))
    env.setdefault("PCMMAD_SANDBOX_ROOT", str(root / "root" / "sandbox"))
    env.setdefault("PCMMAD_TEMP_ROOT", str(root / "temp"))
    env.setdefault("GITHOME_API_KEY", "release-verification-key")
    return env


def run(name: str, command: list[str], timeout: int = 300) -> dict[str, object]:
    print(f"[verify] {name}", flush=True)
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as stdout, tempfile.TemporaryFile(
        mode="w+t", encoding="utf-8"
    ) as stderr:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=_isolated_env(),
            stdout=stdout,
            stderr=stderr,
            text=True,
            timeout=timeout,
            check=False,
        )
        stdout.seek(0)
        stderr.seek(0)
        stdout_text = stdout.read()
        stderr_text = stderr.read()
    return {
        "name": name,
        "command": command,
        "return_code": completed.returncode,
        "clean": completed.returncode == 0,
        "stdout_tail": stdout_text[-4000:],
        "stderr_tail": stderr_text[-4000:],
    }


def manifest_contract() -> dict[str, object]:
    clean, failures = verify_manifest(ROOT)
    return {
        "clean": clean,
        "path": "PACKAGE_MANIFEST_V29.json",
        "failures": failures,
    }


def schema_contract() -> dict[str, object]:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    operation_ids = [
        operation["operationId"]
        for item in schema["paths"].values()
        for operation in item.values()
        if isinstance(operation, dict) and "operationId" in operation
    ]
    return {
        "clean": len(operation_ids) == 30 and len(set(operation_ids)) == 30,
        "path": str(SCHEMA.relative_to(ROOT)),
        "operation_count": len(operation_ids),
        "unique_operation_count": len(set(operation_ids)),
    }


def source_contract() -> dict[str, object]:
    if not SOURCE_AUDIT.exists():
        return {"clean": False, "error": "source corpus inventory missing"}
    payload = json.loads(SOURCE_AUDIT.read_text(encoding="utf-8"))
    return {
        "clean": payload.get("project") == "PCMMAD Receiver"
        and bool(payload.get("forge_document_review"))
        and bool(payload.get("csc_main_alternate_comparison")),
        "path": str(SOURCE_AUDIT.relative_to(ROOT)),
        "forge_documents_reviewed": len(payload.get("forge_document_review", [])),
        "gain_decisions": len(payload.get("gain_decisions", [])),
    }


def gate_report_contract() -> dict[str, object]:
    entries: list[dict[str, object]] = []
    for name in GATE_REPORTS:
        path = ROOT / "reports" / name
        if not path.exists():
            entries.append({"path": name, "clean": False, "error": "missing"})
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            entries.append({"path": name, "clean": payload.get("clean") is True})
        except json.JSONDecodeError as exc:
            entries.append({"path": name, "clean": False, "error": str(exc)})
    return {"clean": all(bool(item["clean"]) for item in entries), "reports": entries}


def csc_contract() -> dict[str, object]:
    event_path = CSC_OUTPUT / "CSC_EVENT_REPORT.json"
    if not event_path.exists():
        return {"clean": False, "error": "CSC event report missing"}
    event = json.loads(event_path.read_text(encoding="utf-8"))
    surfaces = {
        "core_cycle": bool(event.get("core_cycle", {}).get("final_cycle_clean")),
        "sop_availability": bool(event.get("sop_availability", {}).get("clean")),
        "sop_freshness": bool(event.get("sop_freshness", {}).get("clean")),
        "holonic_audit": bool(event.get("holonic_audit", {}).get("clean")),
        "doctrine_coverage": bool(event.get("doctrine_coverage", {}).get("clean")),
    }
    return {"clean": all(surfaces.values()), "surfaces": surfaces}


def main() -> None:
    py = sys.executable
    commands = [
        run("compileall", [py, "-m", "compileall", "-q", "baseline", "tests", "tools", "system"]),
        run("regression_tests", [py, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"]),
        run("runtime_surface_contract", [py, "tools/runtime_surface_contract.py"]),
        run(
            "csc_universal",
            [
                py,
                "tools/csc_native/csc_universal_runner.py",
                "--target-project-root",
                str(ROOT),
                "--output-root",
                str(CSC_OUTPUT),
                "--docs-root",
                str(ROOT / "docs" / "csc_sop"),
                "--max-cycles",
                "1",
            ],
            timeout=600,
        ),
    ]
    manifest = manifest_contract()
    schema = schema_contract()
    source = source_contract()
    gate_reports = gate_report_contract()
    csc = csc_contract()
    clean = (
        all(bool(result["clean"]) for result in commands)
        and bool(manifest["clean"])
        and bool(schema["clean"])
        and bool(source["clean"])
        and bool(gate_reports["clean"])
        and bool(csc["clean"])
    )
    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "release": "PCMMAD Receiver V29 Native Protocol Release Candidate",
        "clean": clean,
        "commands": commands,
        "manifest_contract": manifest,
        "source_contract": source,
        "gate_report_contract": gate_reports,
        "schema_contract": schema,
        "csc_contract": csc,
        "host_bound_deferred": [
            "Windows PowerShell parser/runtime execution",
            "live ngrok tunnel and Custom GPT callback",
            "live D:/E: mount parity against surviving user data",
        ],
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(REPORT), "clean": clean}, indent=2))
    raise SystemExit(0 if clean else 1)


if __name__ == "__main__":
    main()
