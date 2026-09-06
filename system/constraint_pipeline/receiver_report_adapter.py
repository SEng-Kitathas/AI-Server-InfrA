"""Receiver v27 adapter that normalizes existing reports into constraint gate results."""

from __future__ import annotations

import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from constraint_model import GateFinding, GateResult, JsonValue
from tools.csc_native.strict_json_boundary import read_json_boundary

JsonObject = Mapping[str, JsonValue]
STRICT_LEVELS = frozenset({"BLOCKER", "HIGH", "MEDIUM"})
SOURCE_ROOTS = (
    Path("baseline") / "pcmmad_receiver",
    Path("system"),
    Path("tools") / "csc_native",
)
EVIDENCE_SOURCE_SCOPE = MappingProxyType(
    {
        "reports/CODEX_UNIFIED_LOC_COMPLIANCE_AUDIT.json": SOURCE_ROOTS,
        "reports/GEMINI_GUIDE_CODEBASE_EVALUATION.json": SOURCE_ROOTS,
        "reports/SEMANTIC_FOOTGUN_DATAFLOW_GATE_REPORT.json": SOURCE_ROOTS,
        "reports/RECEIVER_FULL_ROUTE_TRACE_GATE_REPORT.json": SOURCE_ROOTS,
        "reports/RECEIVER_RESILIENCE_GATE_SUITE_REPORT.json": SOURCE_ROOTS,
        "reports/FINAL_LOGIC_FOOTGUN_AND_GATE_STACK_REPORT.json": SOURCE_ROOTS,
        "reports/RECEIVER_BASELINE_SELFTEST_GATE_REPORT.json": (
            Path("baseline") / "pcmmad_receiver",
        ),
        "reports/RECEIVER_SCHEMA_AUTHORITY_GATE_REPORT.json": (
            Path("baseline") / "pcmmad_receiver",
        ),
    }
)


@dataclass(frozen=True)
class ReportGateSpec:
    gate_id: str
    family: str
    evidence: str


@dataclass(frozen=True)
class CleanReportGateSpec:
    report_gate: ReportGateSpec
    surface_scope: tuple[str, ...]


def _read_json(path: Path) -> JsonObject | None:
    if not path.exists():
        return None
    try:
        value = read_json_boundary(path)
    except (OSError, ValueError, TypeError):
        return None
    return value if isinstance(value, Mapping) else None


def _latest_source_mtime(project_root: Path, evidence_path: str) -> float:
    latest = 0.0
    for rel_root in EVIDENCE_SOURCE_SCOPE.get(evidence_path, SOURCE_ROOTS):
        source_root = project_root / rel_root
        if not source_root.exists():
            continue
        for path in source_root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            try:
                latest = max(latest, path.stat().st_mtime)
            except OSError:
                continue
    return latest


def _is_stale(project_root: Path, evidence_path: str) -> bool:
    path = project_root / evidence_path
    if not path.exists():
        return True
    try:
        evidence_mtime = path.stat().st_mtime
    except OSError:
        return True
    return evidence_mtime < _latest_source_mtime(project_root, evidence_path)


def _stale_gate(gate_id: str, family: str, profile: str, evidence_path: str) -> GateResult:
    finding = GateFinding(
        rule="stale_evidence",
        severity="HIGH",
        message=f"Evidence report is older than active source surfaces: {evidence_path}",
        claim_effects=("blocks_reply_claim", "blocks_promotion", "blocks_package"),
        recommended_action="rerun_with_fresh_evidence",
    )
    return GateResult(
        gate_id=gate_id,
        gate_family=family,
        status="stale",
        profile=profile,
        claim_effects=("blocks_reply_claim", "blocks_promotion", "blocks_package"),
        recommended_action="rerun_with_fresh_evidence",
        finding_count=1,
        strict_failure_count=1,
        evidence_path=evidence_path,
        freshness="stale",
        findings=(finding,),
    )


