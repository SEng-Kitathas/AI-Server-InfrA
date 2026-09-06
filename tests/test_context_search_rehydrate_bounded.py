from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT))

import context_engine


class ContextSearchRehydrateBoundedTests(unittest.TestCase):
    def setUp(self) -> None:
        context_engine._INDEX_CACHE.clear()
        context_engine._INDEX_CACHE_TOTAL_BYTES = 0

    def test_search_indexes_only_bounded_prefix_without_read_text(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "large.txt"
            target.write_bytes(
                b"needle present near the front\n"
                + (b"x" * (context_engine.MAX_SEARCH_FILE_BYTES + 100000))
            )
            with patch.object(Path, "read_text", side_effect=AssertionError("whole-file read_text forbidden")):
                result = context_engine.search_files(
                    context_engine.FileSearchRequest(
                        query="needle",
                        base_root=str(root),
                        path=".",
                        recursive=True,
                        limit=10,
                    )
                )
        payload = result.to_dict()
        self.assertEqual(payload["count"], 1)
        self.assertIn("needle", payload["hits"][0]["excerpt"].lower())
        cached = context_engine._INDEX_CACHE.get(str(target)) or context_engine._INDEX_CACHE.get(str(target.resolve()))
        if cached:
            indexed = cached["payload"]
            self.assertLessEqual(len(indexed["content"].encode("utf-8")), context_engine.MAX_SEARCH_FILE_BYTES)

    def test_rehydrate_recent_fallback_uses_bounded_excerpt_without_read_text(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "code.py"
            target.write_bytes(b"print('fallback')\n" + (b"z" * 200000))
            with patch.object(Path, "read_text", side_effect=AssertionError("whole-file read_text forbidden")):
                result = context_engine.rehydrate_context(
                    context_engine.RehydrateRequest(
                        topic="term_that_does_not_exist_anywhere",
                        base_root=str(root),
                        path=".",
                        budget_bytes=8000,
                    )
                )
        self.assertTrue(result["ok"])
        self.assertTrue(result["selected"])
        excerpt = result["selected"][0]["excerpt"]
        self.assertLessEqual(len(excerpt.encode("utf-8")), 4000)
        self.assertIn("fallback", excerpt)


if __name__ == "__main__":
    unittest.main()
