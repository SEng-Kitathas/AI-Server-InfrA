"""Global test-runtime isolation for PCMMAD receiver regression suites.

This file is imported by pytest before test modules are collected. Runtime modules bind
PROJECTS_ROOT/SYSTEM_ROOT/SANDBOX_ROOT/TEMP_ROOT at import time, so the environment must
be isolated here rather than inside individual tests. No test is allowed to inherit the
operator's real PCMMAD project stores implicitly.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

_TEST_RUNTIME_ROOT = Path(tempfile.mkdtemp(prefix="pcmmad-pytest-runtime-")).resolve()
_TEST_OS_TEMP = Path(tempfile.gettempdir()).resolve()
_TEST_REPO_ROOT = Path.cwd().resolve()

# Explicitly replace, rather than inherit, operator/runtime path configuration.
# Many context tests create their own TemporaryDirectory beneath the OS temp root;
# authorize that test-only namespace without widening production Runtime policy.
os.environ["PCMMAD_ROOT"] = str(_TEST_RUNTIME_ROOT / "root")
os.environ["PCMMAD_PROJECTS_ROOT"] = str(_TEST_RUNTIME_ROOT / "projects")
os.environ["PCMMAD_SYSTEM_ROOT"] = str(_TEST_RUNTIME_ROOT / "system")
os.environ["PCMMAD_SANDBOX_ROOT"] = str(_TEST_RUNTIME_ROOT / "sandbox")
os.environ["PCMMAD_TEMP_ROOT"] = str(_TEST_RUNTIME_ROOT / "temp")
os.environ["PCMMAD_MOUNTS_JSON"] = json.dumps(
    {
        "pytest_runtime": str(_TEST_RUNTIME_ROOT),
        "pytest_os_temp": str(_TEST_OS_TEMP),
        "pytest_repo": str(_TEST_REPO_ROOT),
    },
    sort_keys=True,
)

for key in ("PCMMAD_ROOT", "PCMMAD_PROJECTS_ROOT", "PCMMAD_SYSTEM_ROOT", "PCMMAD_SANDBOX_ROOT", "PCMMAD_TEMP_ROOT"):
    Path(os.environ[key]).mkdir(parents=True, exist_ok=True)


def pytest_sessionfinish(session, exitstatus) -> None:  # noqa: ARG001
    shutil.rmtree(_TEST_RUNTIME_ROOT, ignore_errors=True)
