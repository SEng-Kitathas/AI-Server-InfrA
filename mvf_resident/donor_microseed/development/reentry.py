from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
from typing import Any, Iterable, Mapping

from ..runtime.types import Authority

REGISTRATION_KINDS = {
    "CAPABILITY_REGISTERED",
    "RECRUITMENT_TOPOLOGY_REGISTERED",
    "OPERATIONAL_COUNTERPARTY_REGISTERED",
    "OPERATIONAL_COORDINATION_REGISTERED",
}
INVALIDATION_KINDS = {
    "CAPABILITY_INVALIDATED",
    "RECRUITMENT_TOPOLOGY_INVALIDATED",
    "OPERATIONAL_COUNTERPARTY_INVALIDATED",
    "OPERATIONAL_COORDINATION_INVALIDATED",
}


def _handle(kind: str, payload: Mapping[str, Any]) -> str:
    if kind == "CAPABILITY_REGISTERED":
        return "CAP:" + str(payload["capability_id"])
    if kind == "RECRUITMENT_TOPOLOGY_REGISTERED":
        return "TOPO:" + str(payload["topology_id"])
    if kind == "OPERATIONAL_COUNTERPARTY_REGISTERED":
        return "CP:" + str(payload["counterparty_id"])
    if kind == "OPERATIONAL_COORDINATION_REGISTERED":
        return "COORD:" + str(payload["coordination_id"])
    raise KeyError(kind)


def _dependencies(kind: str, payload: Mapping[str, Any]) -> tuple[str, ...]:
    out: set[str] = set()
    if kind == "CAPABILITY_REGISTERED":
        out.update("CAP:" + str(x) for x in payload.get("dependencies", ()))
        out.update("TOPO:" + str(x[0]) for x in payload.get("topology_dependencies", ()))
        out.update("CP:" + str(x[0]) for x in payload.get("counterparty_dependencies", ()))
        out.update("COORD:" + str(x[0]) for x in payload.get("coordination_dependencies", ()))
    elif kind == "RECRUITMENT_TOPOLOGY_REGISTERED":
        out.update("CAP:" + str(x[0]) for x in payload.get("capability_dependencies", ()))
    elif kind == "OPERATIONAL_COORDINATION_REGISTERED":
        out.update("CP:" + str(x[0]) for x in payload.get("participant_counterparty_epochs", ()))
    return tuple(sorted(out))


def _invalidated(kind: str, payload: Mapping[str, Any]) -> tuple[str, ...]:
    if kind == "CAPABILITY_INVALIDATED":
        return tuple(sorted("CAP:" + str(x) for x in payload.get("capability_stale", ())))
    if kind == "RECRUITMENT_TOPOLOGY_INVALIDATED":
        return ("TOPO:" + str(payload["topology_id"]),)
    if kind == "OPERATIONAL_COUNTERPARTY_INVALIDATED":
        return ("CP:" + str(payload["counterparty_id"]),)
    if kind == "OPERATIONAL_COORDINATION_INVALIDATED":
        return ("COORD:" + str(payload["coordination_id"]),)
    return ()


