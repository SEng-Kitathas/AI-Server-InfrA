"""Typed research domain models for canonical papers, ranking, topology, and distillation."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
from collections.abc import MutableMapping

JsonObject = MutableMapping[str, Any]


@dataclass(frozen=True)
class QueryFamilyEntry:
    label: str
    query: str

    def to_dict(self) -> JsonObject:
        return asdict(self)


@dataclass(frozen=True)
class RankedResearchHit:
    rank: int
    signal_score: float
    query_hits: int
    matched_queries: list[str]
    matched_labels: list[str]
    paper: JsonObject

    def to_dict(self) -> JsonObject:
        return asdict(self)


@dataclass(frozen=True)
class TopHit:
    rank: int | None
    signal_score: float | None
    paper_id: str | None
    title: str | None
    updated: str | None

    def to_dict(self) -> JsonObject:
        return asdict(self)


@dataclass(frozen=True)
class TopologyCluster:
    label: str
    items: list[Any]

    def to_dict(self) -> JsonObject:
        return {"label": self.label, "items": self.items}


@dataclass(frozen=True)
class TopologySummary:
    dominant_categories: list[JsonObject]
    lineage_hints: list[str]
    integrity: str

    def to_dict(self) -> JsonObject:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceTopology:
    layer: str
    candidate_count: int
    clusters: list[TopologyCluster]
    topology_summary: TopologySummary
    top_hits: list[TopHit] | None = None

    def to_dict(self) -> JsonObject:
        data = {
            "layer": self.layer,
            "candidate_count": self.candidate_count,
            "clusters": [c.to_dict() for c in self.clusters],
            "topology_summary": self.topology_summary.to_dict(),
        }
        if self.top_hits is not None:
            data["top_hits"] = [h.to_dict() for h in self.top_hits]
        return data


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(*parts: str) -> str:
    joined = "::".join(parts)
    digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()[:12]
    return f"{parts[-1]}_{digest}"


@dataclass(frozen=True)
class ResearchObjectContext:
    paper_id: str
    parser_version: str
    ingestion_run_id: str


@dataclass(frozen=True)
class MetadataOptions:
    parser_confidence: float = 0.5
    human_validated: bool = False
    source_span: JsonObject | None = None


def make_metadata(
    object_id: str, ctx: ResearchObjectContext, options: MetadataOptions | None = None
) -> JsonObject:
    opts = options or MetadataOptions()
    return {
        "object_id": object_id,
        "paper_id": ctx.paper_id,
        "ingestion_run_id": ctx.ingestion_run_id,
        "parser_version": ctx.parser_version,
        "created_at": utc_now(),
        "parser_confidence": opts.parser_confidence,
        "human_validated": opts.human_validated,
        "source_span": opts.source_span
        or {
            "start_char": 0,
            "end_char": 0,
            "section_label": "abstract",
        },
    }


@dataclass(frozen=True)
class PaperSummarySpec:
    core_thesis: str
    synthesis_role: str
    must_read_justification: str
    rigor_score: float = 0.5
    novelty_score: float = 0.5
    reproducibility_index: float = 0.4


def paper_summary(ctx: ResearchObjectContext, spec: PaperSummarySpec) -> JsonObject:
    object_id = stable_id(ctx.paper_id, "paper_summary")
    return {
        "object_type": "paper_summary",
        "metadata": make_metadata(object_id, ctx, MetadataOptions(parser_confidence=0.72)),
        "paper_id": ctx.paper_id,
        "synthesis_role": spec.synthesis_role,
        "core_thesis": spec.core_thesis,
        "rigor_score": spec.rigor_score,
        "novelty_score": spec.novelty_score,
        "reproducibility_index": spec.reproducibility_index,
        "derived_object_counts": {
            "claims": 0,
            "methods": 0,
            "limitations": 0,
            "isomorphisms": 0,
        },
        "must_read_justification": spec.must_read_justification,
        "distillation_status": "embedded",
    }


@dataclass(frozen=True)
class ClaimSpec:
    ordinal: int
    claim_statement: str
    claim_type: str = "methodological_advantage"
    evidence_strength: float = 0.45
    falsifiability_surface: str = ""


def claim(ctx: ResearchObjectContext, spec: ClaimSpec) -> JsonObject:
    claim_id = f"c{spec.ordinal}"
    object_id = stable_id(ctx.paper_id, claim_id)
    return {
        "object_type": "claim",
        "metadata": make_metadata(object_id, ctx),
        "paper_id": ctx.paper_id,
        "claim_id": claim_id,
        "claim_statement": spec.claim_statement,
        "claim_type": spec.claim_type,
        "evidence_strength": spec.evidence_strength,
        "falsifiability_surface": spec.falsifiability_surface,
        "source_section": "abstract",
        "contradiction_links": [],
        "tags": [],
    }


@dataclass(frozen=True)
class MethodSpec:
    ordinal: int
    mechanism_name: str
    execution_logic: str
    hardware_substrate_assumptions: list[str] | None = None


def method(ctx: ResearchObjectContext, spec: MethodSpec) -> JsonObject:
    method_id = f"m{spec.ordinal}"
    object_id = stable_id(ctx.paper_id, method_id)
    return {
        "object_type": "method",
        "metadata": make_metadata(object_id, ctx, MetadataOptions(parser_confidence=0.46)),
        "paper_id": ctx.paper_id,
        "method_id": method_id,
        "mechanism_name": spec.mechanism_name,
        "execution_logic": spec.execution_logic,
        "hardware_substrate_assumptions": spec.hardware_substrate_assumptions or [],
        "complexity_metrics": {
            "time_complexity": "unknown",
            "space_complexity": "unknown",
        },
        "dependencies": [],
    }


@dataclass(frozen=True)
class IsomorphicAbstractionSpec:
    ordinal: int
    problem_topology: str
    mechanism_topology: str
    mathematical_core: str
    failure_topology: str = ""
    target_transfer_domains: list[str] | None = None


def isomorphic_abstraction(
    ctx: ResearchObjectContext, spec: IsomorphicAbstractionSpec
) -> JsonObject:
    abstraction_id = f"iso{spec.ordinal}"
    object_id = stable_id(ctx.paper_id, abstraction_id)
    return {
        "object_type": "isomorphic_abstraction",
        "metadata": make_metadata(object_id, ctx, MetadataOptions(parser_confidence=0.35)),
        "paper_id": ctx.paper_id,
        "abstraction_id": abstraction_id,
        "problem_topology": spec.problem_topology,
        "mechanism_topology": spec.mechanism_topology,
        "mathematical_core": spec.mathematical_core,
        "failure_topology": spec.failure_topology,
        "target_transfer_domains": spec.target_transfer_domains or [],
        "reuse_conditions": [],
        "risk_notes": [],
    }
