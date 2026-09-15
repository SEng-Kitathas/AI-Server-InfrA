from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Protocol

from .donor_microseed.runtime.types import Observation
from .donor_microseed.runtime.observation import currentness as microseed_currentness
from .donor_microseed.runtime.commitment import TernaryCommitment, RelationalCommitment

Json = dict[str, Any]


class ToolAdapter(Protocol):
    def call(self, name: str, payload: Mapping[str, Any]) -> Json: ...


class LabToolsAdapter:
    """Read-only bridge to the native runtime router. Adapter grants no authority."""
    def __init__(self, dispatch: Callable[..., Json]) -> None:
        self._dispatch = dispatch

    def call(self, name: str, payload: Mapping[str, Any]) -> Json:
        return self._dispatch(name, dict(payload))


@dataclass(frozen=True)
class DutyContract:
    duty_id: str
    subject: str
    maintained_claim: str
    observation_plan: tuple[tuple[str, Json], ...]
    max_age_seconds: int = 300
    stale_conditions: tuple[str, ...] = ()
    reopen_conditions: tuple[str, ...] = ()
    allowed_cognition: tuple[str, ...] = ("inspect", "compare", "synthesize", "brief")
    allowed_effects: tuple[str, ...] = ("read",)
    escalation_conditions: tuple[str, ...] = ("UNKNOWN_INCOMPLETE", "STALE", "VIOLATED")
    evidence_requirements: tuple[str, ...] = ()
    cadence: str = "triggered_or_periodic"
    authority_ceiling: str = "OBSERVATION_ONLY"

    def __post_init__(self) -> None:
        forbidden = {"mutation", "execution", "restart", "kill", "install"}
        if forbidden.intersection(x.casefold() for x in self.allowed_effects):
            raise ValueError("resident duty prototype is read-only")


@dataclass(frozen=True)
class DutyObservation:
    tool: str
    observed_at: str
    payload: Json
    status: str
    error: str | None = None


@dataclass(frozen=True)
class DutyResult:
    duty_id: str
    subject: str
    status: str
    commitment: str
    reason: str
    observations: tuple[DutyObservation, ...]
    stale_reasons: tuple[str, ...] = ()
    reopen_reasons: tuple[str, ...] = ()
    escalation_required: bool = False
    mutation_authority: bool = False

    def to_dict(self) -> Json:
        return asdict(self)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _unwrap(value: Json) -> Json:
    if value.get("ok") is True and isinstance(value.get("result"), dict):
        return dict(value["result"])
    return value


def _resolve_path(value: Mapping[str, Any], path: str) -> Any:
    cur: Any = value
    for part in path.split('.'):
        if not isinstance(cur, Mapping) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _parse_literal(value: str) -> Any:
    low = value.casefold()
    if low == "true": return True
    if low == "false": return False
    if low == "null" or low == "none": return None
    try: return int(value)
    except ValueError: return value


def _condition_matches(observations: list[DutyObservation], condition: str) -> bool:
    if '=' not in condition:
        raise ValueError(f"condition must be structured field=value, got {condition!r}")
    path, raw_expected = condition.split('=', 1)
    expected = _parse_literal(raw_expected.strip())
    path = path.strip()
    return any(_resolve_path(o.payload, path) == expected for o in observations)


def _obs(tool: str, value: Json, observed_at: str) -> Observation:
    return Observation(
        capture_id=f"mvf:{tool}:{observed_at}",
        origin="MVF_RESIDENT_NATIVE_TOOL",
        referent=tool,
        value=value,
        observed_at=observed_at,
        acquired_at=observed_at,
        currentness_basis="MICROSEED_OBSERVATION_AGE_AND_EXPLICIT_TOOL_RESULT",
        lineage=(tool,),
    )


