"""Browser bridge resilience gate."""

from __future__ import annotations

from pathlib import Path

from receiver_resilience_common import (
    ProbeCase,
    ProbeResult,
    create_client,
    prepare_trace_project,
    report_payload,
    run_probe,
    start_dummy_bridge,
    write_report,
)

REPORT_PATH = (
    Path(__file__).resolve().parents[2]
    / "reports"
    / "RECEIVER_BROWSER_BRIDGE_RESILIENCE_GATE_REPORT.json"
)


def _run_with_bridge(mode: str) -> list[ProbeResult]:
    server = start_dummy_bridge(mode)
    try:
        client = create_client()
        cases = [
            ProbeCase(
                f"browser health {mode}",
                "/lab/dispatch",
                "POST",
                (200, 503),
                "browser_bridge",
                {"tool_name": "browser.health", "payload": {"timeout_seconds": 2}},
            ),
            ProbeCase(
                f"browser screenshot {mode}",
                "/lab/dispatch",
                "POST",
                (200, 404, 503),
                "browser_bridge",
                {
                    "tool_name": "browser.screenshot",
                    "payload": {"session_id": "resilience-session", "timeout_seconds": 2},
                },
            ),
        ]
        return [run_probe(client, case) for case in cases]
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()


def main() -> None:
    prepare_trace_project()
    results = []
    results.extend(_run_with_bridge("success"))
    results.extend(_run_with_bridge("error"))
    results.extend(_run_with_bridge("malformed"))
    payload = report_payload(
        "receiver_browser_bridge_resilience", "PROBE_DERIVE_VERIFY_EMBODY_RECURSE", results
    )
    write_report(REPORT_PATH, payload)


if __name__ == "__main__":
    main()
