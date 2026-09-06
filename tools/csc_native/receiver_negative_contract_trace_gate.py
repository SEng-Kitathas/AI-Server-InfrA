"""Negative-path contract gate for receiver routes."""

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
    Path(__file__).resolve().parents[2]
    / "reports"
    / "RECEIVER_NEGATIVE_CONTRACT_TRACE_GATE_REPORT.json"
)

BAD_PROJECT_ID = "route_trace_missing_project"


NEGATIVE_CASES: tuple[ProbeCase, ...] = (
    ProbeCase("missing auth health", "/health", "GET", (401, 403), "auth", headers={}),
    ProbeCase(
        "bad auth health",
        "/health",
        "GET",
        (401, 403),
        "auth",
        headers={"X-GitHome-Key": "bad"},
    ),
    ProbeCase(
        "missing body init",
        "/project/init",
        "POST",
        (400,),
        "malformed",
        payload=None,
        require_json=False,
    ),
    ProbeCase(
        "wrong project id type",
        "/project/info",
        "POST",
        (400,),
        "type",
        payload={"project_id": 3},
    ),
    ProbeCase(
        "unknown project info",
        "/project/info",
        "POST",
        (200,),
        "not_found",
        payload={"project_id": BAD_PROJECT_ID},
        require_ok=True,
    ),
    ProbeCase(
        "read missing path",
        "/project/files/read",
        "POST",
        (404,),
        "not_found",
        payload={"project_id": TRACE_PROJECT_ID, "path": "missing.txt"},
    ),
    ProbeCase(
        "read traversal",
        "/project/files/read",
        "POST",
        (400, 403, 404),
        "security",
        payload={"project_id": TRACE_PROJECT_ID, "path": "../outside.txt"},
    ),
    ProbeCase(
        "empty content write is explicit",
        "/project/files/write",
        "POST",
        (200,),
        "boundary",
        payload={"project_id": TRACE_PROJECT_ID, "path": "reports/x.txt"},
        require_ok=True,
    ),
    ProbeCase(
        "search missing query",
        "/project/files/search",
        "POST",
        (400,),
        "malformed",
        payload={"project_id": TRACE_PROJECT_ID, "path": "reports"},
    ),
    ProbeCase(
        "run missing command",
        "/run",
        "POST",
        (400,),
        "malformed",
        payload={"project_id": TRACE_PROJECT_ID},
    ),
    ProbeCase(
        "run python missing code",
        "/run/python",
        "POST",
        (400,),
        "malformed",
        payload={"project_id": TRACE_PROJECT_ID},
    ),
    ProbeCase(
        "execution submit missing command",
        "/project/execution/submit",
        "POST",
        (400,),
        "malformed",
        payload={"project_id": TRACE_PROJECT_ID},
    ),
    ProbeCase("zip missing path", "/zip/read", "POST", (400, 404), "malformed", payload={}),
    ProbeCase(
        "archive inspect missing",
        "/project/archives/inspect",
        "POST",
        (404,),
        "not_found",
        payload={"project_id": TRACE_PROJECT_ID, "path": "missing.zip"},
    ),
    ProbeCase(
        "lab missing tool",
        "/lab/dispatch",
        "POST",
        (400,),
        "malformed",
        payload={"payload": {}},
    ),
    ProbeCase(
        "lab unknown tool",
        "/lab/dispatch",
        "POST",
        (400, 404),
        "not_found",
        payload={"tool_name": "missing.tool", "payload": {}},
    ),
    ProbeCase(
        "research empty hunt",
        "/research/hunt",
        "POST",
        (400,),
        "malformed",
        payload={"topic": ""},
    ),
)


def _cases() -> list[ProbeCase]:
    return list(NEGATIVE_CASES)


def main() -> None:
    prepare_trace_project()
    client = create_client()
    results = [run_probe(client, case) for case in _cases()]
    payload = report_payload(
        "receiver_negative_contract_trace", "PROBE_DERIVE_VERIFY_EMBODY_RECURSE", results
    )
    write_report(REPORT_PATH, payload)


if __name__ == "__main__":
    main()
