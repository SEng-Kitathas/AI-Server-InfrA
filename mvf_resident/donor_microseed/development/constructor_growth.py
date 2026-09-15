from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from ..evidence.authority import FixedQualifier
from ..evidence.ledger import EvidenceLedger, canonical_json, sha256_bytes
from ..runtime.types import Authority, EvidenceRef, QualificationState


def _mode(counter: Counter[str]) -> str | None:
    if not counter:
        return None
    return sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


@dataclass(frozen=True, order=True)
class ConstructorAtom:
    """Opaque raw coordinate at one supplied temporal lag.

    lag=0 is current raw input; lag>0 is supplied ordered history. Lag identity
    is operational instrumentation, not semantic time ontology.
    """

    lag: int
    position: int

    def __post_init__(self) -> None:
        if int(self.lag) < 0 or int(self.position) < 0:
            raise ValueError("NEGATIVE_CONSTRUCTOR_ATOM")
        object.__setattr__(self, "lag", int(self.lag))
        object.__setattr__(self, "position", int(self.position))

    def token(self) -> str:
        return f"L{self.lag}:P{self.position}"


@dataclass(frozen=True)
class ConstructorProjectionSample:
    """Opaque interaction/history sample for bounded constructor-growth search.

    `raw_history[0]` is current raw input. Higher indices are supplied ordered
    trace/history slices. Temporal use requires explicit current EpisodeSchema
    ancestry so this type does not silently construct episode/time boundaries.
    """

    sample_id: str
    raw_history: tuple[tuple[str, ...], ...]
    action_token: str
    effect_token: str
    operational_scope_id: str | None
    frame_id: str
    frame_epoch: int
    episode_schema_id: str | None = None
    episode_schema_epoch: int | None = None

    def __post_init__(self) -> None:
        if not self.sample_id or not self.raw_history or not self.action_token or not self.effect_token:
            raise ValueError("INCOMPLETE_CONSTRUCTOR_PROJECTION_SAMPLE")
        history = tuple(tuple(str(y) for y in x) for x in self.raw_history)
        if not history or any(not x for x in history):
            raise ValueError("EMPTY_CONSTRUCTOR_HISTORY_SLICE")
        object.__setattr__(self, "raw_history", history)
        if not self.frame_id or int(self.frame_epoch) < 0:
            raise ValueError("CONSTRUCTOR_SAMPLE_REQUIRES_FRAME_CURRENTNESS")
        object.__setattr__(self, "frame_epoch", int(self.frame_epoch))
        if len(history) > 1:
            if not self.episode_schema_id or self.episode_schema_epoch is None or int(self.episode_schema_epoch) < 0:
                raise ValueError("TEMPORAL_CONSTRUCTOR_SAMPLE_REQUIRES_EPISODE_SCHEMA_CURRENTNESS")
            object.__setattr__(self, "episode_schema_epoch", int(self.episode_schema_epoch))
        elif self.episode_schema_epoch is not None:
            object.__setattr__(self, "episode_schema_epoch", int(self.episode_schema_epoch))

    def serializable(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "raw_history": [list(x) for x in self.raw_history],
            "action_token": self.action_token,
            "effect_token": self.effect_token,
            "operational_scope_id": self.operational_scope_id,
            "frame_id": self.frame_id,
            "frame_epoch": self.frame_epoch,
            "episode_schema_id": self.episode_schema_id,
            "episode_schema_epoch": self.episode_schema_epoch,
        }


