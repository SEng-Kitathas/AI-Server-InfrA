from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

import pcmmad_receiver.lab_tools_continuity as c
from pcmmad_receiver.lab_errors import LabToolError
from pcmmad_receiver.protocol_models import ProtocolEventKind, RuntimeMode
from pcmmad_receiver.shared_core import append_jsonl, load_json, save_json_atomic


class ContinuityResReconcileTests(unittest.TestCase):
    def _fixture(self, root: Path):
        project_root = root / "P"
        target = project_root / "continuity" / "research_epistemic_shadow" / "RESEARCH_EPISTEMIC_SHADOW.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        ledger = project_root / "system" / "ledger" / "commits.jsonl"
        manifest = project_root / "system" / "manifest" / "manifest.json"

        def get_project_root(project_id: str) -> Path:
            self.assertEqual(project_id, "P")
            return project_root

        def resolve_target(project_id: str, artifact_class: str, logical_name: str) -> Path:
            self.assertEqual(project_id, "P")
            self.assertEqual(artifact_class, "continuity.research_epistemic_shadow")
            self.assertEqual(logical_name, "RESEARCH_EPISTEMIC_SHADOW.md")
            return target

        def sha256_file(path: Path) -> str:
            return hashlib.sha256(path.read_bytes()).hexdigest()

        tick = {"n": 0}
        def utc_now() -> str:
            tick["n"] += 1
            return f"2026-09-11T21:00:{tick['n']:02d}+00:00"

        deps = c.AdoptionDeps(
            error_cls=LabToolError,
            get_project_root=get_project_root,
            resolve_target=resolve_target,
            commits_ledger_path_for=lambda _project_id: ledger,
            manifest_path_for=lambda _project_id: manifest,
            sha256_file=sha256_file,
            load_json=load_json,
            save_json_atomic=save_json_atomic,
            append_jsonl=append_jsonl,
            utc_now=utc_now,
        )
        return target, ledger, deps

    @staticmethod
    def _payload(sha: str) -> dict[str, object]:
        return {
            "project_id": "P",
            "expected_sha256": sha,
            "actor": "test",
            "session_id": "res-reconcile-test",
        }

    @staticmethod
    def _ready(*, ready: bool, reasons: list[str], artifact_seq: int | None = None, continuity_seq: int | None = None) -> dict[str, object]:
        return {
            "schema": "pcmmad.res-handoff-readiness.v1",
            "project_id": "P",
            "ready": ready,
            "status": "HANDOFF_READY" if ready else "HANDOFF_BLOCKED",
            "reasons": reasons,
            "latest_res_artifact_sequence": artifact_seq,
            "latest_res_continuity_sequence": continuity_seq,
        }

    def test_reconciles_registration_planes_without_rewriting_snapshot(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-res-reconcile-") as td:
            target, ledger, deps = self._fixture(Path(td))
            original = b"canonical RES bytes\r\nremain exact\r\n"
            target.write_bytes(original)
            sha = hashlib.sha256(original).hexdigest()
            artifact_event = SimpleNamespace(
                sequence=4,
                event_kind=ProtocolEventKind.ARTIFACT_REGISTERED,
                payload={
                    "artifact_id": "res-canonical-test",
                    "artifact_class": c.RES_ARTIFACT_CLASS_SNAPSHOT,
                    "path": c.RES_CANONICAL_SNAPSHOT_PATH.replace("\\", "/"),
                    "sha256": sha,
                },
            )
            continuity_event = SimpleNamespace(sequence=5, payload={})
            with (
                patch.object(c, "build_protocol_snapshot", return_value=SimpleNamespace(current_mode=RuntimeMode.BUILD_COMMIT)),
                patch.object(c, "validate_res_snapshot", return_value={"valid": True, "section_count": 22}),
                patch.object(c, "read_protocol_events", return_value=[]),
                patch.object(c, "register_protocol_artifact", return_value=artifact_event) as register,
                patch.object(c, "record_protocol_continuity", return_value=continuity_event) as record,
                patch.object(c, "res_handoff_readiness", side_effect=[
                    self._ready(ready=False, reasons=["RES_SNAPSHOT_NOT_REGISTERED", "RES_CONTINUITY_EVENT_MISSING"]),
                    self._ready(ready=False, reasons=["RES_ARTIFACT_NOT_ACKNOWLEDGED_BY_CONTINUITY_LEDGER"], artifact_seq=4),
                    self._ready(ready=True, reasons=[], artifact_seq=4, continuity_seq=5),
                ]),
            ):
                result = c.reconcile_res_snapshot(self._payload(sha), deps)
            self.assertEqual(target.read_bytes(), original)
            self.assertFalse(result["content_rewritten"])
            self.assertTrue(result["lineage"]["adopted"])
            self.assertTrue(result["protocol_artifact_registered"])
            self.assertTrue(result["continuity_recorded"])
            self.assertTrue(result["readiness_after"]["ready"])
            register.assert_called_once()
            record.assert_called_once()
            rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["operation"], "adopt")
            self.assertEqual(rows[0]["sha256"], sha)

    def test_already_current_is_true_noop(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-res-current-") as td:
            target, ledger, deps = self._fixture(Path(td))
            original = b"already current\n"
            target.write_bytes(original)
            sha = hashlib.sha256(original).hexdigest()
            c.adopt_existing_artifact({
                "project_id": "P",
                "artifact": {"artifact_class": "continuity.research_epistemic_shadow", "logical_name": "RESEARCH_EPISTEMIC_SHADOW.md"},
                "expected_sha256": sha,
            }, deps)
            existing = SimpleNamespace(
                sequence=7,
                event_kind=ProtocolEventKind.ARTIFACT_REGISTERED,
                payload={
                    "artifact_id": "res-current",
                    "artifact_class": c.RES_ARTIFACT_CLASS_SNAPSHOT,
                    "path": c.RES_CANONICAL_SNAPSHOT_PATH.replace("\\", "/"),
                    "sha256": sha,
                },
            )
            ready = self._ready(ready=True, reasons=[], artifact_seq=7, continuity_seq=8)
            with (
                patch.object(c, "build_protocol_snapshot", return_value=SimpleNamespace(current_mode=RuntimeMode.BUILD_COMMIT)),
                patch.object(c, "validate_res_snapshot", return_value={"valid": True}),
                patch.object(c, "read_protocol_events", return_value=[existing]),
                patch.object(c, "register_protocol_artifact") as register,
                patch.object(c, "record_protocol_continuity") as record,
                patch.object(c, "res_handoff_readiness", side_effect=[ready, ready, ready]),
            ):
                result = c.reconcile_res_snapshot(self._payload(sha), deps)
            self.assertFalse(result["lineage"]["adopted"])
            self.assertTrue(result["lineage"]["already_current"])
            self.assertFalse(result["protocol_artifact_registered"])
            self.assertFalse(result["continuity_recorded"])
            register.assert_not_called()
            record.assert_not_called()
            self.assertEqual(target.read_bytes(), original)
            self.assertEqual(len(ledger.read_text(encoding="utf-8").splitlines()), 1)

    def test_requires_explicit_build_commit_mode_before_any_metadata_mutation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-res-mode-") as td:
            target, ledger, deps = self._fixture(Path(td))
            original = b"mode guard\n"
            target.write_bytes(original)
            sha = hashlib.sha256(original).hexdigest()
            with patch.object(c, "build_protocol_snapshot", return_value=SimpleNamespace(current_mode=RuntimeMode.DISCUSSION)):
                with self.assertRaises(LabToolError) as ctx:
                    c.reconcile_res_snapshot(self._payload(sha), deps)
            self.assertEqual(ctx.exception.error_code, "RES_RECONCILE_BUILD_COMMIT_REQUIRED")
            self.assertFalse(ledger.exists())
            self.assertEqual(target.read_bytes(), original)

    def test_material_staleness_is_not_hidden_by_reregistration(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-res-stale-") as td:
            target, ledger, deps = self._fixture(Path(td))
            original = b"epistemically stale\n"
            target.write_bytes(original)
            sha = hashlib.sha256(original).hexdigest()
            with (
                patch.object(c, "build_protocol_snapshot", return_value=SimpleNamespace(current_mode=RuntimeMode.BUILD_COMMIT)),
                patch.object(c, "validate_res_snapshot", return_value={"valid": True}),
                patch.object(c, "res_handoff_readiness", return_value=self._ready(ready=False, reasons=["RES_STALE_AFTER_MATERIAL_PROTOCOL_CHANGE"])),
                patch.object(c, "register_protocol_artifact") as register,
                patch.object(c, "record_protocol_continuity") as record,
            ):
                with self.assertRaises(LabToolError) as ctx:
                    c.reconcile_res_snapshot(self._payload(sha), deps)
            self.assertEqual(ctx.exception.error_code, "RES_RECONCILE_UNSAFE_STATE")
            register.assert_not_called()
            record.assert_not_called()
            self.assertFalse(ledger.exists())
            self.assertEqual(target.read_bytes(), original)

    def test_exact_file_witness_fails_before_lineage_or_protocol_mutation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-res-sha-") as td:
            target, ledger, deps = self._fixture(Path(td))
            original = b"actual bytes\n"
            target.write_bytes(original)
            wrong = hashlib.sha256(b"wrong").hexdigest()
            with (
                patch.object(c, "build_protocol_snapshot", return_value=SimpleNamespace(current_mode=RuntimeMode.BUILD_COMMIT)),
                patch.object(c, "validate_res_snapshot", return_value={"valid": True}),
                patch.object(c, "register_protocol_artifact") as register,
            ):
                with self.assertRaises(LabToolError) as ctx:
                    c.reconcile_res_snapshot(self._payload(wrong), deps)
            self.assertEqual(ctx.exception.error_code, "ARTIFACT_SHA_MISMATCH")
            register.assert_not_called()
            self.assertFalse(ledger.exists())
            self.assertEqual(target.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
