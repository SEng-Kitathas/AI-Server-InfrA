from __future__ import annotations

import threading
import time
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT))

import lab_tools
import lab_tools_research as ltr
import research_arxiv as arx
from research_models import QueryFamilyEntry


class FakeResponse:
    def __init__(self, chunks, status_code=200, url="https://export.arxiv.org/api/query"):
        self._chunks = list(chunks)
        self.status_code = status_code
        self.url = url

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def iter_content(self, chunk_size=65536):
        for chunk in self._chunks:
            yield chunk


class ResearchBoundedControlTests(unittest.TestCase):
    def setUp(self) -> None:
        with arx._CACHE_LOCK:
            arx._CACHE.clear()
            arx._CACHE_BYTES = 0

    def test_cache_prune_over_budget_does_not_hit_old_undefined_variable_branch(self) -> None:
        old_cap = arx.CACHE_MAX_BYTES
        try:
            arx.CACHE_MAX_BYTES = 64
            arx._cache_put("a", "x" * 40)
            arx._cache_put("b", "y" * 40)
            stats = arx.get_cache_stats()
            self.assertLessEqual(stats["bytes"], 64)
            self.assertLessEqual(stats["entries"], 1)
        finally:
            arx.CACHE_MAX_BYTES = old_cap

    def test_cache_put_get_remain_coherent_under_threads(self) -> None:
        errors = []

        def worker(idx: int) -> None:
            try:
                for j in range(100):
                    key = f"{idx}-{j % 7}"
                    arx._cache_put(key, {"i": idx, "j": j})
                    arx._cache_get(key)
            except Exception as exc:  # pragma: no cover - collected for assertion
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertFalse(errors)
        stats = arx.get_cache_stats()
        self.assertGreaterEqual(stats["bytes"], 0)
        self.assertLessEqual(stats["bytes"], stats["max_bytes"])

    def test_http_body_is_streamed_and_rejected_when_over_bound(self) -> None:
        response = FakeResponse([b"x" * 800, b"y" * 800])
        with patch.object(arx.requests, "get", return_value=response) as getter:
            with self.assertRaises(arx.ArxivBadResponseError) as caught:
                arx._request({"search_query": "all:test"}, max_response_bytes=1024)
        self.assertIn("exceeded bounded body limit", str(caught.exception))
        self.assertTrue(getter.call_args.kwargs["stream"])

    def test_hunt_returns_partial_results_when_later_query_fails(self) -> None:
        family = [
            QueryFamilyEntry(label="one", query="q1"),
            QueryFamilyEntry(label="two", query="q2"),
        ]
        fake_paper = {
            "paper_id": "arXiv:1",
            "source_id": "https://arxiv.org/abs/1",
            "title": "Test",
            "abstract": "bounded system",
            "authors": [],
            "published": "2026-01-01",
            "updated": "2026-01-01",
            "categories": [],
            "pdf_url": "",
            "source_url": "https://arxiv.org/abs/1",
            "source_quality": "abstract_only",
        }
        first = SimpleNamespace(results=[fake_paper])
        calls = []

        def search_arxiv(query, max_results, sort_by, request_timeout_seconds):
            calls.append((query, request_timeout_seconds))
            if query == "q1":
                return first
            raise arx.ArxivUnavailableError("down")

        with patch.object(ltr, "generate_query_family", return_value=family), patch.object(
            ltr, "search_arxiv", side_effect=search_arxiv
        ):
            result = ltr._research_hunt_result(
                "topic", "direct_hunt", 3, wall_seconds=10
            )
        self.assertTrue(result["partial"])
        self.assertEqual(result["queries_attempted"], 2)
        self.assertEqual(result["queries_planned"], 2)
        self.assertEqual(len(result["query_errors"]), 1)
        self.assertGreaterEqual(result["candidate_count_before_dedupe"], 1)
        self.assertLessEqual(max(timeout for _, timeout in calls), 10)

    def test_hunt_stops_before_starting_query_after_wall_budget_exhaustion(self) -> None:
        family = [
            QueryFamilyEntry(label="one", query="q1"),
            QueryFamilyEntry(label="two", query="q2"),
        ]
        clock = iter([0.0, 0.0, 5.1, 5.2, 5.3])
        attempts = []

        def search_arxiv(**kwargs):
            attempts.append(kwargs["query"])
            return SimpleNamespace(results=[])

        with patch.object(ltr, "generate_query_family", return_value=family), patch.object(
            ltr, "search_arxiv", side_effect=search_arxiv
        ), patch.object(ltr.time, "monotonic", side_effect=lambda: next(clock)):
            result = ltr._research_hunt_result(
                "topic", "direct_hunt", 3, wall_seconds=5
            )
        self.assertEqual(attempts, ["q1"])
        self.assertTrue(result["budget_exhausted"])
        self.assertTrue(result["partial"])
        self.assertEqual(result["queries_attempted"], 1)

    def test_research_contracts_expose_bounded_control_traits(self) -> None:
        tools = {row["name"]: row for row in lab_tools.list_tools()}
        hunt = tools["research.hunt"]
        self.assertTrue(
            {"bounded_network_timeout", "bounded_wall_time", "partial_results"}.issubset(
                set(hunt["effect_traits"])
            )
        )
        for name in ("research.arxiv.search", "research.arxiv.paper"):
            self.assertIn("bounded_network_timeout", tools[name]["effect_traits"])


if __name__ == "__main__":
    unittest.main()
