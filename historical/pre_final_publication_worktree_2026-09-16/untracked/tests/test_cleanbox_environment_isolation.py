from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from pcmmad_receiver import context_engine, shared_core


class CleanBoxEnvironmentIsolationTests(unittest.TestCase):
    def test_operator_mount_environment_is_replaced_by_test_namespace(self) -> None:
        mounts = json.loads(os.environ["PCMMAD_MOUNTS_JSON"])
        self.assertEqual(set(mounts), {"pytest_runtime", "pytest_os_temp", "pytest_repo"})
        self.assertTrue(Path(mounts["pytest_runtime"]).name.startswith("pcmmad-pytest-runtime-"))

    def test_os_temp_directory_is_explicitly_allowed_for_context_tests(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-cleanbox-proof-") as td:
            root = Path(td).resolve()
            target = root / "proof.txt"
            target.write_text("proof", encoding="utf-8")
            resolved = context_engine.resolve_user_path("proof.txt", base_root=str(root))
        self.assertEqual(resolved.name, "proof.txt")

    def test_product_roots_are_test_local_not_operator_desktop_state(self) -> None:
        runtime_root = Path(os.environ["PCMMAD_ROOT"]).resolve()
        self.assertTrue(runtime_root.parent.name.startswith("pcmmad-pytest-runtime-"))
        self.assertEqual(shared_core.ROOT, runtime_root)


if __name__ == "__main__":
    unittest.main()
