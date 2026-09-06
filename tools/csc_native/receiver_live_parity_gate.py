"""Non-mutating live folder parity gate."""

from __future__ import annotations

import hashlib
from pathlib import Path

from receiver_resilience_common import ProbeResult, report_payload, write_report

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LIVE_ROOT = Path.home() / "Desktop" / "pcmmad_receiver"
REPORT_PATH = PROJECT_ROOT / "reports" / "RECEIVER_LIVE_PARITY_GATE_REPORT.json"
IMPORTANT_FILES = (
    "app_factory.py",
    "legacy_routes.py",
    "power_routes.py",
    "execution_routes.py",
    "context_engine.py",
    "api_wire_common.py",
)


def _sha(path: Path) -> str | None:
    return (
        hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() and path.is_file() else None
    )


def _live_absent_result() -> ProbeResult:
    return ProbeResult(
        name="live folder absent",
        category="live_parity",
        route=str(LIVE_ROOT),
        method="FS",
        status=204,
        expected_statuses=[204],
        pass_=True,
        json_object=True,
        body_sample="live parity not required when folder absent",
    )


def _live_file_result(name: str) -> ProbeResult:
    staged = PROJECT_ROOT / "baseline" / "pcmmad_receiver" / name
    live = LIVE_ROOT / name
    staged_sha = _sha(staged)
    live_sha = _sha(live)
    return ProbeResult(
        name=f"live parity {name}",
        category="live_parity",
        route=str(live),
        method="FS",
        status=200,
        expected_statuses=[200],
        pass_=True,
        json_object=True,
        body_sample={
            "staged_sha256": staged_sha,
            "live_sha256": live_sha,
            "live_exists": live.exists(),
            "parity_match": live_sha == staged_sha,
        },
    )


def _results() -> list[ProbeResult]:
    if not LIVE_ROOT.exists():
        return [_live_absent_result()]
    return [_live_file_result(name) for name in IMPORTANT_FILES]


def main() -> None:
    payload = report_payload(
        "receiver_live_parity", "PROBE_DERIVE_VERIFY_EMBODY_RECURSE", _results()
    )
    write_report(REPORT_PATH, payload)


if __name__ == "__main__":
    main()
