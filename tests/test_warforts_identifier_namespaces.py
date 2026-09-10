from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "baseline" / "pcmmad_receiver"))

import shared_core
import user_continuity_store as memory


class ProjectIdentifierNamespaceTests(unittest.TestCase):
    def test_dot_project_id_rejected_not_projects_root(self):
        with self.assertRaises(ValueError):
            shared_core.validate_project_id(".")

    def test_dotdot_project_id_rejected(self):
        with self.assertRaises(ValueError):
            shared_core.validate_project_id("..")

    def test_trailing_dot_project_id_rejected(self):
        with self.assertRaises(ValueError):
            shared_core.validate_project_id("project.")

    def test_reserved_windows_device_project_ids_rejected(self):
        for value in ("CON", "NUL", "PRN", "AUX", "COM1", "LPT9", "con.txt"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                shared_core.validate_project_id(value)


    def test_existing_project_case_alias_rejected_on_case_insensitive_identity(self):
        old_root = shared_core.PROJECTS_ROOT
        with tempfile.TemporaryDirectory() as td:
            shared_core.PROJECTS_ROOT = Path(td)
            try:
                (shared_core.PROJECTS_ROOT / "CanonicalProject").mkdir()
                self.assertEqual(shared_core.get_project_root("CanonicalProject").name, "CanonicalProject")
                with self.assertRaises(ValueError):
                    shared_core.get_project_root("canonicalproject")
            finally:
                shared_core.PROJECTS_ROOT = old_root

    def test_normal_current_project_id_remains_valid(self):
        self.assertEqual(shared_core.validate_project_id("PCMMAD_RECEIVER_LAB"), "PCMMAD_RECEIVER_LAB")


class ProfileIdentifierNamespaceTests(unittest.TestCase):
    def test_dot_profile_id_rejected(self):
        with self.assertRaises(memory.UserContinuityError) as ctx:
            memory._profile_id(".")
        self.assertEqual(ctx.exception.error_code, "BAD_PROFILE_ID")

    def test_trailing_dot_profile_id_rejected(self):
        with self.assertRaises(memory.UserContinuityError) as ctx:
            memory._profile_id("user.")
        self.assertEqual(ctx.exception.error_code, "BAD_PROFILE_ID")

    def test_reserved_windows_device_profile_ids_rejected(self):
        for value in ("CON", "NUL", "PRN", "AUX", "COM1", "LPT9", "con.txt"):
            with self.subTest(value=value):
                with self.assertRaises(memory.UserContinuityError) as ctx:
                    memory._profile_id(value)
                self.assertEqual(ctx.exception.error_code, "BAD_PROFILE_ID")

    def test_case_is_canonicalized_after_namespace_validation(self):
        self.assertEqual(memory._profile_id("CaseUser"), "caseuser")


if __name__ == "__main__":
    unittest.main()
