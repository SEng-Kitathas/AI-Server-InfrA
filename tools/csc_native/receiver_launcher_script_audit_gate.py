"""Audit PCMMAD receiver launcher/restart scripts for naïve shell/process footguns."""

from __future__ import annotations

import hashlib
import re
import shutil
import sys
from pathlib import Path
from subprocess import DEVNULL, run as run_process
from typing import TypedDict

from strict_json_boundary import render_json_boundary, write_json_boundary

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RECEIVER_ROOT = PROJECT_ROOT
REPORT_PATH = PROJECT_ROOT / "reports" / "RECEIVER_LAUNCHER_SCRIPT_AUDIT_REPORT.json"
LEGACY_KEY_SHA256 = "24eaa1cb89824db224bd66167c9450b918162f6fec39c087413a215ccf782169"
LONG_TOKEN = re.compile(r"[A-Za-z0-9_\-]{32,}")


class Finding(TypedDict):
    severity: str
    file: str
    line: int
    rule: str
    message: str
    text: str


class FindingSpec(TypedDict):
    severity: str
    rule: str
    message: str


SCRIPT_PATHS = (
    RECEIVER_ROOT / "PCMMAD.ps1",
    RECEIVER_ROOT / "SETUP_PCMMAD_RUNTIME.ps1",
    RECEIVER_ROOT / "RESTART_RECEIVER_AND_NGROK.ps1",
    RECEIVER_ROOT / "RESTART_RECEIVER_AND_NGROK.cmd",
    RECEIVER_ROOT / "RESTART_RECEIVER_ONLY.cmd",
    RECEIVER_ROOT / "START_RECEIVER.cmd",
    RECEIVER_ROOT / "START_RECEIVER_AND_NGROK.cmd",
    RECEIVER_ROOT / "START_BROWSER_BRIDGE.cmd",
    RECEIVER_ROOT / "STOP_BROWSER_BRIDGE.cmd",
)


def _finding(path: Path, line: int, spec: FindingSpec, text: str) -> Finding:
    return Finding(
        severity=spec["severity"],
        file=str(path),
        line=line,
        rule=spec["rule"],
        message=spec["message"],
        text=text,
    )


def _contains_legacy_key(line: str) -> bool:
    for token in LONG_TOKEN.findall(line):
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        if digest == LEGACY_KEY_SHA256:
            return True
    return False


def _credential_findings(path: Path, line_number: int, line: str) -> list[Finding]:
    if not _contains_legacy_key(line):
        return []
    return [
        _finding(
            path,
            line_number,
            FindingSpec(
                severity="HIGH",
                rule="no_hardcoded_api_key",
                message="Launcher contains the retired local API key literal.",
            ),
            line.strip(),
        )
    ]


def _runtime_findings(path: Path, line_number: int, line: str, whole_text: str) -> list[Finding]:
    lowered = line.strip().lower()
    bare_python = bool(re.match(r"(?:call\s+)?python(?:\.exe)?\s+", lowered))
    if not bare_python:
        return []
    return [
        _finding(
            path,
            line_number,
            FindingSpec(
                severity="HIGH",
                rule="explicit_virtualenv_interpreter",
                message="Runtime services must use the canonical .venv interpreter, not PATH Python.",
            ),
            line.strip(),
        )
    ]


def _ngrok_findings(path: Path, line_number: int, line: str) -> list[Finding]:
    lowered = line.lower()
    separate_window = "start-process" in lowered or "start " in lowered
    if (
        "ngrok http" not in lowered
        or separate_window
        or path.suffix.lower() not in {".bat", ".cmd"}
    ):
        return []
    return [
        _finding(
            path,
            line_number,
            FindingSpec(
                severity="MEDIUM",
                rule="ngrok_separate_window",
                message="Ngrok should start in a separate terminal/process surface.",
            ),
            line.strip(),
        )
    ]


def _shell_passthrough_findings(path: Path, line_number: int, line: str) -> list[Finding]:
    if not re.search(r"shell\s*=\s*true", line, flags=re.IGNORECASE):
        return []
    return [
        _finding(
            path,
            line_number,
            FindingSpec(
                severity="HIGH",
                rule="no_shell_passthrough",
                message="Launcher audit forbids shell passthrough execution flags.",
            ),
            line.strip(),
        )
    ]


