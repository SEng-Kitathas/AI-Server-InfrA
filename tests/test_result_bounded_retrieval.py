from __future__ import annotations

import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT))

import lab_results
import lab_routes


class ResultBoundedRetrievalTests(unittest.TestCase):
    def _root_patch(self, root: Path):
        return patch.object(lab_results, "get_project_root", return_value=root)

    def test_range_is_bounded_and_exact(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self._root_patch(root):
                meta = lab_results.store_result("alpha", {"blob": "x" * 50000}, label="big")
                path = lab_results.result_path("alpha", meta["handle"])
                raw = path.read_bytes()
                row = lab_results.read_result_range(
                    "alpha", meta["handle"], offset_bytes=123, length_bytes=999999
                )
            self.assertEqual(row["length_bytes"], lab_results.RESULT_RANGE_MAX_BYTES if len(raw) - 123 >= lab_results.RESULT_RANGE_MAX_BYTES else len(raw) - 123)
            decoded = base64.b64decode(row["data_b64"])
            self.assertEqual(decoded, raw[123 : 123 + row["length_bytes"]])
            self.assertEqual(row["total_bytes"], len(raw))
            self.assertEqual(len(row["sha256"]), 64)

    def test_small_auto_result_remains_full_for_compatibility(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self._root_patch(root):
                meta = lab_results.store_result("alpha", {"value": 1})
                app = Flask(__name__)
                with app.test_request_context(
                    "/lab/results/get",
                    method="POST",
                    json={"project_id": "alpha", "handle": meta["handle"]},
                ), patch.object(lab_routes, "_auth", return_value=None):
                    response = lab_routes.lab_results_get()
                    payload = response.get_json()
            self.assertEqual(payload["mode"], "full")
            self.assertEqual(payload["payload"], {"value": 1})

    def test_large_auto_result_returns_preview_not_full_payload(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self._root_patch(root):
                meta = lab_results.store_result("alpha", {"blob": "x" * 50000})
                app = Flask(__name__)
                with app.test_request_context(
                    "/lab/results/get",
                    method="POST",
                    json={"project_id": "alpha", "handle": meta["handle"]},
                ), patch.object(lab_routes, "_auth", return_value=None):
                    response = lab_routes.lab_results_get()
                    payload = response.get_json()
            self.assertEqual(payload["mode"], "preview")
            self.assertTrue(payload["summary"]["truncated"])
            self.assertTrue(payload["full_available"])
            self.assertTrue(payload["range_available"])
            self.assertNotIn("payload", payload)
            self.assertLessEqual(len(payload["summary"]["preview"]), 1200)

    def test_metadata_mode_returns_identity_without_payload(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self._root_patch(root):
                meta = lab_results.store_result("alpha", {"blob": "x" * 10000}, label="thing", tool_name="x.y")
                app = Flask(__name__)
                with app.test_request_context(
                    "/lab/results/get",
                    method="POST",
                    json={"project_id": "alpha", "handle": meta["handle"], "mode": "metadata"},
                ), patch.object(lab_routes, "_auth", return_value=None):
                    response = lab_routes.lab_results_get()
                    payload = response.get_json()
            self.assertEqual(payload["mode"], "metadata")
            self.assertEqual(payload["label"], "thing")
            self.assertEqual(payload["tool_name"], "x.y")
            self.assertNotIn("payload", payload)
            self.assertEqual(len(payload["sha256"]), 64)

    def test_explicit_full_is_opt_in_even_for_large_result(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self._root_patch(root):
                meta = lab_results.store_result("alpha", {"blob": "x" * 20000})
                app = Flask(__name__)
                with app.test_request_context(
                    "/lab/results/get",
                    method="POST",
                    json={"project_id": "alpha", "handle": meta["handle"], "mode": "full"},
                ), patch.object(lab_routes, "_auth", return_value=None):
                    response = lab_routes.lab_results_get()
                    payload = response.get_json()
            self.assertEqual(payload["mode"], "full")
            self.assertEqual(len(payload["payload"]["blob"]), 20000)

    def test_range_route_caps_requested_length(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self._root_patch(root):
                meta = lab_results.store_result("alpha", {"blob": "x" * 200000})
                app = Flask(__name__)
                with app.test_request_context(
                    "/lab/results/get",
                    method="POST",
                    json={
                        "project_id": "alpha",
                        "handle": meta["handle"],
                        "mode": "range",
                        "offset_bytes": 0,
                        "length_bytes": 999999999,
                    },
                ), patch.object(lab_routes, "_auth", return_value=None):
                    response = lab_routes.lab_results_get()
                    payload = response.get_json()
            self.assertEqual(payload["mode"], "range")
            self.assertLessEqual(payload["length_bytes"], lab_results.RESULT_RANGE_MAX_BYTES)
            self.assertLessEqual(len(base64.b64decode(payload["data_b64"])), lab_results.RESULT_RANGE_MAX_BYTES)


if __name__ == "__main__":
    unittest.main()
