from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT))

import context_engine


class ContextProjectScopeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.global_root = Path(self.temp.name).resolve()
        self.project_a = (self.global_root / "projects" / "a").resolve()
        self.project_b = (self.global_root / "projects" / "b").resolve()
        self.project_a.mkdir(parents=True)
        self.project_b.mkdir(parents=True)
        (self.project_a / "inside.txt").write_text("inside", encoding="utf-8")
        (self.project_b / "secret.txt").write_text("secret", encoding="utf-8")
        self.allowed_patch = patch.object(
            context_engine, "get_allowed_roots", return_value=[self.global_root]
        )
        self.allowed_patch.start()

    def tearDown(self) -> None:
        self.allowed_patch.stop()
        self.temp.cleanup()

    def test_in_scope_relative_path_resolves(self) -> None:
        resolved = context_engine.resolve_user_path(
            "inside.txt", base_root=str(self.project_a)
        )
        self.assertEqual(resolved, self.project_a / "inside.txt")

    def test_relative_dotdot_cannot_escape_project_to_other_allowed_project(self) -> None:
        with self.assertRaises(context_engine.BadPathError):
            context_engine.resolve_user_path(
                "../b/secret.txt", base_root=str(self.project_a)
            )

    def test_absolute_path_to_other_allowed_project_is_rejected_when_scoped(self) -> None:
        with self.assertRaises(context_engine.BadPathError):
            context_engine.resolve_user_path(
                str(self.project_b / "secret.txt"), base_root=str(self.project_a)
            )

    def test_general_unscoped_operation_can_still_address_allowed_root(self) -> None:
        resolved = context_engine.resolve_user_path(str(self.project_b / "secret.txt"))
        self.assertEqual(resolved, self.project_b / "secret.txt")

    def test_symlink_escape_is_rejected_when_platform_allows_symlink(self) -> None:
        link = self.project_a / "escape-link"
        try:
            os.symlink(self.project_b, link, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation not available under current Windows privileges")
        with self.assertRaises(context_engine.BadPathError):
            context_engine.resolve_user_path(
                "escape-link/secret.txt", base_root=str(self.project_a)
            )


if __name__ == "__main__":
    unittest.main()


class ContextWindowsJunctionScopeTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows junction test")
    def test_directory_junction_escape_is_rejected(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory() as td:
            global_root = Path(td).resolve()
            project_a = global_root / "projects" / "a"
            project_b = global_root / "projects" / "b"
            project_a.mkdir(parents=True)
            project_b.mkdir(parents=True)
            (project_b / "secret.txt").write_text("secret", encoding="utf-8")
            junction = project_a / "junction"
            cp = subprocess.run(
                ["cmd", "/d", "/c", "mklink", "/J", str(junction), str(project_b)],
                capture_output=True,
                text=True,
                check=False,
            )
            if cp.returncode != 0:
                self.skipTest(f"junction creation unavailable: {cp.stderr or cp.stdout}")
            with patch.object(context_engine, "get_allowed_roots", return_value=[global_root]):
                with self.assertRaises(context_engine.BadPathError):
                    context_engine.resolve_user_path(
                        "junction/secret.txt", base_root=str(project_a)
                    )