def _missing_gate(gate_id: str, family: str, profile: str, evidence_path: str) -> GateResult:
    finding = GateFinding(
        rule="missing_evidence",
        severity="HIGH",
        message=f"Required evidence report is missing or unreadable: {evidence_path}",
        claim_effects=("blocks_reply_claim", "blocks_promotion", "blocks_package"),
        recommended_action="rerun_with_fresh_evidence",
    )
    return GateResult(
        gate_id=gate_id,
        gate_family=family,
        status="stale",
        profile=profile,
        claim_effects=("blocks_reply_claim", "blocks_promotion", "blocks_package"),
        recommended_action="rerun_with_fresh_evidence",
        finding_count=1,
        strict_failure_count=1,
        evidence_path=evidence_path,
        freshness="stale",
        findings=(finding,),
    )


def _load_fresh_report(
    project_root: Path, profile: str, spec: ReportGateSpec
) -> tuple[JsonObject | None, GateResult | None]:
    report = _read_json(project_root / spec.evidence)
    if report is None:
        return None, _missing_gate(spec.gate_id, spec.family, profile, spec.evidence)
    if _is_stale(project_root, spec.evidence):
        return None, _stale_gate(spec.gate_id, spec.family, profile, spec.evidence)
    return report, None


def _status_for_strict(strict_count: int) -> str:
    return "fail" if strict_count > 0 else "pass"


def _effects_for_status(status: str, should_block_only_promotion: bool = False) -> tuple[str, ...]:
    if status == "pass":
        return ()
    if should_block_only_promotion:
        return ("blocks_promotion", "requires_local_patch")
    return ("blocks_reply_claim", "blocks_promotion", "requires_local_patch")


def _int_value(raw: object) -> int:
    return int(raw) if isinstance(raw, int) else 0


def _finding_line(raw: Mapping[str, JsonValue]) -> int | None:
    line = raw.get("line")
    return int(line) if isinstance(line, int) else None


def _finding_file(raw: Mapping[str, JsonValue]) -> str | None:
    file_name = raw.get("file")
    return str(file_name) if file_name is not None else None


def _finding_message(raw: Mapping[str, JsonValue]) -> str:
    return str(raw.get("message") or raw.get("issue") or "finding")


def _findings_from_report(
    raw_findings: object, default_effects: tuple[str, ...]
) -> tuple[GateFinding, ...]:
    findings: list[GateFinding] = []
    if not isinstance(raw_findings, list):
        return ()
    for raw in raw_findings[:200]:
        if not isinstance(raw, Mapping):
            continue
        severity = str(raw.get("severity") or "LOW")
        effects = default_effects if severity in STRICT_LEVELS else ("advisory_with_waiver",)
        findings.append(
            GateFinding(
                rule=str(raw.get("rule") or raw.get("kind") or "unknown"),
                severity=severity,
                message=_finding_message(raw),
                file=_finding_file(raw),
                line=_finding_line(raw),
                claim_effects=tuple(effects),
                recommended_action="bounded_patch",
            )
        )
    return tuple(findings)


def _strict_count_from_severity(report: JsonObject) -> int:
    severity_counts = report.get("severity_counts")
    if not isinstance(severity_counts, Mapping):
        return 0
    return sum(_int_value(severity_counts.get(level)) for level in STRICT_LEVELS)


def loc_gate(project_root: Path, profile: str) -> GateResult:
    evidence = "reports/CODEX_UNIFIED_LOC_COMPLIANCE_AUDIT.json"
    report, stale = _load_fresh_report(
        project_root, profile, ReportGateSpec("loc_code_shape", "code_quality", evidence)
    )
    if stale is not None:
        return stale
    assert report is not None
    finding_count = _int_value(report.get("finding_count"))
    strict_count = _strict_count_from_severity(report)
    status = _status_for_strict(strict_count)
    effects = _effects_for_status(status, should_block_only_promotion=False)
    return GateResult(
        gate_id="loc_code_shape",
        gate_family="code_quality",
        status=status,
        profile=profile,
        claim_effects=tuple(effects),
        recommended_action="bounded_patch" if effects else "none",
        finding_count=finding_count,
        strict_failure_count=strict_count,
        advisory_count=max(0, finding_count - strict_count),
        evidence_path=evidence,
        surface_scope=("active_python_surfaces",),
        findings=_findings_from_report(report.get("findings"), tuple(effects)),
    )


