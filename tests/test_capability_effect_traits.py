from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT))

from control_plane_models import ToolSpec
from lab_tools import list_tools


class CapabilityEffectTraitTests(unittest.TestCase):
    def test_effect_traits_participate_in_contract_digest(self) -> None:
        base = ToolSpec(
            name="x.y",
            description="x",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            side_effect_class="read",
            effect_traits=["reads_state"],
        )
        changed = ToolSpec(
            name="x.y",
            description="x",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            side_effect_class="read",
            effect_traits=["reads_state", "reconciles_state"],
        )
        self.assertNotEqual(base.contract_digest, changed.contract_digest)

    def test_high_risk_ambiguous_capabilities_are_explicitly_classified(self) -> None:
        tools = {row["name"]: row for row in list_tools()}
        expected = {
            "execution.run": ("execution", {"executes_code", "arbitrary_process_side_effects"}),
            "python.run": ("execution", {"executes_code", "arbitrary_process_side_effects"}),
            "execution.submit": ("execution", {"creates_durable_state", "queues_work", "executes_code"}),
            "execution.status": ("read_reconcile", {"reads_state", "reconciles_state", "may_advance_queue"}),
            "execution.progress": ("read_reconcile", {"reads_state", "reconciles_state", "may_advance_queue"}),
            "execution.wait": ("read_reconcile", {"reads_state", "bounded_wait", "reconciles_state"}),
            "browser.evaluate": ("external_interaction", {"executes_code", "external_interaction", "may_mutate_external_state"}),
            "research.arxiv.search": ("external_read", {"network_io", "reads_external_state", "may_write_cache"}),
            "research.arxiv.paper": ("external_read", {"network_io", "reads_external_state", "may_write_cache"}),
            "research.hunt": ("external_read", {"network_io", "reads_external_state", "may_write_cache"}),
            "semantic.monster.search": ("execution", {"executes_code", "heavy_compute", "reads_state"}),
            "lab.tools.reload": ("runtime_mutation", {"mutates_registry", "loads_code", "changes_capability_surface"}),
            "transfer.export.create": ("ephemeral_mutation", {"creates_ephemeral_state", "reads_files", "hashes_content"}),
        }
        for name, (effect_class, traits) in expected.items():
            with self.subTest(name=name):
                self.assertEqual(tools[name]["side_effect_class"], effect_class)
                self.assertTrue(traits.issubset(set(tools[name]["effect_traits"])))

    def test_declared_mutations_still_receive_default_durable_mutation_trait(self) -> None:
        tools = {row["name"]: row for row in list_tools()}
        self.assertIn("durable_mutation", tools["project.files.write"]["effect_traits"])
        self.assertIn("durable_mutation", tools["git.commit"]["effect_traits"])


if __name__ == "__main__":
    unittest.main()
