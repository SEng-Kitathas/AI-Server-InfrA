from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT))

import lab_tools
import legacy_routes
from runtime_axioms import constitutional_seed


class RuntimeAxiomSeedTests(unittest.TestCase):
    def test_seed_is_stable_and_contains_primary_axiom(self) -> None:
        first = constitutional_seed()
        second = constitutional_seed()
        self.assertEqual(first, second)
        self.assertEqual(first["primary_axiom"]["id"], "AXIOM-01")
        self.assertEqual(
            first["primary_axiom"]["text"],
            "INTENT IS A CONSTRAINT, NOT A CEILING.",
        )
        self.assertEqual(len(first["digest"]), 64)

    def test_native_lab_health_includes_seed(self) -> None:
        payload = lab_tools.tool_lab_health()
        self.assertEqual(payload["constitutional_seed"], constitutional_seed())

    def test_legacy_health_includes_same_seed(self) -> None:
        app = Flask(__name__)
        with app.test_request_context("/health"), patch.object(
            legacy_routes, "require_api_key", return_value=None
        ), patch.object(legacy_routes, "execution_capabilities", return_value={}):
            response = legacy_routes.health()
            payload = response.get_json()
        self.assertEqual(payload["constitutional_seed"], constitutional_seed())


if __name__ == "__main__":
    unittest.main()
