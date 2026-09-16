"""Regression guards for one canonical async execution lifecycle."""

from __future__ import annotations

import sys
import unittest
from contextlib import nullcontext
from unittest.mock import patch
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

import lab_tools_execution


class FakeJob:
    def __init__(self, **payload: Any) -> None:
        self.payload = payload

    def to_dict(self) -> dict[str, Any]:
        return dict(self.payload)


class AsyncUnificationTests(unittest.TestCase):
    def _registry(self) -> tuple[dict[str, Any], Any, Any]:
        handlers: dict[str, Any] = {}
        submitted: list[dict[str, Any]] = []
        terminated: list[tuple[str, str]] = []

        def register_tool(name: str, *args: Any, **kwargs: Any):
            def decorator(fn: Any) -> Any:
                handlers[name] = fn
                return fn
            return decorator

        def submit_job(payload: dict[str, Any]) -> FakeJob:
            submitted.append(dict(payload))
            return FakeJob(project_id=payload["project_id"], job_id="job-canonical", status="QUEUED")

        def terminate_job(project_id: str, job_id: str) -> FakeJob:
            terminated.append((project_id, job_id))
            return FakeJob(project_id=project_id, job_id=job_id, status="TERMINATED")

        class LabError(Exception):
            def __init__(self, code: str, message: str, status: int) -> None:
                super().__init__(message)
                self.code = code
                self.status = status

        lab_tools_execution.register_execution_tools(
            register_tool,
            error_cls=LabError,
            request_optional_positive_int=lambda value, default, **kwargs: default if value is None else int(value),
            resolve_cwd=lambda project_id, cwd: Path.cwd(),
            exec_env=lambda payload: {},
            finalize_job=lambda *args: FakeJob(project_id=args[0], job_id=args[1], status="COMPLETED"),
            read_job=lambda project_id, job_id: FakeJob(project_id=project_id, job_id=job_id, status="COMPLETED"),
            tail_text=lambda path, max_bytes: ("", False),
            execution_modes={"one_shot", "bench", "replay", "ablation"},
            max_output_bytes=1024 * 1024,
            default_timeout_seconds=60,
            default_stdout_max_bytes=65536,
            default_stderr_max_bytes=65536,
            max_timeout_seconds=3600,
            submit_job=submit_job,
            terminate_job=terminate_job,
            utc_now=lambda: "2026-09-05T00:00:00+00:00",
        )
        return handlers, submitted, terminated

    def test_async_submit_delegates_entire_payload_to_canonical_scheduler(self) -> None:
        handlers, submitted, _ = self._registry()
        payload = {
            "project_id": "alpha",
            "command": ["python"],
            "args": ["-c", "print('ok')"],
            "execution_mode": "one_shot",
            "idempotency_key": "same-request",
            "timeout_seconds": 30,
        }
        authority = {"project_id": "alpha", "mode": "lease", "generation": 1, "owner_id": "test-owner", "lease_id": "lease-test"}
        with patch.object(lab_tools_execution, "current_project_mutation_authority", return_value=authority), patch.object(
            lab_tools_execution, "submission_mutation_binding", return_value=nullcontext()
        ):
            result = handlers["execution.submit"](payload)
        self.assertEqual(result["job_id"], "job-canonical")
        self.assertEqual(result["status"], "QUEUED")
        self.assertEqual(submitted, [payload])


    def test_async_submit_without_explicit_authority_fails_before_scheduler(self) -> None:
        handlers, submitted, _ = self._registry()
        payload = {"project_id": "alpha", "command": ["python", "-V"], "execution_mode": "one_shot"}
        with patch.object(lab_tools_execution, "current_project_mutation_authority", return_value=None):
            with self.assertRaises(Exception) as ctx:
                handlers["execution.submit"](payload)
        self.assertEqual(getattr(ctx.exception, "code", None), "PROJECT_MUTATION_AUTHORITY_REQUIRED")
        self.assertEqual(getattr(ctx.exception, "status", None), 423)
        self.assertEqual(submitted, [])

    def test_async_terminate_delegates_to_canonical_lifecycle(self) -> None:
        handlers, _, terminated = self._registry()
        result = handlers["execution.terminate"]({"project_id": "alpha", "job_id": "job-1"})
        self.assertEqual(result["status"], "TERMINATED")
        self.assertEqual(terminated, [("alpha", "job-1")])

    def test_router_module_does_not_own_background_process_lifecycle(self) -> None:
        source = Path(lab_tools_execution.__file__).read_text(encoding="utf-8")
        forbidden = (
            "start_background_process",
            "running_jobs",
            "job_dir",
            "write_job",
            "proc.kill()",
        )
        for marker in forbidden:
            self.assertNotIn(marker, source, marker)


if __name__ == "__main__":
    unittest.main()
