from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT))

import lab_tools


class CapabilityEffectCompletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cards = {row["name"]: row for row in lab_tools.list_tools()}

    def test_no_native_capability_has_unknown_or_empty_effect_contract(self) -> None:
        unknown = [
            name
            for name, card in self.cards.items()
            if card.get("side_effect_class") in (None, "", "unknown")
            or not card.get("effect_traits")
        ]
        self.assertEqual(unknown, [])

    def test_browser_observation_is_external_read_not_local_pure_read(self) -> None:
        for name in (
            "browser.health",
            "browser.sessions.list",
            "browser.pages.list",
            "browser.content",
        ):
            card = self.cards[name]
            self.assertEqual(card["side_effect_class"], "external_read")
            self.assertTrue(
                {"network_io", "reads_external_state", "bridge_scoped", "bounded_wait"}.issubset(
                    set(card["effect_traits"])
                )
            )

    def test_browser_screenshot_preserves_external_artifact_claim_ceiling(self) -> None:
        card = self.cards["browser.screenshot"]
        self.assertEqual(card["side_effect_class"], "external_interaction")
        self.assertTrue(
            {
                "network_io",
                "reads_external_state",
                "captures_visual_state",
                "may_write_external_artifact",
            }.issubset(set(card["effect_traits"]))
        )

    def test_context_search_and_rehydrate_admit_ephemeral_cache_write(self) -> None:
        for name in ("project.files.search", "project.context.rehydrate"):
            card = self.cards[name]
            self.assertEqual(card["side_effect_class"], "read_cache")
            self.assertIn("writes_ephemeral_cache", card["effect_traits"])
            self.assertIn("source_currentness_check", card["effect_traits"])
        self.assertIn("icf_authority_aware", self.cards["project.context.rehydrate"]["effect_traits"])

    def test_health_probes_do_not_masquerade_as_pure_reads(self) -> None:
        lab_health = self.cards["lab.health"]
        self.assertEqual(lab_health["side_effect_class"], "read_probe")
        self.assertIn("probes_browser_bridge", lab_health["effect_traits"])
        self.assertIn("network_io", lab_health["effect_traits"])

        semantic = self.cards["semantic.monster.health"]
        self.assertEqual(semantic["side_effect_class"], "read_probe")
        self.assertTrue(
            {
                "spawns_process",
                "probes_dependencies",
                "bounded_subprocess_output",
                "hashes_content",
            }.issubset(set(semantic["effect_traits"]))
        )

    def test_local_read_families_are_explicit(self) -> None:
        expected_read = (
            "fs.read",
            "fs.glob",
            "fs.grep",
            "fs.tree",
            "zip.read",
            "doctrine.invariants.status",
            "doctrine.invariants.read",
            "doctrine.invariants.search",
            "lab.session.get",
            "lab.reflexion.read",
            "project.files.list",
            "project.files.read",
            "project.files.read_many",
            "project.models.list",
            "project.models.inspect",
            "project.archives.list",
            "project.archives.inspect",
            "control.receiver.restart.status",
        )
        for name in expected_read:
            self.assertEqual(self.cards[name]["side_effect_class"], "read", name)

    def test_control_hud_status_is_process_health_probe(self) -> None:
        card = self.cards["control.hud.status"]
        self.assertEqual(card["side_effect_class"], "read_probe")
        self.assertTrue(
            {"reads_process_state", "reads_service_state", "health_probe"}.issubset(
                set(card["effect_traits"])
            )
        )


if __name__ == "__main__":
    unittest.main()