@dataclass(frozen=True)
class ConstructorGrowthConfig:
    """Supplied ceilings for conflict-directed constructor proposal growth only."""

    max_support_ceiling: int = 4
    max_lag_ceiling: int = 2
    min_train_support: int = 100
    min_validation_accuracy: float = 0.90
    min_lift_over_action_baseline: float = 0.20
    min_scope_accuracy: float = 0.84
    complexity_penalty: float = 0.006
    max_conflict_edges: int = 5000
    node_budget: int = 20000
    max_candidates: int = 8

    def __post_init__(self) -> None:
        if not 1 <= int(self.max_support_ceiling) <= 6:
            raise ValueError("BOUNDED_CONSTRUCTOR_SUPPORT_CEILING_REQUIRED")
        if not 0 <= int(self.max_lag_ceiling) <= 4:
            raise ValueError("BOUNDED_CONSTRUCTOR_HISTORY_CEILING_REQUIRED")
        if int(self.min_train_support) < 1 or int(self.max_conflict_edges) < 1 or int(self.node_budget) < 1:
            raise ValueError("INVALID_CONSTRUCTOR_GROWTH_BOUNDS")
        if int(self.max_candidates) < 1:
            raise ValueError("INVALID_CONSTRUCTOR_MAX_CANDIDATES")

    def assistance_ancestry(self) -> tuple[str, ...]:
        return (
            "SUPPLIED_RAW_OBSERVATION_BOUNDARIES",
            "SUPPLIED_OPAQUE_ACTION_TOKENS",
            "SUPPLIED_OPAQUE_EFFECT_TOKENS",
            f"SUPPLIED_HISTORY_WINDOW_MAX_LAG_{int(self.max_lag_ceiling)}",
            f"SUPPLIED_SUPPORT_CEILING_{int(self.max_support_ceiling)}",
            "EFFECT_DISCORDANCE_CONFLICT_HYPERGRAPH",
            "MINIMAL_HITTING_SET_SUPPORT_GROWTH",
            "PREDICTIVE_EQUIVALENCE_COMPRESSION",
            "FIXED_NOMINATION_THRESHOLDS",
        )


