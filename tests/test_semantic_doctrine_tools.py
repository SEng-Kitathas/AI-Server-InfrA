"""
Arrange: set up focused fixtures.
Act: exercise the target behavior.
Assert: verify the expected contract.
Regression tests for semantic doctrine and retrieval-related lab tool behavior."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "baseline"))
sys.path.insert(0, str(PROJECT_ROOT / "baseline" / "pcmmad_receiver"))

from pcmmad_receiver.lab_tools import dispatch_tool, list_tools


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


if __name__ == "__main__":
    unittest.main()
