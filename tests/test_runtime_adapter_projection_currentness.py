from __future__ import annotations

import json
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS = PROJECT_ROOT / "reports"
MATRIX_JSON = REPORTS / "PCMMAD_RUNTIME_ADAPTER_PROJECTION_MATRIX_V0_1.json"
MATRIX_MD = REPORTS / "PCMMAD_RUNTIME_ADAPTER_PROJECTION_MATRIX_V0_1.md"
COMPAT_MD = REPORTS / "PCMMAD_RUNTIME_ADAPTER_COMPATIBILITY_CONTRACT_V0_1.md"


class RuntimeAdapterProjectionCurrentnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.matrix = json.loads(MATRIX_JSON.read_text(encoding="utf-8"))
        cls.matrix_md = MATRIX_MD.read_text(encoding="utf-8")
        cls.compat = COMPAT_MD.read_text(encoding="utf-8")

    def test_machine_matrix_is_reconciled_through_hud_availability_slice(self) -> None:
        self.assertEqual(self.matrix["reconciled_through"], "A-030")
        self.assertEqual(self.matrix["status"], "current_candidate_shared_contract")
        laws = set(self.matrix["laws"])
        self.assertIn("REGISTRATION != CAPABILITY_AVAILABILITY != TARGET_HEALTH.", laws)
        self.assertIn("GIT_PUBLICATION != LIVE_RUNTIME_PROMOTION.", laws)

    def test_hud_projection_preserves_runtime_authority_boundary(self) -> None:
        concepts = {row["id"]: row for row in self.matrix["concepts"]}
        capability = concepts["capability"]
        runtime_health = concepts["runtime.health"]
        self.assertIn("availability_contract", capability["currentness"])
        self.assertIn("selected-tool native availability probe", capability["hud_projection"])
        self.assertIn("contract-digest", capability["hud_projection"])
        self.assertIn("optional browser bridge", runtime_health["hud_projection"])
        self.assertIn("without disqualifying core", runtime_health["hud_projection"])

    def test_earned_hud_and_native_contract_items_are_not_still_open(self) -> None:
        open_items = "\n".join(self.matrix["open_reconciliation"]).lower()
        forbidden = (
            "full tool side-effect",
            "target-bound approval",
            "result preview/range",
            "capability availability/currentness normalization",
            "plugin lifecycle/version",
            "hud presentation of core-vs-optional health and dynamic availability",
        )
        for item in forbidden:
            self.assertNotIn(item, open_items)
        self.assertIn("remaining openapi/imported-action/runtime-surface parity", open_items)
        self.assertIn("final schema redesign after whole-runtime convergence", open_items)

    def test_human_contract_records_explicit_probe_and_ephemeral_currentness(self) -> None:
        self.assertIn("Current earned HUD projection:", self.compat)
        self.assertIn("selected capability", self.compat)
        self.assertIn("never by a hidden catalog-wide scan", self.compat)
        self.assertIn("discarded when the native `contract_digest` changes", self.compat)
        self.assertIn("optional/degraded presentation, not a false core failure", self.compat)
        self.assertIn("reconciled through A-030", self.matrix_md)
        self.assertIn("explicit selected-tool currentness", self.matrix_md)


if __name__ == "__main__":
    unittest.main()