def guide_gate(project_root: Path, profile: str) -> GateResult:
    evidence = "reports/GEMINI_GUIDE_CODEBASE_EVALUATION.json"
    report, stale = _load_fresh_report(
        project_root, profile, ReportGateSpec("guide_quality_style", "style_quality", evidence)
    )
    if stale is not None:
        return stale
    assert report is not None
    finding_count = _int_value(report.get("finding_count"))
    strict_count = _int_value(report.get("strict_failure_count"))
    status = _status_for_strict(strict_count)
    effects = _effects_for_status(status, should_block_only_promotion=False)
    advisory_count = max(0, finding_count - strict_count)
    if finding_count and not strict_count:
        effects = ("advisory_with_waiver",)
    return GateResult(
        gate_id="guide_quality_style",
        gate_family="style_quality",
        status=status,
        profile=profile,
        claim_effects=tuple(effects),
        recommended_action="bounded_patch" if status == "fail" else "none",
        finding_count=finding_count,
        strict_failure_count=strict_count,
        advisory_count=advisory_count,
        evidence_path=evidence,
        surface_scope=("active_python_surfaces",),
        findings=_findings_from_report(report.get("findings"), tuple(effects)),
    )


def _route_smoke_finding(effects: tuple[str, ...]) -> GateFinding:
    return GateFinding(
        rule="route_smoke",
        severity="HIGH",
        message="Route smoke did not pass in footgun stack report.",
        claim_effects=tuple(effects),
        recommended_action="bounded_patch",
    )


def _footgun_report_status(report: JsonObject) -> tuple[int, bool, int, str, tuple[str, ...]]:
    count = _int_value(report.get("footgun_count"))
    route_ok = bool(report.get("route_smoke_all_pass"))
    strict = count + (0 if route_ok else 1)
    status = "pass" if strict == 0 else "fail"
    effects = _effects_for_status(status, should_block_only_promotion=False)
    return count, route_ok, strict, status, effects


def _footgun_findings(
    report: JsonObject, route_ok: bool, effects: tuple[str, ...]
) -> tuple[GateFinding, ...]:
    findings = list(_findings_from_report(report.get("footgun_findings"), tuple(effects)))
    if not route_ok:
        findings.append(_route_smoke_finding(tuple(effects)))
    return tuple(findings)


def footgun_gate(project_root: Path, profile: str) -> GateResult:
    evidence = "reports/SEMANTIC_FOOTGUN_DATAFLOW_GATE_REPORT.json"
    report, stale = _load_fresh_report(
        project_root,
        profile,
        ReportGateSpec("semantic_footgun_dataflow", "semantic_logic", evidence),
    )
    if stale is not None:
        return stale
    assert report is not None
    _count, route_ok, strict, status, effects = _footgun_report_status(report)
    findings = _footgun_findings(report, route_ok, tuple(effects))
    return GateResult(
        gate_id="semantic_footgun_dataflow",
        gate_family="semantic_logic",
        status=status,
        profile=profile,
        claim_effects=tuple(effects),
        recommended_action="bounded_patch" if effects else "none",
        finding_count=len(findings),
        strict_failure_count=strict,
        evidence_path=evidence,
        surface_scope=("routes", "dataclass_projection", "request_payload_aliases"),
        findings=findings,
    )


def _clean_report_gate(project_root: Path, profile: str, spec: CleanReportGateSpec) -> GateResult:
    report, stale = _load_fresh_report(project_root, profile, spec.report_gate)
    if stale is not None:
        return stale
    assert report is not None
    clean = bool(report.get("clean"))
    status = "pass" if clean else "fail"
    effects = _effects_for_status(status, should_block_only_promotion=False)
    return GateResult(
        gate_id=spec.report_gate.gate_id,
        gate_family=spec.report_gate.family,
        status=status,
        profile=profile,
        claim_effects=tuple(effects),
        recommended_action="bounded_patch" if effects else "none",
        finding_count=0 if clean else 1,
        strict_failure_count=0 if clean else 1,
        evidence_path=spec.report_gate.evidence,
        surface_scope=spec.surface_scope,
    )


