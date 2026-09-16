from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT))

import lab_tools
import lab_tools_ops as ops


def git(root: Path, *args: str) -> str:
    cp = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return cp.stdout.strip()


def init_repo(root: Path) -> None:
    git(root, "init")
    git(root, "config", "user.email", "pcmmad-test@example.invalid")
    git(root, "config", "user.name", "PCMMAD Test")


def dep_for(root: Path):
    def resolve_cwd(_project_id: str, repo_path: str | None):
        candidate = (root / str(repo_path or ".")).resolve()
        candidate.relative_to(root.resolve())
        return candidate

    return SimpleNamespace(
        error_cls=lab_tools.LabToolError,
        get_project_root=lambda _project_id: root,
        resolve_cwd=resolve_cwd,
    )


class GitGroundingPostconditionTests(unittest.TestCase):
    def test_project_subdirectory_inside_ancestor_repo_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            outer = Path(td)
            init_repo(outer)
            (outer / "root.txt").write_text("root", encoding="utf-8")
            git(outer, "add", ".")
            git(outer, "commit", "-m", "root")
            child = outer / "projects" / "child"
            child.mkdir(parents=True)
            dep = dep_for(child)
            with self.assertRaises(lab_tools.LabToolError) as caught:
                ops._git_repo_identity("child", dep)
        self.assertEqual(caught.exception.error_code, "GIT_REPO_SCOPE_MISMATCH")

    def test_nested_repo_path_is_grounded_exactly_within_project(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project = Path(td)
            repo = project / "workspace" / "repo"
            repo.mkdir(parents=True)
            init_repo(repo)
            (repo / "a.txt").write_text("one", encoding="utf-8")
            git(repo, "add", ".")
            git(repo, "commit", "-m", "one")
            resolved, identity = ops._git_repo_identity(
                "alpha", dep_for(project), "workspace/repo"
            )
        self.assertEqual(resolved, repo.resolve())
        self.assertEqual(identity["project_root"], str(project.resolve()))
        self.assertEqual(identity["repo_path"], "workspace/repo")
        self.assertEqual(identity["repo_root"], str(repo.resolve()))
        self.assertTrue(identity["repo_grounded"])

    def test_nested_repo_path_cannot_escape_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / "project"
            outside = Path(td) / "outside"
            project.mkdir(); outside.mkdir(); init_repo(outside)
            with self.assertRaises(ValueError):
                ops._git_repo_identity("alpha", dep_for(project), "../outside")

    def test_unborn_repository_is_valid_identity(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_repo(root)
            resolved, identity = ops._git_repo_identity("alpha", dep_for(root))
        self.assertEqual(resolved, root.resolve())
        self.assertIsNone(identity["head"])
        self.assertTrue(identity["unborn"])

    def test_commit_advances_head_and_verifies_postcondition(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_repo(root)
            (root / "a.txt").write_text("one", encoding="utf-8")
            result = ops._git_commit_payload(
                {"project_id": "alpha", "message": "first"}, dep_for(root)
            )
            self.assertTrue(result["ok"])
            self.assertTrue(result["verified"])
            self.assertIsNone(result["before"]["head"])
            self.assertIsNotNone(result["after"]["head"])
            self.assertNotEqual(result["before"]["head"], result["after"]["head"])
            self.assertFalse(result["after"]["unborn"])
            self.assertFalse(result["status_after"]["dirty"])

    def test_reset_resolves_target_and_verifies_head_and_tracked_tree(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_repo(root)
            target = root / "a.txt"
            target.write_text("one", encoding="utf-8")
            git(root, "add", ".")
            git(root, "commit", "-m", "one")
            first = git(root, "rev-parse", "HEAD")
            target.write_text("two", encoding="utf-8")
            git(root, "add", ".")
            git(root, "commit", "-m", "two")
            second = git(root, "rev-parse", "HEAD")
            self.assertNotEqual(first, second)
            target.write_text("dirty", encoding="utf-8")

            result = ops._git_reset_payload(
                {"project_id": "alpha", "target": first}, dep_for(root)
            )
            self.assertTrue(result["verified"])
            self.assertEqual(result["resolved_target"], first)
            self.assertEqual(result["after"]["head"], first)
            self.assertEqual(target.read_text(encoding="utf-8"), "one")
            self.assertEqual(result["tracked_status"]["stdout"], "")

    def test_invalid_reset_target_fails_before_mutating_head(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_repo(root)
            (root / "a.txt").write_text("one", encoding="utf-8")
            git(root, "add", ".")
            git(root, "commit", "-m", "one")
            before = git(root, "rev-parse", "HEAD")
            with self.assertRaises(lab_tools.LabToolError):
                ops._git_reset_payload(
                    {"project_id": "alpha", "target": "definitely-not-a-ref"},
                    dep_for(root),
                )
            after = git(root, "rev-parse", "HEAD")
        self.assertEqual(before, after)

    def test_clean_previews_then_verifies_no_candidates_remain(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_repo(root)
            (root / "tracked.txt").write_text("tracked", encoding="utf-8")
            git(root, "add", ".")
            git(root, "commit", "-m", "tracked")
            untracked = root / "junk.txt"
            untracked.write_text("junk", encoding="utf-8")

            result = ops._git_clean_payload({"project_id": "alpha"}, dep_for(root))
            self.assertTrue(result["verified"])
            self.assertIn("junk.txt", result["preview_before"]["stdout"])
            self.assertEqual(result["preview_after"]["stdout"], "")
            self.assertFalse(untracked.exists())


if __name__ == "__main__":
    unittest.main()
