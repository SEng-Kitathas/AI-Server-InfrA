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


class VerifyGateContractBoundsTests(unittest.TestCase):
    def _dep(self, root: Path, reflexions=None):
        sink = reflexions if reflexions is not None else []
        return SimpleNamespace(
            error_cls=lab_tools.LabToolError,
            resolve_cwd=lambda project_id, cwd: root,
            append_reflexion=lambda project_id, payload: sink.append((project_id, payload)),
        )

    def test_gate_count_is_hard_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gates = [
                {"name": f"g{i}", "command": [sys.executable, "-c", "pass"]}
                for i in range(ops.VERIFY_MAX_GATES + 1)
            ]
            with self.assertRaises(lab_tools.LabToolError) as caught:
                ops._verify_gate_payload(
                    {"project_id": "alpha", "gates": gates}, self._dep(root)
                )
        self.assertEqual(caught.exception.error_code, "VERIFY_GATE_LIMIT_EXCEEDED")
        self.assertEqual(caught.exception.extra["maximum"], ops.VERIFY_MAX_GATES)

    def test_receipt_states_command_exit_evidence_scope_not_semantic_truth(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = ops._verify_gate_payload(
                {
                    "project_id": "alpha",
                    "gates": [
                        {"name": "smoke", "command": [sys.executable, "-c", "print('ok')"]}
                    ],
                },
                self._dep(root),
            )
        self.assertEqual(result["overall"], "passed")
        self.assertEqual(result["evidence_scope"], "declared_gate_command_exit_only")
        self.assertFalse(result["semantic_claim_verified"])
        self.assertEqual(result["requested_gates"], 1)
        self.assertEqual(result["attempted_gates"], 1)
        self.assertFalse(result["stopped_early"])
        self.assertEqual(result["results"][0]["evidence_scope"], "declared_gate_command_exit")

    def test_stop_on_fail_receipt_reports_partial_attempts(self) -> None:
        reflexions = []
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = ops._verify_gate_payload(
                {
                    "project_id": "alpha",
                    "gates": [
                        {"name": "fail", "command": [sys.executable, "-c", "import sys; sys.exit(2)"]},
                        {"name": "never", "command": [sys.executable, "-c", "print('never')"]},
                    ],
                    "stop_on_fail": True,
                },
                self._dep(root, reflexions),
            )
        self.assertEqual(result["overall"], "failed")
        self.assertEqual(result["requested_gates"], 2)
        self.assertEqual(result["attempted_gates"], 1)
        self.assertTrue(result["stopped_early"])
        self.assertEqual(len(reflexions), 1)

    def test_timeout_each_is_server_capped(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = ops._verify_gate_payload(
                {
                    "project_id": "alpha",
                    "gates": [{"name": "ok", "command": [sys.executable, "-c", "pass"]}],
                    "timeout_each": 999999,
                },
                self._dep(root),
            )
        self.assertEqual(result["timeout_each_seconds"], ops.VERIFY_TIMEOUT_EACH_MAX_SECONDS)

    def test_registry_contract_exposes_bounds_and_effect_truth(self) -> None:
        card = {row["name"]: row for row in lab_tools.list_tools()}["verify.gates"]
        gates_schema = card["input_schema"]["properties"]["gates"]
        self.assertEqual(gates_schema["maxItems"], ops.VERIFY_MAX_GATES)
        self.assertIn("project_id", card["input_schema"]["required"])
        self.assertIn("gates", card["input_schema"]["required"])
        traits = set(card["effect_traits"])
        self.assertTrue(
            {
                "executes_code",
                "project_scope_enforced",
                "bounded_output",
                "bounded_gate_count",
                "command_exit_evidence_only",
            }.issubset(traits)
        )
        self.assertIn("evidence_scope", card["output_schema"]["properties"])
        self.assertIn("semantic_claim_verified", card["output_schema"]["properties"])


if __name__ == "__main__":
    unittest.main()
