"""
Arrange: set up focused fixtures.
Act: exercise the target behavior.
Assert: verify the expected contract.
Regression tests for semantic doctrine and retrieval-related lab tool behavior."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "baseline"))
sys.path.insert(0, str(PROJECT_ROOT / "baseline" / "pcmmad_receiver"))

from pcmmad_receiver.lab_tools import LabToolError, dispatch_tool, list_tools
import pcmmad_receiver.lab_tools_semantic as semantic


class SemanticDoctrineToolTests(unittest.TestCase):
    def test_tools_are_registered(self) -> None:
        names = {tool["name"] for tool in list_tools()}
        self.assertIn("semantic.monster.health", names)
        self.assertIn("semantic.monster.search", names)
        self.assertIn("doctrine.invariants.status", names)
        self.assertIn("doctrine.invariants.read", names)
        self.assertIn("doctrine.invariants.search", names)

    def test_doctrine_invariant_status_and_search(self) -> None:
        status = dispatch_tool("doctrine.invariants.status", {})
        result = status["result"]
        self.assertTrue(result["manifest_exists"])
        self.assertTrue(result["guide_exists"])
        search = dispatch_tool("doctrine.invariants.search", {"query": "finalizer", "limit": 5})
        self.assertIn("count", search["result"])

    def test_monster_health_is_lazy_and_nonfatal(self) -> None:
        health = dispatch_tool("semantic.monster.health", {})
        result = health["result"]
        self.assertIn("script_path", result)
        self.assertIn("dependency_probe", result)

    def test_semantic_health_requires_behavior_complete_runtime_modules(self) -> None:
        self.assertEqual(
            set(semantic._REQUIRED_MODULES),
            {
                "faiss",
                "numpy",
                "torch",
                "sentence_transformers",
                "transformers",
                "PIL",
                "peft",
                "torchvision",
            },
        )

    def test_zero_byte_minilm_snapshot_is_not_qualified(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for rel in (
                "config.json",
                "modules.json",
                "1_Pooling/config.json",
                "tokenizer_config.json",
                "model.safetensors",
                "tokenizer.json",
            ):
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"")
            result = semantic._minilm_model_qualification(root)
            self.assertFalse(result["qualified"])
            self.assertFalse(result["weights_ok"])
            self.assertFalse(result["tokenizer_ok"])

    def test_semantic_child_failure_is_not_reported_as_tool_success(self) -> None:
        resolution = {
            "available": True,
            "resources": {
                "script": {"path": "retriever.py", "sha256": "a" * 64},
                "db": {"path": "corpus.sqlite"},
                "minilm_index": {"path": "minilm"},
                "jina_index": {"path": "jina"},
                "minilm_model": {"path": "model"},
            },
            "python": {"selected": {"path": sys.executable}},
        }
        failed = {
            "ok": False,
            "return_code": 1,
            "stderr": "model failure",
            "stdout": "",
        }
        with patch.object(semantic, "_semantic_resolution", return_value=resolution), patch.object(
            semantic, "run_subprocess_envelope", return_value=failed
        ):
            with self.assertRaises(LabToolError) as caught:
                semantic._monster_search_payload({"query": "needle", "topk": 2}, LabToolError)
        self.assertEqual(caught.exception.error_code, "SEMANTIC_EXECUTION_FAILED")
        self.assertEqual(caught.exception.status, 502)

    def test_semantic_invalid_stdout_is_typed_failure(self) -> None:
        resolution = {
            "available": True,
            "resources": {
                "script": {"path": "retriever.py", "sha256": "a" * 64},
                "db": {"path": "corpus.sqlite"},
                "minilm_index": {"path": "minilm"},
                "jina_index": {"path": "jina"},
                "minilm_model": {"path": "model"},
            },
            "python": {"selected": {"path": sys.executable}},
        }
        invalid = {"ok": True, "return_code": 0, "stdout": "not json", "stderr": ""}
        with patch.object(semantic, "_semantic_resolution", return_value=resolution), patch.object(
            semantic, "run_subprocess_envelope", return_value=invalid
        ):
            with self.assertRaises(LabToolError) as caught:
                semantic._monster_search_payload({"query": "needle", "topk": 2}, LabToolError)
        self.assertEqual(caught.exception.error_code, "SEMANTIC_OUTPUT_INVALID")
        self.assertEqual(caught.exception.status, 502)


if __name__ == "__main__":
    unittest.main()
