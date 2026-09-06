"""Task finalizer that runs CSC gates and reports final project cleanliness."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Mapping
from typing import TypedDict, cast

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.csc_native.strict_json_boundary import (
    read_json_boundary,
    render_json_boundary,
    write_json_boundary,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
CSC_RUNNER = PROJECT_ROOT / "tools" / "csc_native" / "csc_universal_runner.py"
SEMANTIC_GATE = PROJECT_ROOT / "tools" / "csc_native" / "semantic_footgun_dataflow_gate.py"
LOC_GATE = PROJECT_ROOT / "tools" / "csc_native" / "codex_unified_loc_compliance_audit.py"
GUIDE_GATE = PROJECT_ROOT / "tools" / "csc_native" / "guide_quality_audit.py"
ROUTE_TRACE_GATE = PROJECT_ROOT / "tools" / "csc_native" / "receiver_full_route_trace_gate.py"
RESILIENCE_SUITE_GATE = PROJECT_ROOT / "tools" / "csc_native" / "receiver_resilience_gate_suite.py"
LAUNCHER_AUDIT_GATE = (
    PROJECT_ROOT / "tools" / "csc_native" / "receiver_launcher_script_audit_gate.py"
)
BASELINE_SELFTEST_GATE = (
    PROJECT_ROOT / "tools" / "csc_native" / "receiver_baseline_selftest_gate.py"
)
SCHEMA_AUTHORITY_GATE = PROJECT_ROOT / "tools" / "csc_native" / "receiver_schema_authority_gate.py"
LIVE_PARITY_GATE = PROJECT_ROOT / "tools" / "csc_native" / "receiver_live_parity_gate.py"
EXPRESSION_FINALIZER = PROJECT_ROOT / "system" / "constraint_pipeline" / "finalizer_expression.py"
RUNS_ROOT = PROJECT_ROOT / "data" / "csc_runs"


class LocComplianceSummary(TypedDict):
    finding_count: int | None
    strict_failure_count: int | None
    promotion_readiness: str | None


class GuideQualitySummary(TypedDict):
    finding_count: int | None
    strict_failure_count: int | None
    advisory_only: bool | None


class FinalizerEventReportSummary(TypedDict):
    core_cycle_clean: bool | None
    sop_availability_clean: bool | None
    sop_freshness_clean: bool | None
    holonic_audit_clean: bool | None
    doctrine_coverage_clean: bool | None
    loc_compliance: LocComplianceSummary
    guide_quality: GuideQualitySummary


class CscRunSummary(TypedDict):
    command: list[str]
    returncode: int
    stdout_tail: str
    stderr_tail: str
    event_report: FinalizerEventReportSummary


class GateCommandSummary(TypedDict):
    command: list[str]
    returncode: int
    stdout_tail: str
    stderr_tail: str
    report_path: str
    clean: bool | None


class PDVERLevels(TypedDict):
    nano: str
    micro: str
    meso: str
    macro: str


class ExpressionSummary(TypedDict):
    command: list[str]
    returncode: int
    stdout_tail: str
    stderr_tail: str
    report_path: str
    final_clean: bool | None
    required_action: str | None


class FinalSummary(TypedDict):
    project_root: str
    run_name: str
    csc_output_root: str
    pdver_algorithm: str
    pdver_levels: PDVERLevels
    loc_quality: GateCommandSummary
    guide_quality: GateCommandSummary
    semantic_footgun: GateCommandSummary
    launcher_script_audit: GateCommandSummary
    baseline_selftest: GateCommandSummary
    schema_authority: GateCommandSummary
    live_parity: GateCommandSummary
    full_route_trace: GateCommandSummary
    resilience_suite: GateCommandSummary
    csc: CscRunSummary
    expression: ExpressionSummary
    final_clean: bool


@dataclass(frozen=True)
class CompletedCommand:
    command: list[str]
    returncode: int
    stdout_tail: str
    stderr_tail: str


@dataclass(frozen=True)
class FinalCleanContext:
    loc_quality: GateCommandSummary
    guide_quality: GateCommandSummary
    semantic_footgun: GateCommandSummary
    launcher_script_audit: GateCommandSummary
    baseline_selftest: GateCommandSummary
    schema_authority: GateCommandSummary
    live_parity: GateCommandSummary
    full_route_trace: GateCommandSummary
    resilience_suite: GateCommandSummary
    csc: CscRunSummary
    expression: ExpressionSummary


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def _run_command(command: list[str]) -> CompletedCommand:
    completed = subprocess.run(
        command, cwd=str(PROJECT_ROOT), capture_output=True, text=True, check=False
    )
    return CompletedCommand(
        command=command,
        returncode=completed.returncode,
        stdout_tail=completed.stdout[-8000:],
        stderr_tail=completed.stderr[-8000:],
    )


def _loc_compliance_summary(raw: object) -> LocComplianceSummary:
    if not isinstance(raw, dict):
        return LocComplianceSummary(
            finding_count=None,
            strict_failure_count=None,
            promotion_readiness=None,
        )
    severity_counts = raw.get("severity_counts")
    strict_failure_count = None
    if isinstance(severity_counts, dict):
        strict_failure_count = sum(
            int(severity_counts.get(level, 0))
            for level in ("BLOCKER", "HIGH", "MEDIUM")
            if isinstance(severity_counts.get(level, 0), int)
        )
    return LocComplianceSummary(
        finding_count=(
            int(raw["finding_count"]) if isinstance(raw.get("finding_count"), int) else None
        ),
        strict_failure_count=strict_failure_count,
        promotion_readiness=(
            str(raw["promotion_readiness"])
            if isinstance(raw.get("promotion_readiness"), str)
            else None
        ),
    )


def _guide_quality_summary(raw: object) -> GuideQualitySummary:
    if not isinstance(raw, dict):
        return GuideQualitySummary(
            finding_count=None,
            strict_failure_count=None,
            advisory_only=None,
        )
    return GuideQualitySummary(
        finding_count=(
            int(raw["finding_count"]) if isinstance(raw.get("finding_count"), int) else None
        ),
        strict_failure_count=(
            int(raw["strict_failure_count"])
            if isinstance(raw.get("strict_failure_count"), int)
            else None
        ),
        advisory_only=(
            bool(raw.get("advisory_only")) if isinstance(raw.get("advisory_only"), bool) else None
        ),
    )


def _empty_event_report_summary() -> FinalizerEventReportSummary:
    return FinalizerEventReportSummary(
        core_cycle_clean=None,
        sop_availability_clean=None,
        sop_freshness_clean=None,
        holonic_audit_clean=None,
        doctrine_coverage_clean=None,
        loc_compliance=LocComplianceSummary(
            finding_count=None,
            strict_failure_count=None,
            promotion_readiness=None,
        ),
        guide_quality=GuideQualitySummary(
            finding_count=None,
            strict_failure_count=None,
            advisory_only=None,
        ),
    )


def _read_event_report(output_root: Path) -> Mapping[object, object] | None:
    event_report_path = output_root / "CSC_EVENT_REPORT.json"
    if not event_report_path.exists():
        return None
    event_report_raw = read_json_boundary(event_report_path)
    if not isinstance(event_report_raw, dict):
        return None
    return cast(Mapping[object, object], event_report_raw)


def _clean_flag(raw: object, key: str) -> bool | None:
    return bool(raw.get(key)) if isinstance(raw, dict) else None


def _event_report_summary(output_root: Path) -> FinalizerEventReportSummary:
    event_report = _read_event_report(output_root)
    if event_report is None:
        return _empty_event_report_summary()
    core_cycle = event_report.get("core_cycle")
    sop_availability = event_report.get("sop_availability")
    sop_freshness = event_report.get("sop_freshness")
    holonic_audit = event_report.get("holonic_audit")
    doctrine_coverage = event_report.get("doctrine_coverage")
    loc_compliance = event_report.get("loc_compliance")
    guide_quality = event_report.get("guide_quality")
    return FinalizerEventReportSummary(
        core_cycle_clean=_clean_flag(core_cycle, "final_cycle_clean"),
        sop_availability_clean=_clean_flag(sop_availability, "clean"),
        sop_freshness_clean=_clean_flag(sop_freshness, "clean"),
        holonic_audit_clean=_clean_flag(holonic_audit, "clean"),
        doctrine_coverage_clean=_clean_flag(doctrine_coverage, "clean"),
        loc_compliance=_loc_compliance_summary(loc_compliance),
        guide_quality=_guide_quality_summary(guide_quality),
    )


def _read_mapping_report(path: Path) -> Mapping[object, object] | None:
    if not path.exists():
        return None
    raw = read_json_boundary(path)
    return cast(Mapping[object, object], raw) if isinstance(raw, dict) else None


def _clean_from_report(path: Path) -> bool | None:
    report = _read_mapping_report(path)
    if report is None:
        return None
    clean = report.get("clean")
    return bool(clean) if isinstance(clean, bool) else None


def _loc_report_clean(path: Path) -> bool | None:
    report = _read_mapping_report(path)
    if report is None:
        return None
    return int(report.get("finding_count") or 0) == 0


def _guide_report_clean(path: Path) -> bool | None:
    report = _read_mapping_report(path)
    if report is None:
        return None
    return int(report.get("strict_failure_count") or 0) == 0


def _run_loc_gate() -> GateCommandSummary:
    report_path = PROJECT_ROOT / "reports" / "CODEX_UNIFIED_LOC_COMPLIANCE_AUDIT.json"
    completed = _run_command([sys.executable, str(LOC_GATE)])
    return GateCommandSummary(
        command=completed.command,
        returncode=completed.returncode,
        stdout_tail=completed.stdout_tail,
        stderr_tail=completed.stderr_tail,
        report_path=str(report_path),
        clean=_loc_report_clean(report_path),
    )


def _run_guide_gate() -> GateCommandSummary:
    report_path = PROJECT_ROOT / "reports" / "GEMINI_GUIDE_CODEBASE_EVALUATION.json"
    completed = _run_command([sys.executable, str(GUIDE_GATE)])
    return GateCommandSummary(
        command=completed.command,
        returncode=completed.returncode,
        stdout_tail=completed.stdout_tail,
        stderr_tail=completed.stderr_tail,
        report_path=str(report_path),
        clean=_guide_report_clean(report_path),
    )


def _run_semantic_gate() -> GateCommandSummary:
    report_path = PROJECT_ROOT / "reports" / "SEMANTIC_FOOTGUN_DATAFLOW_GATE_REPORT.json"
    completed = _run_command([sys.executable, str(SEMANTIC_GATE)])
    return GateCommandSummary(
        command=completed.command,
        returncode=completed.returncode,
        stdout_tail=completed.stdout_tail,
        stderr_tail=completed.stderr_tail,
        report_path=str(report_path),
        clean=_clean_from_report(report_path),
    )


def _run_full_route_trace_gate() -> GateCommandSummary:
    report_path = PROJECT_ROOT / "reports" / "RECEIVER_FULL_ROUTE_TRACE_GATE_REPORT.json"
    completed = _run_command([sys.executable, str(ROUTE_TRACE_GATE)])
    return GateCommandSummary(
        command=completed.command,
        returncode=completed.returncode,
        stdout_tail=completed.stdout_tail,
        stderr_tail=completed.stderr_tail,
        report_path=str(report_path),
        clean=_clean_from_report(report_path),
    )


def _run_resilience_suite_gate() -> GateCommandSummary:
    report_path = PROJECT_ROOT / "reports" / "RECEIVER_RESILIENCE_GATE_SUITE_REPORT.json"
    completed = _run_command([sys.executable, str(RESILIENCE_SUITE_GATE)])
    return GateCommandSummary(
        command=completed.command,
        returncode=completed.returncode,
        stdout_tail=completed.stdout_tail,
        stderr_tail=completed.stderr_tail,
        report_path=str(report_path),
        clean=_clean_from_report(report_path),
    )


def _run_launcher_audit_gate() -> GateCommandSummary:
    report_path = PROJECT_ROOT / "reports" / "RECEIVER_LAUNCHER_SCRIPT_AUDIT_REPORT.json"
    completed = _run_command([sys.executable, str(LAUNCHER_AUDIT_GATE)])
    return GateCommandSummary(
        command=completed.command,
        returncode=completed.returncode,
        stdout_tail=completed.stdout_tail,
        stderr_tail=completed.stderr_tail,
        report_path=str(report_path),
        clean=_clean_from_report(report_path),
    )


def _run_baseline_selftest_gate() -> GateCommandSummary:
    report_path = PROJECT_ROOT / "reports" / "RECEIVER_BASELINE_SELFTEST_GATE_REPORT.json"
    completed = _run_command([sys.executable, str(BASELINE_SELFTEST_GATE)])
    return GateCommandSummary(
        command=completed.command,
        returncode=completed.returncode,
        stdout_tail=completed.stdout_tail,
        stderr_tail=completed.stderr_tail,
        report_path=str(report_path),
        clean=_clean_from_report(report_path),
    )


def _run_schema_authority_gate() -> GateCommandSummary:
    report_path = PROJECT_ROOT / "reports" / "RECEIVER_SCHEMA_AUTHORITY_GATE_REPORT.json"
    completed = _run_command([sys.executable, str(SCHEMA_AUTHORITY_GATE)])
    return GateCommandSummary(
        command=completed.command,
        returncode=completed.returncode,
        stdout_tail=completed.stdout_tail,
        stderr_tail=completed.stderr_tail,
        report_path=str(report_path),
        clean=_clean_from_report(report_path),
    )


def _run_live_parity_gate() -> GateCommandSummary:
    report_path = PROJECT_ROOT / "reports" / "RECEIVER_LIVE_PARITY_GATE_REPORT.json"
    completed = _run_command([sys.executable, str(LIVE_PARITY_GATE)])
    return GateCommandSummary(
        command=completed.command,
        returncode=completed.returncode,
        stdout_tail=completed.stdout_tail,
        stderr_tail=completed.stderr_tail,
        report_path=str(report_path),
        clean=_clean_from_report(report_path),
    )


def _update_combined_footgun_report(csc_summary: CscRunSummary) -> None:
    semantic_report = _read_mapping_report(
        PROJECT_ROOT / "reports" / "SEMANTIC_FOOTGUN_DATAFLOW_GATE_REPORT.json"
    )
    if semantic_report is None:
        semantic_report = {}
    combined = dict(semantic_report)
    combined["finalizer"] = {
        "latest_run": str(RUNS_ROOT / csc_summary["command"][-1]) if False else None,
        "core_cycle_clean": csc_summary["event_report"]["core_cycle_clean"],
        "sop_freshness_clean": csc_summary["event_report"]["sop_freshness_clean"],
        "doctrine_coverage_clean": csc_summary["event_report"]["doctrine_coverage_clean"],
    }
    write_json_boundary(
        PROJECT_ROOT / "reports" / "FINAL_LOGIC_FOOTGUN_AND_GATE_STACK_REPORT.json", combined
    )


def _expression_final_clean(path: Path) -> bool | None:
    report = _read_mapping_report(path)
    if report is None:
        return None
    final_clean = report.get("final_clean")
    return bool(final_clean) if isinstance(final_clean, bool) else None


def _expression_required_action(path: Path) -> str | None:
    report = _read_mapping_report(path)
    if report is None:
        return None
    required_action = report.get("required_action")
    return str(required_action) if isinstance(required_action, str) else None


def _run_expression_finalizer() -> ExpressionSummary:
    report_path = PROJECT_ROOT / "reports" / "CONSTRAINT_FINALIZER_EXPRESSION_REPORT.json"
    completed = _run_command(
        [sys.executable, str(EXPRESSION_FINALIZER), "--project-root", str(PROJECT_ROOT)]
    )
    return ExpressionSummary(
        command=completed.command,
        returncode=completed.returncode,
        stdout_tail=completed.stdout_tail,
        stderr_tail=completed.stderr_tail,
        report_path=str(report_path),
        final_clean=_expression_final_clean(report_path),
        required_action=_expression_required_action(report_path),
    )


def _run_csc(output_root: Path) -> CscRunSummary:
    command = [
        sys.executable,
        str(CSC_RUNNER),
        "--target-project-root",
        str(PROJECT_ROOT),
        "--output-root",
        str(output_root),
        "--max-cycles",
        "2",
    ]
    completed = _run_command(command)
    return CscRunSummary(
        command=completed.command,
        returncode=completed.returncode,
        stdout_tail=completed.stdout_tail,
        stderr_tail=completed.stderr_tail,
        event_report=_event_report_summary(output_root),
    )


def _gate_summary_clean(summary: GateCommandSummary) -> bool:
    return bool(summary["returncode"] == 0 and summary["clean"])


def _csc_report_clean(csc_summary: CscRunSummary) -> bool:
    event_report = csc_summary["event_report"]
    loc_summary = event_report["loc_compliance"]
    guide_summary = event_report["guide_quality"]
    return bool(
        csc_summary["returncode"] == 0
        and event_report["core_cycle_clean"]
        and event_report["sop_availability_clean"]
        and event_report["sop_freshness_clean"]
        and event_report["holonic_audit_clean"]
        and event_report["doctrine_coverage_clean"]
        and loc_summary["strict_failure_count"] in (0, None)
        and guide_summary["strict_failure_count"] in (0, None)
    )


def _is_final_clean(context: FinalCleanContext) -> bool:
    return bool(
        _gate_summary_clean(context.loc_quality)
        and _gate_summary_clean(context.guide_quality)
        and _gate_summary_clean(context.semantic_footgun)
        and _gate_summary_clean(context.launcher_script_audit)
        and _gate_summary_clean(context.baseline_selftest)
        and _gate_summary_clean(context.schema_authority)
        and _gate_summary_clean(context.live_parity)
        and _gate_summary_clean(context.full_route_trace)
        and _gate_summary_clean(context.resilience_suite)
        and _csc_report_clean(context.csc)
        and context.expression["returncode"] == 0
        and context.expression["final_clean"]
    )


def _run_final_clean_context(output_root: Path) -> FinalCleanContext:
    loc_summary_gate = _run_loc_gate()
    guide_summary_gate = _run_guide_gate()
    semantic_summary = _run_semantic_gate()
    launcher_summary = _run_launcher_audit_gate()
    baseline_selftest_summary = _run_baseline_selftest_gate()
    schema_authority_summary = _run_schema_authority_gate()
    live_parity_summary = _run_live_parity_gate()
    route_trace_summary = _run_full_route_trace_gate()
    resilience_summary = _run_resilience_suite_gate()
    csc_summary = _run_csc(output_root)
    _update_combined_footgun_report(csc_summary)
    expression_summary = _run_expression_finalizer()
    return FinalCleanContext(
        loc_summary_gate,
        guide_summary_gate,
        semantic_summary,
        launcher_summary,
        baseline_selftest_summary,
        schema_authority_summary,
        live_parity_summary,
        route_trace_summary,
        resilience_summary,
        csc_summary,
        expression_summary,
    )


def _final_summary(run_name: str, output_root: Path, context: FinalCleanContext) -> FinalSummary:
    return FinalSummary(
        project_root=str(PROJECT_ROOT),
        run_name=run_name,
        csc_output_root=str(output_root),
        pdver_algorithm="PROBE_DERIVE_VERIFY_EMBODY_RECURSE",
        pdver_levels={
            "nano": "individual route/payload/script/static probe",
            "micro": "gate-level subsystem verification",
            "meso": "cross-gate CSC/doctrine/expression synthesis",
            "macro": "claim-governed final_clean blocker state",
        },
        loc_quality=context.loc_quality,
        guide_quality=context.guide_quality,
        semantic_footgun=context.semantic_footgun,
        launcher_script_audit=context.launcher_script_audit,
        baseline_selftest=context.baseline_selftest,
        schema_authority=context.schema_authority,
        live_parity=context.live_parity,
        full_route_trace=context.full_route_trace,
        resilience_suite=context.resilience_suite,
        csc=context.csc,
        expression=context.expression,
        final_clean=_is_final_clean(context),
    )


def main() -> None:
    run_name = f"auto_finalize_{_utc_stamp()}"
    output_root = RUNS_ROOT / run_name
    output_root.mkdir(parents=True, exist_ok=True)
    context = _run_final_clean_context(output_root)
    summary = _final_summary(run_name, output_root, context)
    sys.stdout.write(render_json_boundary(summary) + "\n")
    if not summary["final_clean"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
