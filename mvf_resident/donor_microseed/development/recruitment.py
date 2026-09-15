from __future__ import annotations
from dataclasses import dataclass, asdict
import hashlib, json, math
from typing import Iterable
from ..runtime.types import Authority, FeasibilityState, QualificationState
from ..runtime.composer import compose_capabilities


@dataclass(frozen=True)
class RecruitmentOption:
    capability_id: str
    feasibility: FeasibilityState
    predicted_effect: tuple[float, ...] = ()
    local_cost: float = 0.0
    resource_tags: tuple[str, ...] = ()
    model_evidence_ids: tuple[str, ...] = ()

    def serializable(self) -> dict:
        d=asdict(self); d["feasibility"]=self.feasibility.value; return d

    @classmethod
    def from_serializable(cls,d:dict) -> "RecruitmentOption":
        return cls(capability_id=d["capability_id"], feasibility=FeasibilityState(d["feasibility"]),
                   predicted_effect=tuple(d.get("predicted_effect",())), local_cost=float(d.get("local_cost",0.0)),
                   resource_tags=tuple(d.get("resource_tags",())), model_evidence_ids=tuple(d.get("model_evidence_ids",())))


@dataclass(frozen=True)
class RecruitmentProposal:
    proposal_id: str
    options: tuple[RecruitmentOption, ...]
    selected_capability_ids: tuple[str, ...]
    capability_epochs: tuple[tuple[str,int], ...]
    value_epochs: tuple[tuple[str,int], ...] = ()
    topology_epoch: tuple[str, int] | None = None
    operational_scope_id: str | None = None
    role_topology_origin: str = "SUPPLIED_AND_PROVENANCED"
    assistance_ancestry: tuple[str, ...] = ()
    authority: str = Authority.MODEL_OUTPUT_ONLY.value
    semantic_goal_authority: str = "NONE"

    def serializable(self) -> dict:
        return {
          "proposal_id":self.proposal_id,"options":[o.serializable() for o in self.options],
          "selected_capability_ids":list(self.selected_capability_ids),
          "capability_epochs":[list(x) for x in self.capability_epochs],"value_epochs":[list(x) for x in self.value_epochs],
          "topology_epoch":list(self.topology_epoch) if self.topology_epoch is not None else None,
          "operational_scope_id":self.operational_scope_id,"role_topology_origin":self.role_topology_origin,
          "assistance_ancestry":list(self.assistance_ancestry),"authority":self.authority,
          "semantic_goal_authority":self.semantic_goal_authority,
        }

    @classmethod
    def from_serializable(cls,d:dict) -> "RecruitmentProposal":
        return cls(proposal_id=d["proposal_id"], options=tuple(RecruitmentOption.from_serializable(x) for x in d.get("options",())),
                   selected_capability_ids=tuple(d.get("selected_capability_ids",())),
                   capability_epochs=tuple((str(a),int(b)) for a,b in d.get("capability_epochs",())),
                   value_epochs=tuple((str(a),int(b)) for a,b in d.get("value_epochs",())),
                   topology_epoch=(str(d["topology_epoch"][0]),int(d["topology_epoch"][1])) if d.get("topology_epoch") is not None else None,
                   operational_scope_id=d.get("operational_scope_id"), role_topology_origin=d.get("role_topology_origin","SUPPLIED_AND_PROVENANCED"),
                   assistance_ancestry=tuple(d.get("assistance_ancestry",())), authority=d.get("authority",Authority.MODEL_OUTPUT_ONLY.value),
                   semantic_goal_authority=d.get("semantic_goal_authority","NONE"))

    def digest(self) -> str:
        payload=self.serializable().copy(); payload.pop("proposal_id",None)
        return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()


