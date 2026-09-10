"""Research lab-tool registration surface."""

from __future__ import annotations

import math
import time
from collections.abc import MutableMapping
from dataclasses import dataclass

from typing import Any, Callable

from .research_arxiv import (
    ArxivBadResponseError,
    ArxivRateLimitedError,
    ArxivUnavailableError,
    fetch_arxiv_paper,
    get_cache_stats,
    search_arxiv,
)
from .research_config import (
    PER_QUERY_MAX_RESULTS,
    RESEARCH_HUNT_DEFAULT_WALL_SECONDS,
    RESEARCH_HUNT_MAX_WALL_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
)
from .research_distill import distill_paper
from .research_predator import dedupe_and_rank, generate_query_family
from .research_starmap import build_evidence_topology

JsonObject = MutableMapping[str, Any]
ResearchRegistrar = Callable[
    ..., Callable[[Callable[[JsonObject], JsonObject]], Callable[[JsonObject], JsonObject]]
]


@dataclass(frozen=True)
class HuntPayloadSpec:
    topic: str
    mode: str
    family: list[Any]
    family_hits: list[JsonObject]
    ranked: list[Any]


def _as_dict(value: Any) -> Any:
    return value.to_dict() if hasattr(value, "to_dict") else value


def _as_dict_list(values: list[Any]) -> list[Any]:
    return [_as_dict(item) for item in values]


def _raise_arxiv_error(error_cls: type[Exception], error: Exception) -> None:
    if isinstance(error, ArxivRateLimitedError):
        raise error_cls(error.error_code, str(error), 429, retryable=True)
    if isinstance(error, ArxivUnavailableError):
        raise error_cls(error.error_code, str(error), 503, retryable=True)
    if isinstance(error, ArxivBadResponseError):
        raise error_cls(error.error_code, str(error), 502, retryable=False)
    raise error


def _register_arxiv_search(register_tool: ResearchRegistrar, error_cls: type[Exception]) -> None:
    @register_tool(
        "research.arxiv.search",
        "Search arXiv using server-side research code.",
        "low",
        category="research",
        side_effect_class="external_read",
        effect_traits=["network_io", "reads_external_state", "may_write_cache", "bounded_network_timeout"],
    )
    def tool_research_arxiv_search(payload: JsonObject) -> JsonObject:
        query = str(payload.get("query", "")).strip()
        if not query:
            raise error_cls("BAD_REQUEST", "query is required", 400)
        max_results = max(1, min(int(payload.get("max_results", 8)), PER_QUERY_MAX_RESULTS))
        sort_by = str(payload.get("sort_by", "relevance"))
        if sort_by not in {"relevance", "lastUpdatedDate", "submittedDate"}:
            raise error_cls("BAD_REQUEST", "sort_by must be relevance|lastUpdatedDate|submittedDate", 400)
        try:
            return _as_dict(search_arxiv(query=query, max_results=max_results, sort_by=sort_by))
        except (ArxivRateLimitedError, ArxivUnavailableError, ArxivBadResponseError) as e:
            _raise_arxiv_error(error_cls, e)


def _register_arxiv_paper(register_tool: ResearchRegistrar, error_cls: type[Exception]) -> None:
    @register_tool(
        "research.arxiv.paper",
        "Fetch a specific arXiv paper and distill derived objects.",
        "low",
        category="research",
        side_effect_class="external_read",
        effect_traits=["network_io", "reads_external_state", "may_write_cache", "bounded_network_timeout"],
    )
    def tool_research_arxiv_paper(payload: JsonObject) -> JsonObject:
        paper_id = str(payload.get("paper_id", "")).strip()
        if not paper_id:
            raise error_cls("BAD_REQUEST", "paper_id is required", 400)
        run_id = str(payload.get("ingestion_run_id", "research_v5_run"))
        try:
            canonical = fetch_arxiv_paper(paper_id)
            derived = distill_paper(canonical_paper=canonical, ingestion_run_id=run_id)
            return {"canonical_paper": _as_dict(canonical), "derived_objects": derived}
        except (ArxivRateLimitedError, ArxivUnavailableError, ArxivBadResponseError) as e:
            _raise_arxiv_error(error_cls, e)
        except ValueError as e:
            raise error_cls("NOT_FOUND", str(e), 404, retryable=False)


def _research_hunt_payload(spec: HuntPayloadSpec) -> JsonObject:
    return {
        "topic": spec.topic,
        "mode": spec.mode,
        "query_families": _as_dict_list(spec.family),
        "candidate_count_before_dedupe": len(spec.family_hits),
        "ranked_results": _as_dict_list(spec.ranked),
        "starmap": _as_dict(build_evidence_topology(spec.ranked)),
        "cache": get_cache_stats(),
        "note": "bounded direct_hunt via lab router",
    }


