"""arXiv API search/fetch client with bounded in-memory response cache."""

from __future__ import annotations
from collections.abc import MutableMapping
import threading
import time
import xml.etree.ElementTree as ET
from typing import Any
from api_wire_models import ArxivPaperRecord, ArxivSearchResponse
import requests
from research_config import (
    ARXIV_API_URL,
    ARXIV_MAX_RESPONSE_BYTES,
    ARXIV_XML_NAMESPACES,
    REQUEST_TIMEOUT_SECONDS,
    RESEARCH_CACHE_MAX_BYTES,
)

JsonObject = MutableMapping[str, Any]

_CACHE: dict[str, JsonObject] = {}
CACHE_TTL_SECONDS = 300
CACHE_MAX_BYTES = RESEARCH_CACHE_MAX_BYTES
_CACHE_BYTES = 0
_CACHE_LOCK = threading.RLock()


class ArxivError(Exception):
    error_code = "ARXIV_ERROR"


class ArxivRateLimitedError(ArxivError):
    error_code = "ARXIV_SEARCH_FAILED"


class ArxivUnavailableError(ArxivError):
    error_code = "ARXIV_UNAVAILABLE"


class ArxivBadResponseError(ArxivError):
    error_code = "ARXIV_BAD_RESPONSE"


def _estimate_size(obj: Any) -> int:
    return len(str(obj).encode("utf-8"))


def _prune_cache_locked() -> None:
    global _CACHE_BYTES
    now = time.time()
    expired = [
        cache_key
        for cache_key, cache_record in _CACHE.items()
        if now - cache_record["time"] > CACHE_TTL_SECONDS
    ]
    for cache_key in expired:
        old = _CACHE.pop(cache_key, None)
        if old:
            _CACHE_BYTES -= int(old.get("size", 0))
    if _CACHE_BYTES > CACHE_MAX_BYTES:
        for cache_key, cache_record in sorted(_CACHE.items(), key=lambda item: item[1]["time"]):
            _CACHE.pop(cache_key, None)
            _CACHE_BYTES -= int(cache_record.get("size", 0))
            if _CACHE_BYTES <= CACHE_MAX_BYTES:
                break
    _CACHE_BYTES = max(0, _CACHE_BYTES)


def _prune_cache() -> None:
    with _CACHE_LOCK:
        _prune_cache_locked()


def get_cache_stats() -> JsonObject:
    with _CACHE_LOCK:
        _prune_cache_locked()
        return {
            "entries": len(_CACHE),
            "bytes": max(_CACHE_BYTES, 0),
            "max_bytes": CACHE_MAX_BYTES,
            "ttl_seconds": CACHE_TTL_SECONDS,
        }


def _cache_get(key: str) -> Any | None:
    with _CACHE_LOCK:
        _prune_cache_locked()
        entry = _CACHE.get(key)
        if not entry:
            return None
        if time.time() - entry["time"] > CACHE_TTL_SECONDS:
            return None
        return entry["value"]


def _cache_put(key: str, value: Any) -> None:
    global _CACHE_BYTES
    size = _estimate_size(value)
    # A single entry larger than the whole cache budget is not worth caching.
    if size > CACHE_MAX_BYTES:
        return
    with _CACHE_LOCK:
        old = _CACHE.pop(key, None)
        if old:
            _CACHE_BYTES -= int(old.get("size", 0))
        _CACHE[key] = {"time": time.time(), "value": value, "size": size}
        _CACHE_BYTES += size
        _prune_cache_locked()


def _strip_arxiv_prefix(paper_id: str) -> str:
    pid = paper_id.strip()
    if pid.lower().startswith("arxiv:"):
        pid = pid.split(":", 1)[1]
    return pid


