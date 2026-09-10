from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

import execution_routes as er

if os.name == "nt":
    import windows_job_object as wjo


@unittest.skipUnless(os.name == "nt", "Windows Job Object resource envelope tests")
class ExecutionResourceEnvelopeTests(unittest.TestCase):
    def test_job_object_resource_envelope_round_trips_from_kernel(self) -> None:
        name = f"Local\\PCMMAD_RESOURCE_{uuid.uuid4().hex}"
        with wjo.create_named_job(name) as job:
            observed = wjo.configure_resource_envelope(
                job,
                kill_on_close=True,
                process_memory_limit_bytes=256 * 1024 * 1024,
                job_memory_limit_bytes=512 * 1024 * 1024,
                active_process_limit=8,
                cpu_rate_percent=50,
            )
            self.assertEqual(
                observed,
                {
                    "kill_on_close": True,
                    "process_memory_limit_bytes": 256 * 1024 * 1024,
                    "job_memory_limit_bytes": 512 * 1024 * 1024,
                    "active_process_limit": 8,
                    "cpu_rate_percent": 50,
                },
            )
            self.assertEqual(wjo.query_resource_envelope(job), observed)
            wjo.set_kill_on_close(job, False)
            toggled = wjo.query_resource_envelope(job)
            self.assertFalse(toggled["kill_on_close"])
            for key in (
                "process_memory_limit_bytes",
                "job_memory_limit_bytes",
                "active_process_limit",
                "cpu_rate_percent",
            ):
                self.assertEqual(toggled[key], observed[key])
            wjo.set_kill_on_close(job, True)
            self.assertEqual(wjo.query_resource_envelope(job), observed)

    def test_active_process_limit_blocks_descendant_creation(self) -> None:
        name = f"Local\\PCMMAD_RESOURCE_PROCESS_{uuid.uuid4().hex}"
        with tempfile.TemporaryDirectory(prefix="pcmmad-resource-limit-") as td:
            root = Path(td)
            release = root / "release"
            outcome = root / "outcome.txt"
            child_code = "import time; time.sleep(2)"
            parent_code = (
                "import subprocess,sys,time; from pathlib import Path; "
                f"release=Path(r'{release}'); outcome=Path(r'{outcome}'); "
                "deadline=time.time()+5; "
                "\nwhile time.time()<deadline and not release.exists(): time.sleep(0.02)\n"
                "try:\n"
                f" p=subprocess.Popen([sys.executable,'-c',{child_code!r}]); outcome.write_text('spawned:'+str(p.pid))\n"
                "except Exception as exc:\n"
                " outcome.write_text('blocked:'+type(exc).__name__)\n"
            )
            with wjo.create_named_job(name) as job:
                wjo.configure_resource_envelope(job, active_process_limit=1)
                proc = subprocess.Popen([sys.executable, "-c", parent_code])
                try:
                    wjo.assign_pid(job, proc.pid)
                    release.write_text("go", encoding="utf-8")
                    deadline = time.time() + 5
                    while time.time() < deadline and not outcome.exists() and proc.poll() is None:
                        time.sleep(0.03)
                    text = outcome.read_text(encoding="utf-8") if outcome.exists() else ""
                    self.assertTrue(
                        text.startswith("blocked:"),
                        f"active process limit failed to block descendant creation: {text!r}",
                    )
                finally:
                    try:
                        wjo.terminate(job, exit_code=9)
                    except OSError:
                        pass
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=3)

    def test_resource_budget_is_validated_and_part_of_idempotency_identity(self) -> None:
        base = {
            "project_id": "alpha",
            "command": [sys.executable],
            "args": ["-c", "print('ok')"],
            "cwd": ".",
            "resource_budget": {
                "process_memory_limit_bytes": 256 * 1024 * 1024,
                "job_memory_limit_bytes": 512 * 1024 * 1024,
                "active_process_limit": 8,
                "cpu_rate_percent": 60,
            },
        }
        with tempfile.TemporaryDirectory(prefix="pcmmad-resource-fingerprint-") as td, patch.object(
            er, "get_project_root", lambda project_id: Path(td) / project_id
        ):
            (Path(td) / "alpha").mkdir()
            first = er._normalize_submit_payload(dict(base))
            changed_data = dict(base)
            changed_data["resource_budget"] = dict(base["resource_budget"], cpu_rate_percent=50)
            changed = er._normalize_submit_payload(changed_data)
        self.assertEqual(first.resource_budget["active_process_limit"], 8)
        self.assertNotEqual(first.submission_fingerprint, changed.submission_fingerprint)

        with self.assertRaises(er.ExecutionRequestError) as bad_cpu:
            er._validated_resource_budget({"cpu_rate_percent": 0})
        self.assertEqual(bad_cpu.exception.error_code, "BAD_RESOURCE_BUDGET")
        with self.assertRaises(er.ExecutionRequestError) as bad_processes:
            er._validated_resource_budget({"active_process_limit": 2})
        self.assertEqual(bad_processes.exception.error_code, "BAD_RESOURCE_BUDGET")
        with self.assertRaises(er.ExecutionRequestError) as unknown:
            er._validated_resource_budget({"gpu_percent": 50})
        self.assertEqual(unknown.exception.error_code, "BAD_RESOURCE_BUDGET")

    def test_scheduler_applies_and_persists_kernel_readback_before_user_execution(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-resource-submit-") as td:
            base = Path(td).resolve()
            projects = base / "projects"
            project = projects / "alpha"
            project.mkdir(parents=True)
            budget = {
                "process_memory_limit_bytes": 512 * 1024 * 1024,
                "job_memory_limit_bytes": 1024 * 1024 * 1024,
                "active_process_limit": 8,
                "cpu_rate_percent": 75,
            }
            with patch.object(er, "PROJECTS_ROOT", projects), patch.object(
                er, "get_project_root", lambda project_id: projects / project_id
            ), patch.object(er, "_ensure_scheduler_started", return_value=None):
                er._RUNNING.clear()
                job = er.submit_execution_job(
                    {
                        "project_id": "alpha",
                        "command": [sys.executable],
                        "args": ["-c", "import time; print('RESOURCE_OK', flush=True); time.sleep(0.5)"],
                        "cwd": ".",
                        "timeout_seconds": 5,
                        "resource_budget": budget,
                    }
                )
                self.assertEqual(job.resource_gate, "pass")
                self.assertEqual(job.resource_budget, budget)
                self.assertEqual(job.applied_resource_envelope["kill_on_close"], True)
                for key, value in budget.items():
                    self.assertEqual(job.applied_resource_envelope[key], value)
                reopened = wjo.open_named_job(str(job.job_object_name), terminate=False)
                try:
                    kernel = wjo.query_resource_envelope(reopened)
                finally:
                    reopened.close()
                self.assertEqual(kernel, job.applied_resource_envelope)

                deadline = time.time() + 8
                current = job
                while time.time() < deadline and current.status not in er.JOB_TERMINAL_STATUSES:
                    time.sleep(0.05)
                    current = er._finalize("alpha", job.job_id, er._read_job("alpha", job.job_id))
                self.assertEqual(current.status, er.JOB_STATUS_COMPLETED)
                persisted = er._read_job("alpha", job.job_id)
                self.assertEqual(persisted.resource_budget, budget)
                self.assertEqual(persisted.applied_resource_envelope, job.applied_resource_envelope)
                self.assertEqual(persisted.resource_gate, "pass")

    def test_capabilities_advertise_resource_envelope_without_hiding_backend(self) -> None:
        capabilities = er.execution_capabilities()
        self.assertTrue(capabilities["resource_envelope_supported"])
        self.assertEqual(capabilities["resource_envelope_backend"], "windows_job_object")
        self.assertEqual(set(capabilities["resource_budget_fields"]), set(er.RESOURCE_BUDGET_FIELDS))


    def test_compact_action_schema_projects_resource_budget_without_changing_operation_count(self) -> None:
        schema_path = RUNTIME_ROOT / "pcmmad_lab_action_schema_v10_3_pcmmad_native_protocol_compact_30_router.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        operations = [
            spec.get("operationId")
            for path in schema["paths"].values()
            for method, spec in path.items()
            if method.lower() in {"get", "post", "put", "patch", "delete"}
        ]
        self.assertEqual(len(operations), 30)
        submit = schema["components"]["schemas"]["ExecutionSubmitRequest"]["properties"]
        self.assertEqual(
            submit["resource_budget"],
            {"$ref": "#/components/schemas/ExecutionResourceBudget"},
        )
        budget = schema["components"]["schemas"]["ExecutionResourceBudget"]
        self.assertFalse(budget["additionalProperties"])
        self.assertEqual(set(budget["properties"]), set(er.RESOURCE_BUDGET_FIELDS))
        job = schema["components"]["schemas"]["ExecutionJob"]["properties"]
        self.assertEqual(job["resource_budget"]["$ref"], "#/components/schemas/ExecutionResourceBudget")
        self.assertEqual(
            job["applied_resource_envelope"]["$ref"],
            "#/components/schemas/ExecutionResourceEnvelope",
        )


if __name__ == "__main__":
    unittest.main()
