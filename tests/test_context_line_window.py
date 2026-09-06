from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT))

import context_engine
import context_routes


class ContextLineWindowTests(unittest.TestCase):
    def test_engine_reads_requested_line_window(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "sample.txt"
            target.write_text("one\ntwo\nthree\nfour\nfive\n", encoding="utf-8")
            result = context_engine.read_file(
                context_engine.FileReadRequest(
                    path="sample.txt",
                    base_root=str(root),
                    start_line=2,
                    end_line=4,
                    max_bytes=5000,
                )
            )
        payload = result.to_dict()
        self.assertEqual(payload["content"], "two\nthree\nfour")
        self.assertEqual(payload["slice"]["start_line"], 2)
        self.assertEqual(payload["slice"]["end_line"], 4)

    def test_http_project_file_read_line_window_does_not_500(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "sample.txt"
            target.write_text("a\nb\nc\nd\n", encoding="utf-8")
            app = Flask(__name__)
            with app.test_request_context(
                "/project/files/read",
                method="POST",
                json={
                    "project_id": "alpha",
                    "path": "sample.txt",
                    "start_line": 2,
                    "end_line": 3,
                    "max_bytes": 4096,
                },
            ), patch.object(context_routes, "_auth", return_value=None), patch.object(
                context_routes, "project_root_path", return_value=str(root)
            ):
                response = context_routes.project_files_read()
                payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["content"], "b\nc")
        self.assertEqual(payload["slice"]["start_line"], 2)
        self.assertEqual(payload["slice"]["end_line"], 3)


if __name__ == "__main__":
    unittest.main()
