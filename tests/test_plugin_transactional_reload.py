from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

import lab_tools


PLUGIN_PREFIX = "pcmmad_lab_plugin_"


class PluginTransactionalReloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        (self.base / "lab_plugins").mkdir()
        self.original_base = lab_tools._BASE_DIR
        self.registry = dict(lab_tools._TOOL_REGISTRY)
        self.plugin_specs = dict(lab_tools._PLUGIN_TOOL_SPECS)
        self.plugin_loads = list(lab_tools._PLUGIN_LOADS)
        self.plugin_errors = list(lab_tools._PLUGIN_ERRORS)
        self.generation = lab_tools._PLUGIN_GENERATION
        self.last_reload = (
            dict(lab_tools._PLUGIN_LAST_RELOAD)
            if isinstance(lab_tools._PLUGIN_LAST_RELOAD, dict)
            else lab_tools._PLUGIN_LAST_RELOAD
        )
        self.loads_id = id(lab_tools._PLUGIN_LOADS)
        self.errors_id = id(lab_tools._PLUGIN_ERRORS)
        self.original_plugin_modules = {
            name: module
            for name, module in sys.modules.items()
            if name.startswith(PLUGIN_PREFIX)
        }
        lab_tools._BASE_DIR = self.base

    def tearDown(self) -> None:
        lab_tools._BASE_DIR = self.original_base
        with lab_tools._REGISTRY_LOCK:
            lab_tools._TOOL_REGISTRY.clear()
            lab_tools._TOOL_REGISTRY.update(self.registry)
            lab_tools._PLUGIN_TOOL_SPECS.clear()
            lab_tools._PLUGIN_TOOL_SPECS.update(self.plugin_specs)
            lab_tools._PLUGIN_LOADS.clear()
            lab_tools._PLUGIN_LOADS.extend(self.plugin_loads)
            lab_tools._PLUGIN_ERRORS.clear()
            lab_tools._PLUGIN_ERRORS.extend(self.plugin_errors)
            lab_tools._PLUGIN_GENERATION = self.generation
            lab_tools._PLUGIN_LAST_RELOAD = self.last_reload
        for name in list(sys.modules):
            if name.startswith(PLUGIN_PREFIX):
                sys.modules.pop(name, None)
        sys.modules.update(self.original_plugin_modules)
        self.temp.cleanup()

    def _write(self, name: str, body: str) -> Path:
        path = self.base / "lab_plugins" / f"{name}.py"
        path.write_text(body, encoding="utf-8")
        return path

    @staticmethod
    def _simple_plugin(tool_name: str, *, marker: str = "v1") -> str:
        return f'''\nMARKER = {marker!r}\ndef register(register_tool):\n    @register_tool({tool_name!r}, "temporary plugin", "low", category="test", side_effect_class="read", effect_traits=["reads_state"])\n    def _tool(payload):\n        return {{"marker": MARKER}}\n'''

    def test_partial_plugin_failure_leaves_live_registry_unchanged(self) -> None:
        self._write("a_good", self._simple_plugin("temp.good"))
        self._write(
            "b_bad",
            '''\ndef register(register_tool):\n    @register_tool("temp.partial", "partial", "low")\n    def _tool(payload):\n        return {"ok": True}\n    raise RuntimeError("boom-after-registration")\n''',
        )
        before_ids = {name: id(spec) for name, spec in lab_tools._TOOL_REGISTRY.items()}
        receipt = lab_tools._load_plugins()
        self.assertFalse(receipt["committed"])
        self.assertEqual(lab_tools._PLUGIN_GENERATION, self.generation)
        self.assertEqual(set(lab_tools._TOOL_REGISTRY), set(self.registry))
        self.assertEqual(
            {name: id(spec) for name, spec in lab_tools._TOOL_REGISTRY.items()},
            before_ids,
        )
        self.assertNotIn("temp.good", lab_tools._TOOL_REGISTRY)
        self.assertNotIn("temp.partial", lab_tools._TOOL_REGISTRY)
        self.assertTrue(lab_tools._PLUGIN_ERRORS)
        self.assertIn("boom-after-registration", lab_tools._PLUGIN_ERRORS[0])
        self.assertNotIn("pcmmad_lab_plugin_a_good", sys.modules)
        self.assertNotIn("pcmmad_lab_plugin_b_bad", sys.modules)

    def test_duplicate_plugin_capability_is_transactionally_rejected(self) -> None:
        self._write("a", self._simple_plugin("temp.dup", marker="a"))
        self._write("b", self._simple_plugin("temp.dup", marker="b"))
        receipt = lab_tools._load_plugins()
        self.assertFalse(receipt["committed"])
        self.assertNotIn("temp.dup", lab_tools._TOOL_REGISTRY)
        self.assertIn("duplicate plugin capability", receipt["error"])

    def test_plugin_cannot_override_core_capability(self) -> None:
        core = lab_tools._TOOL_REGISTRY["lab.health"]
        self._write("collision", self._simple_plugin("lab.health"))
        receipt = lab_tools._load_plugins()
        self.assertFalse(receipt["committed"])
        self.assertIs(lab_tools._TOOL_REGISTRY["lab.health"], core)
        self.assertIn("collides with core tool", receipt["error"])

    def test_successful_reload_removes_stale_plugin_tool_when_file_disappears(self) -> None:
        path = self._write("one", self._simple_plugin("temp.one"))
        first = lab_tools._load_plugins()
        self.assertTrue(first["committed"])
        self.assertIn("temp.one", lab_tools._TOOL_REGISTRY)
        self.assertEqual(set(lab_tools._PLUGIN_TOOL_SPECS), {"temp.one"})
        path.unlink()
        second = lab_tools._load_plugins()
        self.assertTrue(second["committed"])
        self.assertNotIn("temp.one", lab_tools._TOOL_REGISTRY)
        self.assertEqual(lab_tools._PLUGIN_TOOL_SPECS, {})
        self.assertNotIn("pcmmad_lab_plugin_one", sys.modules)

    def test_source_change_changes_plugin_contract_digest_and_load_hash(self) -> None:
        path = self._write("one", self._simple_plugin("temp.one", marker="v1"))
        first = lab_tools._load_plugins()
        digest1 = first["plugin_contract_digest"]
        hash1 = lab_tools._PLUGIN_LOADS[0].sha256
        path.write_text(self._simple_plugin("temp.one", marker="v2"), encoding="utf-8")
        second = lab_tools._load_plugins()
        digest2 = second["plugin_contract_digest"]
        hash2 = lab_tools._PLUGIN_LOADS[0].sha256
        self.assertTrue(second["committed"])
        self.assertNotEqual(digest1, digest2)
        self.assertNotEqual(hash1, hash2)
        self.assertEqual(len(hash2 or ""), 64)
        self.assertGreater(second["generation"], first["generation"])

    def test_plugin_bookkeeping_objects_are_updated_in_place(self) -> None:
        self._write("one", self._simple_plugin("temp.one"))
        result = lab_tools._load_plugins()
        self.assertTrue(result["committed"])
        self.assertEqual(id(lab_tools._PLUGIN_LOADS), self.loads_id)
        self.assertEqual(id(lab_tools._PLUGIN_ERRORS), self.errors_id)
        self.assertEqual(len(lab_tools._PLUGIN_LOADS), 1)
        runtime = lab_tools._plugin_runtime_state()
        self.assertEqual(runtime["generation"], result["generation"])
        self.assertEqual(runtime["plugin_tool_count"], 1)
        self.assertEqual(runtime["contract_digest"], result["plugin_contract_digest"])

    def test_failure_updates_error_list_in_place_but_preserves_previous_plugins(self) -> None:
        self._write("one", self._simple_plugin("temp.one"))
        good = lab_tools._load_plugins()
        self.assertTrue(good["committed"])
        prior_spec = lab_tools._TOOL_REGISTRY["temp.one"]
        prior_generation = lab_tools._PLUGIN_GENERATION
        self._write("bad", "raise RuntimeError('import-failure')\n")
        failed = lab_tools._load_plugins()
        self.assertFalse(failed["committed"])
        self.assertEqual(id(lab_tools._PLUGIN_ERRORS), self.errors_id)
        self.assertEqual(lab_tools._PLUGIN_GENERATION, prior_generation)
        self.assertIs(lab_tools._TOOL_REGISTRY["temp.one"], prior_spec)
        self.assertIn("import-failure", lab_tools._PLUGIN_ERRORS[0])


if __name__ == "__main__":
    unittest.main()