class MVFResident:
    """First read-only resident prototype. Cognitive composition != mutation authority."""

    def __init__(self, adapter: ToolAdapter, *, now: Callable[[], str] = _now_iso) -> None:
        self.adapter = adapter
        self.now = now

    def run_duty(self, contract: DutyContract) -> DutyResult:
        now_iso = self.now()
        observations: list[DutyObservation] = []
        stale: list[str] = []
        reopen: list[str] = []
        failures: list[str] = []
        for tool, payload in contract.observation_plan:
            try:
                raw = self.adapter.call(tool, payload)
                value = _unwrap(raw)
                observed_at = self.now()
                ms_obs = _obs(tool, value, observed_at)
                age_state = microseed_currentness(ms_obs, now_iso, contract.max_age_seconds)
                semantic_ok = bool(value.get("ok", True))
                status = age_state if semantic_ok else "VIOLATED"
                if status == "STALE": stale.append(f"{tool}:observation_age")
                elif status in {"VIOLATED", "UNKNOWN_INCOMPLETE"}: failures.append(f"{tool}:{status}")
                observations.append(DutyObservation(tool, observed_at, value, status))
            except Exception as exc:
                observed_at = self.now()
                failures.append(f"{tool}:ERROR")
                observations.append(DutyObservation(tool, observed_at, {}, "UNKNOWN_INCOMPLETE", f"{type(exc).__name__}: {exc}"))

        for condition in contract.stale_conditions:
            if _condition_matches(observations, condition):
                stale.append(condition)
        for condition in contract.reopen_conditions:
            if _condition_matches(observations, condition):
                reopen.append(condition)

        if failures:
            status = "UNKNOWN_INCOMPLETE" if all(x.endswith("ERROR") or "UNKNOWN" in x for x in failures) else "VIOLATED"
            reason = "; ".join(failures)
            commitment = TernaryCommitment.UNKNOWN.value
        elif stale or reopen:
            status = "STALE"
            reason = "; ".join(stale + reopen) or "reopen required"
            commitment = TernaryCommitment.UNKNOWN.value
        else:
            status = "CURRENT"
            reason = "all required observations are current and non-violating"
            commitment = TernaryCommitment.YES.value

        escalation = status in set(contract.escalation_conditions)
        return DutyResult(
            duty_id=contract.duty_id,
            subject=contract.subject,
            status=status,
            commitment=commitment,
            reason=reason,
            observations=tuple(observations),
            stale_reasons=tuple(stale),
            reopen_reasons=tuple(reopen),
            escalation_required=escalation,
            mutation_authority=False,
        )

    def run_portfolio(self, duties: tuple[DutyContract, ...]) -> Json:
        results = tuple(self.run_duty(d) for d in duties)
        priority = {"VIOLATED": 4, "UNKNOWN_INCOMPLETE": 3, "STALE": 2, "CURRENT": 1}
        overall = max((r.status for r in results), key=lambda s: priority.get(s, 0), default="UNKNOWN_INCOMPLETE")
        decisions = [r.duty_id for r in results if r.escalation_required]
        return {
            "schema": "mvf.resident-brief.v1",
            "overall_status": overall,
            "mutation_authority": False,
            "duties": [r.to_dict() for r in results],
            "decisions_required": decisions,
            "compact": self.compact_brief(results),
        }

    @staticmethod
    def compact_brief(results: tuple[DutyResult, ...]) -> Json:
        current = [r.duty_id for r in results if r.status == "CURRENT"]
        attention = [r.duty_id for r in results if r.status != "CURRENT"]
        return {
            "current": current,
            "attention": attention,
            "high_value_updates": [
                {"duty": r.duty_id, "status": r.status, "reason": r.reason}
                for r in results if r.status != "CURRENT"
            ],
        }


def default_receiver_lab_duties(project_id: str = "RECEIVER-LAB") -> tuple[DutyContract, ...]:
    return (
        DutyContract(
            duty_id="receiver-currentness-ha",
            subject="PCMMAD Receiver + recovery path",
            maintained_claim="receiver and recovery evidence remain current enough for operator briefing",
            observation_plan=(("machine.processes.list", {"name_filter": "python", "limit": 25}), ("machine.processes.list", {"name_filter": "ngrok", "limit": 25}), ("machine.scheduled_tasks.list", {"name_filter": "PCMMAD", "limit": 50})),
            stale_conditions=("status=STALE",),
            reopen_conditions=("status=VIOLATED",),
            evidence_requirements=("process identity metadata", "scheduled task state"),
        ),
        DutyContract(
            duty_id="repository-topology-currentness",
            subject="project/operator repository topology",
            maintained_claim="repository discovery routes remain available and bounded",
            observation_plan=(("git.repositories.list", {"project_id": project_id, "max_depth": 4, "max_results": 50}), ("machine.roots.list", {"include_drives": False})),
            stale_conditions=("status=stale_known_ancestor",),
            reopen_conditions=("status=divergent",),
            evidence_requirements=("exact repo identity", "bounded root inventory"),
        ),
        DutyContract(
            duty_id="continuity-evidence-staleness",
            subject="PCMMAD continuity/evidence surfaces",
            maintained_claim="continuity qualification remains current enough to resume without invention",
            observation_plan=(("continuity.convergence.inspect", {"project_id": project_id, "artifact": {"artifact_class": "continuity.live_shadow", "logical_name": "LIVE_SHADOW.md"}}),),
            stale_conditions=("status=stale_known_ancestor", "status=local_unregistered"),
            reopen_conditions=("status=divergent", "status=unknown"),
            evidence_requirements=("convergence state", "artifact currentness"),
        ),
    )