@dataclass(frozen=True)
class ConstructorSearchDiagnostic:
    lag_depth: int
    atom_count: int
    raw_conflict_edge_count: int
    minimal_conflict_edge_count: int
    empty_conflict_pairs: int
    search_nodes: int
    budget_exhausted: bool
    support_solutions: int
    stage: str

    def serializable(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProjectionConstructorCandidate:
    candidate_id: str
    atoms: tuple[ConstructorAtom, ...]
    key_to_bucket: tuple[tuple[tuple[str, ...], str], ...]
    bucket_action_prediction: tuple[tuple[str, str, str], ...]
    train_accuracy: float
    validation_accuracy: float
    action_baseline_accuracy: float
    min_scope_accuracy: float
    lift: float
    score: float
    source_sample_ids: tuple[str, ...]
    frame_epochs: tuple[tuple[str, int], ...]
    episode_schema_epochs: tuple[tuple[str, int], ...]
    search_trace: tuple[ConstructorSearchDiagnostic, ...]
    assistance_ancestry: tuple[str, ...]
    nomination_basis: str = "CONFLICT_DIRECTED_PREDICTIVE_CONSTRUCTOR_GROWTH"
    proposal_authority: str = "NONE"
    qualification_authority: str = "NONE"
    semantic_projection_authority: str = "NONE"
    truth_authority: str = "NONE"

    def __post_init__(self) -> None:
        if not self.candidate_id or not self.atoms or not self.key_to_bucket or not self.bucket_action_prediction:
            raise ValueError("INCOMPLETE_PROJECTION_CONSTRUCTOR_CANDIDATE")
        if len(set(self.atoms)) != len(self.atoms):
            raise ValueError("DUPLICATE_PROJECTION_CONSTRUCTOR_ATOM")
        if self.proposal_authority != "NONE" or self.qualification_authority != "NONE":
            raise ValueError("CONSTRUCTOR_CANDIDATE_CANNOT_SELF_QUALIFY")
        if self.semantic_projection_authority != "NONE" or self.truth_authority != "NONE":
            raise ValueError("CONSTRUCTOR_CANDIDATE_CANNOT_CARRY_SEMANTIC_OR_TRUTH_AUTHORITY")
        object.__setattr__(self, "atoms", tuple(sorted(self.atoms)))
        object.__setattr__(self, "source_sample_ids", tuple(str(x) for x in self.source_sample_ids))
        object.__setattr__(self, "frame_epochs", tuple((str(a), int(b)) for a, b in self.frame_epochs))
        object.__setattr__(self, "episode_schema_epochs", tuple((str(a), int(b)) for a, b in self.episode_schema_epochs))
        object.__setattr__(self, "search_trace", tuple(self.search_trace))
        object.__setattr__(self, "assistance_ancestry", tuple(str(x) for x in self.assistance_ancestry))

    @property
    def lag_depth_used(self) -> int:
        return max(a.lag for a in self.atoms)

    def signature_payload(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "atoms": [[a.lag, a.position] for a in self.atoms],
            "key_to_bucket": [[list(k), v] for k, v in self.key_to_bucket],
            "bucket_action_prediction": [list(x) for x in self.bucket_action_prediction],
            "train_accuracy": self.train_accuracy,
            "validation_accuracy": self.validation_accuracy,
            "action_baseline_accuracy": self.action_baseline_accuracy,
            "min_scope_accuracy": self.min_scope_accuracy,
            "lift": self.lift,
            "score": self.score,
            "source_sample_ids": list(self.source_sample_ids),
            "frame_epochs": [list(x) for x in self.frame_epochs],
            "episode_schema_epochs": [list(x) for x in self.episode_schema_epochs],
            "search_trace": [x.serializable() for x in self.search_trace],
            "assistance_ancestry": list(self.assistance_ancestry),
            "nomination_basis": self.nomination_basis,
            "proposal_authority": self.proposal_authority,
            "qualification_authority": self.qualification_authority,
            "semantic_projection_authority": self.semantic_projection_authority,
            "truth_authority": self.truth_authority,
        }

    def digest(self) -> str:
        return sha256_bytes(canonical_json(self.signature_payload()))

    def serializable(self) -> dict[str, Any]:
        d = self.signature_payload()
        d["candidate_sha256"] = self.digest()
        return d

    @classmethod
    def from_serializable(cls, d: dict[str, Any]) -> "ProjectionConstructorCandidate":
        return cls(
            candidate_id=str(d["candidate_id"]),
            atoms=tuple(ConstructorAtom(int(x[0]), int(x[1])) for x in d["atoms"]),
            key_to_bucket=tuple((tuple(str(y) for y in k), str(v)) for k, v in d["key_to_bucket"]),
            bucket_action_prediction=tuple(tuple(str(y) for y in x) for x in d["bucket_action_prediction"]),
            train_accuracy=float(d["train_accuracy"]),
            validation_accuracy=float(d["validation_accuracy"]),
            action_baseline_accuracy=float(d["action_baseline_accuracy"]),
            min_scope_accuracy=float(d["min_scope_accuracy"]),
            lift=float(d["lift"]),
            score=float(d["score"]),
            source_sample_ids=tuple(str(x) for x in d["source_sample_ids"]),
            frame_epochs=tuple((str(x[0]), int(x[1])) for x in d.get("frame_epochs", ())),
            episode_schema_epochs=tuple((str(x[0]), int(x[1])) for x in d.get("episode_schema_epochs", ())),
            search_trace=tuple(ConstructorSearchDiagnostic(**x) for x in d.get("search_trace", ())),
            assistance_ancestry=tuple(str(x) for x in d.get("assistance_ancestry", ())),
            nomination_basis=str(d.get("nomination_basis", "CONFLICT_DIRECTED_PREDICTIVE_CONSTRUCTOR_GROWTH")),
            proposal_authority=str(d.get("proposal_authority", "NONE")),
            qualification_authority=str(d.get("qualification_authority", "NONE")),
            semantic_projection_authority=str(d.get("semantic_projection_authority", "NONE")),
            truth_authority=str(d.get("truth_authority", "NONE")),
        )

    def project(self, raw_history: Iterable[Iterable[str]]) -> str | None:
        hist = tuple(tuple(str(y) for y in x) for x in raw_history)
        key: list[str] = []
        for atom in self.atoms:
            if atom.lag >= len(hist) or atom.position >= len(hist[atom.lag]):
                return None
            key.append(hist[atom.lag][atom.position])
        return dict(self.key_to_bucket).get(tuple(key))


@dataclass(frozen=True)
class ConstructorQualificationTicket:
    candidate_id: str
    candidate_sha256: str
    state: QualificationState
    qualifier_id: str
    reason: str
    qualification_evidence: tuple[EvidenceRef, ...]


class ExternalConstructorQualifier:
    """Harness-side constructor qualifier; never part of Microseed cognition."""

    def __init__(self, ledger: EvidenceLedger, *, qualifier_id: str = "HSP-EXTERNAL-CONSTRUCTOR-QUALIFIER"):
        if not qualifier_id or qualifier_id.upper().startswith("MICROSEED"):
            raise ValueError("qualifier_id must identify an external qualification boundary")
        self.ledger = ledger
        self.qualifier_id = qualifier_id

    def qualify(
        self,
        candidate: ProjectionConstructorCandidate,
        *,
        qualification_evidence: Iterable[EvidenceRef],
    ) -> ConstructorQualificationTicket:
        refs = tuple(qualification_evidence)
        decision = FixedQualifier(self.ledger).decide(refs, Authority.REFERENCE_ONLY)
        return ConstructorQualificationTicket(
            candidate.candidate_id,
            candidate.digest(),
            decision.state,
            self.qualifier_id,
            decision.reason,
            refs,
        )


def validate_external_constructor_ticket(
    candidate: ProjectionConstructorCandidate,
    ticket: ConstructorQualificationTicket,
    ledger: EvidenceLedger,
) -> tuple[bool, str]:
    if not ticket.qualifier_id or ticket.qualifier_id.upper().startswith("MICROSEED"):
        return False, "QUALIFIER_NOT_EXTERNAL"
    if ticket.candidate_id != candidate.candidate_id:
        return False, "CANDIDATE_ID_MISMATCH"
    if ticket.candidate_sha256 != candidate.digest():
        return False, "CANDIDATE_DIGEST_MISMATCH"
    if not ticket.qualification_evidence:
        return False, "NO_QUALIFICATION_EVIDENCE"
    decision = FixedQualifier(ledger).decide(ticket.qualification_evidence, Authority.REFERENCE_ONLY)
    if ticket.state != decision.state or ticket.reason != decision.reason:
        return False, "QUALIFICATION_DECISION_MISMATCH"
    if ticket.state not in {QualificationState.SHADOW_QUALIFIED, QualificationState.QUALIFIED}:
        return False, f"NOT_ADMISSIBLE:{ticket.state.value}"
    return True, "VALID_EXTERNAL_CONSTRUCTOR_QUALIFICATION"


def _action_baseline(train: tuple[ConstructorProjectionSample, ...], validation: tuple[ConstructorProjectionSample, ...]) -> float:
    table: dict[str, Counter[str]] = defaultdict(Counter)
    for row in train:
        table[row.action_token][row.effect_token] += 1
    return sum(_mode(table[row.action_token]) == row.effect_token for row in validation) / max(len(validation), 1)


def _available_atoms(samples: tuple[ConstructorProjectionSample, ...], lag_depth: int) -> tuple[ConstructorAtom, ...]:
    max_lag = min(int(lag_depth), min(len(x.raw_history) - 1 for x in samples))
    dims: list[int] = []
    for lag in range(max_lag + 1):
        ds = {len(x.raw_history[lag]) for x in samples}
        if len(ds) != 1:
            return ()
        dims.append(next(iter(ds)))
    return tuple(ConstructorAtom(lag, pos) for lag, dim in enumerate(dims) for pos in range(dim))


def _modal_states(samples: tuple[ConstructorProjectionSample, ...], atoms: tuple[ConstructorAtom, ...]):
    counters: dict[tuple[str, tuple[str, ...]], Counter[str]] = defaultdict(Counter)
    for row in samples:
        state = tuple(row.raw_history[a.lag][a.position] for a in atoms)
        counters[(row.action_token, state)][row.effect_token] += 1
    return tuple((action, state, _mode(cnt)) for (action, state), cnt in sorted(counters.items()))


def _conflict_hypergraph(samples: tuple[ConstructorProjectionSample, ...], atoms: tuple[ConstructorAtom, ...], max_edges: int):
    states = _modal_states(samples, atoms)
    by: dict[str, dict[str, list[tuple[str, ...]]]] = defaultdict(lambda: defaultdict(list))
    for action, state, effect in states:
        if effect is not None:
            by[action][effect].append(state)
    edges: set[frozenset[int]] = set()
    empty = 0
    stop = False
    for action, groups in sorted(by.items()):
        effects = sorted(groups)
        for i in range(len(effects)):
            for j in range(i + 1, len(effects)):
                for left in groups[effects[i]]:
                    for right in groups[effects[j]]:
                        diff = frozenset(k for k, (x, y) in enumerate(zip(left, right)) if x != y)
                        if diff:
                            edges.add(diff)
                        else:
                            empty += 1
                        if len(edges) >= int(max_edges):
                            stop = True
                            break
                    if stop:
                        break
                if stop:
                    break
            if stop:
                break
        if stop:
            break
    raw_count = len(edges)
    minimal: list[frozenset[int]] = []
    for edge in sorted(edges, key=lambda x: (len(x), tuple(sorted(x)))):
        if not any(existing <= edge for existing in minimal):
            minimal.append(edge)
    return tuple(minimal), raw_count, empty


def _minimal_hitting_sets(edges: tuple[frozenset[int], ...], max_support: int, node_budget: int):
    solutions: set[tuple[int, ...]] = set()
    nodes = 0
    exhausted = False

    def rec(selected: tuple[int, ...], remaining: tuple[frozenset[int], ...]) -> None:
        nonlocal nodes, exhausted
        nodes += 1
        if nodes > int(node_budget):
            exhausted = True
            return
        if not remaining:
            solutions.add(tuple(sorted(selected)))
            return
        if len(selected) >= int(max_support):
            return
        edge = min(remaining, key=len)
        coverage: Counter[int] = Counter()
        for e in remaining:
            for atom in e:
                coverage[atom] += 1
        for atom in sorted(edge, key=lambda x: (-coverage[x], x)):
            nxt = selected + (atom,)
            if any(set(s).issubset(nxt) for s in solutions):
                continue
            rec(nxt, tuple(e for e in remaining if atom not in e))

    rec((), tuple(edges))
    minimal: list[tuple[int, ...]] = []
    for solution in sorted(solutions, key=lambda x: (len(x), x)):
        ss = set(solution)
        if not any(set(existing) <= ss for existing in minimal):
            minimal.append(solution)
    return tuple(minimal), nodes, exhausted


def _ancestry(samples: tuple[ConstructorProjectionSample, ...]):
    frames: dict[str, set[int]] = defaultdict(set)
    episodes: dict[str, set[int]] = defaultdict(set)
    for row in samples:
        frames[row.frame_id].add(int(row.frame_epoch))
        if row.episode_schema_id is not None:
            episodes[row.episode_schema_id].add(int(row.episode_schema_epoch))
    if any(len(x) != 1 for x in frames.values()) or any(len(x) != 1 for x in episodes.values()):
        return None
    return (
        tuple((k, next(iter(v))) for k, v in sorted(frames.items())),
        tuple((k, next(iter(v))) for k, v in sorted(episodes.items())),
    )


def _fit_candidate(
    train: tuple[ConstructorProjectionSample, ...],
    validation: tuple[ConstructorProjectionSample, ...],
    atoms: tuple[ConstructorAtom, ...],
    cfg: ConstructorGrowthConfig,
    *,
    search_nodes: int,
    trace: tuple[ConstructorSearchDiagnostic, ...],
) -> ProjectionConstructorCandidate | None:
    if len(train) < int(cfg.min_train_support):
        return None
    ancestry = _ancestry(train + validation)
    if ancestry is None:
        return None
    frame_epochs, episode_epochs = ancestry
    actions = sorted({x.action_token for x in train})
    table: dict[tuple[tuple[str, ...], str], Counter[str]] = defaultdict(Counter)
    keys: set[tuple[str, ...]] = set()
    for row in train:
        try:
            key = tuple(row.raw_history[a.lag][a.position] for a in atoms)
        except IndexError:
            return None
        keys.add(key)
        table[(key, row.action_token)][row.effect_token] += 1
    key_signature: dict[tuple[str, ...], tuple[tuple[str, str], ...]] = {}
    for key in sorted(keys):
        key_signature[key] = tuple((action, str(_mode(table[(key, action)]) or "UNKNOWN")) for action in actions)
    signature_bucket = {
        sig: "bucket-" + hashlib.sha256(canonical_json(sig)).hexdigest()[:16]
        for sig in sorted(set(key_signature.values()))
    }
    key_to_bucket = {key: signature_bucket[sig] for key, sig in key_signature.items()}
    prediction = {(bucket, action): effect for sig, bucket in signature_bucket.items() for action, effect in sig}

    def accuracy(rows: tuple[ConstructorProjectionSample, ...]) -> tuple[float, float]:
        good = 0
        by_scope: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for row in rows:
            try:
                key = tuple(row.raw_history[a.lag][a.position] for a in atoms)
            except IndexError:
                continue
            bucket = key_to_bucket.get(key)
            pred = prediction.get((bucket, row.action_token), "UNKNOWN") if bucket else "UNKNOWN"
            hit = pred == row.effect_token
            good += hit
            scope = row.operational_scope_id or "__GLOBAL__"
            by_scope[scope][0] += int(hit)
            by_scope[scope][1] += 1
        return good / max(len(rows), 1), min((g / max(n, 1) for g, n in by_scope.values()), default=0.0)

    train_accuracy, _ = accuracy(train)
    validation_accuracy, min_scope_accuracy = accuracy(validation)
    baseline = _action_baseline(train, validation)
    lift = validation_accuracy - baseline
    score = lift - cfg.complexity_penalty * (len(atoms) - 1) - cfg.complexity_penalty * math.log2(max(len(signature_bucket), 1))
    if (
        validation_accuracy < cfg.min_validation_accuracy
        or lift < cfg.min_lift_over_action_baseline
        or min_scope_accuracy < cfg.min_scope_accuracy
    ):
        return None
    mapping = tuple(sorted(key_to_bucket.items()))
    bap = tuple(sorted((b, a, e) for (b, a), e in prediction.items()))
    payload = {
        "atoms": [[a.lag, a.position] for a in atoms],
        "key_to_bucket": [[list(k), v] for k, v in mapping],
        "bucket_action_prediction": [list(x) for x in bap],
        "frame_epochs": [list(x) for x in frame_epochs],
        "episode_schema_epochs": [list(x) for x in episode_epochs],
    }
    cid = "constructor-cand-" + hashlib.sha256(canonical_json(payload)).hexdigest()[:20]
    return ProjectionConstructorCandidate(
        candidate_id=cid,
        atoms=atoms,
        key_to_bucket=mapping,
        bucket_action_prediction=bap,
        train_accuracy=train_accuracy,
        validation_accuracy=validation_accuracy,
        action_baseline_accuracy=baseline,
        min_scope_accuracy=min_scope_accuracy,
        lift=lift,
        score=score,
        source_sample_ids=tuple(sorted(x.sample_id for x in train)),
        frame_epochs=frame_epochs,
        episode_schema_epochs=episode_epochs,
        search_trace=trace,
        assistance_ancestry=cfg.assistance_ancestry(),
    )


def _search_once(
    search_rows: tuple[ConstructorProjectionSample, ...],
    fit_rows: tuple[ConstructorProjectionSample, ...],
    check_rows: tuple[ConstructorProjectionSample, ...],
    cfg: ConstructorGrowthConfig,
    lag_depth: int,
    stage: str,
    prior_trace: tuple[ConstructorSearchDiagnostic, ...],
):
    atoms = _available_atoms(search_rows + fit_rows + check_rows, lag_depth)
    if not atoms:
        diag = ConstructorSearchDiagnostic(lag_depth, 0, 0, 0, 0, 0, False, 0, stage)
        return (), diag
    edges, raw_edges, empty = _conflict_hypergraph(search_rows, atoms, cfg.max_conflict_edges)
    if empty:
        diag = ConstructorSearchDiagnostic(lag_depth, len(atoms), raw_edges, len(edges), empty, 0, False, 0, stage)
        return (), diag
    supports, nodes, exhausted = _minimal_hitting_sets(edges, cfg.max_support_ceiling, cfg.node_budget)
    diag = ConstructorSearchDiagnostic(lag_depth, len(atoms), raw_edges, len(edges), empty, nodes, exhausted, len(supports), stage)
    trace = prior_trace + (diag,)
    out: list[ProjectionConstructorCandidate] = []
    for support in supports:
        selected = tuple(atoms[i] for i in support)
        candidate = _fit_candidate(fit_rows, check_rows, selected, cfg, search_nodes=nodes, trace=trace)
        if candidate is not None:
            out.append(candidate)
    out.sort(key=lambda x: (-x.score, len(x.atoms), x.lag_depth_used, -x.validation_accuracy, x.atoms))
    return tuple(out), diag


def discover_projection_constructor_candidates(
    training_samples: Iterable[ConstructorProjectionSample],
    pressure_samples: Iterable[ConstructorProjectionSample],
    validation_samples: Iterable[ConstructorProjectionSample],
    cfg: ConstructorGrowthConfig | None = None,
) -> list[ProjectionConstructorCandidate]:
    """Grow/select bounded support and lag depth from opaque conflicts.

    Search is proposal-only. It starts at present-state lag 0 and grows lag depth
    only when the current grammar yields no nomination-valid support. A separate
    pressure split can falsify a deceptively minimal construction support before
    untouched nomination validation. All ceilings remain supplied assistance.
    """

    cfg = cfg or ConstructorGrowthConfig()
    train = tuple(training_samples)
    pressure = tuple(pressure_samples)
    validation = tuple(validation_samples)
    if not train or not pressure or not validation:
        return []
    combined = train + pressure + validation
    if any(len(x.raw_history) <= cfg.max_lag_ceiling for x in combined):
        # Ceiling may exceed available history only if all samples simply have a
        # shorter common history; search will naturally stop at available depth.
        pass
    trace: tuple[ConstructorSearchDiagnostic, ...] = ()
    for lag in range(int(cfg.max_lag_ceiling) + 1):
        first, diag = _search_once(train, train, pressure, cfg, lag, "CONSTRUCTION_TO_PRESSURE", trace)
        trace = trace + (diag,)
        if first:
            survivors: list[ProjectionConstructorCandidate] = []
            for c0 in first:
                c = _fit_candidate(train + pressure, validation, c0.atoms, cfg, search_nodes=c0.search_trace[-1].search_nodes, trace=trace)
                if c is not None:
                    survivors.append(c)
            if survivors:
                survivors.sort(key=lambda x: (-x.score, len(x.atoms), x.lag_depth_used, -x.validation_accuracy, x.atoms))
                return survivors[: int(cfg.max_candidates)]
        refined, diag2 = _search_once(train + pressure, train + pressure, validation, cfg, lag, "COUNTEREXAMPLE_REFINED", trace)
        trace = trace + (diag2,)
        if refined:
            return list(refined[: int(cfg.max_candidates)])
    return []
