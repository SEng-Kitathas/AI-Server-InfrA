"""Regression fixtures for constraint-pipeline runtime footguns."""

from __future__ import annotations

import ast
import tempfile
import time
import unittest
from pathlib import Path

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "tools" / "csc_native") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "tools" / "csc_native"))
if str(PROJECT_ROOT / "system" / "constraint_pipeline") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "system" / "constraint_pipeline"))
if str(PROJECT_ROOT / "baseline" / "pcmmad_receiver") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "baseline" / "pcmmad_receiver"))

import receiver_schema_authority_gate as schema_gate
import semantic_footgun_dataflow_gate as footgun_gate
from claim_governor import claim_permissions
from constraint_model import GateResult
from receiver_report_adapter import loc_gate
from strict_json_boundary import write_json_boundary


class ConstraintPipelineRegressionTests(unittest.TestCase):
    def test_request_payload_stale_d_is_detected(self) -> None:
        # Arrange
        source = """
def route_func():
    request_payload = get_request_json()
    return d.get("project_id", "")
"""
        tree = ast.parse(source)
        # Act
        findings = footgun_gate._request_payload_stale_findings(
            PROJECT_ROOT / "baseline" / "pcmmad_receiver" / "fake_route.py",
            tree,
            source.splitlines(),
        )
        # Assert
        self.assertEqual([finding["kind"] for finding in findings], ["request_payload_stale_d"])

    def test_immediate_to_dict_missing_method_is_detected(self) -> None:
        # Arrange
        source = """
class Envelope:
    value = 1

def build():
    return Envelope().to_dict()
"""
        tree = ast.parse(source)
        # Act
        findings = footgun_gate._missing_to_dict_findings(
            PROJECT_ROOT / "baseline" / "pcmmad_receiver" / "fake_projection.py",
            tree,
            source.splitlines(),
        )
        # Assert
        self.assertEqual(
            [finding["kind"] for finding in findings], ["instantiate_to_dict_missing_method"]
        )

    def test_known_corruption_identifier_is_detected(self) -> None:
        # Arrange
        lines = ["value = recordefault", "other = execution_log_direfault"]
        # Act
        findings = footgun_gate._known_corruption_findings(
            PROJECT_ROOT / "baseline" / "pcmmad_receiver" / "fake_corruption.py",
            lines,
        )
        # Assert
        self.assertEqual(len(findings), 2)
        self.assertEqual({finding["severity"] for finding in findings}, {"HIGH"})

    def test_schema_route_template_normalization(self) -> None:
        # Arrange / Act / Assert
        self.assertEqual(
            schema_gate._normalize_runtime_path("/status/<commit_id>"), "/status/{commit_id}"
        )
        self.assertEqual(
            schema_gate._normalize_runtime_path("/static/<path:filename>"),
            "/static/{filename}",
        )

    def test_stale_evidence_blocks_claims(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            reports = project_root / "reports"
            source = project_root / "baseline" / "pcmmad_receiver"
            source.mkdir(parents=True)
            reports.mkdir()
            report_path = reports / "CODEX_UNIFIED_LOC_COMPLIANCE_AUDIT.json"
            write_json_boundary(
                report_path,
                {"finding_count": 0, "severity_counts": {}, "promotion_readiness": "READY"},
            )
            time.sleep(0.02)
            (source / "changed.py").write_text("x = 1\n", encoding="utf-8")
            gate = loc_gate(project_root, "promotion")
            # Assert
            self.assertEqual(gate.status, "stale")
            self.assertIn("blocks_promotion", gate.claim_effects)

    def test_claim_governor_blocks_missing_or_failed_gate(self) -> None:
        # Arrange
        gates = (
            GateResult("loc_code_shape", "code_quality", "pass", "promotion"),
            GateResult("guide_quality_style", "style_quality", "fail", "promotion"),
            GateResult("semantic_footgun_dataflow", "semantic_logic", "pass", "promotion"),
        )
        # Act
        claims = {claim.claim: claim for claim in claim_permissions(gates)}
        # Assert
        self.assertEqual(claims["reply_claim_clean"].status, "blocked")
        self.assertIn("guide_quality_style", claims["reply_claim_clean"].blocking_gates)


class LiveTracebackRegressionTests(unittest.TestCase):
    def test_artifact_class_from_path_uses_defined_path_text(self) -> None:
        # Arrange
        import context_engine

        target = PROJECT_ROOT / "reports" / "CONSTRAINT_FINALIZER_EXPRESSION_REPORT.json"
        # Act
        artifact_class = context_engine._artifact_class_from_path(target)
        # Assert
        self.assertIsInstance(artifact_class, str)
        self.assertTrue(artifact_class)

    def test_power_wire_env_string_map_is_defined(self) -> None:
        # Arrange
        import api_wire_power

        payload = {
            "project_id": "pcmmad_receiver_v27_lab_20260428",
            "code": "print('ok')",
            "env": {"A": 1},
        }
        # Act
        request = api_wire_power.PythonExecRequest.from_json(payload)
        # Assert
        self.assertEqual(request.env, {"A": "1"})

    def test_lab_project_files_list_request_symbol_is_imported(self) -> None:
        # Arrange / Act
        import lab_tools_project

        # Assert
        self.assertTrue(hasattr(lab_tools_project, "FileListRequest"))

    def test_power_routes_start_background_process_symbol_exists(self) -> None:
        # Arrange / Act
        import power_routes

        # Assert
        self.assertTrue(hasattr(power_routes, "start_background_process"))

    def test_power_routes_read_text_window_symbol_exists(self) -> None:
        # Arrange / Act
        import power_routes

        # Assert
        self.assertTrue(hasattr(power_routes, "read_text_window"))


if __name__ == "__main__":
    unittest.main()
