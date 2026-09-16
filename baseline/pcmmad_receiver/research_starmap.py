"""Evidence topology builder for ranked research retrieval results."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from typing import TypeAlias

from research_models import EvidenceTopology, TopHit, TopologyCluster, TopologySummary

PaperValue: TypeAlias = str | int | float | list[str] | None
PaperRecord: TypeAlias = Mapping[str, PaperValue]
RankedEntry: TypeAlias = Mapping[str, PaperValue | PaperRecord] | Any
CategoryRecord: TypeAlias = Mapping[str, str | int]


LINEAGE_TITLE_MARKERS = (
    ("transformer-xl", "transformer_xl"),
    ("compressive transformer", "compressive_transformer"),
    ("compressive transformers", "compressive_transformer"),
    ("memorizing transformer", "memorizing_transformer"),
    ("memorizing transformers", "memorizing_transformer"),
    ("mamba", "mamba"),
    ("rwkv", "rwkv"),
    ("retnet", "retnet"),
)


def _entry_mapping(entry: RankedEntry) -> Mapping[str, Any]:
    if isinstance(entry, Mapping):
        return entry
    if hasattr(entry, "to_dict"):
        value = entry.to_dict()
        return value if isinstance(value, Mapping) else {}
    return {}


def _entry_paper(entry: RankedEntry) -> PaperRecord:
    paper = _entry_mapping(entry).get("paper", {})
    return paper if isinstance(paper, Mapping) else {}


def _entry_value(entry: RankedEntry, key: str, default: PaperValue = None) -> PaperValue:
    value = _entry_mapping(entry).get(key, default)
    return value if not isinstance(value, Mapping) else default


def _dominant_categories(ranked_results: list[RankedEntry]) -> list[CategoryRecord]:
    cat_counts: dict[str, int] = {}
    for entry in ranked_results:
        categories = _entry_paper(entry).get("categories", [])
        for cat in categories if isinstance(categories, list) else []:
            cat_key = str(cat)
            cat_counts[cat_key] = cat_counts.get(cat_key, 0) + 1
    return [
        {"category": category_key, "count": category_count}
        for category_key, category_count in sorted(
            cat_counts.items(), key=lambda item: item[1], reverse=True
        )[:5]
    ]


def _lineage_hints(ranked_results: list[RankedEntry]) -> list[str]:
    hints: list[str] = []
    for entry in ranked_results:
        title = str(_entry_paper(entry).get("title") or "").lower()
        for marker, label in LINEAGE_TITLE_MARKERS:
            if marker in title and label not in hints:
                hints.append(label)
    return hints


def _top_hits(ranked_results: list[RankedEntry]) -> list[TopHit]:
    hits: list[TopHit] = []
    for entry in ranked_results[:5]:
        paper = _entry_paper(entry)
        hits.append(
            TopHit(
                rank=_entry_value(entry, "rank"),
                signal_score=_entry_value(entry, "signal_score"),
                paper_id=paper.get("paper_id"),
                title=paper.get("title"),
                updated=paper.get("updated"),
            )
        )
    return hits


def _topology_integrity(ranked_results: list[RankedEntry]) -> str:
    first_score = _entry_value(ranked_results[0], "signal_score", 0)
    score = float(first_score) if isinstance(first_score, int | float) else 0.0
    return "coherent" if score >= 2.0 else "weak"


def build_evidence_topology(ranked_results: list[RankedEntry]) -> EvidenceTopology:
    if not ranked_results:
        return EvidenceTopology(
            layer="gen1_5",
            candidate_count=0,
            clusters=[],
            topology_summary=TopologySummary(
                dominant_categories=[], lineage_hints=[], integrity="empty"
            ),
            top_hits=[],
        )
    categories = _dominant_categories(ranked_results)
    lineage = _lineage_hints(ranked_results)
    return EvidenceTopology(
        layer="gen1_5",
        candidate_count=len(ranked_results),
        top_hits=_top_hits(ranked_results),
        clusters=[
            TopologyCluster(label="dominant_categories", items=categories),
            TopologyCluster(label="lineage_hints", items=lineage),
        ],
        topology_summary=TopologySummary(
            dominant_categories=categories,
            lineage_hints=lineage,
            integrity=_topology_integrity(ranked_results),
        ),
    )
