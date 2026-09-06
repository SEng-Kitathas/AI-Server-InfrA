from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT))

import lab_routes
from lab_tools import list_tools


class McpManifestContractTests(unittest.TestCase):
    def test_manifest_digest_is_stable_for_same_contract_cards(self) -> None:
        cards = [lab_routes._mcp_manifest_tool_card(tool) for tool in list_tools()]
        self.assertEqual(lab_routes._manifest_digest(cards), lab_routes._manifest_digest(cards))
        self.assertEqual(len(lab_routes._manifest_digest(cards)), 64)

    def test_manifest_cards_preserve_native_contract_currentness(self) -> None:
        source = {tool["name"]: tool for tool in list_tools()}
        card = lab_routes._mcp_manifest_tool_card(source["control.receiver.restart"])
        for key in (
            "capability_version",
            "schema_version",
            "schema_hash",
            "contract_digest",
            "effective_approval_required",
            "side_effect_class",
            "input_schema",
            "output_schema",
        ):
            self.assertIn(key, card)
        self.assertTrue(card["effective_approval_required"])
        self.assertEqual(card["side_effect_class"], "mutation")

    def test_http_manifest_exposes_digest_and_full_contract_cards(self) -> None:
        app = Flask(__name__)
        with app.test_request_context("/lab/mcp/manifest"), patch.object(
            lab_routes, "_auth", return_value=None
        ):
            response = lab_routes.lab_mcp_manifest()
            payload = response.get_json()
        self.assertEqual(payload["tool_count"], len(payload["tools"]))
        self.assertEqual(len(payload["manifest_digest"]), 64)
        restart = next(row for row in payload["tools"] if row["name"] == "control.receiver.restart")
        self.assertTrue(restart["effective_approval_required"])
        self.assertEqual(len(restart["schema_hash"]), 64)
        self.assertEqual(len(restart["contract_digest"]), 64)


if __name__ == "__main__":
    unittest.main()
