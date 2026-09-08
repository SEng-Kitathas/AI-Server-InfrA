from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT))

from lab_tools import LabToolError
from lab_tools_continuity import ContinuityDeps, inspect_convergence


class ContinuityConvergenceClassifierTests(unittest.TestCase):
    def _artifact_fixture(self, root: Path) -> tuple[ContinuityDeps, Path, Path]:
        project_root = root / "project"
        target = project_root / "state" / "current" / "CURRENT_STATE.md"
        ledger = project_root / "system" / "ledger" / "commits.jsonl"
        target.parent.mkdir(parents=True, exist_ok=True)
        ledger.parent.mkdir(parents=True, exist_ok=True)

        def sha(path: Path) -> str:
            return hashlib.sha256(path.read_bytes()).hexdigest()

        deps = ContinuityDeps(
            error_cls=LabToolError,
            get_project_root=lambda _project_id: project_root,
            resolve_target=lambda _project_id, _artifact_class, _logical_name: target,
            commits_ledger_path_for=lambda _project_id: ledger,
            sha256_file=sha,
        )
        return deps, target, ledger

    def _append_registration(self, ledger: Path, sha256: str, commit_id: str) -> None:
        row = {
            "time": "2026-09-07T00:00:00+00:00",
            "project_id": "alpha",
            "artifact_class": "state.current",
            "logical_name": "CURRENT_STATE.md",
            "operation": "update",
            "sha256": sha256,
            "commit_id": commit_id,
        }
        with ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    def test_registered_lineage_distinguishes_equal_stale_and_unknown_divergence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-continuity-lineage-") as td:
            root = Path(td)
            deps, target, ledger = self._artifact_fixture(root)
            target.write_text("generation-one\n", encoding="utf-8")
            sha1 = hashlib.sha256(target.read_bytes()).hexdigest()
            self._append_registration(ledger, sha1, "c1")
            # Duplicate registration of identical bytes must not create a content generation.
            self._append_registration(ledger, sha1, "c1-repeat")

            target.write_text("generation-two\n", encoding="utf-8")
            sha2 = hashlib.sha256(target.read_bytes()).hexdigest()
            self._append_registration(ledger, sha2, "c2")
            unknown = "f" * 64

            observed = inspect_convergence(
                {
                    "project_id": "alpha",
                    "artifact": {
                        "artifact_class": "state.current",
                        "logical_name": "CURRENT_STATE.md",
                    },
                    "observations": [
                        {"source": "same", "sha256": sha2},
                        {"source": "old", "sha256": sha1},
                        {"source": "unknown", "sha256": unknown},
                    ],
                },
                deps,
            )
            artifact = observed["artifact"]
            self.assertTrue(artifact["registration_current"])
            self.assertEqual(artifact["current_generation"], 2)
            relations = {row["source"]: row for row in artifact["observations"]}
            self.assertEqual(relations["same"]["relation"], "equal_current")
            self.assertEqual(relations["old"]["relation"], "stale_known_ancestor")
            self.assertFalse(relations["old"]["human_conflict_required"])
            self.assertEqual(relations["unknown"]["relation"], "divergent_or_ahead_unknown")
            self.assertTrue(relations["unknown"]["human_conflict_required"])
            self.assertEqual(observed["status"], "divergent_or_unproven")

    def test_unregistered_local_bytes_fail_closed_even_when_observation_matches_them(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-continuity-unregistered-") as td:
            root = Path(td)
            deps, target, ledger = self._artifact_fixture(root)
            target.write_text("registered\n", encoding="utf-8")
            registered = hashlib.sha256(target.read_bytes()).hexdigest()
            self._append_registration(ledger, registered, "c1")
            target.write_text("newer-unregistered\n", encoding="utf-8")
            local_sha = hashlib.sha256(target.read_bytes()).hexdigest()

            observed = inspect_convergence(
                {
                    "project_id": "alpha",
                    "artifact": {
                        "artifact_class": "state.current",
                        "logical_name": "CURRENT_STATE.md",
                    },
                    "observations": [{"source": "mirror", "sha256": local_sha}],
                },
                deps,
            )
            self.assertFalse(observed["artifact"]["registration_current"])
            self.assertEqual(observed["artifact"]["observations"][0]["relation"], "matches_unregistered_local")
            self.assertTrue(observed["artifact"]["observations"][0]["human_conflict_required"])
            self.assertEqual(observed["status"], "local_unregistered")

    def test_git_ancestry_classifies_stale_ahead_and_divergent_without_timestamps(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-continuity-git-") as td:
            root = Path(td)
            deps, target, ledger = self._artifact_fixture(root)
            target.write_text("current\n", encoding="utf-8")
            current_sha = hashlib.sha256(target.read_bytes()).hexdigest()
            self._append_registration(ledger, current_sha, "artifact-current")

            repo = deps.get_project_root("alpha") / "repo"
            repo.mkdir(parents=True)
            def git(*args: str) -> str:
                completed = subprocess.run(
                    ["git", *args], cwd=repo, capture_output=True, text=True, check=True
                )
                return completed.stdout.strip()

            git("init")
            git("config", "user.email", "pcmmad@example.invalid")
            git("config", "user.name", "PCMMAD Test")
            (repo / "f.txt").write_text("one\n", encoding="utf-8")
            git("add", "f.txt")
            git("commit", "-m", "one")
            old = git("rev-parse", "HEAD")
            (repo / "f.txt").write_text("two\n", encoding="utf-8")
            git("commit", "-am", "two")
            target_commit = git("rev-parse", "HEAD")
            git("branch", "side", old)
            (repo / "f.txt").write_text("three\n", encoding="utf-8")
            git("commit", "-am", "three")
            ahead = git("rev-parse", "HEAD")
            git("checkout", "side")
            (repo / "side.txt").write_text("side\n", encoding="utf-8")
            git("add", "side.txt")
            git("commit", "-m", "side")
            divergent = git("rev-parse", "HEAD")
            git("checkout", "-")

            observed = inspect_convergence(
                {
                    "project_id": "alpha",
                    "artifact": {
                        "artifact_class": "state.current",
                        "logical_name": "CURRENT_STATE.md",
                    },
                    "git": {
                        "repo_path": "repo",
                        "target_commit": target_commit,
                        "observations": [
                            {"source": "old", "commit": old},
                            {"source": "ahead", "commit": ahead},
                            {"source": "side", "commit": divergent},
                            {"source": "unknown", "commit": "f" * 40},
                        ],
                    },
                },
                deps,
            )
            rows = {row["source"]: row for row in observed["git"]["observations"]}
            self.assertEqual(rows["old"]["relation"], "stale_known_ancestor")
            self.assertEqual(rows["ahead"]["relation"], "ahead_known_descendant")
            self.assertEqual(rows["side"]["relation"], "divergent")
            self.assertTrue(rows["side"]["human_conflict_required"])
            self.assertEqual(rows["unknown"]["relation"], "unknown_commit")
            self.assertEqual(observed["status"], "divergent_or_unproven")

    def test_git_repo_path_must_name_exact_grounded_repo_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-continuity-git-scope-") as td:
            root = Path(td)
            deps, target, ledger = self._artifact_fixture(root)
            target.write_text("current\n", encoding="utf-8")
            current_sha = hashlib.sha256(target.read_bytes()).hexdigest()
            self._append_registration(ledger, current_sha, "artifact-current")
            repo = deps.get_project_root("alpha") / "repo"
            child = repo / "child"
            child.mkdir(parents=True)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            with self.assertRaises(LabToolError) as raised:
                inspect_convergence(
                    {
                        "project_id": "alpha",
                        "artifact": {
                            "artifact_class": "state.current",
                            "logical_name": "CURRENT_STATE.md",
                        },
                        "git": {"repo_path": "repo/child", "observations": []},
                    },
                    deps,
                )
            self.assertEqual(raised.exception.error_code, "GIT_REPO_SCOPE_MISMATCH")


if __name__ == "__main__":
    unittest.main()
