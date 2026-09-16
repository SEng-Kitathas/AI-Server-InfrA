"""First-pass research paper distillation from canonical paper payloads."""

from __future__ import annotations
from collections.abc import MutableMapping

from typing import Any

from research_config import PARSER_VERSION
from research_models import paper_summary, claim, method, isomorphic_abstraction

JsonObject = MutableMapping[str, Any]


def _pick_mechanism_name(title: str, abstract: str) -> str:
    text = f"{title} {abstract}".lower()
    candidates = [
        ("compression", "compression strategy"),
        ("cache", "cache management mechanism"),
        ("retrieval", "retrieval-augmented retention"),
        ("memory", "memory retention mechanism"),
        ("quantization", "quantization mechanism"),
        ("sparse", "sparse selection mechanism"),
        ("attention", "attention-centric architecture"),
        ("transformer", "transformer sequence architecture"),
    ]
    for needle, label in candidates:
        if needle in text:
            return label
    return "latent state management mechanism"


def _derive_problem_topology(title: str, abstract: str) -> str:
    text = f"{title} {abstract}".lower()
    if "memory" in text or "cache" in text:
        return "bounded retention of useful state under sequential pressure"
    if "compression" in text:
        return "information preservation under bounded representation budget"
    if "sequence" in text:
        return "performance preservation under long-range sequential dependency pressure"
    return "performance preservation under constrained representational resources"


def _derive_mechanism_topology(title: str, abstract: str) -> str:
    text = f"{title} {abstract}".lower()
    if "sparse" in text:
        return "selective sparse retention of high-value state"
    if "quantization" in text:
        return "lossy low-precision retention of compressed state"
    if "cache" in text or "memory" in text:
        return "managed buffering and reuse of salient intermediate state"
    if "compression" in text:
        return "lossy compression with selective reconstruction pressure"
    if "attention" in text:
        return "attention-driven contextual state routing"
    return "compressed retention with task-biased state prioritization"


def _derive_math_core(title: str, abstract: str) -> str:
    text = f"{title} {abstract}".lower()
    if "quantization" in text:
        return "precision-bounded approximation under information loss"
    if "sparse" in text:
        return "sparse selection and representation"
    if "compression" in text:
        return "information bottleneck under bounded capacity"
    if "attention" in text:
        return "weighted contextual aggregation"
    return "bounded-state approximation"


def _paper_inputs(canonical_paper: JsonObject) -> tuple[str, str, str, str]:
    paper_id = str(canonical_paper["paper_id"])
    title = str(canonical_paper.get("title", ""))
    abstract = str(canonical_paper.get("abstract", ""))
    thesis = (abstract if abstract else title)[:500]
    return paper_id, title, abstract, thesis


def _paper_summary(paper_id: str, thesis: str, ingestion_run_id: str) -> JsonObject:
    summary = paper_summary(
        paper_id=paper_id,
        parser_version=PARSER_VERSION,
        ingestion_run_id=ingestion_run_id,
        core_thesis=thesis,
        synthesis_role="foundational",
        must_read_justification="Direct paper ingestion for canonical-to-derived object test.",
        rigor_score=0.5,
        novelty_score=0.5,
        reproducibility_index=0.4,
    )
    summary["derived_object_counts"] = {
        "claims": 1,
        "methods": 1,
        "limitations": 0,
        "isomorphisms": 1,
    }
    return summary


def _paper_claim(paper_id: str, thesis: str, ingestion_run_id: str) -> JsonObject:
    return claim(
        paper_id=paper_id,
        parser_version=PARSER_VERSION,
        ingestion_run_id=ingestion_run_id,
        ordinal=1,
        claim_statement=thesis,
        claim_type="methodological_advantage",
        evidence_strength=0.4,
        falsifiability_surface=(
            "Requires full paper review and empirical comparison against cited baseline."
        ),
    )


def _paper_method(paper_id: str, title: str, abstract: str, ingestion_run_id: str) -> JsonObject:
    return method(
        paper_id=paper_id,
        parser_version=PARSER_VERSION,
        ingestion_run_id=ingestion_run_id,
        ordinal=1,
        mechanism_name=_pick_mechanism_name(title, abstract),
        execution_logic=(
            "First-pass abstract distillation inferred a primary mechanism from "
            "title/abstract tokens. "
            "This is a bounded heuristic, not a full methodological parse."
        ),
        hardware_substrate_assumptions=[],
    )


def _paper_isomorphism(
    paper_id: str, title: str, abstract: str, ingestion_run_id: str
) -> JsonObject:
    return isomorphic_abstraction(
        paper_id=paper_id,
        parser_version=PARSER_VERSION,
        ingestion_run_id=ingestion_run_id,
        ordinal=1,
        problem_topology=_derive_problem_topology(title, abstract),
        mechanism_topology=_derive_mechanism_topology(title, abstract),
        mathematical_core=_derive_math_core(title, abstract),
        failure_topology="unknown_from_abstract_only",
        target_transfer_domains=["signal processing", "systems caching", "video compression"],
    )


def distill_paper(canonical_paper: JsonObject, ingestion_run_id: str) -> JsonObject:
    paper_id, title, abstract, thesis = _paper_inputs(canonical_paper)
    return {
        "paper_summary": _paper_summary(paper_id, thesis, ingestion_run_id),
        "claims": [_paper_claim(paper_id, thesis, ingestion_run_id)],
        "methods": [_paper_method(paper_id, title, abstract, ingestion_run_id)],
        "limitations": [],
        "isomorphic_abstractions": [
            _paper_isomorphism(paper_id, title, abstract, ingestion_run_id)
        ],
    }
