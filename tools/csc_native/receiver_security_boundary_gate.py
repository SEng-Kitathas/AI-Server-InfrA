"""Security boundary probes for receiver routes."""

from __future__ import annotations

from pathlib import Path

from receiver_resilience_common import (
    TRACE_PROJECT_ID,
    ProbeCase,
    create_client,
    prepare_trace_project,
    report_payload,
    run_probe,
    write_report,
)

REPORT_PATH = (
    Path(__file__).resolve().parents[2] / "reports" / "RECEIVER_SECURITY_BOUNDARY_GATE_REPORT.json"
)


SECURITY_CASES: tuple[ProbeCase, ...] = (
    ProbeCase(
        "absolute path read",
        "/project/files/read",
        "POST",
        (400, 403),
        "path_boundary",
        {
            "project_id": TRACE_PROJECT_ID,
            "path": str(Path.home() / "definitely_outside_project_boundary.txt"),
        },
    ),
    ProbeCase(
        "dotdot write",
        "/project/files/write",
        "POST",
        (400, 403),
        "path_boundary",
        {"project_id": TRACE_PROJECT_ID, "path": "../escape.txt", "content": "bad"},
    ),
    ProbeCase(
        "archive slip extract contained",
        "/project/archives/extract",
        "POST",
        (200,),
        "archive_boundary",
        {
            "project_id": TRACE_PROJECT_ID,
            "path": "data/route_trace_workspace/slip.zip",
            "destination_path": "data/route_trace_workspace/extracted",
            "overwrite": True,
        },
    ),
    ProbeCase(
        "shell metachar run arg",
        "/run",
        "POST",
        (200,),
        "command_boundary",
        {
            "project_id": TRACE_PROJECT_ID,
            "command": ["python"],
            "args": ["-c", "import sys; sys.stdout.write('safe')"],
            "timeout_seconds": 10,
            "stdout_max_bytes": 10000,
        },
        require_ok=True,
    ),
    ProbeCase(
        "oversize small stdout cap",
        "/run/python",
        "POST",
        (200,),
        "resource_boundary",
        {
            "project_id": TRACE_PROJECT_ID,
            "code": "import sys; sys.stdout.write('x'*1000)",
            "stdout_max_bytes": 10,
            "timeout_seconds": 10,
        },
        require_ok=True,
    ),
    ProbeCase(
        "invalid zip bytes",
        "/zip/read",
        "POST",
        (400, 404),
        "archive_boundary",
        {"zip_path": str((Path(__file__).resolve().parents[2] / "reports" / "missing.zip"))},
    ),
)


def _cases() -> list[ProbeCase]:
    return list(SECURITY_CASES)


def main() -> None:
    prepare_trace_project()
    client = create_client()
    results = [run_probe(client, case) for case in _cases()]
    payload = report_payload(
        "receiver_security_boundary", "PROBE_DERIVE_VERIFY_EMBODY_RECURSE", results
    )
    write_report(REPORT_PATH, payload)


if __name__ == "__main__":
    main()
