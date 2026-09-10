from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASELINE_ROOT = PROJECT_ROOT / "baseline"


class PackageEmbeddingBoundaryTests(unittest.TestCase):
    def _run(
        self,
        code: str,
        *,
        pythonpath: Path = BASELINE_ROOT,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(pythonpath)
        return subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(cwd or PROJECT_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_package_import_works_without_package_directory_on_sys_path(self) -> None:
        code = (
            "import json, pcmmad_receiver.lab_tools as x; "
            "print(json.dumps({'count': len(x.list_tools()), 'plugin_errors': x._PLUGIN_ERRORS}))"
        )
        result = self._run(code)
        self.assertEqual(result.returncode, 0, result.stderr)
        observed = json.loads(result.stdout)
        self.assertEqual(observed["count"], 158)
        self.assertEqual(observed["plugin_errors"], [])

    def test_package_first_and_legacy_second_share_single_module_identity(self) -> None:
        code = r'''
import importlib, json
package_tools=importlib.import_module("pcmmad_receiver.lab_tools")
legacy_tools=importlib.import_module("lab_tools")
package_core=importlib.import_module("pcmmad_receiver.shared_core")
legacy_core=importlib.import_module("shared_core")
print(json.dumps({
  "tools_same": package_tools is legacy_tools,
  "core_same": package_core is legacy_core,
  "registry_same": package_tools._TOOL_REGISTRY is legacy_tools._TOOL_REGISTRY,
}))
'''
        result = self._run(code)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            {"tools_same": True, "core_same": True, "registry_same": True},
        )

    def test_legacy_first_and_package_second_share_single_module_identity(self) -> None:
        code = r'''
import importlib, json
legacy_tools=importlib.import_module("lab_tools")
package_tools=importlib.import_module("pcmmad_receiver.lab_tools")
legacy_core=importlib.import_module("shared_core")
package_core=importlib.import_module("pcmmad_receiver.shared_core")
print(json.dumps({
  "tools_same": package_tools is legacy_tools,
  "core_same": package_core is legacy_core,
  "registry_same": package_tools._TOOL_REGISTRY is legacy_tools._TOOL_REGISTRY,
}))
'''
        result = self._run(code)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            {"tools_same": True, "core_same": True, "registry_same": True},
        )

    def test_direct_execution_worker_entrypoint_bootstraps_package_imports(self) -> None:
        missing = PROJECT_ROOT / ".missing-worker-request.json"
        result = subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "baseline" / "pcmmad_receiver" / "execution_worker.py"),
                str(missing),
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("attempted relative import", result.stderr)
        self.assertNotIn("ModuleNotFoundError", result.stderr)
        self.assertIn("FileNotFoundError", result.stderr)

    def test_zip_read_no_longer_imports_back_from_lab_tools(self) -> None:
        code = r'''
import json, tempfile, zipfile
from pathlib import Path
import pcmmad_receiver.lab_tools_filesystem as fs
with tempfile.TemporaryDirectory() as td:
    path=Path(td)/"x.zip"
    with zipfile.ZipFile(path,"w") as zf:
        zf.writestr("a.txt","hello")
    with zipfile.ZipFile(path,"r") as zf:
        req=fs.ZipReadRequest(entries=["a.txt"], max_entry_bytes=1024)
        class D: pass
        dep=D()
        print(json.dumps(fs._zip_contents(zf, req, dep)))
'''
        result = self._run(code)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["a.txt"]["content"], "hello")

    def test_wheel_build_and_clean_install_support_full_runtime(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-wheel-") as td:
            root = Path(td)
            dist = root / "dist"
            target = root / "target"
            dist.mkdir()
            target.mkdir()
            build = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "wheel",
                    ".",
                    "--no-deps",
                    "--wheel-dir",
                    str(dist),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=90,
            )
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            wheels = list(dist.glob("*.whl"))
            self.assertEqual(len(wheels), 1)
            with zipfile.ZipFile(wheels[0], "r") as zf:
                names = set(zf.namelist())
            self.assertIn("pcmmad_receiver/lab_tools.py", names)
            self.assertIn("pcmmad_receiver/lab_plugins/transfer.py", names)
            self.assertIn("lab_tools.py", names)
            install = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--no-deps",
                    "--target",
                    str(target),
                    str(wheels[0]),
                ],
                capture_output=True,
                text=True,
                timeout=90,
            )
            self.assertEqual(install.returncode, 0, install.stdout + install.stderr)
            result = self._run(
                "import json, pcmmad_receiver.lab_tools as x; "
                "print(json.dumps({'count': len(x.list_tools()), 'plugin_errors': x._PLUGIN_ERRORS}))",
                pythonpath=target,
                cwd=root,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            observed = json.loads(result.stdout)
            self.assertEqual(observed["count"], 158)
            self.assertEqual(observed["plugin_errors"], [])


if __name__ == "__main__":
    unittest.main()
