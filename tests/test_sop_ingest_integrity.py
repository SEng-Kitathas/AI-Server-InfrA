from __future__ import annotations

import hashlib
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

import sop_ingest as sop


class SopIngestIntegrityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.projects = Path(self.temp.name) / "projects"
        self.projects.mkdir(parents=True)
        self.root_patch = patch.object(sop, "get_project_root", lambda project_id: self.projects / project_id)
        self.root_patch.start()
        (self.projects / "alpha").mkdir(parents=True)

    def tearDown(self) -> None:
        self.root_patch.stop()
        self.temp.cleanup()

    def _prepare_registered_single_file(self, content: str = "hello world"):
        source = Path(self.temp.name) / "source"
        source.mkdir()
        target = source / "file.txt"
        target.write_text(content, encoding="utf-8")
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        meta = {
            "project_id": "alpha",
            "corpus_id": "c1",
            "source_path": str(source),
            "verified": True,
            "chunk_chars": 1000,
            "files": [
                {
                    "seq": 1,
                    "file_name": "file.txt",
                    "bytes": len(target.read_bytes()),
                    "sha256": digest,
                    "chars": len(content),
                    "artifact_class": "test",
                    "default_read_next_file": None,
                }
            ],
        }
        state = {
            "project_id": "alpha",
            "corpus_id": "c1",
            "verified": True,
            "current_file_index": 0,
            "current_chunk_index": 0,
            "awaiting_file_completion": False,
            "issued_chunk": None,
            "completed_files": {},
            "acked_chunks": {},
            "completed_at": None,
            "last_action_at": "now",
        }
        sop._save_json(sop._meta_path("alpha", "c1"), meta)
        sop._save_json(sop._state_path("alpha", "c1"), state)
        return source, target, meta, state

    def test_merkle_parser_uses_actual_merkle_match(self) -> None:
        digest = "a" * 64
        self.assertEqual(
            sop._parse_merkle_root(f"Merkle root (sha256): {digest}\n"), digest
        )

    def test_missing_corpus_status_is_read_only(self) -> None:
        corpus_root = self.projects / "alpha" / "system" / "lab" / "corpora"
        self.assertFalse(corpus_root.exists())
        with self.assertRaises(sop.SopError) as caught:
            sop.ingestion_status("alpha", "missing")
        self.assertEqual(caught.exception.code, "SOP_CORPUS_NOT_FOUND")
        self.assertFalse(corpus_root.exists())

    def test_source_change_after_registration_blocks_chunk_delivery(self) -> None:
        _, target, _, _ = self._prepare_registered_single_file("original")
        target.write_text("changed", encoding="utf-8")
        with self.assertRaises(sop.SopError) as caught:
            sop.next_chunk("alpha", "c1")
        self.assertEqual(caught.exception.code, "SOP_SOURCE_CHANGED")
        self.assertNotEqual(
            caught.exception.extra["expected_sha256"],
            caught.exception.extra["actual_sha256"],
        )

    def test_ack_requires_exact_chunk_sha(self) -> None:
        self._prepare_registered_single_file("hello")
        issued = sop.next_chunk("alpha", "c1")
        with self.assertRaises(sop.SopError) as caught:
            sop.ack_chunk("alpha", "c1", issued["ack_token"])
        self.assertEqual(caught.exception.code, "SOP_CHUNK_SHA_REQUIRED")
        status = sop.ingestion_status("alpha", "c1")
        self.assertIsNotNone(status["issued_chunk"])

    def test_concurrent_next_chunk_replays_same_token_and_chunk(self) -> None:
        self._prepare_registered_single_file("hello concurrency")
        barrier = threading.Barrier(3)
        results = []
        errors = []

        def worker():
            try:
                barrier.wait(timeout=5)
                results.append(sop.next_chunk("alpha", "c1"))
            except Exception as exc:  # pragma: no cover
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        barrier.wait(timeout=5)
        for thread in threads:
            thread.join(timeout=5)
        self.assertFalse(errors)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["ack_token"], results[1]["ack_token"])
        self.assertEqual(results[0]["content_sha256"], results[1]["content_sha256"])
        self.assertEqual(results[0]["content"], results[1]["content"])
        self.assertTrue(any(row.get("replayed") is True for row in results))

    def test_guard_requires_fresh_source_currentness_even_if_completion_is_green(self) -> None:
        _, _, meta, state = self._prepare_registered_single_file("hello")
        state["completed_files"] = {"file.txt": {"completed_at": "x", "receipt": {}}}
        state["current_file_index"] = 1
        state["completed_at"] = "done"
        sop._save_json(sop._state_path("alpha", "c1"), state)
        with patch.object(
            sop,
            "_source_currentness",
            return_value={"ok": False, "file_identity_match": False},
        ):
            result = sop.guard_check("alpha", "c1")
        self.assertTrue(result["integrity_verified_at_registration"])
        self.assertTrue(result["ingestion_complete"])
        self.assertFalse(result["source_current"]["ok"])
        self.assertFalse(result["proceed_allowed"])


if __name__ == "__main__":
    unittest.main()