def _request(
    params: JsonObject,
    *,
    timeout_seconds: int | float = REQUEST_TIMEOUT_SECONDS,
    max_response_bytes: int = ARXIV_MAX_RESPONSE_BYTES,
) -> str:
    timeout = max(0.25, min(float(timeout_seconds), float(REQUEST_TIMEOUT_SECONDS)))
    byte_cap = max(1024, min(int(max_response_bytes), int(ARXIV_MAX_RESPONSE_BYTES)))
    try:
        with requests.get(
            ARXIV_API_URL,
            params=params,
            timeout=timeout,
            headers={"User-Agent": "PCMMAD-Receiver/5.0"},
            stream=True,
        ) as resp:
            if resp.status_code == 429:
                raise ArxivRateLimitedError(
                    f"{resp.status_code} Client Error: rate limit for url: {resp.url}"
                )
            if 500 <= resp.status_code < 600:
                raise ArxivUnavailableError(f"{resp.status_code} Server Error for url: {resp.url}")
            if resp.status_code != 200:
                raise ArxivBadResponseError(f"{resp.status_code} Client Error for url: {resp.url}")
            chunks: list[bytes] = []
            used = 0
            for chunk in resp.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                remaining = byte_cap + 1 - used
                if remaining <= 0:
                    break
                take = chunk[:remaining]
                chunks.append(take)
                used += len(take)
                if used > byte_cap:
                    raise ArxivBadResponseError(
                        f"arXiv response exceeded bounded body limit of {byte_cap} bytes"
                    )
            raw = b"".join(chunks)
    except (ArxivError,):
        raise
    except requests.RequestException as e:
        raise ArxivUnavailableError(str(e))
    return raw.decode("utf-8", errors="replace")


def _entry_pdf_url(entry: ET.Element, ns: dict[str, str]) -> str:
    for link in entry.findall("atom:link", ns):
        href = link.attrib.get("href", "")
        title_attr = link.attrib.get("title", "")
        rel = link.attrib.get("rel", "")
        if title_attr == "pdf" or (rel == "related" and "pdf" in href):
            return href
    return ""


def _entry_terms(entry: ET.Element, ns: dict[str, str]) -> list[str]:
    return [
        category.attrib.get("term", "").strip()
        for category in entry.findall("atom:category", ns)
        if category.attrib.get("term", "").strip()
    ]


def _paper_from_entry(entry: ET.Element, ns: dict[str, str]) -> ArxivPaperRecord:
    entry_id = entry.findtext("atom:id", default="", namespaces=ns).strip()
    paper_id = entry_id.rsplit("/", 1)[-1]
    return ArxivPaperRecord(
        paper_id=f"arXiv:{paper_id}",
        source_id=entry_id,
        title=" ".join(entry.findtext("atom:title", default="", namespaces=ns).split()),
        abstract=" ".join(entry.findtext("atom:summary", default="", namespaces=ns).split()),
        authors=[
            author.findtext("atom:name", default="", namespaces=ns).strip()
            for author in entry.findall("atom:author", ns)
        ],
        published=entry.findtext("atom:published", default="", namespaces=ns).strip(),
        updated=entry.findtext("atom:updated", default="", namespaces=ns).strip(),
        categories=_entry_terms(entry, ns),
        pdf_url=_entry_pdf_url(entry, ns),
        source_url=entry_id,
        source_quality="abstract_only",
    )


def _parse_feed(xml_text: str) -> list[ArxivPaperRecord]:
    ns = dict(ARXIV_XML_NAMESPACES)
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ArxivBadResponseError(f"Could not parse arXiv response XML: {e}")
    return [_paper_from_entry(entry, ns) for entry in root.findall("atom:entry", ns)]


def search_arxiv(
    query: str,
    max_results: int = 8,
    sort_by: str = "relevance",
    *,
    request_timeout_seconds: int | float = REQUEST_TIMEOUT_SECONDS,
) -> ArxivSearchResponse:
    key = f"search::{query}::{max_results}::{sort_by}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    xml = _request(
        {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": "descending",
        },
        timeout_seconds=request_timeout_seconds,
    )
    results = _parse_feed(xml)
    payload = ArxivSearchResponse(
        ok=True, query=query, max_results=max_results, sort_by=sort_by, results=results
    )
    _cache_put(key, payload)
    return payload


def fetch_arxiv_paper(
    paper_id: str, *, request_timeout_seconds: int | float = REQUEST_TIMEOUT_SECONDS
) -> ArxivPaperRecord:
    stripped = _strip_arxiv_prefix(paper_id)
    key = f"paper::{stripped}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    xml = _request(
        {"id_list": stripped, "start": 0, "max_results": 1},
        timeout_seconds=request_timeout_seconds,
    )
    results = _parse_feed(xml)
    if not results:
        raise ValueError(f"Paper not found: {paper_id}")
    payload = results[0]
    _cache_put(key, payload)
    return payload
