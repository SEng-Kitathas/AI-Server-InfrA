from __future__ import annotations
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Iterable


class EpistemicDeficitState(str, Enum):
    ACTION_LIMITED = "ACTION_LIMITED"
    PROBE_AVAILABLE = "PROBE_AVAILABLE"
    REVISIT_REQUIRED = "REVISIT_REQUIRED"
    STALE = "STALE"


@dataclass(frozen=True)
class EpistemicCurrentnessAnchor:
    """Opaque content/currentness ancestry for one bounded epistemic deficit.

    `kind` names an operational registry surface, not a semantic question type.
    `object_id` and `epoch` bind the deficit to the exact premise state that made
    its historical UNKNOWN and missing-discriminator pressure current.
    """

    kind: str
    object_id: str
    epoch: int

    def __post_init__(self) -> None:
        if not self.kind or not self.object_id:
            raise ValueError("EMPTY_EPISTEMIC_CURRENTNESS_ANCHOR")
        if int(self.epoch) < 0:
            raise ValueError("NEGATIVE_EPISTEMIC_CURRENTNESS_EPOCH")
        object.__setattr__(self, "kind", str(self.kind).upper())
        object.__setattr__(self, "object_id", str(self.object_id))
        object.__setattr__(self, "epoch", int(self.epoch))

    def serializable(self) -> dict[str, Any]:
        return {"kind": self.kind, "object_id": self.object_id, "epoch": self.epoch}

    @classmethod
    def from_serializable(cls, d: dict[str, Any]) -> "EpistemicCurrentnessAnchor":
        return cls(kind=str(d["kind"]), object_id=str(d["object_id"]), epoch=int(d["epoch"]))


@dataclass
class EpistemicDeficitRecord:
    """Proposal/scheduling state for one action-limited UNKNOWN.

    This record does not represent a semantic question ontology and has no truth
    authority. It preserves why the entity could not currently discriminate a
    bounded hypothesis set and the opaque signature of a missing discriminator.

    MS1153-1177 adds a second distinction: durable historical memory is not the
    same as *current developmental pressure*. Typed opaque premise anchors may
    stale the current deficit while preserving its historical UNKNOWN. Loss of a
    probe alone instead reopens ACTION_LIMITED when those question premises are
    still current.
    """

    deficit_id: str
    question_key: str
    hypothesis_digest_sha256: str
    unknown_evidence_id: str
    missing_discriminator_signature_sha256: str
    identifiability_class: str = "C_ACTION_LIMITED"
    state: EpistemicDeficitState = EpistemicDeficitState.ACTION_LIMITED
    probe_capability_id: str | None = None
    probe_capability_epoch: int | None = None
    candidate_ids: tuple[str, ...] = ()
    probe_evidence_ids: tuple[str, ...] = ()
    relevant_evidence_ids: tuple[str, ...] = ()
    premise_anchors: tuple[EpistemicCurrentnessAnchor, ...] = ()
    stale_reason: str | None = None
    stale_evidence_id: str | None = None
    assistance_ancestry: tuple[str, ...] = ()
    truth_authority: str = "NONE"
    semantic_question_authority: str = "NONE"

    def serializable(self) -> dict[str, Any]:
        d = asdict(self)
        d["state"] = self.state.value
        d["premise_anchors"] = [a.serializable() for a in self.premise_anchors]
        return d

    @classmethod
    def from_serializable(cls, d: dict[str, Any]) -> "EpistemicDeficitRecord":
        x = dict(d)
        x["state"] = EpistemicDeficitState(x.get("state", "ACTION_LIMITED"))
        x["candidate_ids"] = tuple(x.get("candidate_ids", ()))
        x["probe_evidence_ids"] = tuple(x.get("probe_evidence_ids", ()))
        x["relevant_evidence_ids"] = tuple(x.get("relevant_evidence_ids", ()))
        x["premise_anchors"] = tuple(
            EpistemicCurrentnessAnchor.from_serializable(a)
            if not isinstance(a, EpistemicCurrentnessAnchor) else a
            for a in x.get("premise_anchors", ())
        )
        x["assistance_ancestry"] = tuple(x.get("assistance_ancestry", ()))
        return cls(**x)