def _research_family_hits(
    topic: str,
    family: list[object],
    max_results: int,
    *,
    deadline: float,
) -> tuple[list[JsonObject], list[JsonObject], bool, int]:
    family_hits: list[JsonObject] = []
    errors: list[JsonObject] = []
    budget_exhausted = False
    attempted = 0
    for entry in family:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            budget_exhausted = True
            break
        query_used = getattr(entry, "query", None) or entry["query"]
        query_label = getattr(entry, "label", None) or entry["label"]
        timeout = max(0.25, min(float(REQUEST_TIMEOUT_SECONDS), float(remaining)))
        attempted += 1
        try:
            result = search_arxiv(
                query=query_used,
                max_results=max_results,
                sort_by="relevance",
                request_timeout_seconds=timeout,
            )
        except (ArxivRateLimitedError, ArxivUnavailableError, ArxivBadResponseError) as exc:
            errors.append(
                {
                    "query_used": query_used,
                    "query_label": query_label,
                    "error_code": getattr(exc, "error_code", "ARXIV_ERROR"),
                    "error": str(exc),
                }
            )
            if time.monotonic() >= deadline:
                budget_exhausted = True
                break
            continue
        if hasattr(result, "results"):
            papers = getattr(result, "results")
        elif isinstance(result, dict):
            papers = result.get("results", [])
        else:
            papers = []
        family_hits.extend(
            {"query_used": query_used, "query_label": query_label, "paper": _as_dict(paper)}
            for paper in papers
        )
    return family_hits, errors, budget_exhausted, attempted


def _research_hunt_result(
    topic: str, mode: str, max_results: int, *, wall_seconds: int
) -> JsonObject:
    started = time.monotonic()
    deadline = started + wall_seconds
    family = generate_query_family(topic)
    family_hits, query_errors, budget_exhausted, queries_attempted = _research_family_hits(
        topic, family, max_results, deadline=deadline
    )
    ranked = dedupe_and_rank(topic, family_hits)
    payload = _research_hunt_payload(HuntPayloadSpec(topic, mode, family, family_hits, ranked))
    payload.update(
        {
            "query_errors": query_errors,
            "partial": bool(query_errors or budget_exhausted),
            "budget_exhausted": budget_exhausted,
            "wall_budget_seconds": wall_seconds,
            "elapsed_ms": int((time.monotonic() - started) * 1000),
            "queries_attempted": queries_attempted,
            "queries_planned": len(family),
            "decision_note": (
                "partial bounded research result; operator may deepen asynchronously if needed"
                if query_errors or budget_exhausted
                else "bounded research hunt completed within interactive control budget"
            ),
        }
    )
    return payload


def _register_research_hunt(register_tool: ResearchRegistrar, error_cls: type[Exception]) -> None:
    @register_tool(
        "research.hunt",
        "Run bounded multi-query research hunt server-side.",
        "medium",
        category="research",
        side_effect_class="external_read",
        effect_traits=["network_io", "reads_external_state", "may_write_cache", "bounded_network_timeout", "bounded_wall_time", "partial_results"],
    )
    def tool_research_hunt(payload: JsonObject) -> JsonObject:
        topic = str(payload.get("topic", "")).strip()
        if not topic:
            raise error_cls("BAD_REQUEST", "topic is required", 400)
        mode = str(payload.get("mode", "direct_hunt"))
        if mode != "direct_hunt":
            raise error_cls("MODE_NOT_ENABLED", "v5 supports direct_hunt only", 400)
        max_results = max(1, min(int(payload.get("max_results", 5)), PER_QUERY_MAX_RESULTS))
        wall_seconds = max(
            3,
            min(
                int(payload.get("wall_time_seconds", RESEARCH_HUNT_DEFAULT_WALL_SECONDS)),
                RESEARCH_HUNT_MAX_WALL_SECONDS,
            ),
        )
        try:
            return _research_hunt_result(
                topic, mode, max_results, wall_seconds=wall_seconds
            )
        except (ArxivRateLimitedError, ArxivUnavailableError, ArxivBadResponseError) as e:
            _raise_arxiv_error(error_cls, e)


def register_research_tools(
    register_tool: ResearchRegistrar, *, error_cls: type[Exception]
) -> None:
    _register_arxiv_search(register_tool, error_cls)
    _register_arxiv_paper(register_tool, error_cls)
    _register_research_hunt(register_tool, error_cls)
