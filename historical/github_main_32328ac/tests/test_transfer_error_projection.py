from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "baseline"))

from pcmmad_receiver import lab_tools
from pcmmad_receiver import transfer_plane as tp


class TransferErrorProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = {}
        def register_tool(name, *_args, **_kwargs):
            def decorate(fn):
                self.registry[name] = fn
                return fn
            return decorate
        tp.register(register_tool)

    def test_transfer_and_lab_use_same_structured_error_type(self) -> None:
        self.assertIs(tp.LabToolError, lab_tools.LabToolError)

    def test_live_value_error_failures_project_as_transfer_error_400(self) -> None:
        messages = [
            "resolved path escapes project transfer scope",
            "offset mismatch: expected 0, got 1",
            "chunk sha256 mismatch",
            "destination changed after import ticket creation",
            "full sha256 mismatch: abc",
        ]
        for message in messages:
            with self.subTest(message=message), patch.object(tp, "append_chunk", side_effect=ValueError(message)):
                with self.assertRaises(lab_tools.LabToolError) as caught:
                    self.registry["transfer.chunk.write"]({"ticket": "t", "offset": 0, "data_b64": "", "chunk_sha256": ""})
                self.assertEqual(caught.exception.error_code, "TRANSFER_ERROR")
                self.assertEqual(caught.exception.message, message)
                self.assertEqual(caught.exception.status, 400)
                self.assertEqual(caught.exception.extra.get("transfer_exception"), "ValueError")

    def test_file_not_found_projects_as_not_found_404(self) -> None:
        with patch.object(tp, "_load", side_effect=FileNotFoundError("missing ticket")):
            with self.assertRaises(lab_tools.LabToolError) as caught:
                self.registry["transfer.meta"]({"ticket": "missing"})
        self.assertEqual(caught.exception.error_code, "NOT_FOUND")
        self.assertEqual(caught.exception.status, 404)
        self.assertEqual(caught.exception.extra.get("transfer_exception"), "FileNotFoundError")

    def test_timeout_and_existing_destination_preserve_native_http_status_semantics(self) -> None:
        cases = [(TimeoutError("expired"), 410), (FileExistsError("exists"), 409)]
        for error, expected_status in cases:
            with self.subTest(error=type(error).__name__), patch.object(tp, "create_import", side_effect=error):
                with self.assertRaises(lab_tools.LabToolError) as caught:
                    self.registry["transfer.import.create"]({"path": "x", "expected_size": 0, "expected_sha256": "0" * 64})
                self.assertEqual(caught.exception.error_code, "TRANSFER_ERROR")
                self.assertEqual(caught.exception.status, expected_status)
                self.assertEqual(caught.exception.extra.get("transfer_exception"), type(error).__name__)


if __name__ == "__main__":
    unittest.main()
