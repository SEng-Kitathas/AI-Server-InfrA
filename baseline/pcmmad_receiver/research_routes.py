"""Research HTTP routes for health, arXiv fetch/search, and bounded direct hunt."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from api_wire_models import (
    ArxivPaperRequest,
    ArxivPaperResponse,
    ArxivSearchRequest,
    ErrorEnvelope,
    ResearchHealthResponse,
    ResearchHuntRequest,
    ResearchHuntResponse,
)
from research_config import (
    ENABLED_HUNT_MODES,
    ENABLED_SOURCES,
    PARSER_VERSION,
    PER_QUERY_MAX_RESULTS,
)
from research_arxiv import (
    ArxivBadResponseError,
    ArxivRateLimitedError,
    ArxivUnavailableError,
    fetch_arxiv_paper,
    get_cache_stats,
    search_arxiv,
)
from research_distill import distill_paper
from research_predator import dedupe_and_rank, generate_query_family
from research_starmap import build_evidence_topology

research_bp = Blueprint("research", __name__, url_prefix="/research")


def _error(error_code: str, message: str, status: int, **extra: object) -> object:
    return (
        jsonify(
            ErrorEnvelope(ok=False, error_code=error_code, message=message, extra=extra).to_dict()
        ),
        status,
    )


def _json_body() -> dict:
    data = request.get_json(silent=False, force=True)
    if not isinstance(data, dict):
        raise ValueError("JSON request body must be an object")
    return data


@research_bp.get("/health")
def research_health() -> object:
    return jsonify(
        ResearchHealthResponse(
            ok=True,
            status="online",
            sources=ENABLED_SOURCES,
            modes=ENABLED_HUNT_MODES,
            parser_version=PARSER_VERSION,
            cache=get_cache_stats(),
            predator_generation="gen1",
            starmap_layer="gen1_5",
        ).to_dict()
    )


@research_bp.post("/arxiv/search")
def research_arxiv_search() -> object:
    try:
        req = ArxivSearchRequest.from_json(_json_body())
        if not req.query:
            return _error("BAD_REQUEST", "query is required", 400)
        return jsonify(
            search_arxiv(
                query=req.query, max_results=req.max_results, sort_by=req.sort_by
            ).to_dict()
        )
    except ArxivRateLimitedError as e:
        return _error(e.error_code, str(e), 429, retryable=True)
    except ArxivUnavailableError as e:
        return _error(e.error_code, str(e), 503, retryable=True)
    except ArxivBadResponseError as e:
        return _error(e.error_code, str(e), 502, retryable=False)
    except (OSError, RuntimeError, ValueError, TypeError) as e:
        return _error("ARXIV_SEARCH_FAILED", str(e), 500, retryable=False)


@research_bp.post("/arxiv/paper")
def research_arxiv_paper() -> object:
    try:
        req = ArxivPaperRequest.from_json(_json_body())
        if not req.paper_id:
            return _error("BAD_REQUEST", "paper_id is required", 400)
        canonical = fetch_arxiv_paper(req.paper_id)
        derived = distill_paper(
            canonical_paper=canonical.to_dict(), ingestion_run_id=req.ingestion_run_id
        )
        return jsonify(
            ArxivPaperResponse(
                ok=True, canonical_paper=canonical.to_dict(), derived_objects=derived
            ).to_dict()
        )
    except ArxivRateLimitedError as e:
        return _error(e.error_code, str(e), 429, retryable=True)
    except ArxivUnavailableError as e:
        return _error(e.error_code, str(e), 503, retryable=True)
    except ArxivBadResponseError as e:
        return _error(e.error_code, str(e), 502, retryable=False)
    except ValueError as e:
        return _error("NOT_FOUND", str(e), 404, retryable=False)
    except (OSError, RuntimeError, ValueError, TypeError) as e:
        return _error("ARXIV_FETCH_FAILED", str(e), 500, retryable=False)


def _direct_hunt_payload(req: ResearchHuntRequest) -> ResearchHuntResponse:
    max_results = min(req.max_results, PER_QUERY_MAX_RESULTS)
    family = generate_query_family(req.topic)
    family_hits = []
    for entry in family:
        result = search_arxiv(query=entry.query, max_results=max_results, sort_by="relevance")
        for paper in result.results:
            family_hits.append(
                {
                    "query_used": entry.query,
                    "query_label": entry.label,
                    "paper": paper.to_dict(),
                }
            )
    ranked = dedupe_and_rank(req.topic, family_hits)
    starmap = build_evidence_topology(ranked)
    return ResearchHuntResponse(
        ok=True,
        topic=req.topic,
        mode=req.mode,
        query_families=[item.to_dict() for item in family],
        candidate_count_before_dedupe=len(family_hits),
        ranked_results=[item.to_dict() for item in ranked],
        starmap=starmap.to_dict(),
        cache=get_cache_stats(),
        note="v5 direct_hunt bounded and non-persistent",
    )


@research_bp.post("/hunt")
def research_hunt() -> object:
    try:
        req = ResearchHuntRequest.from_json(_json_body())
        if not req.topic:
            return _error("BAD_REQUEST", "topic is required", 400)
        if req.mode != "direct_hunt":
            return _error("MODE_NOT_ENABLED", "v5 supports direct_hunt only", 400)
        return jsonify(_direct_hunt_payload(req).to_dict())
    except ArxivRateLimitedError as e:
        return _error(e.error_code, str(e), 429, retryable=True)
    except ArxivUnavailableError as e:
        return _error(e.error_code, str(e), 503, retryable=True)
    except ArxivBadResponseError as e:
        return _error(e.error_code, str(e), 502, retryable=False)
    except (OSError, RuntimeError, ValueError, TypeError) as e:
        return _error("HUNT_FAILED", str(e), 500, retryable=False)
