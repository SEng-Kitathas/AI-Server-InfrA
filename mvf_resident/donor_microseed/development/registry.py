from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Iterable
from ..runtime.types import Authority, CapabilityContract, QualificationState, EvidenceRef
from ..evidence.authority import FixedQualifier


@dataclass
class DevelopmentRecord:
    artifact_id: str
    kind: str
    lineage: tuple[str, ...]
    assistance_ancestry: tuple[str, ...]
    dependencies: tuple[str, ...]
    qualification: QualificationState = QualificationState.CANDIDATE
    authority: Authority = Authority.NONE
    thermal_status: str = "COLD"
    evidence: tuple[EvidenceRef, ...] = ()
    notes: tuple[str, ...] = ()

    def serializable(self) -> dict[str, Any]:
        return asdict(self)


class DevelopmentRegistry:
    def __init__(self, qualifier: FixedQualifier):
        self.qualifier = qualifier
        self.records: dict[str, DevelopmentRecord] = {}
        self.reverse_deps: dict[str, set[str]] = {}

    def nominate(self, record: DevelopmentRecord) -> None:
        if record.artifact_id in self.records:
            raise ValueError(f"duplicate artifact_id: {record.artifact_id}")
        self.records[record.artifact_id] = record
        for dep in record.dependencies:
            self.reverse_deps.setdefault(dep, set()).add(record.artifact_id)

    def qualify(self, artifact_id: str, *, requested_authority: Authority | None = None) -> DevelopmentRecord:
        r = self.records[artifact_id]
        req = requested_authority if requested_authority is not None else r.authority
        d = self.qualifier.decide(r.evidence, req)
        r.qualification = d.state
        r.authority = d.authority
        return r

    def invalidate(self, artifact_id: str, reason: str) -> set[str]:
        """Mark the changed artifact and transitive dependents stale, preserving history."""
        stale: set[str] = set()
        q = [artifact_id]
        while q:
            x = q.pop()
            if x in stale:
                continue
            stale.add(x)
            if x in self.records:
                self.records[x].qualification = QualificationState.STALE
                self.records[x].notes = self.records[x].notes + (f"STALE:{reason}",)
            q.extend(sorted(self.reverse_deps.get(x, ())))
        return stale

    def hot(self, artifact_id: str, status: str) -> None:
        self.records[artifact_id].thermal_status = status

    def snapshot(self) -> dict[str, Any]:
        return {k: v.serializable() for k, v in sorted(self.records.items())}
