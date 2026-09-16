from __future__ import annotations

import hashlib
import itertools
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from ..evidence.authority import FixedQualifier
from ..evidence.ledger import EvidenceLedger, canonical_json, sha256_bytes
from ..runtime.types import Authority, EvidenceRef, QualificationState
from .constructor_growth import ConstructorAtom, ConstructorProjectionSample


def _mode(counter: Counter[str]) -> str | None:
    if not counter:
        return None
    return sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


@dataclass(frozen=True)
class RobustConstructorGrowthConfig:
    """Supplied ceilings for bounded robust constructor proposal search.

    Discordance observations stay exact. Robustness comes only from no longer
    requiring one support to explain every observed conflict; support candidates
    are ranked by exact conflict coverage then must survive separate predictive
    pressure/validation. This is not a supplied effect-distance or noise-rate model.
    """

    max_support_ceiling: int = 4
    max_lag_ceiling: int = 0
    top_supports_per_order: int = 16
    min_train_support: int = 100
    min_validation_accuracy: float = 0.90
    min_lift_over_action_baseline: float = 0.25
    min_scope_accuracy: float = 0.85
    max_conflict_edges: int = 5000
    combination_budget: int = 50000
    max_candidates: int = 8

    def __post_init__(self) -> None:
        if not 1 <= int(self.max_support_ceiling) <= 6:
            raise ValueError("BOUNDED_ROBUST_SUPPORT_CEILING_REQUIRED")
        if not 0 <= int(self.max_lag_ceiling) <= 4:
            raise ValueError("BOUNDED_ROBUST_HISTORY_CEILING_REQUIRED")
        if int(self.top_supports_per_order) < 1 or int(self.max_conflict_edges) < 1 or int(self.combination_budget) < 1:
            raise ValueError("INVALID_ROBUST_CONSTRUCTOR_BOUNDS")
        if int(self.min_train_support) < 1 or int(self.max_candidates) < 1:
            raise ValueError("INVALID_ROBUST_CONSTRUCTOR_SUPPORT")

    def assistance_ancestry(self) -> tuple[str, ...]:
        return (
            "SUPPLIED_RAW_OBSERVATION_BOUNDARIES",
            "SUPPLIED_OPAQUE_ACTION_TOKENS",
            "SUPPLIED_OPAQUE_EFFECT_TOKENS",
            f"SUPPLIED_HISTORY_WINDOW_MAX_LAG_{int(self.max_lag_ceiling)}",
            f"SUPPLIED_SUPPORT_CEILING_{int(self.max_support_ceiling)}",
            f"SUPPLIED_TOP_SUPPORTS_PER_ORDER_{int(self.top_supports_per_order)}",
            "EXACT_OBSERVED_EFFECT_DISCORDANCE_EDGES",
            "BOUNDED_CONFLICT_COVERAGE_RANKING",
            "SMALLEST_PREDICTIVELY_VALIDATED_SUPPORT_ORDER",
            "UNTOUCHED_PRESSURE_AND_NOMINATION_VALIDATION",
            "NO_EFFECT_DISTANCE_METRIC",
            "NO_NOISE_RATE_MODEL",
        )


