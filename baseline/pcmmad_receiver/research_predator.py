"""Bounded research-query expansion, dedupe, and ranking heuristics."""

from __future__ import annotations
from collections.abc import MutableMapping

import re
from collections import OrderedDict
from typing import Any

from .research_models import QueryFamilyEntry, RankedResearchHit

JsonObject = MutableMapping[str, Any]

TOKEN_RE = re.compile(r"[A-Za-z0-9_./:-]{3,}")

STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "that",
        "with",
        "from",
        "this",
        "have",
        "their",
        "into",
        "using",
        "used",
        "are",
        "was",
        "were",
        "has",
        "had",
        "but",
        "not",
        "you",
        "your",
        "can",
        "will",
        "they",
        "its",
        "than",
        "then",
        "such",
        "over",
        "also",
        "these",
        "those",
        "our",
        "out",
        "all",
        "one",
        "two",
        "may",
        "via",
        "use",
        "file",
        "files",
        "data",
        "notes",
        "note",
        "read",
        "search",
        "project",
        "state",
        "context",
        "latest",
        "current",
        "work",
        "line",
    }
)

HIGH_SIGNAL_PHRASES = (
    (
        "compressive transformer",
        (
            "compressive transformers long range sequence modeling",
            "transformer-xl compressive memory",
        ),
    ),
    ("memory compression", ("transformer memory compression", "long context transformer memory")),
    ("kv cache", ("kv cache compression transformer", "paged attention kv cache")),
    (
        "long context",
        ("long context transformer memory", "efficient transformer long range sequence"),
    ),
    ("transformer", ("transformer sequence modeling", "attention memory architecture")),
    ("mamba", ("mamba state space sequence modeling", "state space model long context")),
    ("rwkv", ("rwkv recurrent transformer memory", "rwkv long context")),
    ("retnet", ("retnet retention mechanism long context", "retention network sequence modeling")),
    ("quantization", ("transformer quantization memory", "low precision transformer state")),
    ("sparse", ("sparse transformer memory routing", "sparse attention long context")),
)

CANONICAL_BOOSTS = (
    "compressive transformers long range sequence modeling",
    "transformer-xl",
    "memorizing transformers",
    "mamba state space",
    "rwkv",
    "retnet",
)


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text) if token.lower() not in STOPWORDS]


def _add_query(queries: "OrderedDict[str, QueryFamilyEntry]", label: str, query: str) -> None:
    if query not in queries:
        queries[query] = QueryFamilyEntry(label=label, query=query)


def _add_high_signal_queries(queries: "OrderedDict[str, QueryFamilyEntry]", topic_l: str) -> None:
    for needle, expansions in HIGH_SIGNAL_PHRASES:
        if needle not in topic_l:
            continue
        for query_variant in expansions:
            _add_query(queries, f"expansion:{needle}", query_variant)


def _add_canonical_topic_queries(
    queries: "OrderedDict[str, QueryFamilyEntry]", topic_l: str
) -> None:
    if "transformer" in topic_l and "memory" in topic_l:
        for query_variant in [
            "transformer-xl memory",
            "compressive transformers long range sequence modeling",
            "memorizing transformers retrieval memory",
        ]:
            _add_query(queries, "canonical_memory_lineage", query_variant)
    if "kv" in topic_l or "cache" in topic_l:
        for query_variant in [
            "kv cache compression transformer",
            "paged attention kv cache",
            "long context kv memory transformer",
        ]:
            _add_query(queries, "kv_family", query_variant)


def generate_query_family(topic: str) -> list[QueryFamilyEntry]:
    topic_norm = " ".join(topic.strip().split())
    topic_l = topic_norm.lower()
    queries: "OrderedDict[str, QueryFamilyEntry]" = OrderedDict()
    queries[topic_norm] = QueryFamilyEntry(label="direct", query=topic_norm)
    _add_high_signal_queries(queries, topic_l)
    toks = _tokens(topic_norm)
    short = " ".join(toks[:5]) if toks else topic_norm
    _add_query(queries, "compressed", short) if short else None
    _add_canonical_topic_queries(queries, topic_l)
    return list(queries.values())[:5]


def _paper_key(paper: JsonObject) -> str:
    return paper.get("paper_id") or paper.get("source_id") or paper.get("title", "")


def _canonical_score(title: str, abstract: str) -> float:
    score = 0.0
    for phrase in CANONICAL_BOOSTS:
        if phrase in title:
            score += 4.0
        elif phrase in abstract:
            score += 2.0
    return score


def _token_score(topic: str, title: str, abstract: str, query_used: str) -> float:
    score = 0.0
    for tok in _tokens(topic.lower()):
        score += 1.2 if tok in title else 0.0
        score += 0.35 if tok in abstract else 0.0
        score += 0.15 if tok in query_used else 0.0
    return score


def _preferred_term_score(title: str, abstract: str) -> float:
    preferred = ["memory", "compress", "context", "transformer", "sequence", "retention", "cache"]
    return sum(
        (0.5 if tok in title else 0.0) + (0.15 if tok in abstract else 0.0) for tok in preferred
    )


def _score_hit(topic: str, hit: JsonObject) -> float:
    paper = hit.get("paper", {})
    title = (paper.get("title") or "").lower()
    abstract = (paper.get("abstract") or "").lower()
    query_used = (hit.get("query_used") or "").lower()
    topic_l = topic.lower()

    score = _canonical_score(title, abstract)
    score += _token_score(topic_l, title, abstract, query_used)
    score += _preferred_term_score(title, abstract)
    updated = paper.get("updated") or ""
    score += 0.2 if updated >= "2024-01-01" else 0.0
    return round(score, 4)


def _merge_ranked_hit(merged: JsonObject, key: str, hit: JsonObject, hit_score: float) -> None:
    if key not in merged:
        merged[key] = {
            "paper": hit.get("paper", {}),
            "score": hit_score,
            "matched_queries": [hit.get("query_used")],
            "matched_labels": [hit.get("query_label")],
            "query_hits": 1,
        }
        return
    merged[key]["score"] = max(merged[key]["score"], hit_score) + 0.15
    if hit.get("query_used") not in merged[key]["matched_queries"]:
        merged[key]["matched_queries"].append(hit.get("query_used"))
    if hit.get("query_label") not in merged[key]["matched_labels"]:
        merged[key]["matched_labels"].append(hit.get("query_label"))
    merged[key]["query_hits"] += 1


def _ranked_hit(entry: JsonObject, rank: int) -> RankedResearchHit:
    return RankedResearchHit(
        rank=rank,
        signal_score=round(entry["score"], 4),
        query_hits=entry["query_hits"],
        matched_queries=entry["matched_queries"],
        matched_labels=entry["matched_labels"],
        paper=entry["paper"],
    )


def dedupe_and_rank(topic: str, family_hits: list[JsonObject]) -> list[RankedResearchHit]:
    merged: JsonObject = {}
    for hit in family_hits:
        paper = hit.get("paper", {})
        key = _paper_key(paper)
        if key:
            _merge_ranked_hit(merged, key, hit, _score_hit(topic, hit))
    ranked = sorted(
        merged.values(),
        key=lambda x: (x["score"], x["query_hits"], x["paper"].get("updated", "")),
        reverse=True,
    )
    return [_ranked_hit(entry, rank) for rank, entry in enumerate(ranked[:10], start=1)]
