"""
Arrange: set up focused fixtures.
Act: exercise the target behavior.
Assert: verify the expected contract.
Regression tests for git and gate operation hardening envelopes."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
import sys
from collections.abc import Mapping, MutableMapping
from typing import Callable, TypeAlias

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "baseline" / "pcmmad_receiver"))

from lab_tools_ops import register_ops_tools

ToolValue: TypeAlias = (
    str | int | float | bool | None | list["ToolValue"] | Mapping[str, "ToolValue"]
)
ToolPayload: TypeAlias = Mapping[str, ToolValue]
ToolResult: TypeAlias = Mapping[str, ToolValue]
ToolCallable: TypeAlias = Callable[[ToolPayload], ToolResult]
ToolRegistry: TypeAlias = MutableMapping[str, ToolCallable]


class ToolError(Exception):
    def __init__(self, error_code: str, message: str, status: int = 400, **extra: object) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.status = status
        self.extra = extra


def _registry_for(root: Path) -> ToolRegistry:
    registry: ToolRegistry = {}

    def register_tool(
        name: str, description: str, danger_tier: str = "medium", **kwargs: ToolValue
    ) -> Callable[[ToolCallable], ToolCallable]:
        def deco(fn: ToolCallable) -> ToolCallable:
            registry[name] = fn
            return fn

        return deco

    register_ops_tools(
        register_tool,
        error_cls=ToolError,
        get_project_root=lambda project_id: root,
        resolve_cwd=lambda project_id, cwd: root if not cwd else (root / str(cwd)).resolve(),
        exec_env=lambda payload: {},
        append_reflexion=lambda project_id, payload: None,
        beautiful_soup=None,
    )
    return registry


class GitOpsHardeningTests(unittest.TestCase):
    def test_verify_gates_returns_subprocess_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = _registry_for(root)
            result = registry["verify.gates"](
                {
                    "project_id": "x",
                    "gates": [{"name": "ok", "command": ["python", "-c", 'print("ok")']}],
                    "timeout_each": 10,
                }
            )
            self.assertEqual(result["overall"], "passed")
            self.assertTrue(result["results"][0]["ok"])
            self.assertIn("duration_ms", result["results"][0])
            self.assertIn("stdout_truncated", result["results"][0])

    def test_git_status_supports_exact_nested_repo_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "nested" / "repo"
            repo.mkdir(parents=True)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "pcmmad-test@example.invalid"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "PCMMAD Test"], cwd=repo, check=True)
            (repo / "a.txt").write_text("one", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "one"], cwd=repo, check=True, capture_output=True)
            registry = _registry_for(root)
            result = registry["git.status"](
                {"project_id": "x", "repo_path": "nested/repo"}
            )
            self.assertTrue(result["ok"])
            self.assertTrue(result["repo_grounded"])
            self.assertEqual(result["repo_identity"]["repo_path"], "nested/repo")
            self.assertEqual(Path(result["repo_identity"]["repo_root"]), repo.resolve())

    def test_git_status_returns_envelope_even_outside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = _registry_for(root)
            result = registry["git.status"]({"project_id": "x"})
            self.assertIn("ok", result)
            self.assertIn("status", result)
            self.assertIn("return_code", result)
            self.assertIn("stderr_truncated", result)


if __name__ == "__main__":
    unittest.main()
