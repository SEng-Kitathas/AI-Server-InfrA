from __future__ import annotations

import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

import lab_tools_execution as lte


def clamp_optional(value, default, *, minimum=1, maximum=None):
    if value is None:
        result = default
    else:
        result = int(value)
    if result is None:
        return None
    result = max(int(minimum), int(result))
    if maximum is not None:
        result = min(int(maximum), result)
    return result


class FakeError(Exception):
    pass


class ExecutionBoundedProgressTests(unittest.TestCase):
    def test_wait_defaults_are_bounded(self) -> None:
        req = lte._wait_request(
            FakeError,
            {"project_id": "p", "job_id": "j"},
            request_optional_positive_int=clamp_optional,
            max_output_bytes=1024 * 1024,
        )
        self.assertEqual(req.timeout_seconds, lte.AI_WAIT_DEFAULT_SECONDS)
        self.assertEqual(req.max_bytes, lte.AI_WAIT_DEFAULT_OUTPUT_BYTES)
        self.assertLessEqual(req.timeout_seconds, lte.AI_WAIT_MAX_SECONDS)
        self.assertLessEqual(req.max_bytes, lte.AI_WAIT_MAX_OUTPUT_BYTES)

    def test_wait_cannot_be_raised_beyond_server_caps(self) -> None:
        req = lte._wait_request(
            FakeError,
            {
                "project_id": "p",
                "job_id": "j",
                "timeout_seconds": 999999,
                "max_bytes": 999999999,
            },
            request_optional_positive_int=clamp_optional,
            max_output_bytes=1024 * 1024,
        )
        self.assertEqual(req.timeout_seconds, lte.AI_WAIT_MAX_SECONDS)
        self.assertEqual(req.max_bytes, lte.AI_WAIT_MAX_OUTPUT_BYTES)

    def test_active_progress_receipt_is_compact_and_decision_grade(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            stdout = base / "stdout.log"
            stderr = base / "stderr.log"
            heartbeat = base / "heartbeat.json"
            stdout.write_text("progress\n", encoding="utf-8")
            stderr.write_text("", encoding="utf-8")
            heartbeat.write_text("{}", encoding="utf-8")
            now = time.time()
            job = {
                "status": "RUNNING",
                "stage": "runtime",
                "started_at": None,
                "submitted_at": None,
                "queue_position": None,
                "supervision_state": "worker_heartbeat",
                "worker_heartbeat_path": str(heartbeat),
                "stdout_path": str(stdout),
                "stderr_path": str(stderr),
                "return_code": None,
                "result_artifact_targets": [],
                "artifact_registration_status": "not_attempted",
            }
            dep = SimpleNamespace()
            receipt = lte._progress_receipt(
                lte.ExecutionIdentity("p", "j"), job, dep, wait_timed_out=True
            )
            self.assertEqual(receipt["status"], "RUNNING")
            self.assertEqual(receipt["progress_class"], "PROGRESSING")
            self.assertTrue(receipt["wait_timed_out"])
            self.assertTrue(receipt["output_available"])
            self.assertEqual(receipt["bulk_output_tool"], "execution.output")
            self.assertNotIn("stdout", receipt)
            self.assertNotIn("stderr", receipt)
            self.assertLessEqual(receipt["suggested_recheck_seconds"], 30)

    def test_terminal_wait_returns_bounded_excerpts_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            stdout = base / "stdout.log"
            stderr = base / "stderr.log"
            stdout.write_text("x" * 50000, encoding="utf-8")
            stderr.write_text("y" * 50000, encoding="utf-8")

            def tail(path: Path, max_bytes: int | None):
                data = path.read_text(encoding="utf-8")
                budget = int(max_bytes or len(data))
                encoded = data.encode("utf-8")
                clipped = encoded[-budget:].decode("utf-8", errors="replace")
                return clipped, len(encoded) > budget

            dep = SimpleNamespace(tail_text=tail)
            req = lte.WaitRequest(
                identity=lte.ExecutionIdentity("p", "j"),
                timeout_seconds=8,
                max_bytes=4096,
            )
            job = {
                "status": "COMPLETED",
                "stage": "complete",
                "stdout_path": str(stdout),
                "stderr_path": str(stderr),
                "return_code": 0,
                "duration_ms": 1234,
                "result_artifact_targets": [],
                "artifact_registration_status": "not_attempted",
            }
            receipt = lte._completed_wait_payload(req, job, dep)
            self.assertEqual(receipt["progress_class"], "TERMINAL")
            self.assertEqual(receipt["excerpt_max_bytes"], 4096)
            self.assertLessEqual(len(receipt["stdout_excerpt"].encode("utf-8")), 4096)
            self.assertLessEqual(len(receipt["stderr_excerpt"].encode("utf-8")), 4096)
            self.assertTrue(receipt["stdout_truncated"])
            self.assertTrue(receipt["stderr_truncated"])

    def test_wait_loop_returns_after_bounded_timeout_not_indefinitely(self) -> None:
        request = lte.WaitRequest(
            identity=lte.ExecutionIdentity("p", "j"),
            timeout_seconds=1,
            max_bytes=4096,
        )
        job = {
            "status": "RUNNING",
            "stage": "runtime",
            "stdout_path": "",
            "stderr_path": "",
            "worker_heartbeat_path": "",
            "supervision_state": "worker_heartbeat",
            "result_artifact_targets": [],
            "artifact_registration_status": "not_attempted",
        }
        dep = SimpleNamespace()
        with patch.object(lte, "_observed_job", return_value=job), patch.object(
            lte.time, "sleep", return_value=None
        ), patch.object(lte.time, "time", side_effect=[0.0, 0.1, 1.1, 1.1, 1.1, 1.1]):
            result = lte._wait_until_done(request, dep)
        self.assertTrue(result["wait_timed_out"])
        self.assertEqual(result["status"], "RUNNING")


if __name__ == "__main__":
    unittest.main()
