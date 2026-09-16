from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "baseline" / "pcmmad_receiver"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

import lab_tools
from lab_tools_ops import _resolve_git_executable


def _git() -> str:
    executable, error = _resolve_git_executable()
    if executable is None or error is not None:
        raise RuntimeError(error or "GIT_EXECUTABLE_NOT_FOUND")
    return executable


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run([_git(), "init"], cwd=path, check=True, capture_output=True)


def _result(payload):
    envelope = lab_tools.dispatch_tool("machine.repositories.list", payload)
    assert envelope["ok"] is True
    return envelope["result"]


def test_machine_repository_discovery_requires_explicit_root():
    with pytest.raises(lab_tools.LabToolError) as caught:
        lab_tools.dispatch_tool("machine.repositories.list", {})
    assert caught.value.error_code == "BAD_REQUEST"
    assert "machine.roots.list" in caught.value.extra["lawful_next"]


def test_machine_repository_discovery_finds_exact_nested_repositories():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        repo_a = base / "a"
        repo_b = base / "deep" / "b"
        _init_repo(repo_a); _init_repo(repo_b)
        result = _result({"root": str(base), "max_depth": 4, "max_results": 10})
        assert result["scope"] == "operator_machine_read"
        assert result["mutation_authority"] is False
        assert result["count"] == 2
        roots = {Path(row["repo_root"]).resolve() for row in result["repositories"]}
        assert roots == {repo_a.resolve(), repo_b.resolve()}
        assert all(row["exact_repo_identity"] is True for row in result["repositories"])


def test_machine_repository_discovery_bounds_depth_and_results():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        shallow = base / "one"
        deep = base / "x" / "y" / "repo"
        _init_repo(shallow); _init_repo(deep)
        depth_limited = _result({"root": str(base), "max_depth": 1, "max_results": 10})
        assert [row["root_relative_path"] for row in depth_limited["repositories"]] == ["one"]
        result_limited = _result({"root": str(base), "max_depth": 4, "max_results": 1})
        assert result_limited["count"] == 1
        assert result_limited["truncated"] is True


def test_machine_repository_discovery_rejects_relative_root():
    with pytest.raises(lab_tools.LabToolError) as caught:
        lab_tools.dispatch_tool("machine.repositories.list", {"root": "relative/path"})
    assert caught.value.error_code == "BAD_REQUEST"


def test_machine_repository_discovery_is_read_only_operator_scope():
    spec = lab_tools._TOOL_REGISTRY["machine.repositories.list"]
    assert spec.category == "machine"
    assert spec.approval_required is False
    assert spec.mutating is False
    traits = set(spec.effect_traits or [])
    assert {"operator_scope", "explicit_root_required", "bounded_results", "bounded_traversal", "does_not_grant_mutation_authority"} <= traits