def historical_registration_fingerprint(kind: str, payload: Mapping[str, Any]) -> str:
    """Fingerprint only the historical claim present in the existing event.

    This deliberately excludes executable/provider facts that the event never
    carried. Structural historical coherence is not provider compatibility.
    """
    blob = json.dumps(
        {"kind": kind, "payload": dict(payload)},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode()
    return hashlib.sha256(blob).hexdigest()


@dataclass(frozen=True)
class HistoricalReentryRecord:
    handle: str
    kind: str
    status: str
    registration_seq: int | None
    fingerprint_sha256: str | None
    dependencies: tuple[str, ...] = ()
    equivalent_repeat_count: int = 0
    conflict_fingerprints: tuple[str, ...] = ()
    invalidation_seq: int | None = None


@dataclass(frozen=True)
class HistoricalReentryProjection:
    records: tuple[HistoricalReentryRecord, ...]
    eligible_handles: tuple[str, ...]
    blocked: tuple[tuple[str, tuple[str, ...]], ...]
    layers: tuple[tuple[str, ...], ...]
    cycles: tuple[str, ...]
    authority: Authority = Authority.NONE

    def record(self, handle: str) -> HistoricalReentryRecord | None:
        return next((x for x in self.records if x.handle == handle), None)

    def blocked_map(self) -> dict[str, tuple[str, ...]]:
        return dict(self.blocked)

    def serializable(self) -> dict[str, Any]:
        return {
            "records": [
                {
                    "handle": r.handle,
                    "kind": r.kind,
                    "status": r.status,
                    "registration_seq": r.registration_seq,
                    "fingerprint_sha256": r.fingerprint_sha256,
                    "dependencies": list(r.dependencies),
                    "equivalent_repeat_count": r.equivalent_repeat_count,
                    "conflict_fingerprints": list(r.conflict_fingerprints),
                    "invalidation_seq": r.invalidation_seq,
                }
                for r in self.records
            ],
            "eligible_handles": list(self.eligible_handles),
            "blocked": {k: list(v) for k, v in self.blocked},
            "layers": [list(x) for x in self.layers],
            "cycles": list(self.cycles),
            "authority": self.authority.value,
        }


def derive_historical_reentry_projection(events: Iterable[Mapping[str, Any]]) -> HistoricalReentryProjection:
    state: dict[str, HistoricalReentryRecord] = {}
    latest_kind_payload: dict[str, tuple[str, Mapping[str, Any]]] = {}

    for event in events:
        kind = str(event.get("kind", ""))
        payload = event.get("payload", {}) or {}
        seq = int(event.get("seq", 0))
        if kind in REGISTRATION_KINDS:
            h = _handle(kind, payload)
            fp = historical_registration_fingerprint(kind, payload)
            deps = _dependencies(kind, payload)
            latest_kind_payload[h] = (kind, payload)
            prev = state.get(h)
            if prev is None or prev.status == "HISTORICAL_STALE":
                state[h] = HistoricalReentryRecord(
                    h, kind, "HISTORICAL_NOMINATION_ONLY", seq, fp, deps
                )
            elif prev.status == "HISTORICAL_NOMINATION_ONLY":
                if prev.fingerprint_sha256 == fp:
                    state[h] = replace(
                        prev,
                        registration_seq=seq,
                        dependencies=deps,
                        equivalent_repeat_count=prev.equivalent_repeat_count + 1,
                    )
                else:
                    state[h] = HistoricalReentryRecord(
                        h,
                        kind,
                        "HISTORICAL_CONFLICT",
                        seq,
                        None,
                        deps,
                        prev.equivalent_repeat_count,
                        tuple(sorted({str(prev.fingerprint_sha256), fp})),
                    )
            else:  # conflict remains a conflict until an explicit lifecycle break
                fps = set(prev.conflict_fingerprints)
                fps.add(fp)
                state[h] = replace(
                    prev,
                    registration_seq=seq,
                    dependencies=deps,
                    conflict_fingerprints=tuple(sorted(fps)),
                )
        elif kind in INVALIDATION_KINDS:
            for h in _invalidated(kind, payload):
                prev = state.get(h)
                if prev is not None:
                    state[h] = replace(prev, status="HISTORICAL_STALE", invalidation_seq=seq)

    eligible = {h for h, r in state.items() if r.status == "HISTORICAL_NOMINATION_ONLY"}
    blocked: dict[str, tuple[str, ...]] = {}
    changed = True
    while changed:
        changed = False
        for h in sorted(tuple(eligible)):
            missing = tuple(sorted(d for d in state[h].dependencies if d not in eligible))
            if missing:
                blocked[h] = missing
                eligible.remove(h)
                changed = True

    emitted: set[str] = set()
    layers: list[tuple[str, ...]] = []
    while True:
        ready = tuple(sorted(
            h for h in eligible - emitted
            if set(state[h].dependencies).intersection(eligible).issubset(emitted)
        ))
        if not ready:
            break
        layers.append(ready)
        emitted.update(ready)
    cycles = tuple(sorted(eligible - emitted))

    return HistoricalReentryProjection(
        records=tuple(state[h] for h in sorted(state)),
        eligible_handles=tuple(sorted(eligible)),
        blocked=tuple((h, blocked[h]) for h in sorted(blocked)),
        layers=tuple(layers),
        cycles=cycles,
    )


@dataclass(frozen=True)
class ReentryWarrant:
    """Externally supplied, transient re-entry evidence bundle.

    A warrant carries no handler or current contract and grants no authority.
    It is deliberately orthogonal: historical coherence, provider compatibility,
    executable challenge, scope, and dependency currentness cannot substitute
    for one another.
    """

    handle: str
    historical_fingerprint_sha256: str | None = None
    provider_compatible: bool | None = None
    provider_evidence_id: str | None = None
    executable_challenge_passed: bool | None = None
    executable_evidence_id: str | None = None
    diagnostic_scope: tuple[str, ...] = ()
    dependency_currentness: tuple[tuple[str, bool], ...] = ()
    authority: Authority = Authority.NONE


@dataclass(frozen=True)
class ReentryDecision:
    handle: str
    status: str
    reason: str
    requested_scope: str
    blocking_dependencies: tuple[str, ...] = ()
    authority: Authority = Authority.NONE

    def serializable(self) -> dict[str, Any]:
        return {
            "handle": self.handle,
            "status": self.status,
            "reason": self.reason,
            "requested_scope": self.requested_scope,
            "blocking_dependencies": list(self.blocking_dependencies),
            "authority": self.authority.value,
        }


def assess_reentry(
    projection: HistoricalReentryProjection,
    warrant: ReentryWarrant,
    *,
    requested_scope: str,
) -> ReentryDecision:
    if warrant.authority != Authority.NONE:
        return ReentryDecision(warrant.handle, "DEFER", "WARRANT_AUTHORITY_MUST_BE_NONE", requested_scope)
    record = projection.record(warrant.handle)
    if record is None:
        return ReentryDecision(warrant.handle, "DEFER", "NO_HISTORICAL_REGISTRATION", requested_scope)
    if record.status != "HISTORICAL_NOMINATION_ONLY":
        return ReentryDecision(warrant.handle, "DEFER", record.status, requested_scope)
    if warrant.historical_fingerprint_sha256 != record.fingerprint_sha256:
        return ReentryDecision(warrant.handle, "DEFER", "HISTORICAL_FINGERPRINT_MISMATCH", requested_scope)
    if warrant.provider_compatible is not True or not warrant.provider_evidence_id:
        reason = "PROVIDER_COMPATIBILITY_UNRESOLVED" if warrant.provider_compatible is None else "PROVIDER_INCOMPATIBLE"
        return ReentryDecision(warrant.handle, "DEFER", reason, requested_scope)
    if warrant.executable_challenge_passed is not True or not warrant.executable_evidence_id:
        reason = "EXECUTABLE_COMPATIBILITY_UNRESOLVED" if warrant.executable_challenge_passed is None else "EXECUTABLE_CHALLENGE_FAILED"
        return ReentryDecision(warrant.handle, "DEFER", reason, requested_scope)
    if warrant.provider_evidence_id == warrant.executable_evidence_id:
        return ReentryDecision(warrant.handle, "DEFER", "EVIDENCE_PLANE_OVERLAP", requested_scope)
    if requested_scope not in set(warrant.diagnostic_scope):
        return ReentryDecision(warrant.handle, "DEFER", "OUTSIDE_DIAGNOSTIC_SCOPE", requested_scope)
    current = dict(warrant.dependency_currentness)
    missing = tuple(sorted(d for d in record.dependencies if current.get(d) is not True))
    if missing:
        return ReentryDecision(warrant.handle, "DEFER", "DEPENDENCY_NOT_CURRENT", requested_scope, missing)
    if warrant.handle in projection.cycles:
        return ReentryDecision(warrant.handle, "DEFER", "HISTORICAL_DEPENDENCY_CYCLE", requested_scope)
    return ReentryDecision(
        warrant.handle,
        "READY_FOR_EXISTING_REGISTRATION_PATH",
        "ALL_ORTHOGONAL_REENTRY_PLANES_GREEN",
        requested_scope,
    )
