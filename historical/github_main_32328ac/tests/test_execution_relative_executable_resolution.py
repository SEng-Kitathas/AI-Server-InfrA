from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pcmmad_receiver import execution_routes as er


@unittest.skipUnless(os.name == "nt", "Windows executable-resolution tests")
class ExecutionRelativeExecutableResolutionTests(unittest.TestCase):
    def test_async_normalization_persists_cwd_resolved_executable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-relative-exec-") as td:
            project = Path(td) / "project"
            cwd = project / "work"
            tools = cwd / "tools"
            tools.mkdir(parents=True)
            local_cmd = tools / "cmd.exe"
            shutil.copy2(Path(os.environ.get("COMSPEC", r"C:\Windows\System32\cmd.exe")), local_cmd)
            with patch.object(er, "get_project_root", return_value=project):
                normalized = er._normalize_submit_payload(
                    {
                        "project_id": "alpha",
                        "command": [r"tools\cmd.exe"],
                        "args": ["/c", "echo", "ok"],
                        "cwd": "work",
                    }
                )
            self.assertEqual(Path(normalized.command[0]), local_cmd.resolve())
            self.assertEqual(normalized.cwd, str(cwd.resolve()))
            self.assertTrue(normalized.submission_fingerprint)

    def test_async_missing_relative_executable_has_typed_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-relative-exec-") as td:
            project = Path(td) / "project"
            (project / "work").mkdir(parents=True)
            with patch.object(er, "get_project_root", return_value=project):
                with self.assertRaises(er.ExecutionRequestError) as ctx:
                    er._normalize_submit_payload(
                        {
                            "project_id": "alpha",
                            "command": [r"missing\tool.exe"],
                            "cwd": "work",
                        }
                    )
            self.assertEqual(ctx.exception.error_code, "COMMAND_NOT_FOUND")

    def test_async_drive_relative_executable_is_typed_workdir_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-relative-exec-") as td:
            project = Path(td) / "project"
            project.mkdir(parents=True)
            with patch.object(er, "get_project_root", return_value=project):
                with self.assertRaises(er.ExecutionRequestError) as ctx:
                    er._normalize_submit_payload(
                        {"project_id": "alpha", "command": [r"C:tool.exe"], "cwd": "."}
                    )
            self.assertEqual(ctx.exception.error_code, "WORKDIR_INVALID")

    def test_bare_command_remains_path_resolved(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-relative-exec-") as td:
            project = Path(td) / "project"
            project.mkdir(parents=True)
            with patch.object(er, "get_project_root", return_value=project):
                normalized = er._normalize_submit_payload(
                    {"project_id": "alpha", "command": ["python"], "args": ["--version"], "cwd": "."}
                )
            self.assertEqual(normalized.command[0], "python")


if __name__ == "__main__":
    unittest.main()
