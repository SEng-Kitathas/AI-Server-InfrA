from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

import context_engine


class RehydrateBudgetStrictTests(unittest.TestCase):
    def setUp(self) -> None:
        context_engine._INDEX_CACHE.clear()
        context_engine._INDEX_CACHE_TOTAL_BYTES = 0

    def test_search_hit_selection_never_exceeds_budget(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "state.md").write_text(
                ("needle αβγ important context " * 300), encoding="utf-8"
            )
            result = context_engine.rehydrate_context(
                context_engine.RehydrateRequest(
                    topic="needle important",
                    base_root=str(root),
                    path=".",
                    budget_bytes=127,
                )
            )
        self.assertTrue(result["selected"])
        self.assertLessEqual(result["header"]["used_bytes"], 127)
        self.assertLessEqual(
            sum(len(row["excerpt"].encode("utf-8")) for row in result["selected"]),
            127,
        )
        for row in result["selected"]:
            self.assertLessEqual(row["window"]["start_line"], row["window"]["end_line"])

    def test_recent_fallback_first_item_is_clipped_to_budget(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "code.py").write_text(
                "print('fallback')\n" + ("界" * 5000), encoding="utf-8"
            )
            result = context_engine.rehydrate_context(
                context_engine.RehydrateRequest(
                    topic="term_that_will_not_match_anything",
                    base_root=str(root),
                    path=".",
                    budget_bytes=65,
                )
            )
        self.assertTrue(result["selected"])
        self.assertLessEqual(result["header"]["used_bytes"], 65)
        self.assertLessEqual(len(result["selected"][0]["excerpt"].encode("utf-8")), 65)

    def test_clip_helper_never_splits_into_over_budget_utf8(self) -> None:
        clipped = context_engine._clip_excerpt_to_budget("界" * 100, 10)
        self.assertLessEqual(len(clipped.encode("utf-8")), 10)

    def test_omitted_budget_uses_finite_default_not_unbounded_sentinel(self) -> None:
        request = context_engine.RehydrateRequest(topic="frontier", budget_bytes=None)
        self.assertEqual(context_engine._rehydrate_budget(request), 40_000)

    def test_explicit_unbounded_budget_does_not_request_absurd_single_file_read(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "small.md"
            path.write_text("alpha\nbeta\n", encoding="utf-8")
            content, start, end = context_engine._read_prefix_bounded(
                path, context_engine.MAX_REHYDRATE_BUDGET_BYTES
            )
        self.assertEqual(content, "alpha\nbeta\n")
        self.assertEqual((start, end), (1, 2))


if __name__ == "__main__":
    unittest.main()
