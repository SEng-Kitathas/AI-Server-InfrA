"""Concurrency trace gate for receiver route families."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from receiver_resilience_common import (
    TRACE_PROJECT_ID,
    ProbeCase,
    create_client,
    prepare_trace_project,
    report_payload,
    run_probe,
    shutdown_test_runtime,
    write_report,
)

REPORT_PATH = (
    Path(__file__).resolve().parents[2] / "reports" / "RECEIVER_CONCURRENCY_TRACE_GATE_REPORT.json"
)


def _case(index: int) -> ProbeCase:
    return ProbeCase(
        f"concurrent write {index}",
        "/project/files/write",
        "POST",
        (200,),
        "concurrency",
        {
            "project_id": TRACE_PROJECT_ID,
            "path": f"reports/concurrent_{index}.txt",
            "content": f"concurrent {index}\n",
        },
        require_ok=True,
    )


def main() -> None:
    try:
        prepare_trace_project()
        client = create_client()
        cases = [_case(index) for index in range(12)]
        results = []
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(run_probe, client, case) for case in cases]
            for future in as_completed(futures):
                results.append(future.result())
        payload = report_payload(
            "receiver_concurrency_trace", "PROBE_DERIVE_VERIFY_EMBODY_RECURSE", results
        )
        write_report(REPORT_PATH, payload)
    finally:
        shutdown_test_runtime()


if __name__ == "__main__":
    main()