class EpistemicDeficitRegistry:
    """Durable bounded epistemic-deficit lifecycle, never truth adjudication."""

    def __init__(self):
        self.records: dict[str, EpistemicDeficitRecord] = {}

    def register(self, record: EpistemicDeficitRecord) -> None:
        if not record.deficit_id or record.deficit_id in self.records:
            raise ValueError("duplicate/empty epistemic deficit")
        if record.identifiability_class != "C_ACTION_LIMITED":
            raise ValueError("ONLY_C_ACTION_LIMITED_DEFICITS_SUPPORTED")
        if record.truth_authority != "NONE" or record.semantic_question_authority != "NONE":
            raise ValueError("EPISTEMIC_DEFICIT_CANNOT_CARRY_TRUTH_OR_SEMANTIC_QUESTION_AUTHORITY")
        if record.state == EpistemicDeficitState.STALE and not record.stale_reason:
            raise ValueError("STALE_EPISTEMIC_DEFICIT_REQUIRES_REASON")
        self.records[record.deficit_id] = record

    def link_candidate(self, deficit_id: str, candidate_id: str) -> EpistemicDeficitRecord:
        r = self.records[deficit_id]
        if r.state == EpistemicDeficitState.STALE:
            raise ValueError("STALE_EPISTEMIC_DEFICIT_CANNOT_ACCEPT_CANDIDATE")
        if candidate_id not in r.candidate_ids:
            r.candidate_ids = tuple(r.candidate_ids) + (candidate_id,)
        return r

    def bind_probe(self, deficit_id: str, capability_id: str, epoch: int) -> EpistemicDeficitRecord:
        r = self.records[deficit_id]
        if r.state == EpistemicDeficitState.STALE:
            raise ValueError("STALE_EPISTEMIC_DEFICIT_CANNOT_ACCEPT_PROBE")
        r.probe_capability_id = capability_id
        r.probe_capability_epoch = int(epoch)
        r.state = EpistemicDeficitState.PROBE_AVAILABLE
        return r

    def record_probe_evidence(self, deficit_id: str, evidence_id: str) -> EpistemicDeficitRecord:
        r = self.records[deficit_id]
        if r.state != EpistemicDeficitState.PROBE_AVAILABLE:
            raise ValueError("PROBE_NOT_CURRENTLY_AVAILABLE")
        if evidence_id not in r.probe_evidence_ids:
            r.probe_evidence_ids = tuple(r.probe_evidence_ids) + (evidence_id,)
        r.state = EpistemicDeficitState.REVISIT_REQUIRED
        return r

    def request_revisit(self, deficit_id: str, evidence_id: str) -> EpistemicDeficitRecord:
        """Record explicitly supplied relevance and request revisit, never answer."""
        r = self.records[deficit_id]
        if r.state == EpistemicDeficitState.STALE:
            raise ValueError("STALE_EPISTEMIC_DEFICIT_CANNOT_REQUEST_REVISIT")
        if evidence_id not in r.relevant_evidence_ids:
            r.relevant_evidence_ids = tuple(r.relevant_evidence_ids) + (evidence_id,)
        r.state = EpistemicDeficitState.REVISIT_REQUIRED
        return r

    def mark_stale(
        self,
        deficit_id: str,
        *,
        reason: str,
        evidence_id: str | None = None,
    ) -> EpistemicDeficitRecord:
        """Suppress current pressure without deleting or rewriting history."""
        if not reason:
            raise ValueError("STALE_EPISTEMIC_DEFICIT_REQUIRES_REASON")
        r = self.records[deficit_id]
        if r.state != EpistemicDeficitState.STALE:
            r.state = EpistemicDeficitState.STALE
            r.stale_reason = str(reason)
            r.stale_evidence_id = evidence_id
        return r

    def invalidate_premise(
        self,
        kind: str,
        object_id: str,
        new_epoch: int,
        *,
        reason: str,
        force: bool = False,
    ) -> set[str]:
        """Stale only deficits bound to the changed opaque premise/currentness state."""
        k = str(kind).upper()
        oid = str(object_id)
        changed: set[str] = set()
        for deficit_id, r in self.records.items():
            if r.state == EpistemicDeficitState.STALE:
                continue
            if any(a.kind == k and a.object_id == oid and (force or a.epoch != int(new_epoch)) for a in r.premise_anchors):
                self.mark_stale(
                    deficit_id,
                    reason=f"PREMISE_DRIFT:{k}:{oid}@{int(new_epoch)}:{reason}",
                )
                changed.add(deficit_id)
        return changed

    def invalidate_probe(self, capability_id: str) -> set[str]:
        changed: set[str] = set()
        for deficit_id, r in self.records.items():
            if r.state == EpistemicDeficitState.STALE:
                continue
            if r.probe_capability_id == capability_id and r.state in {
                EpistemicDeficitState.PROBE_AVAILABLE,
                EpistemicDeficitState.REVISIT_REQUIRED,
            }:
                # Probe/access loss does not stale the question premises. Preserve
                # historical probe/evidence fields; only current action access falls away.
                r.state = EpistemicDeficitState.ACTION_LIMITED
                changed.add(deficit_id)
        return changed

    def development_pressure_ids(self) -> tuple[str, ...]:
        """Bounded eligibility surface, not a scheduler or priority policy."""
        return tuple(sorted(k for k, r in self.records.items() if r.state == EpistemicDeficitState.ACTION_LIMITED))

    def revisit_required_ids(self) -> tuple[str, ...]:
        """Bounded eligibility surface, not automatic execution or truth."""
        return tuple(sorted(k for k, r in self.records.items() if r.state == EpistemicDeficitState.REVISIT_REQUIRED))

    def premise_dependents(self, kind: str, object_id: str) -> tuple[str, ...]:
        k = str(kind).upper(); oid = str(object_id)
        return tuple(sorted(
            did for did, r in self.records.items()
            if any(a.kind == k and a.object_id == oid for a in r.premise_anchors)
        ))

    def snapshot(self) -> dict[str, dict[str, Any]]:
        return {k: v.serializable() for k, v in sorted(self.records.items())}


