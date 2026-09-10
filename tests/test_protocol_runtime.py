"""Contract tests for the PCMMAD-native append-only runtime protocol."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(PROJECT_ROOT / "baseline"))
sys.path.insert(0, str(RUNTIME_ROOT.parent))

import shared_core
import protocol_store
import approval_authority as approval_authority
from protocol_models import ProtocolValidationError
from protocol_store import (
    ProtocolConflictError,
    ensure_protocol,
    protocol_status,
    record_claim,
    record_promotion,
    register_artifact,
    set_objective,
    transition_mode,
    verify_events,
)
from pcmmad_receiver.lab_tools import LabToolError, dispatch_tool, list_tools


class ProtocolRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name) / "root"
        projects = root / "projects"
        system = root / "system"
        sandbox = root / "sandbox"
        temp = root / "temp"
        for path in (root, projects, system, sandbox, temp):
            path.mkdir(parents=True, exist_ok=True)
        self._patchers = [
            patch.object(shared_core, "ROOT", root),
            patch.object(shared_core, "PROJECTS_ROOT", projects),
            patch.object(shared_core, "SYSTEM_ROOT", system),
            patch.object(shared_core, "SANDBOX_ROOT", sandbox),
            patch.object(shared_core, "TEMP_ROOT", temp),
            patch.object(approval_authority, "SYSTEM_ROOT", system),
            patch.object(
                shared_core,
                "MOUNT_TABLE",
                {
                    "root": root,
                    "projects": projects,
                    "system": system,
                    "sandbox": sandbox,
                    "temp": temp,
                },
            ),
        ]
        for patcher in self._patchers:
            patcher.start()
        protocol_store._PROJECT_LOCKS.clear()

    def tearDown(self) -> None:
        protocol_store._PROJECT_LOCKS.clear()
        for patcher in reversed(self._patchers):
            patcher.stop()
        self.tempdir.cleanup()

    def test_protocol_tool_family_is_registered_without_expanding_action_schema(self) -> None:
        protocol_names = {
            card["name"] for card in list_tools() if card["name"].startswith("protocol.")
        }
        self.assertEqual(len(protocol_names), 15)
        self.assertIn("protocol.ledger.verify", protocol_names)
        self.assertIn("protocol.merkle.root", protocol_names)
        self.assertIn("protocol.merkle.inclusion", protocol_names)
        self.assertIn("protocol.merkle.consistency", protocol_names)
        self.assertIn("protocol.promotion.record", protocol_names)

    def test_genesis_and_superseding_objective_are_append_only(self) -> None:
        first = ensure_protocol(
            "alpha", actor="test", rigor_level="ELEVATED", initial_mode="AUDIT"
        )
        self.assertEqual(first.event_count, 1)
        set_objective(
            "alpha", objective_id="objective-1", statement="First", actor="test"
        )
        set_objective(
            "alpha", objective_id="objective-2", statement="Second", actor="test"
        )
        status = protocol_status("alpha")
        self.assertTrue(status["ok"])
        self.assertEqual(status["state"]["event_count"], 3)
        self.assertEqual(status["state"]["objective"]["objective_id"], "objective-2")
        self.assertEqual(
            status["state"]["objective"]["supersedes_objective_id"], "objective-1"
        )

    def test_hash_chain_detects_silent_history_edits(self) -> None:
        ensure_protocol("alpha", actor="test")
        set_objective("alpha", objective_id="main", statement="Original", actor="test")
        path = shared_core.get_project_root("alpha") / "system" / "protocol" / "events.jsonl"
        path.write_text(path.read_text(encoding="utf-8").replace("Original", "Altered", 1))
        verification = verify_events("alpha")
        self.assertFalse(verification["ok"])
        self.assertIn("event_hash_mismatch", {item["error"] for item in verification["failures"]})

    def test_elevated_ratification_requires_two_evidence_refs_and_promotion_mode(self) -> None:
        ensure_protocol("alpha", actor="test", rigor_level="ELEVATED", initial_mode="AUDIT")
        record_claim(
            "alpha",
            claim_id="claim-1",
            kind="KNOWN",
            statement="A verified statement",
            actor="test",
        )
        with self.assertRaises(ProtocolConflictError):
            record_promotion(
                "alpha",
                target_type="claim",
                target_id="claim-1",
                decision="RATIFIED",
                rationale="Not in promotion mode",
                actor="test",
                evidence=[{"kind": "test", "ref": "one", "status": "VERIFIED"}, {"kind": "audit", "ref": "two"}],
            )
        transition_mode(
            "alpha",
            to_mode="PROMOTION",
            expected_mode="AUDIT",
            reason="Evidence review",
            actor="test",
        )
        with self.assertRaises(ProtocolValidationError):
            record_promotion(
                "alpha",
                target_type="claim",
                target_id="claim-1",
                decision="RATIFIED",
                rationale="Insufficient evidence",
                actor="test",
                evidence=[{"kind": "test", "ref": "one", "status": "VERIFIED"}],
            )
        event = record_promotion(
            "alpha",
            target_type="claim",
            target_id="claim-1",
            decision="RATIFIED",
            rationale="Two independent anchors",
            actor="test",
            evidence=[{"kind": "test", "ref": "one", "status": "VERIFIED"}, {"kind": "audit", "ref": "two"}],
        )
        self.assertEqual(event.payload["decision"], "RATIFIED")

    def test_sealed_artifact_identity_cannot_be_rewritten(self) -> None:
        ensure_protocol("alpha", actor="test")
        artifact = shared_core.get_project_root("alpha") / "code" / "artifact.txt"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("first", encoding="utf-8")
        register_artifact(
            "alpha",
            artifact_id="artifact-1",
            artifact_class="code",
            path="code/artifact.txt",
            sealed=True,
            actor="test",
        )
        artifact.write_text("second", encoding="utf-8")
        with self.assertRaises(ProtocolConflictError):
            register_artifact(
                "alpha",
                artifact_id="artifact-1",
                artifact_class="code",
                path="code/artifact.txt",
                sealed=True,
                actor="test",
            )

    def test_router_dispatch_returns_verified_protocol_state(self) -> None:
        with patch.dict(
            "os.environ",
            {"PCMMAD_LAB_POLICY_MODE": "strict", "PCMMAD_TOOL_VALIDATION_MODE": "strict"},
            clear=False,
        ):
            arguments = {
                "project_id": "alpha",
                "rigor_level": "STANDARD",
                "initial_mode": "DISCUSSION",
            }
            with self.assertRaises(LabToolError) as approval_required:
                dispatch_tool("protocol.initialize", arguments)
            self.assertEqual(approval_required.exception.error_code, "APPROVAL_REQUIRED")
            challenge = approval_required.exception.extra["approval_challenge"]
            initialized = dispatch_tool(
                "protocol.initialize",
                arguments,
                authority={
                    "approval_handle": challenge["handle"],
                    "permit": True,
                    "operator_id": "test-operator",
                    "provenance": "protocol-runtime-test",
                },
            )
            self.assertTrue(initialized["ok"])
            self.assertEqual(initialized["approval_mode"], "bound_challenge")
            status = dispatch_tool("protocol.status", {"project_id": "alpha"})
        self.assertTrue(status["result"]["ok"])
        self.assertEqual(status["result"]["state"]["current_mode"], "DISCUSSION")
        events_path = shared_core.get_project_root("alpha") / "system" / "protocol" / "events.jsonl"
        first_line = json.loads(events_path.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(first_line["event_kind"], "GENESIS")

    def test_strict_mode_gate_blocks_specimen_mutation_in_discussion(self) -> None:
        ensure_protocol("alpha", actor="test", initial_mode="DISCUSSION")
        with patch.dict(
            "os.environ",
            {
                "PCMMAD_LAB_POLICY_MODE": "strict",
                "PCMMAD_TOOL_VALIDATION_MODE": "advisory",
                "PCMMAD_PROTOCOL_POLICY_MODE": "strict",
            },
            clear=False,
        ):
            with self.assertRaises(Exception) as context:
                dispatch_tool(
                    "project.files.write",
                    {
                        "project_id": "alpha",
                        "path": "code/blocked.txt",
                        "content": "blocked",
                        "approval": {"permit": True},
                    },
                )
        self.assertEqual(getattr(context.exception, "error_code", None), "PROTOCOL_MODE_REQUIRED")

    def test_advisory_mode_gate_preserves_legacy_execution_with_warning(self) -> None:
        ensure_protocol("alpha", actor="test", initial_mode="DISCUSSION")
        with patch.dict(
            "os.environ",
            {
                "PCMMAD_LAB_POLICY_MODE": "strict",
                "PCMMAD_TOOL_VALIDATION_MODE": "advisory",
                "PCMMAD_PROTOCOL_POLICY_MODE": "advisory",
                "PCMMAD_ALLOW_LEGACY_INLINE_APPROVAL": "1",
            },
            clear=False,
        ):
            result = dispatch_tool(
                "project.files.write",
                {
                    "project_id": "alpha",
                    "path": "code/advisory.txt",
                    "content": "allowed with warning",
                    "approval": {"permit": True},
                },
            )
        self.assertTrue(result["ok"])
        self.assertIn("does not permit SPECIMEN mutation", result["warning"])



if __name__ == "__main__":
    unittest.main()
