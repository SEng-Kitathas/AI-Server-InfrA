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

import lab_tools_semantic as sem


class FakeLabToolError(Exception):
    def __init__(self, error_code: str, message: str, status: int = 400, **extra):
        super().__init__(message)
        self.error_code = error_code
        self.status = status
        self.extra = extra


class SemanticRuntimeResolutionTests(unittest.TestCase):
    def test_dependency_probe_executes_valid_python_c_payload(self) -> None:
        probe = sem._dependency_probe(Path(sys.executable), PROJECT_ROOT)
        self.assertTrue(probe.execution_ok, probe.probe)
        self.assertEqual(set(probe.modules), set(sem._REQUIRED_MODULES))
        self.assertNotIn("SyntaxError", str(probe.probe.get("stderr") or ""))

    def test_unavailable_search_fails_before_retriever_execution(self) -> None:
        resolution = {
            "status": "unavailable",
            "available": False,
            "blockers": ["no_qualified_python_runtime"],
        }
        with patch.object(sem, "_semantic_resolution", return_value=resolution), patch.object(
            sem, "run_subprocess_envelope"
        ) as execute:
            with self.assertRaises(FakeLabToolError) as caught:
                sem._monster_search_payload({"query": "test"}, FakeLabToolError)
            self.assertEqual(caught.exception.error_code, "SEMANTIC_UNAVAILABLE")
            self.assertEqual(caught.exception.status, 503)
            execute.assert_not_called()

    def test_search_injects_resolved_paths_without_mutating_parent_environment(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            script = base / "retriever.py"
            py = Path(sys.executable)
            db = base / "db.sqlite"
            minilm = base / "minilm"
            jina = base / "jina"
            model = base / "model"
            script.write_text("print('{}')", encoding="utf-8")
            db.write_text("x", encoding="utf-8")
            for p in (minilm, jina, model):
                p.mkdir()
            resolution = {
                "status": "online",
                "available": True,
                "blockers": [],
                "resources": {
                    "script": {"path": str(script), "sha256": "abc", "exists": True},
                    "db": {"path": str(db), "exists": True},
                    "minilm_index": {"path": str(minilm), "exists": True},
                    "jina_index": {"path": str(jina), "exists": True},
                    "minilm_model": {"path": str(model), "exists": True},
                },
                "python": {"selected": {"path": str(py)}},
            }
            captured = {}

            def fake_run(command, **options):
                captured["command"] = command
                captured["env"] = options.get("env")
                return {"ok": True, "stdout": "{}", "stderr": "", "return_code": 0}

            before = os.environ.get("MONSTER_DB_HELPER_DB_PATH")
            with patch.object(sem, "_semantic_resolution", return_value=resolution), patch.object(
                sem, "run_subprocess_envelope", side_effect=fake_run
            ):
                result = sem._monster_search_payload({"query": "hello", "topk": 3}, FakeLabToolError)
            self.assertTrue(result["parsed_ok"])
            self.assertEqual(captured["command"][0], str(py))
            self.assertEqual(captured["env"]["MONSTER_DB_HELPER_DB_PATH"], str(db))
            self.assertEqual(captured["env"]["MONSTER_DB_HELPER_MINILM_INDEX_DIR"], str(minilm))
            self.assertEqual(captured["env"]["MONSTER_DB_HELPER_JINA_INDEX_DIR"], str(jina))
            self.assertEqual(captured["env"]["MONSTER_DB_HELPER_MINILM_MODEL_PATH"], str(model))
            self.assertEqual(os.environ.get("MONSTER_DB_HELPER_DB_PATH"), before)

    def test_projects_root_prefers_explicit_environment(self) -> None:
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ, {"PCMMAD_PROJECTS_ROOT": td}, clear=False
        ):
            self.assertEqual(sem._projects_root(), Path(td))


if __name__ == "__main__":
    unittest.main()