def _sha256_token(value: str, *, error: str) -> str:
    v = str(value).lower()
    if len(v) != 64 or any(c not in "0123456789abcdef" for c in v):
        raise ValueError(error)
    return v


@dataclass
class EpistemicProjectionRecord:
    """Externally supplied opaque evidence-coordinate currentness handle.

    This is deliberately *not* a semantic feature/channel ontology and contains
    no machinery for discovering a projection from raw observations. It only
    lets Main-Dev bind a contrast to the exact version of an already supplied
    operational evidence coordinate.
    """

    projection_id: str
    signature_sha256: str
    epoch: int = 0
    assistance_ancestry: tuple[str, ...] = ()
    projection_origin: str = "SUPPLIED_AND_PROVENANCED"
    proposal_candidate_sha256: str | None = None
    qualification_evidence_ids: tuple[str, ...] = ()
    frame_epochs: tuple[tuple[str, int], ...] = ()
    episode_schema_epochs: tuple[tuple[str, int], ...] = ()
    current: bool = True
    semantic_projection_authority: str = "NONE"
    discovery_authority: str = "NONE"

    def __post_init__(self) -> None:
        if not self.projection_id:
            raise ValueError("EMPTY_EPISTEMIC_PROJECTION_ID")
        self.signature_sha256 = _sha256_token(
            self.signature_sha256, error="EPISTEMIC_PROJECTION_SIGNATURE_SHA256_REQUIRED"
        )
        self.epoch = int(self.epoch)
        if self.epoch < 0:
            raise ValueError("NEGATIVE_EPISTEMIC_PROJECTION_EPOCH")
        self.assistance_ancestry = tuple(self.assistance_ancestry)
        if self.projection_origin not in {
            "SUPPLIED_AND_PROVENANCED",
            "ENDOGENOUS_PROPOSAL_EXTERNALLY_QUALIFIED",
            "ENDOGENOUS_CONSTRUCTOR_GROWTH_EXTERNALLY_QUALIFIED",
            "ENDOGENOUS_ROBUST_CONSTRUCTOR_GROWTH_EXTERNALLY_QUALIFIED",
        }:
            raise ValueError("EPISTEMIC_PROJECTION_ORIGIN_UNQUALIFIED")
        if self.proposal_candidate_sha256 is not None:
            self.proposal_candidate_sha256 = _sha256_token(
                self.proposal_candidate_sha256, error="EPISTEMIC_PROJECTION_CANDIDATE_SHA256_REQUIRED"
            )
        self.qualification_evidence_ids = tuple(str(x) for x in self.qualification_evidence_ids)
        self.frame_epochs = tuple((str(x[0]), int(x[1])) for x in self.frame_epochs)
        self.episode_schema_epochs = tuple((str(x[0]), int(x[1])) for x in self.episode_schema_epochs)
        self.current = bool(self.current)
        if self.projection_origin in {
            "ENDOGENOUS_PROPOSAL_EXTERNALLY_QUALIFIED",
            "ENDOGENOUS_CONSTRUCTOR_GROWTH_EXTERNALLY_QUALIFIED",
            "ENDOGENOUS_ROBUST_CONSTRUCTOR_GROWTH_EXTERNALLY_QUALIFIED",
        }:
            if self.proposal_candidate_sha256 is None or not self.qualification_evidence_ids:
                raise ValueError("DISCOVERED_EPISTEMIC_PROJECTION_REQUIRES_EXTERNAL_QUALIFICATION_ANCESTRY")
        if self.semantic_projection_authority != "NONE" or self.discovery_authority != "NONE":
            raise ValueError("EPISTEMIC_PROJECTION_CANNOT_CARRY_SEMANTIC_OR_DISCOVERY_AUTHORITY")

    def serializable(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_serializable(cls, d: dict[str, Any]) -> "EpistemicProjectionRecord":
        x = dict(d)
        x["assistance_ancestry"] = tuple(x.get("assistance_ancestry", ()))
        x["qualification_evidence_ids"] = tuple(x.get("qualification_evidence_ids", ()))
        x["frame_epochs"] = tuple((str(a), int(b)) for a, b in x.get("frame_epochs", ()))
        x["episode_schema_epochs"] = tuple((str(a), int(b)) for a, b in x.get("episode_schema_epochs", ()))
        x["current"] = bool(x.get("current", True))
        return cls(**x)


class EpistemicProjectionRegistry:
    """Versioned opaque projection handles; formation/discovery remains external."""

    def __init__(self) -> None:
        self.records: dict[str, EpistemicProjectionRecord] = {}

    def register(self, record: EpistemicProjectionRecord) -> None:
        if record.projection_id in self.records:
            raise ValueError("DUPLICATE_EPISTEMIC_PROJECTION")
        self.records[record.projection_id] = record

    def change(
        self,
        projection_id: str,
        *,
        new_signature_sha256: str,
    ) -> EpistemicProjectionRecord:
        if projection_id not in self.records:
            raise ValueError("UNKNOWN_EPISTEMIC_PROJECTION")
        old = self.records[projection_id]
        rec = EpistemicProjectionRecord(
            projection_id=projection_id,
            signature_sha256=new_signature_sha256,
            epoch=old.epoch + 1,
            assistance_ancestry=old.assistance_ancestry,
            projection_origin=old.projection_origin,
            proposal_candidate_sha256=old.proposal_candidate_sha256,
            qualification_evidence_ids=old.qualification_evidence_ids,
            frame_epochs=old.frame_epochs,
            episode_schema_epochs=old.episode_schema_epochs,
            current=True,
        )
        self.records[projection_id] = rec
        return rec

    def reactivate(
        self, projection_id: str, *, qualification_evidence_ids: tuple[str, ...],
        assistance_ancestry: tuple[str, ...] = (),
    ) -> EpistemicProjectionRecord:
        """Return a stale opaque projection to operational currentness as a new epoch.

        Reactivation is only a currentness transition. The caller is responsible for
        external requalification and dependency checks; this registry never infers
        recurring-regime identity.
        """
        if projection_id not in self.records:
            raise ValueError("UNKNOWN_EPISTEMIC_PROJECTION")
        old = self.records[projection_id]
        if old.current:
            raise ValueError("CURRENT_EPISTEMIC_PROJECTION_CANNOT_REACTIVATE")
        qids = tuple(str(x) for x in qualification_evidence_ids)
        if not qids:
            raise ValueError("EPISTEMIC_PROJECTION_REACTIVATION_REQUIRES_REQUALIFICATION_EVIDENCE")
        rec = EpistemicProjectionRecord(
            projection_id=old.projection_id, signature_sha256=old.signature_sha256, epoch=old.epoch + 1,
            assistance_ancestry=tuple(old.assistance_ancestry) + tuple(str(x) for x in assistance_ancestry),
            projection_origin=old.projection_origin, proposal_candidate_sha256=old.proposal_candidate_sha256,
            qualification_evidence_ids=tuple(old.qualification_evidence_ids) + qids,
            frame_epochs=old.frame_epochs, episode_schema_epochs=old.episode_schema_epochs, current=True,
        )
        self.records[projection_id] = rec
        return rec

    def invalidate(self, projection_id: str) -> EpistemicProjectionRecord:
        if projection_id not in self.records:
            raise ValueError("UNKNOWN_EPISTEMIC_PROJECTION")
        old = self.records[projection_id]
        if not old.current:
            return old
        rec = EpistemicProjectionRecord(
            projection_id=old.projection_id, signature_sha256=old.signature_sha256, epoch=old.epoch + 1,
            assistance_ancestry=old.assistance_ancestry, projection_origin=old.projection_origin,
            proposal_candidate_sha256=old.proposal_candidate_sha256,
            qualification_evidence_ids=old.qualification_evidence_ids,
            frame_epochs=old.frame_epochs, episode_schema_epochs=old.episode_schema_epochs, current=False,
        )
        self.records[projection_id] = rec
        return rec

    def invalidate_dependency(self, kind: str, object_id: str) -> tuple[str, ...]:
        changed=[]
        k=str(kind).upper()
        for pid, rec in sorted(self.records.items()):
            if not rec.current:
                continue
            deps = rec.frame_epochs if k == "FRAME" else rec.episode_schema_epochs if k == "EPISODE" else ()
            if any(dep_id == str(object_id) for dep_id, _ in deps):
                self.invalidate(pid); changed.append(pid)
        return tuple(changed)

    def is_current(self, projection_id: str, epoch: int) -> bool:
        r = self.records.get(projection_id)
        return bool(r is not None and r.current and r.epoch == int(epoch))

    def snapshot(self) -> dict[str, dict[str, Any]]:
        return {k: v.serializable() for k, v in sorted(self.records.items())}


@dataclass(frozen=True)
class EpistemicContrastRow:
    """One opaque projection's candidate-prediction partition.

    Candidate handles and outcome digests are intentionally uninterpreted. An
    optional condition digest keeps action-conditioned contrasts distinct from
    passive surfaces without supplying semantic action identity.
    """

    projection_id: str
    projection_epoch: int
    candidate_outcome_digests: tuple[tuple[str, str], ...]
    condition_signature_sha256: str | None = None

    def __post_init__(self) -> None:
        if not self.projection_id:
            raise ValueError("EMPTY_EPISTEMIC_CONTRAST_PROJECTION")
        if int(self.projection_epoch) < 0:
            raise ValueError("NEGATIVE_EPISTEMIC_CONTRAST_PROJECTION_EPOCH")
        object.__setattr__(self, "projection_epoch", int(self.projection_epoch))
        rows = tuple((str(cid), _sha256_token(out, error="EPISTEMIC_OUTCOME_DIGEST_SHA256_REQUIRED"))
                     for cid, out in self.candidate_outcome_digests)
        if len(rows) < 2 or len({cid for cid, _ in rows}) != len(rows):
            raise ValueError("EPISTEMIC_CONTRAST_REQUIRES_DISTINCT_CANDIDATES")
        object.__setattr__(self, "candidate_outcome_digests", tuple(sorted(rows)))
        if self.condition_signature_sha256 is not None:
            object.__setattr__(
                self,
                "condition_signature_sha256",
                _sha256_token(
                    self.condition_signature_sha256,
                    error="EPISTEMIC_CONDITION_SIGNATURE_SHA256_REQUIRED",
                ),
            )

    def serializable(self) -> dict[str, Any]:
        return {
            "projection_id": self.projection_id,
            "projection_epoch": self.projection_epoch,
            "candidate_outcome_digests": [list(x) for x in self.candidate_outcome_digests],
            "condition_signature_sha256": self.condition_signature_sha256,
        }

    @classmethod
    def from_serializable(cls, d: dict[str, Any]) -> "EpistemicContrastRow":
        return cls(
            projection_id=str(d["projection_id"]),
            projection_epoch=int(d["projection_epoch"]),
            candidate_outcome_digests=tuple(tuple(x) for x in d["candidate_outcome_digests"]),
            condition_signature_sha256=d.get("condition_signature_sha256"),
        )


@dataclass
class EpistemicContrastBinding:
    """Content-bound opaque contrast for one exact deficit hypothesis digest."""

    binding_id: str
    deficit_id: str
    hypothesis_digest_sha256: str
    rows: tuple[EpistemicContrastRow, ...]
    binding_origin: str = "SUPPLIED_AND_PROVENANCED"
    assistance_ancestry: tuple[str, ...] = ()
    state: str = "CURRENT"
    stale_reason: str | None = None
    truth_authority: str = "NONE"
    semantic_question_authority: str = "NONE"
    raw_projection_discovery_authority: str = "NONE"

    def __post_init__(self) -> None:
        if not self.binding_id or not self.deficit_id:
            raise ValueError("EMPTY_EPISTEMIC_CONTRAST_BINDING")
        self.hypothesis_digest_sha256 = _sha256_token(
            self.hypothesis_digest_sha256, error="EPISTEMIC_HYPOTHESIS_DIGEST_SHA256_REQUIRED"
        )
        self.rows = tuple(self.rows)
        if not self.rows or len({r.projection_id for r in self.rows}) != len(self.rows):
            raise ValueError("EPISTEMIC_CONTRAST_ROWS_REQUIRED_AND_UNIQUE")
        if self.binding_origin not in {
            "SUPPLIED_AND_PROVENANCED",
            "EXTERNALLY_QUALIFIED_OPAQUE_CONTRAST",
        }:
            raise ValueError("EPISTEMIC_CONTRAST_BINDING_ORIGIN_UNQUALIFIED")
        self.assistance_ancestry = tuple(self.assistance_ancestry)
        if self.state not in {"CURRENT", "STALE"}:
            raise ValueError("INVALID_EPISTEMIC_CONTRAST_STATE")
        if self.state == "STALE" and not self.stale_reason:
            raise ValueError("STALE_EPISTEMIC_CONTRAST_REQUIRES_REASON")
        if (
            self.truth_authority != "NONE"
            or self.semantic_question_authority != "NONE"
            or self.raw_projection_discovery_authority != "NONE"
        ):
            raise ValueError("EPISTEMIC_CONTRAST_CANNOT_CARRY_TRUTH_SEMANTIC_OR_DISCOVERY_AUTHORITY")

    def signature_payload(self) -> dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "deficit_id": self.deficit_id,
            "hypothesis_digest_sha256": self.hypothesis_digest_sha256,
            "rows": [r.serializable() for r in self.rows],
            "binding_origin": self.binding_origin,
            "assistance_ancestry": list(self.assistance_ancestry),
            "truth_authority": self.truth_authority,
            "semantic_question_authority": self.semantic_question_authority,
            "raw_projection_discovery_authority": self.raw_projection_discovery_authority,
        }

    def computed_signature_sha256(self) -> str:
        import hashlib, json
        raw = json.dumps(
            self.signature_payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def serializable(self) -> dict[str, Any]:
        d = self.signature_payload()
        d.update({
            "state": self.state,
            "stale_reason": self.stale_reason,
            "signature_sha256": self.computed_signature_sha256(),
        })
        return d

    @classmethod
    def from_serializable(cls, d: dict[str, Any]) -> "EpistemicContrastBinding":
        return cls(
            binding_id=str(d["binding_id"]),
            deficit_id=str(d["deficit_id"]),
            hypothesis_digest_sha256=str(d["hypothesis_digest_sha256"]),
            rows=tuple(EpistemicContrastRow.from_serializable(x) for x in d["rows"]),
            binding_origin=str(d.get("binding_origin", "SUPPLIED_AND_PROVENANCED")),
            assistance_ancestry=tuple(d.get("assistance_ancestry", ())),
            state=str(d.get("state", "CURRENT")),
            stale_reason=d.get("stale_reason"),
            truth_authority=str(d.get("truth_authority", "NONE")),
            semantic_question_authority=str(d.get("semantic_question_authority", "NONE")),
            raw_projection_discovery_authority=str(d.get("raw_projection_discovery_authority", "NONE")),
        )


class EpistemicBearingKind(str, Enum):
    DISCRIMINATES_LIVE_SET = "DISCRIMINATES_LIVE_SET"
    MODEL_SPACE_CHALLENGE = "MODEL_SPACE_CHALLENGE"
    CONSENSUS_NONDISCRIMINATING = "CONSENSUS_NONDISCRIMINATING"
    UNBOUND_PROJECTION = "UNBOUND_PROJECTION"
    STALE_BINDING = "STALE_BINDING"
    CONDITION_MISMATCH = "CONDITION_MISMATCH"


@dataclass(frozen=True)
class EpistemicBearingWitness:
    """Derived proof that one evidence packet bears on one bounded contrast."""

    witness_id: str
    deficit_id: str
    binding_id: str
    binding_signature_sha256: str
    hypothesis_digest_sha256: str
    evidence_id: str
    evidence_sha256: str
    projection_id: str
    projection_epoch: int
    outcome_digest_sha256: str
    partition_digest_sha256: str
    kind: EpistemicBearingKind
    condition_signature_sha256: str | None = None
    bearing_authority: str = "BOUNDED_OPERATIONAL_BEARING_ONLY"
    truth_authority: str = "NONE"
    semantic_question_authority: str = "NONE"
    answer_authority: str = "NONE"

    def serializable(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        return d

    @classmethod
    def from_serializable(cls, d: dict[str, Any]) -> "EpistemicBearingWitness":
        x = dict(d)
        x["kind"] = EpistemicBearingKind(x["kind"])
        return cls(**x)


class EpistemicContrastRegistry:
    """Current opaque contrasts + historical bearing witnesses.

    This registry can verify bearing *inside* supplied operational coordinates.
    It cannot discover those coordinates, generate semantic questions, choose a
    scheduler priority, resolve a deficit, or invent replacement hypotheses.
    """

    def __init__(self, projections: EpistemicProjectionRegistry) -> None:
        self.projections = projections
        self.bindings: dict[str, EpistemicContrastBinding] = {}
        self.witnesses: dict[str, EpistemicBearingWitness] = {}
        self._seen: set[tuple[str, str, str]] = set()

    def register(self, binding: EpistemicContrastBinding) -> None:
        if binding.binding_id in self.bindings:
            raise ValueError("DUPLICATE_EPISTEMIC_CONTRAST_BINDING")
        for row in binding.rows:
            if not self.projections.is_current(row.projection_id, row.projection_epoch):
                raise ValueError(
                    f"EPISTEMIC_CONTRAST_PROJECTION_NOT_CURRENT:{row.projection_id}@{row.projection_epoch}"
                )
        self.bindings[binding.binding_id] = binding

    def mark_stale(self, binding_id: str, *, reason: str) -> EpistemicContrastBinding:
        if not reason:
            raise ValueError("STALE_EPISTEMIC_CONTRAST_REQUIRES_REASON")
        b = self.bindings[binding_id]
        if b.state != "STALE":
            b.state = "STALE"
            b.stale_reason = str(reason)
        return b

    def invalidate_projection(self, projection_id: str, new_epoch: int) -> tuple[str, ...]:
        changed=[]
        for bid,b in self.bindings.items():
            if b.state == "STALE":
                continue
            if any(r.projection_id == projection_id and r.projection_epoch != int(new_epoch) for r in b.rows):
                self.mark_stale(bid, reason=f"PROJECTION_DRIFT:{projection_id}@{int(new_epoch)}")
                changed.append(bid)
        return tuple(sorted(changed))

    def invalidate_deficit(self, deficit_id: str, *, reason: str) -> tuple[str, ...]:
        changed=[]
        for bid,b in self.bindings.items():
            if b.deficit_id == deficit_id and b.state != "STALE":
                self.mark_stale(bid, reason=f"DEFICIT_STALE:{reason}")
                changed.append(bid)
        return tuple(sorted(changed))

    def _row(self, binding: EpistemicContrastBinding, projection_id: str) -> EpistemicContrastRow | None:
        for row in binding.rows:
            if row.projection_id == projection_id:
                return row
        return None

    def assess(
        self,
        *,
        binding_id: str,
        current_hypothesis_digest_sha256: str,
        evidence_id: str,
        evidence_sha256: str,
        projection_id: str,
        projection_epoch: int,
        outcome_digest_sha256: str,
        condition_signature_sha256: str | None = None,
    ) -> tuple[EpistemicBearingKind, EpistemicBearingWitness | None, bool]:
        import hashlib, json

        b = self.bindings[binding_id]
        current_hyp = _sha256_token(
            current_hypothesis_digest_sha256,
            error="EPISTEMIC_HYPOTHESIS_DIGEST_SHA256_REQUIRED",
        )
        out = _sha256_token(outcome_digest_sha256, error="EPISTEMIC_OUTCOME_DIGEST_SHA256_REQUIRED")
        evsha = _sha256_token(evidence_sha256, error="EPISTEMIC_EVIDENCE_SHA256_REQUIRED")
        cond = None
        if condition_signature_sha256 is not None:
            cond = _sha256_token(
                condition_signature_sha256,
                error="EPISTEMIC_CONDITION_SIGNATURE_SHA256_REQUIRED",
            )
        if b.state != "CURRENT" or b.hypothesis_digest_sha256 != current_hyp:
            return EpistemicBearingKind.STALE_BINDING, None, False
        row = self._row(b, str(projection_id))
        if row is None:
            return EpistemicBearingKind.UNBOUND_PROJECTION, None, False
        if (
            row.projection_epoch != int(projection_epoch)
            or not self.projections.is_current(row.projection_id, row.projection_epoch)
        ):
            return EpistemicBearingKind.STALE_BINDING, None, False
        if row.condition_signature_sha256 != cond:
            return EpistemicBearingKind.CONDITION_MISMATCH, None, False

        predictions = dict(row.candidate_outcome_digests)
        unique = set(predictions.values())
        if out not in unique:
            kind = EpistemicBearingKind.MODEL_SPACE_CHALLENGE
        elif len(unique) > 1:
            kind = EpistemicBearingKind.DISCRIMINATES_LIVE_SET
        else:
            return EpistemicBearingKind.CONSENSUS_NONDISCRIMINATING, None, False

        partition: dict[str, list[str]] = {}
        for candidate_id, outcome in predictions.items():
            partition.setdefault(outcome, []).append(candidate_id)
        partition_payload = {k: sorted(v) for k, v in sorted(partition.items())}
        partition_sha = hashlib.sha256(
            json.dumps(partition_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        key=(binding_id,str(evidence_id),evsha)
        if key in self._seen:
            return kind, None, True
        witness_payload = {
            "binding_signature_sha256": b.computed_signature_sha256(),
            "evidence_sha256": evsha,
            "projection_id": row.projection_id,
            "projection_epoch": row.projection_epoch,
            "outcome_digest_sha256": out,
            "partition_digest_sha256": partition_sha,
            "kind": kind.value,
        }
        witness_id="bearing-"+hashlib.sha256(
            json.dumps(witness_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:24]
        w=EpistemicBearingWitness(
            witness_id=witness_id,
            deficit_id=b.deficit_id,
            binding_id=b.binding_id,
            binding_signature_sha256=b.computed_signature_sha256(),
            hypothesis_digest_sha256=b.hypothesis_digest_sha256,
            evidence_id=str(evidence_id),
            evidence_sha256=evsha,
            projection_id=row.projection_id,
            projection_epoch=row.projection_epoch,
            outcome_digest_sha256=out,
            partition_digest_sha256=partition_sha,
            kind=kind,
            condition_signature_sha256=cond,
        )
        self.witnesses[w.witness_id]=w
        self._seen.add(key)
        return kind,w,False

    def replay_witness(self, witness: EpistemicBearingWitness) -> None:
        if witness.witness_id not in self.witnesses:
            self.witnesses[witness.witness_id]=witness
            self._seen.add((witness.binding_id,witness.evidence_id,witness.evidence_sha256))

    def binding_status(self, binding_id: str) -> dict[str, Any]:
        return self.bindings[binding_id].serializable()

    def witnesses_for_deficit(self, deficit_id: str) -> tuple[EpistemicBearingWitness, ...]:
        return tuple(
            sorted(
                (w for w in self.witnesses.values() if w.deficit_id == deficit_id),
                key=lambda w: w.witness_id,
            )
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "bindings": {k: v.serializable() for k,v in sorted(self.bindings.items())},
            "witnesses": {k: v.serializable() for k,v in sorted(self.witnesses.items())},
        }