def selftest_gate(project_root: Path, profile: str) -> GateResult:
    return _clean_report_gate(
        project_root,
        profile,
        CleanReportGateSpec(
            ReportGateSpec(
                "receiver_selftest",
                "runtime",
                "reports/RECEIVER_BASELINE_SELFTEST_GATE_REPORT.json",
            ),
            ("receiver_baseline",),
        ),
    )


def route_trace_gate(project_root: Path, profile: str) -> GateResult:
    return _clean_report_gate(
        project_root,
        profile,
        CleanReportGateSpec(
            ReportGateSpec(
                "receiver_full_route_trace",
                "runtime",
                "reports/RECEIVER_FULL_ROUTE_TRACE_GATE_REPORT.json",
            ),
            ("routes", "payloads", "projection", "trace_matrix"),
        ),
    )


def schema_gate(project_root: Path, profile: str) -> GateResult:
    return _clean_report_gate(
        project_root,
        profile,
        CleanReportGateSpec(
            ReportGateSpec(
                "schema_authority", "runtime", "reports/RECEIVER_SCHEMA_AUTHORITY_GATE_REPORT.json"
            ),
            ("schema", "tool_registry"),
        ),
    )


def resilience_suite_gate(project_root: Path, profile: str) -> GateResult:
    return _clean_report_gate(
        project_root,
        profile,
        CleanReportGateSpec(
            ReportGateSpec(
                "receiver_resilience_suite",
                "runtime",
                "reports/RECEIVER_RESILIENCE_GATE_SUITE_REPORT.json",
            ),
            (
                "negative_contracts",
                "stateful_replay",
                "security_boundaries",
                "browser_bridge",
                "package_integrity",
                "live_parity",
                "concurrency",
            ),
        ),
    )


def launcher_script_audit_gate(project_root: Path, profile: str) -> GateResult:
    return _clean_report_gate(
        project_root,
        profile,
        CleanReportGateSpec(
            ReportGateSpec(
                "receiver_launcher_script_audit",
                "runtime",
                "reports/RECEIVER_LAUNCHER_SCRIPT_AUDIT_REPORT.json",
            ),
            ("launcher", "restart", "ngrok", "local_env", "process_control"),
        ),
    )


def finalizer_gate(project_root: Path, profile: str) -> GateResult:
    evidence = "reports/FINAL_LOGIC_FOOTGUN_AND_GATE_STACK_REPORT.json"
    report, stale = _load_fresh_report(
        project_root, profile, ReportGateSpec("task_finalizer", "doctrine_sop_csc", evidence)
    )
    if stale is not None:
        return stale
    assert report is not None
    finalizer = report.get("finalizer") if isinstance(report.get("finalizer"), Mapping) else {}
    clean = (
        bool(finalizer.get("core_cycle_clean"))
        and bool(finalizer.get("sop_freshness_clean"))
        and bool(finalizer.get("doctrine_coverage_clean"))
    )
    status = "pass" if clean else "fail"
    effects = _effects_for_status(status, should_block_only_promotion=True)
    return GateResult(
        gate_id="task_finalizer",
        gate_family="doctrine_sop_csc",
        status=status,
        profile=profile,
        claim_effects=tuple(effects),
        recommended_action="rerun_with_fresh_evidence" if effects else "none",
        finding_count=0 if clean else 1,
        strict_failure_count=0 if clean else 1,
        evidence_path=evidence,
        surface_scope=("csc_finalizer", "sop_freshness", "doctrine_coverage"),
        notes=(f"latest_run={finalizer.get('latest_run')}",) if finalizer else (),
    )


def receiver_gates(project_root: Path, profile: str) -> tuple[GateResult, ...]:
    return (
        loc_gate(project_root, profile),
        guide_gate(project_root, profile),
        footgun_gate(project_root, profile),
        route_trace_gate(project_root, profile),
        resilience_suite_gate(project_root, profile),
        launcher_script_audit_gate(project_root, profile),
        selftest_gate(project_root, profile),
        schema_gate(project_root, profile),
        finalizer_gate(project_root, profile),
    )
