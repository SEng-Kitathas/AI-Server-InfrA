from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

import context_engine as ce


class IcfCsRehydrationTests(unittest.TestCase):
    def setUp(self) -> None:
        with ce._INDEX_CACHE_LOCK:
            ce._INDEX_CACHE.clear()
            ce._INDEX_CACHE_TOTAL_BYTES = 0

    def _write_icf_project(self, root: Path) -> None:
        files = {
            "state/current/CURRENT_STATE.md": "FRONTIER current state\ncurrent blocker none\n",
            "state/doctrine_snapshot/INTENT_CONSTRAINT_FRONTIER_CONTINUITY_STANDARD.md": "ICF STANDARD\nDIRECTION != CONSTRAINTS != FRONTIER != HISTORY\n",
            "checkpoints/COMMANDERS_INTENT_CURRENT.md": "INTENT\nbuild the durable laboratory runtime\n",
            "state/next_steps/NEXT_STEPS.md": "FRONTIER next\ncontinue hostile audit\n",
            "state/doctrine_snapshot/DOCTRINE_SNAPSHOT.md": "CONSTRAINTS doctrine\ntransport is not authority\n",
            "state/revisit_ledger/REVISIT_LEDGER.md": "CONSTRAINTS revisit\nkeep scars visible\n",
            "state/trace_matrix/TRACE_MATRIX.md": "CONSTRAINTS trace\nclaims require evidence\n",
            "continuity/live_shadow/LIVE_SHADOW.md": "HISTORY ACTIVE\nlive shadow shadowwarmtoken\n",
            "continuity/research_epistemic_shadow/RESEARCH_EPISTEMIC_SHADOW.md": "EPISTEMIC RES\nUNKNOWN — fixture research frontier\n",
            "continuity/design_thread_stream/DESIGN_THREAD_STREAM.md": "HISTORY CHRONOLOGY\nphase sequence\n",
            ".pcmmad_sync_runs/noise.log": "needle needle needle newest misleading transient log\n",
            ".pcmmad_hardening_postpub_stage/stale.md": "needle needle stale staged recovery replica\n",
            ".pcmmad_stage_rollover_commanders.md": "needle needle stale root-level stage replica\n",
            ".pcmmad_tmp_fake.md": "needle needle misleading scratch handoff\n",
        }
        for rel, text in files.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    def test_default_root_search_skips_transient_internal_noise(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_icf_project(root)
            result = ce.search_files(
                ce.FileSearchRequest(
                    query="needle",
                    base_root=str(root),
                    path=".",
                    recursive=True,
                    limit=20,
                )
            ).to_dict()
        self.assertEqual(result["count"], 0)
        self.assertFalse(any(".pcmmad_sync_runs" in hit["path"] for hit in result["hits"]))
        self.assertFalse(any(".pcmmad_hardening_postpub_stage" in hit["path"] for hit in result["hits"]))
        self.assertFalse(any(Path(hit["path"]).name.startswith(".pcmmad_") for hit in result["hits"]))

    def test_explicit_internal_path_target_remains_searchable(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_icf_project(root)
            result = ce.search_files(
                ce.FileSearchRequest(
                    query="needle",
                    base_root=str(root),
                    path=".pcmmad_sync_runs",
                    recursive=True,
                    limit=20,
                )
            ).to_dict()
        self.assertEqual(result["count"], 1)
        self.assertIn(".pcmmad_sync_runs", result["hits"][0]["path"])

    def test_cache_invalidates_immediately_on_same_size_mtime_change(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "state.md"
            target.write_text("cacheoldtoken", encoding="utf-8")
            first = ce.search_files(
                ce.FileSearchRequest(query="cacheoldtoken", base_root=str(root), path=".", limit=10)
            ).to_dict()
            self.assertEqual(first["count"], 1)
            old = target.stat()
            target.write_text("cachenewtoken", encoding="utf-8")  # same byte length
            os.utime(target, ns=(old.st_atime_ns, old.st_mtime_ns + 5_000_000))
            second = ce.search_files(
                ce.FileSearchRequest(query="cachenewtoken", base_root=str(root), path=".", limit=10)
            ).to_dict()
            stale = ce.search_files(
                ce.FileSearchRequest(query="cacheoldtoken", base_root=str(root), path=".", limit=10)
            ).to_dict()
        self.assertEqual(second["count"], 1)
        self.assertIn("cachenewtoken", second["hits"][0]["excerpt"])
        self.assertEqual(stale["count"], 0)
        self.assertEqual(
            second["index_cache"]["source_currentness"],
            "canonical_path+size+mtime_ns",
        )

    def test_root_rehydrate_seeds_all_icf_authority_roles_before_noise(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_icf_project(root)
            result = ce.rehydrate_context(
                ce.RehydrateRequest(
                    topic="needle only appears in transient runtime noise",
                    base_root=str(root),
                    path=".",
                    budget_bytes=32000,
                )
            )
        classes = [row["artifact_class"] for row in result["selected"]]
        for expected in ce.ICF_ANCHOR_CLASSES:
            self.assertIn(expected, classes)
        self.assertFalse(any(".pcmmad_sync_runs" in row["path"] for row in result["selected"]))
        self.assertFalse(any(".pcmmad_hardening_postpub_stage" in row["path"] for row in result["selected"]))
        self.assertFalse(any(Path(row["path"]).name.startswith(".pcmmad_") for row in result["selected"]))
        paths = [row["path"] for row in result["selected"]]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertEqual(result["icf_cs"]["version"], "1.2")
        self.assertEqual(
            result["icf_cs"]["cold_start_law"],
            "DIRECTION != CONSTRAINTS != FRONTIER != HISTORY",
        )
        self.assertEqual(result["open_seams"], [])
        roles = {row.get("authority_role") for row in result["selected"] if row.get("seeded")}
        self.assertTrue({"frontier", "standard", "intent", "constraints", "epistemic", "history"}.issubset(roles))

    def test_moving_frontier_anchor_seeds_bounded_tail_not_stale_header(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            current = root / "state" / "current" / "CURRENT_STATE.md"
            current.parent.mkdir(parents=True)
            current.write_text(
                "STALE_HEADER A-OLD\n"
                + "\n".join(f"historical filler {i:04d} xxxxxxxxxxxxxxxxxxxx" for i in range(250))
                + "\nCURRENT_FRONTIER NEW_HEAD_ABC123\nNEXT current repair qualification\n",
                encoding="utf-8",
            )
            result = ce.rehydrate_context(
                ce.RehydrateRequest(
                    topic="current frontier",
                    base_root=str(root),
                    path=".",
                    budget_bytes=1024,
                )
            )
        row = next(item for item in result["selected"] if item["artifact_class"] == "state.current")
        self.assertTrue(row["seeded"])
        self.assertEqual(row["seed_window"], "tail")
        self.assertGreater(row["window"]["start_line"], 1)
        self.assertIn("CURRENT_FRONTIER NEW_HEAD_ABC123", row["excerpt"])
        self.assertNotIn("STALE_HEADER A-OLD", row["excerpt"])

    def test_live_shadow_update_is_visible_on_next_rehydrate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_icf_project(root)
            live = root / "continuity" / "live_shadow" / "LIVE_SHADOW.md"
            # Warm both search/index and rehydration paths with the old content.
            ce.search_files(
                ce.FileSearchRequest(query="shadowwarmtoken", base_root=str(root), path=".", limit=20)
            )
            before = ce.rehydrate_context(
                ce.RehydrateRequest(topic="shadowwarmtoken", base_root=str(root), path=".", budget_bytes=32000)
            )
            old_stat = live.stat()
            live.write_text("HISTORY ACTIVE\nlive shadow UPDATED\n", encoding="utf-8")
            os.utime(live, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns + 5_000_000))
            after = ce.rehydrate_context(
                ce.RehydrateRequest(topic="UPDATED", base_root=str(root), path=".", budget_bytes=32000)
            )
        before_live = next(row for row in before["selected"] if row["artifact_class"] == "continuity.live_shadow")
        after_live = next(row for row in after["selected"] if row["artifact_class"] == "continuity.live_shadow")
        self.assertIn("shadowwarmtoken", before_live["excerpt"])
        self.assertIn("UPDATED", after_live["excerpt"])
        self.assertNotIn("live shadow shadowwarmtoken", after_live["excerpt"])

    def test_doctrine_revisit_trace_are_first_class_rehydrate_priorities(self) -> None:
        priority = ce._rehydrate_priority()
        self.assertIn("state.doctrine_snapshot", priority)
        self.assertIn("state.revisit_ledger", priority)
        self.assertIn("state.trace_matrix", priority)
        self.assertLess(priority.index("state.doctrine_snapshot"), priority.index("code"))
        self.assertLess(priority.index("state.revisit_ledger"), priority.index("generic"))
        self.assertLess(priority.index("state.trace_matrix"), priority.index("generic"))


if __name__ == "__main__":
    unittest.main()
