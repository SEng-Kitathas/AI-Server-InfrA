from __future__ import annotations

import argparse
import json
import random
import sys
import tempfile
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASELINE_ROOT = PROJECT_ROOT / "baseline"
if str(BASELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(BASELINE_ROOT))

from pcmmad_receiver import execution_routes as er
from pcmmad_receiver.control_plane_models import ExecutionJobRecord, SchedulerTelemetry

Json = dict[str, Any]


@dataclass
class VirtualClock:
    instant: datetime = datetime(2026, 9, 6, tzinfo=timezone.utc)

    def now(self) -> str:
        value = self.instant
        self.instant += timedelta(milliseconds=10)
        return value.isoformat()

    def jump(self, milliseconds: int) -> None:
        self.instant += timedelta(milliseconds=int(milliseconds))


class SimulationInvariantError(AssertionError):
    pass


class DeterministicExecutionLifecycleSim:
    """Seeded hostile schedule runner over the real execution scheduler/store.

    The simulator keeps Runtime lifecycle/storage/admission/reconciliation code real.
    It virtualizes only nondeterministic boundaries: process spawn/liveness and clock.
    Every action is traceable and a failing invariant includes an exact replay seed.
    """

    PROJECTS = ("p1", "p2")

    def __init__(
        self,
        seed: int,
        *,
        global_limit: int = 2,
        project_limit: int = 1,
        scheduler_variant: str = "current",
        legacy_identity_variant: str = "current",
    ):
        self.seed = int(seed)
        self.rng = random.Random(self.seed)
        self.global_limit = int(global_limit)
        self.project_limit = int(project_limit)
        if scheduler_variant not in {"current", "pre_a034"}:
            raise ValueError("scheduler_variant must be current or pre_a034")
        if legacy_identity_variant not in {"current", "pid_only"}:
            raise ValueError("legacy_identity_variant must be current or pid_only")
        self.scheduler_variant = scheduler_variant
        self.legacy_identity_variant = legacy_identity_variant
        self.clock = VirtualClock()
        self.trace: list[Json] = []
        self.job_counter = 0
        self.next_pid = 10000
        self.pid_generation: dict[int, int] = {}
        self.job_process_identity: dict[str, tuple[int, int]] = {}
        self.drain_calls = 0
        self.spawn_failures = 0
        self.reconcile_faults = 0
        self.pid_recycles = 0
        self._temp: tempfile.TemporaryDirectory[str] | None = None
        self._stack: ExitStack | None = None
        self.projects_root: Path | None = None
        self._real_iter_job_files: Callable[..., Any] | None = None
        self._real_drain_queue: Callable[..., Any] | None = None
        self._base_spawn: Callable[[ExecutionJobRecord], ExecutionJobRecord] = self._fake_spawn

    def __enter__(self) -> "DeterministicExecutionLifecycleSim":
        # Deterministic simulation cannot share state with the process-global live
        # scheduler. Hosted-suite ordering can otherwise interleave real ticks with
        # the virtual clock/process model and destroy replay identity.
        er._shutdown_scheduler()
        self._temp = tempfile.TemporaryDirectory(prefix=f"pcmmad-a038-{self.seed}-")
        root = Path(self._temp.name)
        self.projects_root = root / "projects"
        self.projects_root.mkdir(parents=True, exist_ok=True)
        self._stack = ExitStack()
        self._real_iter_job_files = er._iter_job_files
        self._real_drain_queue = er._drain_queue
        self._stack.enter_context(patch.object(er, "PROJECTS_ROOT", self.projects_root))
        self._stack.enter_context(
            patch.object(
                er,
                "get_project_root",
                side_effect=lambda project_id: self.projects_root / project_id,
            )
        )
        self._stack.enter_context(patch.object(er, "_EXECUTION_STORE_LAYOUT_READY_ROOTS", set()))
        self._stack.enter_context(patch.object(er, "_RUNNING", {}))
        self._stack.enter_context(patch.object(er, "_SCHEDULER_TELEMETRY", SchedulerTelemetry()))
        self._stack.enter_context(patch.object(er, "EXECUTION_GLOBAL_CONCURRENCY", self.global_limit))
        self._stack.enter_context(patch.object(er, "EXECUTION_PROJECT_CONCURRENCY", self.project_limit))
        self._stack.enter_context(patch.object(er, "EXECUTION_DRAIN_BATCH", None))
        self._stack.enter_context(patch.object(er, "utc_now", side_effect=self.clock.now))
        self._stack.enter_context(patch.object(er, "_pid_alive", side_effect=self._pid_alive))
        self._stack.enter_context(
            patch.object(
                er, "_process_creation_time_100ns", side_effect=self._process_creation_time_100ns
            )
        )
        if self.legacy_identity_variant == "pid_only":
            self._stack.enter_context(
                patch.object(
                    er,
                    "_legacy_process_identity_state",
                    side_effect=self._pid_only_identity_state,
                )
            )
        self._stack.enter_context(patch.object(er, "_spawn_job", side_effect=self._fake_spawn))
        self._stack.enter_context(patch.object(er, "_iter_job_files", side_effect=self._sorted_hot_iter))
        self._stack.enter_context(patch.object(er, "_drain_queue", side_effect=self._observed_drain))
        if self.scheduler_variant == "pre_a034":
            # Historical vulnerable reference: before A-034, one reconcile exception
            # escaped the per-record loop and prevented the later queue drain.
            self._stack.enter_context(
                patch.object(er, "_scheduler_tick", side_effect=self._pre_a034_scheduler_tick)
            )
        er._ensure_execution_store_layout()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        er._shutdown_scheduler()
        if self._stack is not None:
            self._stack.close()
        if self._temp is not None:
            self._temp.cleanup()

    def _pre_a034_scheduler_tick(self) -> None:
        """Historical scar specimen: reconcile errors abort before queue drain."""
        paths = list(er._iter_job_files(None))
        for path in paths:
            job, _error = er._load_job_file(path)
            if not job:
                continue
            with er._ADMISSION_LOCK:
                er._reconcile_job_locked(job)
        started = er._drain_queue(None)
        if started:
            er._scheduler_stat_inc("jobs_started", len(started))

    def _sorted_hot_iter(self, project_id: str | None = None):
        assert self._real_iter_job_files is not None
        return iter(sorted(list(self._real_iter_job_files(project_id)), key=lambda p: str(p)))

    def _observed_drain(self, project_id: str | None = None, **kwargs):
        assert self._real_drain_queue is not None
        self.drain_calls += 1
        return self._real_drain_queue(project_id, **kwargs)

    def _pid_alive(self, pid: int | None) -> bool:
        if pid is None:
            return False
        try:
            return int(pid) in self.pid_generation
        except (TypeError, ValueError):
            return False

    def _process_creation_time_100ns(self, pid: int | None) -> int | None:
        if pid is None:
            return None
        try:
            return self.pid_generation.get(int(pid))
        except (TypeError, ValueError):
            return None

    def _pid_only_identity_state(
        self, job: ExecutionJobRecord
    ) -> tuple[str, int | None]:
        observed = self._process_creation_time_100ns(job.pid)
        if not self._pid_alive(job.pid):
            return er.LEGACY_PROCESS_IDENTITY_DEAD, observed
        return er.LEGACY_PROCESS_IDENTITY_SAME, observed

    def _fake_spawn(self, job: ExecutionJobRecord) -> ExecutionJobRecord:
        pid = self.next_pid
        self.next_pid += 1
        generation = self.pid_generation.get(pid, 0) + 1
        self.pid_generation[pid] = generation
        self.job_process_identity[job.job_id] = (pid, generation)
        er._set_job_status(job, er.JOB_STATUS_RUNNING, "runtime")
        job.pid = pid
        job.pid_creation_time_100ns = generation
        job.started_at = self.clock.now()
        job.supervision_state = "simulated_process"
        return job

    def _new_record(
        self,
        project_id: str,
        status: str,
        *,
        pid: int | None = 0,
        job_id: str | None = None,
    ) -> ExecutionJobRecord:
        self.job_counter += 1
        jid = job_id or f"job-{self.job_counter:05d}"
        stamp = self.clock.now()
        return ExecutionJobRecord.from_dict(
            {
                "job_id": jid,
                "project_id": project_id,
                "status": status,
                "pid": pid,
                "command": ["simulated"],
                "stdout_path": "",
                "stderr_path": "",
                "worker_token": None,
                "supervision_state": "simulated",
                "created_at": stamp,
                "submitted_at": stamp,
            }
        )

    def _active_records(self) -> list[ExecutionJobRecord]:
        records: list[ExecutionJobRecord] = []
        for path in self._sorted_hot_iter(None):
            job, error = er._load_job_file(path)
            if error is None and job is not None:
                records.append(job)
        return records

    def _terminal_records(self) -> list[ExecutionJobRecord]:
        records: list[ExecutionJobRecord] = []
        assert self.projects_root is not None
        for project_id in self.PROJECTS:
            root = self.projects_root / project_id / "system" / "logs" / "execution" / "terminal"
            if not root.is_dir():
                continue
            for path in sorted(root.glob("*.json"), key=lambda p: str(p)):
                job, error = er._load_job_file(path)
                if error is None and job is not None:
                    records.append(job)
        return records

    def _state_summary(self) -> Json:
        active = self._active_records()
        terminal = self._terminal_records()
        aliases: list[str] = []
        for job in active:
            identity = self.job_process_identity.get(job.job_id)
            if identity is None or job.pid is None:
                continue
            pid, original_generation = identity
            current_generation = self.pid_generation.get(pid)
            if current_generation is not None and current_generation != original_generation:
                aliases.append(job.job_id)
        return {
            "active": sorted((j.job_id, j.project_id, j.status, j.pid) for j in active),
            "terminal": sorted((j.job_id, j.project_id, j.status) for j in terminal),
            "alive_pids": sorted((pid, gen) for pid, gen in self.pid_generation.items()),
            "pid_alias_jobs": sorted(aliases),
            "drain_calls": self.drain_calls,
            "scheduler_variant": self.scheduler_variant,
            "legacy_identity_variant": self.legacy_identity_variant,
            "pid_recycles": self.pid_recycles,
            "telemetry": {
                "jobs_reconcile_errors": er._scheduler_snapshot().get("jobs_reconcile_errors"),
                "last_tick_reconcile_errors": er._scheduler_snapshot().get("last_tick_reconcile_errors"),
            },
        }

    def _record_trace(self, action: str, detail: Json | None = None) -> None:
        self.trace.append(
            {
                "step": len(self.trace),
                "action": action,
                "detail": detail or {},
                "state": self._state_summary(),
            }
        )

    def _fail(self, message: str) -> None:
        payload = json.dumps(self.trace, sort_keys=True, separators=(",", ":"))
        raise SimulationInvariantError(
            f"{message}; A038_REPLAY_SEED={self.seed}; A038_TRACE={payload}"
        )

    def _assert_structural_invariants(self) -> None:
        active = self._active_records()
        terminal = self._terminal_records()
        active_ids = {job.job_id for job in active}
        terminal_ids = {job.job_id for job in terminal}
        if active_ids & terminal_ids:
            self._fail(f"job present in active and terminal: {sorted(active_ids & terminal_ids)}")
        for job in active:
            if job.status not in er.JOB_ACTIVE_STATUSES:
                self._fail(f"terminal status stranded in active store: {job.job_id}:{job.status}")
        for job in terminal:
            if job.status not in er.JOB_TERMINAL_STATUSES:
                self._fail(f"active status stranded in terminal store: {job.job_id}:{job.status}")
        running = [
            j
            for j in active
            if j.status == er.JOB_STATUS_RUNNING
            and (
                self._pid_alive(j.pid)
                if getattr(j, "worker_token", None)
                else er._legacy_process_identity_state(j)[0]
                == er.LEGACY_PROCESS_IDENTITY_SAME
            )
        ]
        if len(running) > self.global_limit:
            self._fail(f"global running limit exceeded: {len(running)} > {self.global_limit}")
        for project_id in self.PROJECTS:
            count = sum(1 for j in running if j.project_id == project_id)
            if count > self.project_limit:
                self._fail(
                    f"project running limit exceeded: {project_id} {count} > {self.project_limit}"
                )

    def action_queue(self, project_id: str) -> None:
        job = self._new_record(project_id, er.JOB_STATUS_QUEUED)
        er._write_job(project_id, job.job_id, job)
        self._record_trace("queue", {"project_id": project_id, "job_id": job.job_id})

    def action_dead_running(self, project_id: str) -> None:
        pid = self.next_pid
        self.next_pid += 1
        job = self._new_record(project_id, er.JOB_STATUS_RUNNING, pid=pid)
        job.stage = "runtime"
        # Deliberately do not register PID as alive: this is a supervision-loss specimen.
        er._write_job(project_id, job.job_id, job)
        self._record_trace("dead_running", {"project_id": project_id, "job_id": job.job_id, "pid": pid})

    def action_kill_live(self) -> bool:
        candidates: list[tuple[str, int, int]] = []
        for job in self._active_records():
            identity = self.job_process_identity.get(job.job_id)
            if identity is None:
                continue
            pid, generation = identity
            if self.pid_generation.get(pid) == generation:
                candidates.append((job.job_id, pid, generation))
        if not candidates:
            return False
        job_id, pid, generation = self.rng.choice(candidates)
        self.pid_generation.pop(pid, None)
        self._record_trace("kill_live", {"job_id": job_id, "pid": pid, "generation": generation})
        return True

    def action_recycle_pid(self) -> bool:
        candidates: list[tuple[str, int, int]] = []
        for job in self._active_records():
            identity = self.job_process_identity.get(job.job_id)
            if identity is None:
                continue
            pid, generation = identity
            if self.pid_generation.get(pid) == generation:
                candidates.append((job.job_id, pid, generation))
        if not candidates:
            return False
        job_id, pid, generation = self.rng.choice(candidates)
        self.pid_generation[pid] = generation + 1
        self.pid_recycles += 1
        self._record_trace(
            "recycle_pid",
            {
                "job_id": job_id,
                "pid": pid,
                "old_generation": generation,
                "new_generation": generation + 1,
            },
        )
        return True

    def action_clock_jump(self) -> None:
        delta = self.rng.choice((-5000, -1000, 1000, 5000, 60000))
        self.clock.jump(delta)
        self._record_trace("clock_jump", {"milliseconds": delta})

    def action_tick(self) -> None:
        before = self.drain_calls
        er._scheduler_tick()
        if self.drain_calls <= before:
            self._fail("scheduler tick failed to reach drain")
        # On a clean tick, every invalid legacy non-worker RUNNING identity
        # (dead, recycled, or otherwise unverifiable) should be reconciled.
        stranded = [
            job.job_id
            for job in self._active_records()
            if job.status == er.JOB_STATUS_RUNNING
            and not getattr(job, "worker_token", None)
            and er._legacy_process_identity_state(job)[0]
            != er.LEGACY_PROCESS_IDENTITY_SAME
        ]
        if stranded:
            self._fail(f"invalid legacy RUNNING identities survived clean tick: {stranded}")
        self._record_trace("tick")

    def action_tick_reconcile_fault(self) -> bool:
        if not self._active_records():
            return False
        before = self.drain_calls
        original = er._reconcile_job_locked
        injected = {"done": False}

        def faulty(job):
            if not injected["done"]:
                injected["done"] = True
                self.reconcile_faults += 1
                raise PermissionError("A038 injected reconcile fault")
            return original(job)

        with patch.object(er, "_reconcile_job_locked", side_effect=faulty):
            er._scheduler_tick()
        if self.drain_calls <= before:
            self._fail("reconcile fault suppressed scheduler drain")
        if er._scheduler_snapshot().get("last_tick_reconcile_errors", 0) < 1:
            self._fail("reconcile fault was not surfaced in scheduler telemetry")
        self._record_trace("tick_reconcile_fault")
        return True

    def action_tick_spawn_fault(self) -> bool:
        if not any(j.status == er.JOB_STATUS_QUEUED for j in self._active_records()):
            return False
        before = self.drain_calls
        original = self._base_spawn
        injected = {"done": False}

        def faulty(job):
            if not injected["done"]:
                injected["done"] = True
                self.spawn_failures += 1
                raise OSError("A038 injected spawn fault")
            return original(job)

        with patch.object(er, "_spawn_job", side_effect=faulty):
            er._scheduler_tick()
        if self.drain_calls <= before:
            self._fail("spawn fault suppressed scheduler drain")
        self._record_trace("tick_spawn_fault")
        return True

    def available_actions(self) -> list[tuple[str, Callable[[], Any]]]:
        actions: list[tuple[str, Callable[[], Any]]] = [
            ("queue:p1", lambda: self.action_queue("p1")),
            ("queue:p2", lambda: self.action_queue("p2")),
            ("dead_running:p1", lambda: self.action_dead_running("p1")),
            ("dead_running:p2", lambda: self.action_dead_running("p2")),
            ("tick", self.action_tick),
            ("clock_jump", self.action_clock_jump),
        ]
        if self._active_records():
            actions.append(("tick_reconcile_fault", self.action_tick_reconcile_fault))
        if any(j.status == er.JOB_STATUS_QUEUED for j in self._active_records()):
            actions.append(("tick_spawn_fault", self.action_tick_spawn_fault))
        if any(
            self.job_process_identity.get(j.job_id) is not None
            for j in self._active_records()
        ):
            actions.extend(
                [
                    ("kill_live", self.action_kill_live),
                    ("recycle_pid", self.action_recycle_pid),
                ]
            )
        return actions


    def run(self, steps: int = 40) -> Json:
        for _ in range(int(steps)):
            actions = self.available_actions()
            action_name, action = self.rng.choice(actions)
            try:
                action()
            except SimulationInvariantError:
                raise
            except Exception as exc:
                self._record_trace(
                    "action_exception",
                    {
                        "scheduled_action": action_name,
                        "exception_type": type(exc).__name__,
                        "message": str(exc)[:500],
                    },
                )
                self._fail(
                    f"scheduled action {action_name} raised {type(exc).__name__}: {exc}"
                )
            self._assert_structural_invariants()
        return {
            "seed": self.seed,
            "steps": int(steps),
            "scheduler_variant": self.scheduler_variant,
            "legacy_identity_variant": self.legacy_identity_variant,
            "trace": self.trace,
            "final_state": self._state_summary(),
            "reconcile_faults": self.reconcile_faults,
            "spawn_failures": self.spawn_failures,
            "pid_recycles": self.pid_recycles,
        }


