from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

import lab_tools
import lab_tools_ops as ops


class VerifyGateEffectTruthTests(unittest.TestCase):
    def test_custom_gate_can_mutate_project_and_contract_admits_execution_effects(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            marker = root / "mutated.txt"
            dep = SimpleNamespace(
                error_cls=lab_tools.LabToolError,
                resolve_cwd=lambda project_id, cwd: root,
                append_reflexion=lambda project_id, payload: None,
            )
            payload = {
                "project_id": "alpha",
                "gates": [
                    {
                        "name": "mutation-proof",
                        "command": [
                            sys.executable,
                            "-c",
                            f"from pathlib import Path; Path(r'{marker}').write_text('changed')",
                        ],
                    }
                ],
            }
            result = ops._verify_gate_payload(payload, dep)
            self.assertEqual(result["overall"], "passed")
            self.assertTrue(marker.exists())

        tools = {row["name"]: row for row in lab_tools.list_tools()}
        card = tools["verify.gates"]
        self.assertTrue(card["mutating"])
        self.assertEqual(card["side_effect_class"], "execution")
        self.assertTrue(
            {
                "executes_code",
                "spawns_process",
                "arbitrary_process_side_effects",
                "may_write_project_state",
            }.issubset(set(card["effect_traits"]))
        )

    def test_failed_gate_records_project_state_side_effect(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reflexions = []
            dep = SimpleNamespace(
                error_cls=lab_tools.LabToolError,
                resolve_cwd=lambda project_id, cwd: root,
                append_reflexion=lambda project_id, payload: reflexions.append((project_id, payload)),
            )
            result = ops._verify_gate_payload(
                {
                    "project_id": "alpha",
                    "gates": [
                        {
                            "name": "fail",
                            "command": [sys.executable, "-c", "import sys; sys.exit(7)"],
                        }
                    ],
                },
                dep,
            )
            self.assertEqual(result["overall"], "failed")
            self.assertEqual(len(reflexions), 1)
            self.assertEqual(reflexions[0][0], "alpha")
            self.assertIn("gate_failed:fail", reflexions[0][1]["title"])


if __name__ == "__main__":
    unittest.main()
