from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

from pcmmad_receiver.lab_errors import LabToolError
from pcmmad_receiver.lab_tools_continuity import AdoptionDeps, ContinuityDeps, adopt_existing_artifact, inspect_convergence
from pcmmad_receiver.server_hardening import safe_json_dumps, safe_json_loads
from pcmmad_receiver.shared_core import append_jsonl, load_json, save_json_atomic


class ContinuityArtifactAdoptionTests(unittest.TestCase):
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
            return f"2026-09-11T20:00:{tick['n']:02d}+00:00"

        adopt = AdoptionDeps(
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
        inspect = ContinuityDeps(
            error_cls=LabToolError,
            get_project_root=get_project_root,
            resolve_target=resolve_target,
            commits_ledger_path_for=lambda _project_id: ledger,
            sha256_file=sha256_file,
        )
        return project_root, target, ledger, manifest, adopt, inspect

    @staticmethod
    def _payload(sha: str, *, expected_registered_sha256: str | None = None) -> dict[str, object]:
        payload: dict[str, object] = {
            "project_id": "P",
            "artifact": {
                "artifact_class": "continuity.research_epistemic_shadow",
                "logical_name": "RESEARCH_EPISTEMIC_SHADOW.md",
            },
            "expected_sha256": sha,
            "session_id": "migration-test",
        }
        if expected_registered_sha256 is not None:
            payload["expected_registered_sha256"] = expected_registered_sha256
        return payload

    def test_adopts_existing_bytes_without_rewrite_and_becomes_current(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-adopt-") as td:
            _project, target, ledger, manifest, adopt, inspect = self._fixture(Path(td))
            original = b"# RES CONSOLIDATED SNAPSHOT\n\nUNKNOWN initialization\n"
            target.write_bytes(original)
            sha = hashlib.sha256(original).hexdigest()
            result = adopt_existing_artifact(self._payload(sha), adopt)
            self.assertTrue(result["adopted"])
            self.assertEqual(result["generation"], 1)
            self.assertEqual(result["operation"], "adopt")
            self.assertEqual(target.read_bytes(), original)
            rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["sha256"], sha)
            self.assertEqual(rows[0]["operation"], "adopt")
            doc = load_json(manifest, {})
            rel = "continuity/research_epistemic_shadow/RESEARCH_EPISTEMIC_SHADOW.md"
            self.assertEqual(doc["files"][rel]["sha256"], sha)
            converged = inspect_convergence(self._payload(sha), inspect)
            self.assertEqual(converged["status"], "converged")
            self.assertTrue(converged["artifact"]["registration_current"])
            self.assertEqual(converged["artifact"]["current_generation"], 1)

    def test_repeat_of_current_adoption_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-adopt-idem-") as td:
            _project, target, ledger, _manifest, adopt, _inspect = self._fixture(Path(td))
            original = b"same bytes\n"
            target.write_bytes(original)
            sha = hashlib.sha256(original).hexdigest()
            first = adopt_existing_artifact(self._payload(sha), adopt)
            second = adopt_existing_artifact(self._payload(sha), adopt)
            self.assertTrue(first["adopted"])
            self.assertFalse(second["adopted"])
            self.assertTrue(second["already_current"])
            self.assertEqual(target.read_bytes(), original)
            self.assertEqual(len(ledger.read_text(encoding="utf-8").splitlines()), 1)

    def test_rejects_wrong_current_file_witness_without_metadata_mutation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-adopt-sha-") as td:
            _project, target, ledger, manifest, adopt, _inspect = self._fixture(Path(td))
            original = b"actual\n"
            target.write_bytes(original)
            wrong = hashlib.sha256(b"other").hexdigest()
            with self.assertRaises(LabToolError) as ctx:
                adopt_existing_artifact(self._payload(wrong), adopt)
            self.assertEqual(ctx.exception.error_code, "ARTIFACT_SHA_MISMATCH")
            self.assertEqual(target.read_bytes(), original)
            self.assertFalse(ledger.exists())
            self.assertFalse(manifest.exists())

    def test_existing_lineage_requires_explicit_registered_head_cas(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-adopt-cas-") as td:
            _project, target, ledger, _manifest, adopt, inspect = self._fixture(Path(td))
            old_bytes = b"old\n"
            target.write_bytes(old_bytes)
            old_sha = hashlib.sha256(old_bytes).hexdigest()
            adopt_existing_artifact(self._payload(old_sha), adopt)
            new_bytes = b"new\n"
            target.write_bytes(new_bytes)
            new_sha = hashlib.sha256(new_bytes).hexdigest()
            with self.assertRaises(LabToolError) as missing:
                adopt_existing_artifact(self._payload(new_sha), adopt)
            self.assertEqual(missing.exception.error_code, "REGISTERED_LINEAGE_EXPECTATION_REQUIRED")
            with self.assertRaises(LabToolError) as wrong:
                adopt_existing_artifact(self._payload(new_sha, expected_registered_sha256=new_sha), adopt)
            self.assertEqual(wrong.exception.error_code, "REGISTERED_LINEAGE_MISMATCH")
            adopted = adopt_existing_artifact(self._payload(new_sha, expected_registered_sha256=old_sha), adopt)
            self.assertEqual(adopted["generation"], 2)
            self.assertEqual(target.read_bytes(), new_bytes)
            self.assertEqual(len(ledger.read_text(encoding="utf-8").splitlines()), 2)
            converged = inspect_convergence(self._payload(new_sha), inspect)
            self.assertTrue(converged["artifact"]["registration_current"])
            self.assertEqual(converged["artifact"]["current_generation"], 2)

    def test_missing_artifact_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-adopt-missing-") as td:
            _project, _target, ledger, manifest, adopt, _inspect = self._fixture(Path(td))
            expected = hashlib.sha256(b"missing").hexdigest()
            with self.assertRaises(LabToolError) as ctx:
                adopt_existing_artifact(self._payload(expected), adopt)
            self.assertEqual(ctx.exception.error_code, "ARTIFACT_NOT_FOUND")
            self.assertFalse(ledger.exists())
            self.assertFalse(manifest.exists())


if __name__ == "__main__":
    unittest.main()
