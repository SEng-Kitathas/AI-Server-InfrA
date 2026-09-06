"""Stateful replay and idempotency gate."""

from __future__ import annotations

import time
from pathlib import Path

from receiver_resilience_common import (
    TRACE_PROJECT_ID,
    JsonRecord,
    ProbeCase,
    authorized_headers,
    create_client,
    prepare_trace_project,
    report_payload,
    run_probe,
    write_report,
)

REPORT_PATH = (
    Path(__file__).resolve().parents[2] / "reports" / "RECEIVER_STATEFUL_REPLAY_GATE_REPORT.json"
)


def _submit_payload(run_id: str) -> JsonRecord:
    return {
        "project_id": TRACE_PROJECT_ID,
        "command": ["python"],
        "args": ["-c", "import sys; sys.stdout.write('stateful')"],
        "timeout_seconds": 10,
        "stdout_max_bytes": 10000,
        "idempotency_key": f"stateful-{run_id}",
    }


def _commit_payload(run_id: str) -> JsonRecord:
    return {
        "project_id": TRACE_PROJECT_ID,
        "artifact_class": "notes.maintenance",
        "logical_name": f"stateful_{run_id}.txt",
        "operation": "create",
        "content": "stateful",
        "session_id": "stateful",
        "commit_id": f"stateful-{run_id}",
        "idempotency_key": f"commit-{run_id}",
    }


def _execution_cases(run_id: str) -> list[ProbeCase]:
    payload = _submit_payload(run_id)
    return [
        ProbeCase(
            "execution submit first",
            "/project/execution/submit",
            "POST",
            (200,),
            "idempotency",
            payload,
            require_ok=True,
        ),
        ProbeCase(
            "execution submit replay",
            "/project/execution/submit",
            "POST",
            (200, 409),
            "idempotency",
            payload,
        ),
    ]


def _commit_cases(run_id: str) -> list[ProbeCase]:
    payload = _commit_payload(run_id)
    return [
        ProbeCase(
            "commit first", "/commit", "POST", (200,), "idempotency", payload, require_ok=True
        ),
        ProbeCase("commit replay", "/commit", "POST", (200, 409), "idempotency", payload),
    ]


def _journal_cases() -> list[ProbeCase]:
    return [
        ProbeCase(
            "journal append",
            "/project/journal/append",
            "POST",
            (200,),
            "replay",
            {
                "project_id": TRACE_PROJECT_ID,
                "entry_type": "stateful",
                "title": "Stateful",
                "content": "entry",
                "tags": ["stateful"],
            },
            require_ok=True,
        ),
        ProbeCase(
            "journal read",
            "/project/journal/read",
            "POST",
            (200,),
            "replay",
            {"project_id": TRACE_PROJECT_ID, "limit": 5},
            require_ok=True,
        ),
    ]


def _cases(run_id: str) -> list[ProbeCase]:
    return [*_execution_cases(run_id), *_commit_cases(run_id), *_journal_cases()]


def main() -> None:
    prepare_trace_project()
    client = create_client()
    results = [run_probe(client, case) for case in _cases(str(time.time_ns()))]
    payload = report_payload(
        "receiver_stateful_replay", "PROBE_DERIVE_VERIFY_EMBODY_RECURSE", results
    )
    write_report(REPORT_PATH, payload)


if __name__ == "__main__":
    main()