def _command_line_secret_findings(path: Path, line_number: int, line: str) -> list[Finding]:
    lowered = line.lower()
    risky = "githome_api_key=$" in lowered or "githome_api_key=%" in lowered
    if not risky:
        return []
    spec = FindingSpec(
        severity="HIGH",
        rule="no_secret_in_child_command_line",
        message="Start scripts must import local env, not embed key values in child commands.",
    )
    return [_finding(path, line_number, spec, line.strip())]


def _kill_boundary_findings(path: Path, line_number: int, line: str) -> list[Finding]:
    lowered = line.lower()
    bounded = "ngrok" in lowered or "pid" in lowered or "processid" in lowered
    if "stop-process" not in lowered or "-force" not in lowered or bounded:
        return []
    return [
        _finding(
            path,
            line_number,
            FindingSpec(
                severity="MEDIUM",
                rule="bounded_process_kill",
                message="Forceful process stops must be bounded to discovered process identifiers.",
            ),
            line.strip(),
        )
    ]


def _line_findings(path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        findings.extend(_credential_findings(path, line_number, line))
        findings.extend(_runtime_findings(path, line_number, line, text))
        findings.extend(_ngrok_findings(path, line_number, line))
        findings.extend(_shell_passthrough_findings(path, line_number, line))
        findings.extend(_command_line_secret_findings(path, line_number, line))
        findings.extend(_kill_boundary_findings(path, line_number, line))
    return findings


def _parse_powershell(path: Path) -> list[Finding]:
    if not path.exists() or path.suffix.lower() != ".ps1":
        return []
    executable = shutil.which("powershell") or shutil.which("pwsh")
    if executable is None:
        return []
    escaped = str(path).replace("'", "''")
    command = (
        "try { $null = [scriptblock]::Create((Get-Content -Raw '"
        + escaped
        + "')); exit 0 } catch { Write-Host $_.Exception.Message; exit 1 }"
    )
    proc = run_process(
        [executable, "-NoProfile", "-Command", command],
        cwd=RECEIVER_ROOT,
        stdout=DEVNULL,
        stderr=DEVNULL,
        text=True,
        timeout=60,
    )
    if proc.returncode == 0:
        return []
    return [
        _finding(
            path,
            1,
            FindingSpec(
                severity="HIGH",
                rule="powershell_parse",
                message="PowerShell script failed parser check.",
            ),
            "parser returned non-zero status",
        )
    ]


def _missing_script_findings(path: Path) -> list[Finding]:
    if path.exists():
        return []
    spec = FindingSpec(
        severity="HIGH", rule="script_missing", message="Required launcher script is missing."
    )
    return [_finding(path, 0, spec, "")]


def _start_delegation_findings(path: Path, text: str) -> list[Finding]:
    start_script = path.name in {"START_RECEIVER_AND_NGROK.cmd", "START_RECEIVER.cmd", "RESTART_RECEIVER_ONLY.cmd", "RESTART_RECEIVER_AND_NGROK.cmd"}
    if not start_script or "RESTART_RECEIVER_AND_NGROK.ps1" in text:
        return []
    spec = FindingSpec(
        severity="HIGH",
        rule="start_delegates_to_safe_restart",
        message="Start launcher must delegate to the duplicate-safe restart script.",
    )
    return [_finding(path, 1, spec, text[:200])]


def _script_findings(path: Path) -> list[Finding]:
    missing = _missing_script_findings(path)
    if missing:
        return missing
    text = path.read_text(encoding="utf-8", errors="replace")
    findings = _line_findings(path, text)
    findings.extend(_parse_powershell(path))
    findings.extend(_start_delegation_findings(path, text))
    return findings


def _severity_counts(findings: list[Finding]) -> dict[str, int]:
    return {
        level: sum(1 for item in findings if item["severity"] == level)
        for level in sorted({item["severity"] for item in findings})
    }


def main() -> None:
    findings: list[Finding] = []
    for path in SCRIPT_PATHS:
        findings.extend(_script_findings(path))
    payload = {
        "clean": not findings,
        "finding_count": len(findings),
        "severity_counts": _severity_counts(findings),
        "scripts": [str(path) for path in SCRIPT_PATHS],
        "findings": findings,
    }
    write_json_boundary(REPORT_PATH, payload)
    sys.stdout.write(
        render_json_boundary(
            {"report": str(REPORT_PATH), "clean": payload["clean"], "finding_count": len(findings)}
        )
        + "\n"
    )
    if findings:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
