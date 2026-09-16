from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT))

import lab_routes


class BatchResultBoundednessTests(unittest.TestCase):
    def test_small_foreground_batch_stays_inline(self) -> None:
        response = lab_routes._batch_response_payload([{"ok": True}], 1)
        result = lab_routes._bounded_foreground_batch_response(
            {"project_id": "alpha"}, response
        )
        self.assertIs(result, response)
        self.assertFalse(result["atomic"])

    def test_large_foreground_batch_is_stored_and_returns_compact_receipt(self) -> None:
        response = lab_routes._batch_response_payload(
            [{"ok": True, "payload": "x" * 13000}], 2
        )
        meta = {
            "handle": "res-test",
            "bytes": 14000,
            "sha256": "a" * 64,
        }
        with patch.object(lab_routes, "store_result", return_value=meta) as store:
            result = lab_routes._bounded_foreground_batch_response(
                {"project_id": "alpha"}, response
            )
        self.assertTrue(result["stored"])
        self.assertEqual(result["handle"], "res-test")
        self.assertNotIn("results", result)
        self.assertFalse(result["atomic"])
        store.assert_called_once()

    def test_caller_cannot_raise_foreground_safety_ceiling(self) -> None:
        response = lab_routes._batch_response_payload(
            [{"ok": True, "payload": "x" * 13000}], 1
        )
        meta = {"handle": "res-test", "bytes": 14000, "sha256": "b" * 64}
        with patch.object(lab_routes, "store_result", return_value=meta) as store:
            result = lab_routes._bounded_foreground_batch_response(
                {
                    "project_id": "alpha",
                    "result_handle_threshold_chars": 99999999,
                },
                response,
            )
        self.assertTrue(result["stored"])
        store.assert_called_once()

    def test_no_project_id_preserves_legacy_inline_response(self) -> None:
        response = lab_routes._batch_response_payload(
            [{"ok": True, "payload": "x" * 30000}], 1
        )
        with patch.object(lab_routes, "store_result") as store:
            result = lab_routes._bounded_foreground_batch_response({}, response)
        self.assertIs(result, response)
        store.assert_not_called()


if __name__ == "__main__":
    unittest.main()
