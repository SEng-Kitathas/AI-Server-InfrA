"""Build a project constraint-expression report from existing gate evidence."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from collections.abc import Mapping
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from claim_governor import claim_permissions, final_clean_from_claims, required_action
from constraint_model import ConstraintFinalizerReport, JsonValue
from receiver_report_adapter import receiver_gates
from tools.csc_native.strict_json_boundary import render_json_boundary, write_json_boundary


def _project_id(project_root: Path) -> str:
    return project_root.name


def _summary(gates: object, claims: object) -> Mapping[str, JsonValue]:
    gate_tuple = tuple(gates)  # type: ignore[arg-type]
    claim_tuple = tuple(claims)  # type: ignore[arg-type]
    return {
        "gate_count": len(gate_tuple),
        "passing_gates": sum(1 for gate in gate_tuple if gate.status == "pass"),
        "failing_gates": sum(1 for gate in gate_tuple if gate.status == "fail"),
        "stale_gates": sum(1 for gate in gate_tuple if gate.status == "stale"),
        "blocked_claims": [claim.claim for claim in claim_tuple if claim.status == "blocked"],
        "downgraded_claims": [claim.claim for claim in claim_tuple if claim.status == "downgraded"],
        "allowed_claims": [claim.claim for claim in claim_tuple if claim.status == "allowed"],
    }


def build_report(project_root: Path, profile: str) -> ConstraintFinalizerReport:
    gates = receiver_gates(project_root, profile)
    claims = claim_permissions(gates)
    return ConstraintFinalizerReport(
        project_id=_project_id(project_root),
        profile=profile,
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        gates=gates,
        claims=claims,
        final_clean=final_clean_from_claims(claims),
        required_action=required_action(gates),
        summary=_summary(gates, claims),
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build project constraint-expression finalizer report"
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--profile", default="promotion")
    parser.add_argument("--output", default="reports/CONSTRAINT_FINALIZER_EXPRESSION_REPORT.json")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    project_root = Path(args.project_root).resolve()
    output = (project_root / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    report = build_report(project_root, args.profile)
    write_json_boundary(output, report.to_dict())
    console_summary = {
        "output": str(output),
        "final_clean": report.final_clean,
        "required_action": report.required_action,
        "summary": report.summary,
    }
    sys.stdout.write(render_json_boundary(console_summary) + "\n")


if __name__ == "__main__":
    main()
