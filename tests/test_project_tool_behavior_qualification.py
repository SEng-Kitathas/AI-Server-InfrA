"""Behavior qualification for native project read/context/model/archive tools.

These regressions exist because a registered tool card once advertised project.context.rehydrate
while its handler raised NameError at execution, and sibling project tools returned dataclass
responses that the lab router rejected as non-object results.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT))

import context_engine as ce
import lab_tools
import lab_tools_project as project_tools


class _Response:
    def __init__(self, request: object) -> None:
        self.request = request

    def to_dict(self) -> dict[str, object]:
        return {"ok": True, "request_type": type(self.request).__name__}


class ProjectToolBehaviorQualificationTests(unittest.TestCase):
    def _deps(self) -> SimpleNamespace:
        def wrap(fn):
            return lab_tools._context_wrap(fn)

        return SimpleNamespace(
            context_wrap=wrap,
            normalize_project_path=lambda payload: str(payload.get("path") or "."),
            project_root_path=lambda project_id: f"/qualified/{project_id}",
            read_file=lambda request: _Response(request),
            search_files=lambda request: _Response(request),
            rehydrate_context=lambda request: _Response(request),
            list_models=lambda request: _Response(request),
            list_archives=lambda request: _Response(request),
        )

    def test_context_wrap_projects_to_json_object(self) -> None:
        result = lab_tools._context_wrap(lambda: _Response(object()))
        self.assertEqual(result["ok"], True)
        self.assertEqual(result["request_type"], "object")

    def test_project_read_family_constructs_real_context_request_types(self) -> None:
        dep = self._deps()
        cases = [
            (
                project_tools._project_files_read_payload,
                {"project_id": "alpha", "path": "README.md", "start_line": 1, "end_line": 5},
                "FileReadRequest",
            ),
            (
                project_tools._project_files_search_payload,
                {"project_id": "alpha", "path": ".", "query": "needle", "limit": 5},
                "FileSearchRequest",
            ),
            (
                project_tools._project_context_rehydrate_payload,
                {"project_id": "alpha", "path": ".", "topic": "current frontier", "budget_bytes": 4096},
                "RehydrateRequest",
            ),
            (
                project_tools._project_models_list_payload,
                {"project_id": "alpha", "path": ".", "limit": 5},
                "ModelListRequest",
            ),
            (
                project_tools._project_archives_list_payload,
                {"project_id": "alpha", "path": ".", "limit": 5},
                "ArchiveListRequest",
            ),
        ]
        for helper, payload, expected in cases:
            with self.subTest(helper=helper.__name__):
                result = helper(payload, dep)
                self.assertEqual(result["ok"], True)
                self.assertEqual(result["request_type"], expected)

    def test_project_module_imports_all_context_request_types_it_uses(self) -> None:
        expected = {
            "ArchiveExtractRequest": ce.ArchiveExtractRequest,
            "ArchiveListRequest": ce.ArchiveListRequest,
            "FileListRequest": ce.FileListRequest,
            "FileReadRequest": ce.FileReadRequest,
            "FileSearchRequest": ce.FileSearchRequest,
            "ModelListRequest": ce.ModelListRequest,
            "RehydrateRequest": ce.RehydrateRequest,
        }
        for name, request_type in expected.items():
            with self.subTest(name=name):
                self.assertIs(getattr(project_tools, name), request_type)


if __name__ == "__main__":
    unittest.main()