def run_seed(
    seed: int,
    steps: int = 40,
    *,
    scheduler_variant: str = "current",
    legacy_identity_variant: str = "current",
) -> Json:
    with DeterministicExecutionLifecycleSim(
        seed,
        scheduler_variant=scheduler_variant,
        legacy_identity_variant=legacy_identity_variant,
    ) as sim:
        return sim.run(steps)


def run_pid_reuse_probe(*, legacy_identity_variant: str) -> Json:
    """Execute one fixed legacy PID-reuse schedule for vulnerable/current comparison."""
    with DeterministicExecutionLifecycleSim(
        0, legacy_identity_variant=legacy_identity_variant
    ) as sim:
        sim.action_queue("p1")
        sim.action_tick()
        running_before = [
            job.job_id
            for job in sim._active_records()
            if job.status == er.JOB_STATUS_RUNNING
        ]
        if len(running_before) != 1:
            sim._fail(f"PID reuse probe expected one RUNNING job, got {running_before}")
        target = running_before[0]
        if not sim.action_recycle_pid():
            sim._fail("PID reuse probe could not recycle target process")
        sim.action_tick()
        active_after = {job.job_id: job.status for job in sim._active_records()}
        terminal_after = {job.job_id: job.status for job in sim._terminal_records()}
        return {
            "legacy_identity_variant": legacy_identity_variant,
            "target_job_id": target,
            "target_active_after": active_after.get(target),
            "target_terminal_after": terminal_after.get(target),
            "trace": sim.trace,
            "final_state": sim._state_summary(),
        }


def discover_failure(
    *,
    scheduler_variant: str,
    seed_limit: int = 100,
    steps: int = 40,
) -> Json | None:
    """Return the first deterministic failing schedule in a bounded seed search."""
    for seed in range(int(seed_limit)):
        try:
            run_seed(seed, steps, scheduler_variant=scheduler_variant)
        except SimulationInvariantError as exc:
            return {
                "seed": seed,
                "steps": int(steps),
                "scheduler_variant": scheduler_variant,
                "failure": str(exc),
            }
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay deterministic PCMMAD execution lifecycle schedules")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--steps", type=int, default=40)
    parser.add_argument(
        "--scheduler-variant", choices=("current", "pre_a034"), default="current"
    )
    parser.add_argument(
        "--legacy-identity-variant", choices=("current", "pid_only"), default="current"
    )
    args = parser.parse_args()
    try:
        result = run_seed(
            args.seed,
            args.steps,
            scheduler_variant=args.scheduler_variant,
            legacy_identity_variant=args.legacy_identity_variant,
        )
    except SimulationInvariantError as exc:
        print(str(exc))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