class RecruitmentRegistry:
    """Proposal-only hierarchy/recruitment substrate earned by MS978-1002.

    It does not discover parent/child topology, learn forward models, decide truth,
    or override subordinate feasibility. It content-binds a proposed set of
    currently qualified capabilities so the existing composer can test/use the
    proposal without laundering model output into authority.
    """
    def __init__(self): self.proposals: dict[str,RecruitmentProposal]={}

    @staticmethod
    def validate_inputs(options: Iterable[RecruitmentOption], selected: Iterable[str]) -> tuple[RecruitmentOption,...]:
        opts=tuple(options); sel=tuple(selected)
        if not opts:
            raise ValueError("recruitment requires nonempty options")
        if len({o.capability_id for o in opts}) != len(opts):
            raise ValueError("RECRUITMENT_DUPLICATE_OPTION_CAPABILITY")
        by={o.capability_id:o for o in opts}
        if not sel or len(set(sel))!=len(sel): raise ValueError("recruitment requires unique nonempty selected capabilities")
        for o in opts:
            if not math.isfinite(float(o.local_cost)) or any(not math.isfinite(float(x)) for x in o.predicted_effect):
                raise ValueError("nonfinite recruitment model output")
        for cid in sel:
            if cid not in by: raise ValueError(f"RECRUITMENT_SELECTED_OPTION_MISSING:{cid}")
            if by[cid].feasibility != FeasibilityState.FEASIBLE:
                raise ValueError(f"RECRUITMENT_NOT_FEASIBLE:{cid}:{by[cid].feasibility.value}")
        tags=[]
        for cid in sel: tags.extend(by[cid].resource_tags)
        if len(tags)!=len(set(tags)): raise ValueError("RECRUITMENT_RESOURCE_CONFLICT")
        return opts

    def add(self, proposal: RecruitmentProposal) -> None:
        if proposal.proposal_id in self.proposals:
            raise ValueError("duplicate recruitment proposal")
        if proposal.authority != Authority.MODEL_OUTPUT_ONLY.value:
            raise ValueError("RECRUITMENT_AUTHORITY_ESCALATION")
        if proposal.semantic_goal_authority != "NONE":
            raise ValueError("RECRUITMENT_SEMANTIC_GOAL_AUTHORITY_FORBIDDEN")
        if proposal.topology_epoch is None:
            if proposal.role_topology_origin != "SUPPLIED_AND_PROVENANCED":
                raise ValueError("RECRUITMENT_TOPOLOGY_ORIGIN_UNQUALIFIED")
            if "SUPPLIED_RECRUITMENT_TOPOLOGY" not in proposal.assistance_ancestry:
                raise ValueError("RECRUITMENT_TOPOLOGY_ASSISTANCE_ANCESTRY_MISSING")
        else:
            topology_id, epoch = proposal.topology_epoch
            if proposal.role_topology_origin != "EXTERNALLY_QUALIFIED_OPERATIONAL_TOPOLOGY":
                raise ValueError("RECRUITMENT_TOPOLOGY_ORIGIN_MISMATCH")
            marker=f"QUALIFIED_OPERATIONAL_RECRUITMENT_TOPOLOGY:{topology_id}@{epoch}"
            if marker not in proposal.assistance_ancestry:
                raise ValueError("RECRUITMENT_QUALIFIED_TOPOLOGY_ANCESTRY_MISSING")
        self.proposals[proposal.proposal_id] = proposal

    def currentness(self,proposal_id,capabilities,values,topologies=None) -> dict:
        p=self.proposals.get(proposal_id)
        if p is None: return {"status":"UNKNOWN_INCOMPLETE","reason":"RECRUITMENT_PROPOSAL_NOT_FOUND"}
        for cid,epoch in p.capability_epochs:
            c=capabilities.contracts.get(cid)
            if c is None or c.qualification not in {QualificationState.QUALIFIED,QualificationState.SHADOW_QUALIFIED}:
                return {"status":"UNKNOWN_INCOMPLETE","reason":f"RECRUITMENT_CAPABILITY_NOT_CURRENT:{cid}"}
            if capabilities.epochs.get(cid,-1)!=epoch:
                return {"status":"UNKNOWN_INCOMPLETE","reason":f"RECRUITMENT_CAPABILITY_EPOCH_DRIFT:{cid}"}
        for vid,epoch in p.value_epochs:
            if not values.is_current(vid,epoch): return {"status":"UNKNOWN_INCOMPLETE","reason":f"RECRUITMENT_VALUE_EPOCH_DRIFT:{vid}"}
        if p.topology_epoch is not None:
            topology_id, epoch = p.topology_epoch
            if topologies is None or not topologies.is_current(topology_id, epoch):
                return {"status":"UNKNOWN_INCOMPLETE","reason":f"RECRUITMENT_TOPOLOGY_EPOCH_DRIFT:{topology_id}"}
        return {"status":"CURRENT","proposal_id":proposal_id,"authority":p.authority,"semantic_goal_authority":p.semantic_goal_authority}

    def compose(self,proposal_id,capabilities,values,topologies=None):
        st=self.currentness(proposal_id,capabilities,values,topologies)
        if st["status"]!="CURRENT": return {**st,"plan":[],"composition_authority":Authority.NONE.value}
        p=self.proposals[proposal_id]; r=compose_capabilities(capabilities.contracts,p.selected_capability_ids)
        return {"status":r.status,"proposal_id":proposal_id,"plan":list(r.plan),"missing":list(r.missing),
                "composition_authority":r.authority.value,"proposal_authority":p.authority,"semantic_goal_authority":"NONE"}