@dataclass(frozen=True)
class RobustConstructorSearchDiagnostic:
    lag_depth: int
    support_order: int
    atom_count: int
    conflict_edge_count: int
    combinations_evaluated: int
    budget_exhausted: bool
    top_coverage: float
    candidates_survived: int

    def serializable(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RobustProjectionConstructorCandidate:
    candidate_id: str
    atoms: tuple[ConstructorAtom, ...]
    key_to_bucket: tuple[tuple[tuple[str, ...], str], ...]
    bucket_action_prediction: tuple[tuple[str, str, str], ...]
    train_accuracy: float
    pressure_accuracy: float
    validation_accuracy: float
    action_baseline_accuracy: float
    min_scope_accuracy: float
    lift: float
    observed_conflict_coverage: float
    evaluated_support_count: int
    source_sample_ids: tuple[str, ...]
    frame_epochs: tuple[tuple[str, int], ...]
    episode_schema_epochs: tuple[tuple[str, int], ...]
    search_trace: tuple[RobustConstructorSearchDiagnostic, ...]
    assistance_ancestry: tuple[str, ...]
    nomination_basis: str = "ROBUST_CONFLICT_COVERAGE_PREDICTIVE_CONSTRUCTOR_GROWTH"
    proposal_authority: str = "NONE"
    qualification_authority: str = "NONE"
    semantic_projection_authority: str = "NONE"
    truth_authority: str = "NONE"

    def __post_init__(self) -> None:
        if not self.candidate_id or not self.atoms or not self.key_to_bucket or not self.bucket_action_prediction:
            raise ValueError("INCOMPLETE_ROBUST_CONSTRUCTOR_CANDIDATE")
        if self.proposal_authority != "NONE" or self.qualification_authority != "NONE":
            raise ValueError("ROBUST_CONSTRUCTOR_CANDIDATE_CANNOT_SELF_QUALIFY")
        if self.semantic_projection_authority != "NONE" or self.truth_authority != "NONE":
            raise ValueError("ROBUST_CONSTRUCTOR_CANDIDATE_CANNOT_CARRY_SEMANTIC_OR_TRUTH_AUTHORITY")
        object.__setattr__(self, "atoms", tuple(sorted(self.atoms)))
        object.__setattr__(self, "source_sample_ids", tuple(str(x) for x in self.source_sample_ids))
        object.__setattr__(self, "frame_epochs", tuple((str(a), int(b)) for a,b in self.frame_epochs))
        object.__setattr__(self, "episode_schema_epochs", tuple((str(a), int(b)) for a,b in self.episode_schema_epochs))
        object.__setattr__(self, "search_trace", tuple(self.search_trace))
        object.__setattr__(self, "assistance_ancestry", tuple(str(x) for x in self.assistance_ancestry))

    @property
    def lag_depth_used(self) -> int:
        return max(a.lag for a in self.atoms)

    def signature_payload(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "atoms": [[a.lag,a.position] for a in self.atoms],
            "key_to_bucket": [[list(k),v] for k,v in self.key_to_bucket],
            "bucket_action_prediction": [list(x) for x in self.bucket_action_prediction],
            "train_accuracy": self.train_accuracy,
            "pressure_accuracy": self.pressure_accuracy,
            "validation_accuracy": self.validation_accuracy,
            "action_baseline_accuracy": self.action_baseline_accuracy,
            "min_scope_accuracy": self.min_scope_accuracy,
            "lift": self.lift,
            "observed_conflict_coverage": self.observed_conflict_coverage,
            "evaluated_support_count": self.evaluated_support_count,
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
        d=self.signature_payload(); d["candidate_sha256"]=self.digest(); return d

    @classmethod
    def from_serializable(cls,d:dict[str,Any]) -> "RobustProjectionConstructorCandidate":
        return cls(
            candidate_id=str(d["candidate_id"]),
            atoms=tuple(ConstructorAtom(int(x[0]),int(x[1])) for x in d["atoms"]),
            key_to_bucket=tuple((tuple(str(y) for y in k),str(v)) for k,v in d["key_to_bucket"]),
            bucket_action_prediction=tuple(tuple(str(y) for y in x) for x in d["bucket_action_prediction"]),
            train_accuracy=float(d["train_accuracy"]),pressure_accuracy=float(d["pressure_accuracy"]),validation_accuracy=float(d["validation_accuracy"]),
            action_baseline_accuracy=float(d["action_baseline_accuracy"]),min_scope_accuracy=float(d["min_scope_accuracy"]),lift=float(d["lift"]),
            observed_conflict_coverage=float(d["observed_conflict_coverage"]),evaluated_support_count=int(d["evaluated_support_count"]),
            source_sample_ids=tuple(str(x) for x in d["source_sample_ids"]),
            frame_epochs=tuple((str(a),int(b)) for a,b in d.get("frame_epochs",())),
            episode_schema_epochs=tuple((str(a),int(b)) for a,b in d.get("episode_schema_epochs",())),
            search_trace=tuple(RobustConstructorSearchDiagnostic(**x) for x in d.get("search_trace",())),
            assistance_ancestry=tuple(str(x) for x in d.get("assistance_ancestry",())),
            nomination_basis=str(d.get("nomination_basis","ROBUST_CONFLICT_COVERAGE_PREDICTIVE_CONSTRUCTOR_GROWTH")),
            proposal_authority=str(d.get("proposal_authority","NONE")),qualification_authority=str(d.get("qualification_authority","NONE")),
            semantic_projection_authority=str(d.get("semantic_projection_authority","NONE")),truth_authority=str(d.get("truth_authority","NONE")),
        )

    def project(self, raw_history: Iterable[Iterable[str]]) -> str | None:
        hist=tuple(tuple(str(y) for y in x) for x in raw_history)
        try:key=tuple(hist[a.lag][a.position] for a in self.atoms)
        except IndexError:return None
        return dict(self.key_to_bucket).get(key)


@dataclass(frozen=True)
class RobustConstructorQualificationTicket:
    candidate_id: str
    candidate_sha256: str
    state: QualificationState
    qualifier_id: str
    reason: str
    qualification_evidence: tuple[EvidenceRef, ...]


class ExternalRobustConstructorQualifier:
    """Harness-side qualifier. Robust proposal evidence cannot self-promote."""
    def __init__(self, ledger: EvidenceLedger, *, qualifier_id: str="HSP-EXTERNAL-ROBUST-CONSTRUCTOR-QUALIFIER"):
        if not qualifier_id or qualifier_id.upper().startswith("MICROSEED"):
            raise ValueError("qualifier_id must identify an external qualification boundary")
        self.ledger=ledger; self.qualifier_id=qualifier_id

    def qualify(self,candidate:RobustProjectionConstructorCandidate,*,qualification_evidence:Iterable[EvidenceRef]) -> RobustConstructorQualificationTicket:
        refs=tuple(qualification_evidence); decision=FixedQualifier(self.ledger).decide(refs,Authority.REFERENCE_ONLY)
        return RobustConstructorQualificationTicket(candidate.candidate_id,candidate.digest(),decision.state,self.qualifier_id,decision.reason,refs)


def validate_external_robust_constructor_ticket(candidate:RobustProjectionConstructorCandidate,ticket:RobustConstructorQualificationTicket,ledger:EvidenceLedger)->tuple[bool,str]:
    if not ticket.qualifier_id or ticket.qualifier_id.upper().startswith("MICROSEED"): return False,"QUALIFIER_NOT_EXTERNAL"
    if ticket.candidate_id!=candidate.candidate_id:return False,"CANDIDATE_ID_MISMATCH"
    if ticket.candidate_sha256!=candidate.digest():return False,"CANDIDATE_DIGEST_MISMATCH"
    if not ticket.qualification_evidence:return False,"NO_QUALIFICATION_EVIDENCE"
    decision=FixedQualifier(ledger).decide(ticket.qualification_evidence,Authority.REFERENCE_ONLY)
    if ticket.state!=decision.state or ticket.reason!=decision.reason:return False,"QUALIFICATION_DECISION_MISMATCH"
    if ticket.state not in {QualificationState.SHADOW_QUALIFIED,QualificationState.QUALIFIED}:return False,f"NOT_ADMISSIBLE:{ticket.state.value}"
    return True,"VALID_EXTERNAL_ROBUST_CONSTRUCTOR_QUALIFICATION"


@dataclass(frozen=True)
class ProjectionPredictiveCurrentnessConfig:
    window_size: int = 256
    min_window_accuracy: float = 0.82
    consecutive_failure_windows: int = 2
    def __post_init__(self)->None:
        if int(self.window_size)<8 or not 0.0<=float(self.min_window_accuracy)<=1.0 or int(self.consecutive_failure_windows)<1:
            raise ValueError("INVALID_PREDICTIVE_CURRENTNESS_BOUNDS")
    def assistance_ancestry(self)->tuple[str,...]:
        return (
            f"SUPPLIED_CURRENTNESS_WINDOW_SIZE_{int(self.window_size)}",
            f"SUPPLIED_MIN_WINDOW_ACCURACY_{float(self.min_window_accuracy):.6f}",
            f"SUPPLIED_CONSECUTIVE_FAILURE_WINDOWS_{int(self.consecutive_failure_windows)}",
            "PREDICTIVE_FAILURE_IS_CURRENTNESS_EVIDENCE_NOT_CAUSE_IDENTITY",
        )


@dataclass(frozen=True)
class ProjectionPredictiveCurrentnessWitness:
    projection_id: str
    projection_epoch: int
    status: str
    window_accuracies: tuple[float,...]
    first_failure_window: int|None
    drift_window: int|None
    assistance_ancestry: tuple[str,...]
    truth_authority: str="NONE"
    regime_identity_authority: str="NONE"
    drift_cause_authority: str="NONE"
    def serializable(self)->dict[str,Any]: return asdict(self)


def _available_atoms(samples:tuple[ConstructorProjectionSample,...],lag_depth:int)->tuple[ConstructorAtom,...]:
    max_lag=min(int(lag_depth),min(len(x.raw_history)-1 for x in samples)); out=[]
    for lag in range(max_lag+1):
        ds={len(x.raw_history[lag]) for x in samples}
        if len(ds)!=1:return ()
        out.extend(ConstructorAtom(lag,pos) for pos in range(next(iter(ds))))
    return tuple(out)


def _ancestry(samples:tuple[ConstructorProjectionSample,...]):
    frames:dict[str,set[int]]=defaultdict(set);episodes:dict[str,set[int]]=defaultdict(set)
    for r in samples:
        frames[r.frame_id].add(int(r.frame_epoch))
        if r.episode_schema_id is not None:episodes[r.episode_schema_id].add(int(r.episode_schema_epoch))
    if any(len(x)!=1 for x in frames.values()) or any(len(x)!=1 for x in episodes.values()):return None
    return tuple((k,next(iter(v))) for k,v in sorted(frames.items())),tuple((k,next(iter(v))) for k,v in sorted(episodes.items()))


def _exact_conflict_masks(rows:tuple[ConstructorProjectionSample,...],atoms:tuple[ConstructorAtom,...],max_edges:int)->tuple[int,...]:
    by=defaultdict(lambda:defaultdict(list))
    for r in rows:by[r.action_token][r.effect_token].append(r)
    masks=[]
    for _,groups in sorted(by.items()):
        effects=sorted(groups)
        for i in range(len(effects)):
            for j in range(i+1,len(effects)):
                for x in groups[effects[i]]:
                    for y in groups[effects[j]]:
                        mask=0
                        for ai,a in enumerate(atoms):
                            try:diff=x.raw_history[a.lag][a.position]!=y.raw_history[a.lag][a.position]
                            except IndexError:return ()
                            if diff:mask|=1<<ai
                        if mask:masks.append(mask)
                        if len(masks)>=int(max_edges):return tuple(masks)
    return tuple(masks)


def _rank_supports(edge_masks:tuple[int,...],atom_count:int,order:int,topk:int,budget:int):
    if not edge_masks:return (),0,False
    bits=[0]*atom_count
    for ei,mask in enumerate(edge_masks):
        marker=1<<ei
        for a in range(atom_count):
            if mask&(1<<a):bits[a]|=marker
    ranked=[];count=0;exhausted=False
    for support in itertools.combinations(range(atom_count),int(order)):
        count+=1
        if count>int(budget):exhausted=True;break
        covered=0
        for a in support:covered|=bits[a]
        ranked.append((covered.bit_count()/len(edge_masks),support))
    ranked.sort(key=lambda x:(-x[0],x[1]))
    return tuple(ranked[:int(topk)]),count,exhausted


def _action_baseline(train,validation):
    tab=defaultdict(Counter)
    for r in train:tab[r.action_token][r.effect_token]+=1
    return sum(_mode(tab[r.action_token])==r.effect_token for r in validation)/max(len(validation),1)


def _fit(train,pressure,validation,atoms,coverage,cfg,trace,evaluated):
    if len(train)<int(cfg.min_train_support):return None
    ancestry=_ancestry(train+pressure+validation)
    if ancestry is None:return None
    frame_epochs,episode_epochs=ancestry
    actions=sorted({r.action_token for r in train});tab=defaultdict(Counter);keys=set()
    for r in train:
        try:key=tuple(r.raw_history[a.lag][a.position] for a in atoms)
        except IndexError:return None
        keys.add(key);tab[(key,r.action_token)][r.effect_token]+=1
    sig={k:tuple((a,str(_mode(tab[(k,a)]) or "UNKNOWN")) for a in actions) for k in sorted(keys)}
    buckets={s:"bucket-"+hashlib.sha256(canonical_json(s)).hexdigest()[:16] for s in sorted(set(sig.values()))}
    ktb={k:buckets[s] for k,s in sig.items()};pred={(b,a):e for s,b in buckets.items() for a,e in s}
    def acc(rows):
        good=0;scopes=defaultdict(lambda:[0,0])
        for r in rows:
            try:key=tuple(r.raw_history[a.lag][a.position] for a in atoms)
            except IndexError:continue
            b=ktb.get(key);p=pred.get((b,r.action_token),"UNKNOWN") if b else "UNKNOWN";hit=p==r.effect_token;good+=hit
            scope=r.operational_scope_id or "__GLOBAL__";scopes[scope][0]+=int(hit);scopes[scope][1]+=1
        return good/max(len(rows),1),min((g/max(n,1) for g,n in scopes.values()),default=0.0)
    tr,_=acc(train);pr,_=acc(pressure);va,msa=acc(validation);base=_action_baseline(train,validation);lift=va-base
    if pr<cfg.min_validation_accuracy or va<cfg.min_validation_accuracy or lift<cfg.min_lift_over_action_baseline or msa<cfg.min_scope_accuracy:return None
    mapping=tuple(sorted(ktb.items()));bap=tuple(sorted((b,a,e) for (b,a),e in pred.items()))
    payload={"atoms":[[a.lag,a.position] for a in atoms],"mapping":[[list(k),v] for k,v in mapping],"frame_epochs":[list(x) for x in frame_epochs],"episode_schema_epochs":[list(x) for x in episode_epochs]}
    cid="robust-constructor-cand-"+hashlib.sha256(canonical_json(payload)).hexdigest()[:20]
    return RobustProjectionConstructorCandidate(cid,tuple(atoms),mapping,bap,tr,pr,va,base,msa,lift,float(coverage),int(evaluated),tuple(sorted(x.sample_id for x in train)),frame_epochs,episode_epochs,tuple(trace),cfg.assistance_ancestry())


def discover_robust_projection_constructor_candidates(training_samples:Iterable[ConstructorProjectionSample],pressure_samples:Iterable[ConstructorProjectionSample],validation_samples:Iterable[ConstructorProjectionSample],cfg:RobustConstructorGrowthConfig|None=None)->list[RobustProjectionConstructorCandidate]:
    cfg=cfg or RobustConstructorGrowthConfig();train=tuple(training_samples);pressure=tuple(pressure_samples);validation=tuple(validation_samples)
    if not train or not pressure or not validation:return []
    combined=train+pressure+validation;trace=[];evaluated_total=0;remaining=int(cfg.combination_budget)
    for lag in range(int(cfg.max_lag_ceiling)+1):
        atoms=_available_atoms(combined,lag)
        if not atoms:continue
        edges=_exact_conflict_masks(train,atoms,cfg.max_conflict_edges)
        if not edges:continue
        for order in range(1,int(cfg.max_support_ceiling)+1):
            ranked,evaluated,exhausted=_rank_supports(edges,len(atoms),order,cfg.top_supports_per_order,remaining)
            evaluated_total+=evaluated;remaining=max(0,remaining-evaluated);survivors=[]
            for coverage,idxs in ranked:
                c=_fit(train,pressure,validation,tuple(atoms[i] for i in idxs),coverage,cfg,tuple(trace),evaluated_total)
                if c is not None:survivors.append(c)
            diag=RobustConstructorSearchDiagnostic(lag,order,len(atoms),len(edges),evaluated,exhausted,ranked[0][0] if ranked else 0.0,len(survivors));trace.append(diag)
            if survivors:
                survivors.sort(key=lambda c:(-c.validation_accuracy,-c.pressure_accuracy,-c.observed_conflict_coverage,c.atoms))
                return [RobustProjectionConstructorCandidate(**{**asdict(c),"atoms":c.atoms,"key_to_bucket":c.key_to_bucket,"bucket_action_prediction":c.bucket_action_prediction,"search_trace":tuple(trace),"assistance_ancestry":c.assistance_ancestry}) for c in survivors[:int(cfg.max_candidates)]]
            if exhausted or remaining<=0:return []
    return []


def candidate_accuracy(candidate:RobustProjectionConstructorCandidate,rows:Iterable[ConstructorProjectionSample])->float:
    rows=tuple(rows);ktb=dict(candidate.key_to_bucket);pred={(b,a):e for b,a,e in candidate.bucket_action_prediction};good=0
    for r in rows:
        try:key=tuple(r.raw_history[a.lag][a.position] for a in candidate.atoms)
        except IndexError:continue
        b=ktb.get(key);p=pred.get((b,r.action_token),"UNKNOWN") if b else "UNKNOWN";good+=p==r.effect_token
    return good/max(len(rows),1)


def assess_projection_predictive_currentness(projection_id:str,projection_epoch:int,candidate:RobustProjectionConstructorCandidate,ordered_samples:Iterable[ConstructorProjectionSample],cfg:ProjectionPredictiveCurrentnessConfig|None=None)->ProjectionPredictiveCurrentnessWitness:
    cfg=cfg or ProjectionPredictiveCurrentnessConfig();rows=tuple(ordered_samples);accs=[];consecutive=0;first=None;drift=None
    # Iterable order is the supplied operational order; no semantic time ontology is inferred.
    for wi,start in enumerate(range(0,len(rows),int(cfg.window_size))):
        block=rows[start:start+int(cfg.window_size)]
        if len(block)<int(cfg.window_size):break
        a=candidate_accuracy(candidate,block);accs.append(a)
        if a<float(cfg.min_window_accuracy):
            if first is None:first=wi
            consecutive+=1
            if consecutive>=int(cfg.consecutive_failure_windows) and drift is None:drift=wi
        else:consecutive=0
    return ProjectionPredictiveCurrentnessWitness(str(projection_id),int(projection_epoch),"DRIFT_WITNESS" if drift is not None else "CURRENT_WITHIN_BOUNDS",tuple(accs),first,drift,cfg.assistance_ancestry())
