"""Typed API wire models for bounded research health, search, paper, and hunt responses."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from collections.abc import MutableMapping

from .control_plane_models import (
    CapacitySnapshot,
    CompactControlSurfaceDescriptor,
    CorruptJobFileRecord,
    ExecutionJobRecord,
    ServerCapabilityRouterDescriptor,
    TextWindow,
)
from .api_wire_common import (
    ErrorEnvelope,
    WarningItem,
    IndexCacheStats,
    _require_object,
    _as_str,
    _as_bool,
    _as_int,
)

JsonObject = MutableMapping[str, Any]


@dataclass
class ArxivPaperRecord:
    paper_id: str
    source_id: str
    title: str
    abstract: str
    authors: list[str]
    published: str
    updated: str
    categories: list[str]
    pdf_url: str
    source_url: str
    source_quality: str

    def to_dict(self) -> JsonObject:
        return asdict(self)


@dataclass
class ArxivSearchResponse:
    ok: bool
    query: str
    max_results: int
    sort_by: str
    results: list[ArxivPaperRecord]

    def to_dict(self) -> JsonObject:
        return {
            "ok": self.ok,
            "query": self.query,
            "max_results": self.max_results,
            "sort_by": self.sort_by,
            "results": [result.to_dict() for result in self.results],
        }


@dataclass
class ArxivSearchRequest:
    query: str
    max_results: int = 8
    sort_by: str = "relevance"

    @classmethod
    def from_json(cls, data: JsonObject) -> "ArxivSearchRequest":
        data = _require_object(data)
        return cls(
            query=_as_str(data.get("query", "")).strip(),
            max_results=int(data.get("max_results", 8)),
            sort_by=_as_str(data.get("sort_by", "relevance"), "relevance"),
        )


@dataclass
class ArxivPaperRequest:
    paper_id: str
    ingestion_run_id: str = "research_v5_run"

    @classmethod
    def from_json(cls, data: JsonObject) -> "ArxivPaperRequest":
        data = _require_object(data)
        return cls(
            paper_id=_as_str(data.get("paper_id", "")).strip(),
            ingestion_run_id=_as_str(
                data.get("ingestion_run_id", "research_v5_run"), "research_v5_run"
            ),
        )


@dataclass
class ResearchHuntRequest:
    topic: str
    mode: str = "direct_hunt"
    max_results: int = 5

    @classmethod
    def from_json(cls, data: JsonObject) -> "ResearchHuntRequest":
        data = _require_object(data)
        return cls(
            topic=_as_str(data.get("topic", "")).strip(),
            mode=_as_str(data.get("mode", "direct_hunt"), "direct_hunt"),
            max_results=int(data.get("max_results", 5)),
        )


@dataclass
class ResearchHealthResponse:
    ok: bool
    status: str
    sources: list[str]
    modes: list[str]
    parser_version: str
    cache: JsonObject
    predator_generation: str
    starmap_layer: str

    def to_dict(self) -> JsonObject:
        return asdict(self)


@dataclass
class ArxivPaperResponse:
    ok: bool
    canonical_paper: JsonObject
    derived_objects: JsonObject

    def to_dict(self) -> JsonObject:
        return asdict(self)


@dataclass
class ResearchHuntResponse:
    ok: bool
    topic: str
    mode: str
    query_families: list[JsonObject]
    candidate_count_before_dedupe: int
    ranked_results: list[JsonObject]
    starmap: JsonObject
    cache: JsonObject
    note: str

    def to_dict(self) -> JsonObject:
        return asdict(self)
