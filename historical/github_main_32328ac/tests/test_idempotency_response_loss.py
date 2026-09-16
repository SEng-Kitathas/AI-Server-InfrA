"""Hostile response-loss tests for Runtime idempotency semantics."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

import execution_routes as er
import legacy_routes as lr
import lab_tools
from control_plane_models import ExecutionIdempotencyLedger, ToolSpec


class ExecutionIdempotencyRecoveryTests(unittest.TestCase):
    def _payload(self, *, fingerprint: str = "fp-a") -> SimpleNamespace:
        return SimpleNamespace(
            project_id="alpha",
            idempotency_key="idem-1",
            submission_fingerprint=fingerprint,
        )

    def _job(self, *, fingerprint: str = "fp-a", status: str = "QUEUED") -> SimpleNamespace:
        return SimpleNamespace(
            project_id="alpha",
            job_id="job-existing",
            idempotency_key="idem-1",
            submission_fingerprint=fingerprint,
            submitted_at="2026-09-07T00:00:00+00:00",
            status=status,
            replayed=False,
        )

    def test_missing_auxiliary_index_is_rebuilt_from_authoritative_job_record(self) -> None:
        payload = self._payload()
        job = self._job()
        saved: list[ExecutionIdempotencyLedger] = []
        with patch.object(er, "_iter_all_job_files", return_value=iter([Path("job.json")])), patch.object(
            er, "_load_job_file", return_value=(job, None)
        ), patch.object(er, "_load_execution_idempotency", return_value=ExecutionIdempotencyLedger()), patch.object(
            er, "_save_execution_idempotency", side_effect=lambda _pid, ledger: saved.append(ledger)
        ):
            recovered = er._recover_idempotency_from_job_records(payload)
        self.assertIs(recovered, job)
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0].keys["idem-1"].job_id, "job-existing")
        self.assertEqual(saved[0].keys["idem-1"].submission_fingerprint, "fp-a")

    def test_recovered_key_conflicts_with_different_payload(self) -> None:
        payload = self._payload(fingerprint="fp-new")
        job = self._job(fingerprint="fp-old")
        with patch.object(er, "_iter_all_job_files", return_value=iter([Path("job.json")])), patch.object(
            er, "_load_job_file", return_value=(job, None)
        ):
            with self.assertRaises(er.ExecutionRequestError) as caught:
                er._recover_idempotency_from_job_records(payload)
        self.assertEqual(caught.exception.error_code, "IDEMPOTENCY_KEY_CONFLICT")

    def test_duplicate_authoritative_claims_fail_closed(self) -> None:
        payload = self._payload()
        jobs = [self._job(), self._job()]
        jobs[1].job_id = "job-other"
        with patch.object(
            er, "_iter_all_job_files", return_value=iter([Path("a.json"), Path("b.json")])
        ), patch.object(er, "_load_job_file", side_effect=[(jobs[0], None), (jobs[1], None)]):
            with self.assertRaises(er.ExecutionRequestError) as caught:
                er._recover_idempotency_from_job_records(payload)
        self.assertEqual(caught.exception.error_code, "IDEMPOTENCY_RECOVERY_AMBIGUOUS")

    def test_new_key_reservation_is_durable_before_spawn_or_queue_consequence(self) -> None:
        payload = self._payload()
        spec = SimpleNamespace(job_id="job-new")
        job = self._job(status=er.JOB_STATUS_SUBMITTED)
        job.job_id = "job-new"
        order: list[str] = []

        def write_job(*_args):
            order.append("job_record")

        def persist(*_args):
            order.append("idempotency_index")

        def spawn(candidate):
            order.append("spawn_or_queue")
            candidate.status = er.JOB_STATUS_QUEUED
            return candidate

        with patch.object(er, "_resolve_existing_idempotent_job", return_value=None), patch.object(
            er, "_new_execution_job_spec", return_value=spec
        ), patch.object(er, "_build_execution_job", return_value=job), patch.object(
            er, "_write_job", side_effect=write_job
        ), patch.object(er, "_persist_idempotency_key", side_effect=persist), patch.object(
            er, "_spawn_or_queue_job", side_effect=spawn
        ), patch.object(er, "_journal_job_submission", return_value=None), patch.object(
            er, "_ensure_scheduler_started", return_value=None
        ), patch.object(er, "_drain_queue_locked", return_value=[]):
            result = er._submit_job_locked(payload, None)

        self.assertIs(result, job)
        self.assertLess(order.index("job_record"), order.index("idempotency_index"))
        self.assertLess(order.index("idempotency_index"), order.index("spawn_or_queue"))


    def test_scheduler_recovers_orphaned_submitted_reservation_without_client_retry(self) -> None:
        job = self._job(status=er.JOB_STATUS_SUBMITTED)
        job.worker_token = None
        writes = []
        journals = []
        stats = []

        def spawn(candidate):
            candidate.status = er.JOB_STATUS_QUEUED
            candidate.stage = "queued"
            return candidate

        with patch.object(er, "_spawn_or_queue_job", side_effect=spawn), patch.object(
            er, "_journal_job_submission", side_effect=lambda candidate: journals.append(candidate.status)
        ), patch.object(er, "_write_job", side_effect=lambda *_args: writes.append(_args[-1].status)), patch.object(
            er, "_scheduler_stat_inc", side_effect=lambda name, amount=1: stats.append((name, amount))
        ):
            er._reconcile_job_locked(job)

        self.assertEqual(job.status, er.JOB_STATUS_QUEUED)
        self.assertEqual(journals, [er.JOB_STATUS_QUEUED])
        self.assertEqual(writes, [er.JOB_STATUS_QUEUED])
        self.assertIn(("jobs_reconciled", 1), stats)

    def test_scheduler_leaves_submitted_reservation_retryable_when_queue_is_full(self) -> None:
        job = self._job(status=er.JOB_STATUS_SUBMITTED)
        job.worker_token = None
        capacity = er.CapacitySnapshot(
            running_global=12, running_project=12, global_limit=12, project_limit=None,
            queued_global=1, queued_project=1, global_queue_limit=1, project_queue_limit=1,
            oldest_queued_age_seconds=1.0, oldest_project_queued_age_seconds=1.0,
        )
        with patch.object(
            er, "_spawn_or_queue_job", side_effect=er.ExecutionOverCapacity("full", capacity=capacity.to_dict())
        ), patch.object(er, "_write_job") as write_job:
            er._reconcile_job_locked(job)
        self.assertEqual(job.status, er.JOB_STATUS_SUBMITTED)
        write_job.assert_not_called()

    def test_worker_starting_record_is_durable_before_process_launch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            order: list[str] = []
            job = SimpleNamespace(
                project_id="alpha",
                job_id="job-1",
                job_object_name=None,
                command=["python", "-c", "pass"],
                cwd=str(root),
                env_allowlist={},
                stdout_path=str(root / "stdout.log"),
                stderr_path=str(root / "stderr.log"),
                timeout_seconds=30,
                worker_token=None,
                queue_position=None,
                resource_budget={},
                applied_resource_envelope={},
                resource_gate="not_evaluated",
            )
            paths = {
                "control_stdout": root / "control.stdout.log",
                "control_stderr": root / "control.stderr.log",
            }

            class Proc:
                pid = 4321

                def poll(self):
                    return None

            def write_request(candidate):
                candidate.worker_token = "worker-token"
                candidate.worker_ownership_release_path = str(root / "ownership_release.json")
                candidate.worker_heartbeat_path = str(root / "heartbeat.json")
                candidate.worker_completion_path = str(root / "completion.json")
                candidate.worker_cancel_path = str(root / "cancel.json")
                order.append("request")
                return root / "request.json"

            def set_status(candidate, status, stage):
                candidate.status = status
                candidate.stage = stage

            def write_job(*_args):
                order.append("job_record")

            def launch(*_args, **_kwargs):
                order.append("process_launch")
                return Proc()

            fake_wjo = SimpleNamespace(
                create_named_job=lambda _name: object(),
                configure_resource_envelope=lambda _handle, **_kwargs: {
                    "kill_on_close": True,
                    "process_memory_limit_bytes": None,
                    "job_memory_limit_bytes": None,
                    "active_process_limit": None,
                    "cpu_rate_percent": None,
                },
                assign_pid=lambda _handle, _pid: None,
                query_process_ids=lambda _handle: [4321],
                process_creation_time_100ns=lambda _pid: 123456,
                close_handle=lambda _handle: None,
            )
            with patch.object(er, "_wjo", fake_wjo), patch.object(
                er, "_write_worker_request", side_effect=write_request
            ), patch.object(er, "_worker_paths", return_value=paths), patch.object(
                er, "_set_job_status", side_effect=set_status
            ), patch.object(er, "_write_job", side_effect=write_job), patch.object(
                er, "start_background_process", side_effect=launch
            ), patch.object(
                er, "_wait_for_ownership_ready",
                return_value={"worker_pid": 4321},
            ), patch.object(er, "_RUNNING", {}):
                result = er._spawn_job(job)

            self.assertIs(result, job)
            self.assertLess(order.index("job_record"), order.index("process_launch"))


class LegacyCommitIdempotencyRecoveryTests(unittest.TestCase):
    def _patch_project(self, root: Path):
        def get_root(_project_id: str) -> Path:
            return root

        def init_layout(_project_id: str) -> Path:
            root.mkdir(parents=True, exist_ok=True)
            return root

        def resolve(_project_id: str, _artifact_class: str, logical_name: str) -> Path:
            return root / logical_name

        return patch.multiple(
            lr,
            get_project_root=get_root,
            init_project_layout=init_layout,
            resolve_target=resolve,
            manifest_path_for=lambda _pid: root / "system" / "manifest.json",
            idempotency_path_for=lambda _pid: root / "system" / "ledger" / "idempotency.json",
            commits_ledger_path_for=lambda _pid: root / "system" / "ledger" / "commits.jsonl",
        )

    def _request(
        self,
        *,
        operation: str,
        content: str,
        expected_previous_sha: str | None,
        key: str = "idem-legacy",
        artifact_class: str = "state.current",
    ) -> lr.LegacyCommitRequest:
        plan = lr.LegacyPlanRequest(
            project_id="alpha",
            artifact_class=artifact_class,
            logical_name="artifact.txt",
            operation=operation,
            content=content,
            provided_sha=lr.sha256_text(content),
            expected_previous_sha=expected_previous_sha,
        )
        return lr.LegacyCommitRequest(
            plan=plan,
            session_id="session-a",
            commit_id="commit-a",
            idempotency_key=key,
        )

    def test_append_response_loss_after_effect_recovers_without_duplicate_append(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "artifact.txt"
            target.write_text("base\n", encoding="utf-8")
            before = lr.sha256_file(target)
            request = self._request(
                operation="append",
                content="once\n",
                expected_previous_sha=before,
                artifact_class="continuity.design_thread_stream",
            )
            with self._patch_project(root):
                validation = lr._validate_legacy_plan(request.plan)
                prepared = lr._prepared_idempotency_entry(request, validation)
                lr.save_idempotency("alpha", {request.idempotency_key: prepared})
                # Inject the critical crash window: target consequence happened, but
                # manifest/commit/idempotency finalization did not.
                lr._write_legacy_content(target, "append", request.plan.content)
                record, replayed = lr._replay_or_resume_legacy_commit(request, prepared)
                self.assertTrue(replayed)
                self.assertEqual(target.read_text(encoding="utf-8"), "base\nonce\n")
                self.assertEqual(record.sha256, lr.sha256_file(target))
                ledger_lines = (root / "system" / "ledger" / "commits.jsonl").read_text(
                    encoding="utf-8"
                ).splitlines()
                self.assertEqual(len(ledger_lines), 1)
                entry = lr.get_idempotency("alpha")[request.idempotency_key]
                self.assertEqual(entry["state"], "committed")

    def test_prepared_before_state_resumes_effect_exactly_once(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "artifact.txt"
            target.write_text("old", encoding="utf-8")
            before = lr.sha256_file(target)
            request = self._request(operation="update", content="new", expected_previous_sha=before)
            with self._patch_project(root):
                validation = lr._validate_legacy_plan(request.plan)
                prepared = lr._prepared_idempotency_entry(request, validation)
                lr.save_idempotency("alpha", {request.idempotency_key: prepared})
                record, replayed = lr._replay_or_resume_legacy_commit(request, prepared)
                self.assertTrue(replayed)
                self.assertEqual(target.read_text(encoding="utf-8"), "new")
                self.assertEqual(record.sha256, lr.sha256_file(target))

    def test_same_idempotency_key_with_different_request_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "artifact.txt"
            target.write_text("old", encoding="utf-8")
            before = lr.sha256_file(target)
            first = self._request(operation="update", content="new-a", expected_previous_sha=before)
            second = self._request(operation="update", content="new-b", expected_previous_sha=before)
            with self._patch_project(root):
                prepared = lr._prepared_idempotency_entry(first, lr._validate_legacy_plan(first.plan))
                with self.assertRaises(lr.LegacyIdempotencyError) as caught:
                    lr._replay_or_resume_legacy_commit(second, prepared)
            self.assertEqual(caught.exception.error_code, "IDEMPOTENCY_KEY_CONFLICT")

    def test_intervening_target_state_fails_closed_instead_of_reapplying(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "artifact.txt"
            target.write_text("old", encoding="utf-8")
            before = lr.sha256_file(target)
            request = self._request(operation="update", content="new", expected_previous_sha=before)
            with self._patch_project(root):
                prepared = lr._prepared_idempotency_entry(request, lr._validate_legacy_plan(request.plan))
                target.write_text("intervening", encoding="utf-8")
                with self.assertRaises(lr.LegacyIdempotencyError) as caught:
                    lr._replay_or_resume_legacy_commit(request, prepared)
            self.assertEqual(caught.exception.error_code, "IDEMPOTENCY_RECOVERY_CONFLICT")


class CapabilityIdempotencyMetadataTests(unittest.TestCase):
    def test_read_defaults_safe_repeat_and_effect_defaults_unsafe(self) -> None:
        read = ToolSpec(name="r", description="r", side_effect_class="read")
        effect = ToolSpec(name="m", description="m", mutating=True)
        self.assertEqual(read.effective_idempotency_semantics, "safe_repeat")
        self.assertEqual(effect.effective_idempotency_semantics, "unsafe_retry")

    def test_proven_state_and_position_replay_traits_are_exposed(self) -> None:
        state_bound = ToolSpec(
            name="s",
            description="s",
            mutating=True,
            effect_traits=["idempotent_replay_while_unacked"],
        )
        position_bound = ToolSpec(
            name="p",
            description="p",
            mutating=True,
            effect_traits=["exact_offset_required", "requires_chunk_hash"],
        )
        self.assertEqual(state_bound.effective_idempotency_semantics, "state_bound_replay")
        self.assertEqual(position_bound.effective_idempotency_semantics, "position_bound_replay")
        self.assertEqual(state_bound.to_card()["idempotency_semantics"], "state_bound_replay")


    def test_runtime_registry_is_conservative_about_retry_safety(self) -> None:
        cards = {card["name"]: card for card in lab_tools.list_tools()}
        self.assertEqual(
            cards["execution.submit"]["idempotency_semantics"],
            "keyed_replay_when_keyed",
        )
        self.assertEqual(
            cards["sop.ingest.next_chunk"]["idempotency_semantics"],
            "state_bound_replay",
        )
        self.assertEqual(
            cards["transfer.chunk.write"]["idempotency_semantics"],
            "position_bound_replay",
        )
        for name in (
            "lab.session.note",
            "lab.reflexion.append",
            "protocol.claim.record",
            "git.commit",
            "browser.click",
            "execution.run",
        ):
            self.assertEqual(cards[name]["idempotency_semantics"], "unsafe_retry", name)



if __name__ == "__main__":
    unittest.main()
