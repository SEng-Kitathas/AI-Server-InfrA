from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT))

import lab_tools


class SopEffectContractTests(unittest.TestCase):
    def test_observation_and_guard_surfaces_are_explicit_reads(self) -> None:
        tools = {row["name"]: row for row in lab_tools.list_tools()}
        expected = {
            "sop.package.inspect": {"reads_files", "verifies_integrity", "bounded_package_preflight"},
            "sop.ingest.status": {"reads_state", "non_initializing"},
            "sop.guard.check": {"reads_state", "revalidates_source_currentness", "proceed_gate"},
        }
        for name, traits in expected.items():
            with self.subTest(name=name):
                self.assertEqual(tools[name]["side_effect_class"], "read")
                self.assertTrue(traits.issubset(set(tools[name]["effect_traits"])))

    def test_next_chunk_is_not_laundered_as_read(self) -> None:
        tools = {row["name"]: row for row in lab_tools.list_tools()}
        card = tools["sop.ingest.next_chunk"]
        self.assertTrue(card["mutating"])
        self.assertTrue(card["effective_approval_required"])
        self.assertEqual(card["side_effect_class"], "ephemeral_mutation")
        self.assertTrue(
            {
                "issues_chunk_authority",
                "updates_ingestion_cursor_state",
                "idempotent_replay_while_unacked",
                "revalidates_source_file_hash",
            }.issubset(set(card["effect_traits"]))
        )

    def test_ack_complete_register_reset_carry_specific_mutation_traits(self) -> None:
        tools = {row["name"]: row for row in lab_tools.list_tools()}
        checks = {
            "sop.package.register": "registers_corpus",
            "sop.ingest.reset": "clears_ingestion_progress",
            "sop.ingest.ack_chunk": "requires_chunk_hash_confirmation",
            "sop.ingest.complete_file": "requires_metadata_bound_receipt",
        }
        for name, trait in checks.items():
            with self.subTest(name=name):
                self.assertTrue(tools[name]["mutating"])
                self.assertIn(trait, tools[name]["effect_traits"])


if __name__ == "__main__":
    unittest.main()
