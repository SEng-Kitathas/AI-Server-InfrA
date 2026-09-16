from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

import execution_routes as er
from control_plane_models import SchedulerTelemetry
from windows_directory_watch import DirectoryChangeEvent, WindowsRecursiveDirectoryWatcher


class _AliveWatcher:
    def is_alive(self) -> bool:
        return True


class _DeadWatcher:
    def is_alive(self) -> bool:
        return False


class ExecutionInformerWatchTests(unittest.TestCase):
    def setUp(self) -> None:
        er._SCHEDULER_WAKE.clear()
        self.telemetry_patch = patch.object(er, "_SCHEDULER_TELEMETRY", SchedulerTelemetry())
        self.telemetry_patch.start()

    def tearDown(self) -> None:
        er._SCHEDULER_WAKE.clear()
        self.telemetry_patch.stop()

    def test_path_filter_ignores_heartbeat_and_active_metadata_but_accepts_completion(self) -> None:
        self.assertFalse(
            er._execution_watch_path_relevant(
                r"p1\system\logs\execution\job1\worker_heartbeat.json"
            )
        )
        self.assertFalse(
            er._execution_watch_path_relevant(
                r"p1\system\logs\execution\active\job1.json"
            )
        )
        self.assertFalse(er._execution_watch_path_relevant(r"p1\src\worker_completion.json"))
        self.assertTrue(
            er._execution_watch_path_relevant(
                r"p1\system\logs\execution\job1\worker_completion.json"
            )
        )

    def test_completion_edges_coalesce_to_one_wake_and_noise_is_ignored(self) -> None:
        noise = [
            DirectoryChangeEvent(1, r"p1\system\logs\execution\job1\worker_heartbeat.json"),
            DirectoryChangeEvent(5, r"p1\system\logs\execution\active\job1.json"),
        ]
        er._scheduler_watch_events(noise)
        self.assertFalse(er._SCHEDULER_WAKE.is_set())
        self.assertEqual(er._scheduler_snapshot()["watcher_events"], 0)

        completions = [
            DirectoryChangeEvent(1, r"p1\system\logs\execution\j1\worker_completion.json"),
            DirectoryChangeEvent(5, r"p2\system\logs\execution\j2\worker_completion.json"),
        ]
        er._scheduler_watch_events(completions)
        self.assertTrue(er._SCHEDULER_WAKE.is_set())
        snap = er._scheduler_snapshot()
        self.assertEqual(snap["watcher_events"], 2)
        self.assertIsNotNone(snap["last_watcher_event_at"])

    def test_overflow_forces_wake_without_claiming_event_completeness(self) -> None:
        er._scheduler_watch_overflow()
        self.assertTrue(er._SCHEDULER_WAKE.is_set())
        self.assertEqual(er._scheduler_snapshot()["watcher_overflows"], 1)

    def test_wait_policy_uses_idle_active_and_poll_fallback_modes(self) -> None:
        with patch.object(er, "_EXECUTION_WATCHER", _AliveWatcher()):
            timeout, mode = er._scheduler_wait_timeout(0)
            self.assertEqual(timeout, er.EXECUTION_SCHEDULER_IDLE_RESYNC_SECONDS)
            self.assertEqual(mode, "watch_idle")
            timeout, mode = er._scheduler_wait_timeout(3)
            self.assertEqual(timeout, er.EXECUTION_SCHEDULER_ACTIVE_RESYNC_SECONDS)
            self.assertEqual(mode, "watch_active")

        with patch.object(er, "_EXECUTION_WATCHER", _DeadWatcher()):
            timeout, mode = er._scheduler_wait_timeout(0)
            self.assertEqual(timeout, er.EXECUTION_SCHEDULER_INTERVAL_SECONDS)
            self.assertEqual(mode, "poll_fallback")

    def test_capabilities_expose_policy_while_telemetry_exposes_live_wait_mode(self) -> None:
        with patch.object(er, "_EXECUTION_WATCHER", _AliveWatcher()):
            capabilities = er.execution_capabilities()
        self.assertEqual(capabilities["watcher_supported"], bool(os.name == "nt" and er._WindowsRecursiveDirectoryWatcher is not None))
        # watcher_active reports the live watcher object, not platform capability.
        self.assertTrue(capabilities["watcher_active"])
        self.assertEqual(
            capabilities["scheduler_active_resync_seconds"],
            er.EXECUTION_SCHEDULER_ACTIVE_RESYNC_SECONDS,
        )
        self.assertEqual(
            capabilities["scheduler_idle_resync_seconds"],
            er.EXECUTION_SCHEDULER_IDLE_RESYNC_SECONDS,
        )
        er._scheduler_stat_set("scheduler_wait_mode", "watch_idle")
        self.assertEqual(er._scheduler_snapshot()["scheduler_wait_mode"], "watch_idle")

    def test_watch_error_disables_accelerator_and_wakes_fallback(self) -> None:
        with patch.object(er, "_EXECUTION_WATCH_FAILED", False):
            er._scheduler_watch_error("synthetic failure")
            self.assertTrue(er._SCHEDULER_WAKE.is_set())
            snap = er._scheduler_snapshot()
            self.assertEqual(snap["watcher_errors"], 1)
            self.assertIn("synthetic failure", snap["last_watcher_error"])

    @unittest.skipUnless(os.name == "nt", "native watcher smoke requires Windows")
    def test_native_watcher_observes_atomic_completion_and_stops_cleanly(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-a040-watch-") as td:
            root = Path(td)
            target_dir = root / "p1" / "system" / "logs" / "execution" / "job1"
            target_dir.mkdir(parents=True)
            events: list[DirectoryChangeEvent] = []
            errors: list[str] = []
            watcher = WindowsRecursiveDirectoryWatcher(
                root,
                on_events=lambda rows: events.extend(rows),
                on_overflow=lambda: None,
                on_error=errors.append,
            )
            watcher.start()
            try:
                time.sleep(0.05)
                temp = target_dir / "worker_completion.json.tmp"
                final = target_dir / "worker_completion.json"
                temp.write_text("{}", encoding="utf-8")
                os.replace(temp, final)
                deadline = time.monotonic() + 2.0
                while time.monotonic() < deadline and not any(
                    row.relative_path.endswith("worker_completion.json") for row in events
                ):
                    time.sleep(0.01)
            finally:
                watcher.stop()

            self.assertFalse(watcher.is_alive())
            self.assertEqual(errors, [])
            self.assertTrue(
                any(row.relative_path.endswith("worker_completion.json") for row in events),
                events,
            )

    @unittest.skipUnless(os.name == "nt", "scheduler/watch integration requires Windows")
    def test_idle_scheduler_does_not_poll_at_250ms_and_completion_wakes_it(self) -> None:
        # Earlier execution tests may have legitimately started the process-global
        # scheduler. This test owns a manual loop and patches _scheduler_tick, so it
        # must first quiesce that global loop or full-suite ordering creates duplicate
        # ticks that cannot occur in the single-scheduler production topology.
        er._shutdown_scheduler()
        er._SCHEDULER_STOP.clear()
        er._SCHEDULER_WAKE.clear()
        with tempfile.TemporaryDirectory(prefix="pcmmad-a040-loop-") as td:
            root = Path(td)
            target_dir = root / "p1" / "system" / "logs" / "execution" / "job1"
            target_dir.mkdir(parents=True)
            tick_times: list[float] = []
            original_tick = er._scheduler_tick

            def counted_tick() -> int:
                tick_times.append(time.monotonic())
                return original_tick()

            with patch.object(er, "PROJECTS_ROOT", root), patch.object(
                er, "_scheduler_tick", side_effect=counted_tick
            ), patch.object(er, "EXECUTION_SCHEDULER_IDLE_RESYNC_SECONDS", 5.0), patch.object(
                er, "EXECUTION_SCHEDULER_ACTIVE_RESYNC_SECONDS", 1.0
            ), patch.object(er, "_EXECUTION_WATCH_FAILED", False):
                er._SCHEDULER_STOP.clear()
                er._SCHEDULER_WAKE.clear()
                self.assertTrue(er._ensure_execution_watcher_started())
                thread = threading.Thread(target=er._scheduler_loop, daemon=True)
                thread.start()
                try:
                    deadline = time.monotonic() + 1.0
                    while time.monotonic() < deadline and len(tick_times) < 1:
                        time.sleep(0.01)
                    self.assertEqual(len(tick_times), 1)
                    # More than one historical 250 ms period, but less than idle resync.
                    time.sleep(0.40)
                    self.assertEqual(len(tick_times), 1, tick_times)

                    temp = target_dir / "worker_completion.json.tmp"
                    final = target_dir / "worker_completion.json"
                    temp.write_text("{}", encoding="utf-8")
                    os.replace(temp, final)
                    deadline = time.monotonic() + 1.5
                    while time.monotonic() < deadline and len(tick_times) < 2:
                        time.sleep(0.01)
                    self.assertGreaterEqual(len(tick_times), 2, tick_times)
                    self.assertLess(tick_times[1] - tick_times[0], 2.0)
                finally:
                    er._SCHEDULER_STOP.set()
                    er._SCHEDULER_WAKE.set()
                    thread.join(timeout=2.0)
                    er._shutdown_execution_watcher()
                    er._SCHEDULER_STOP.clear()
                    er._SCHEDULER_WAKE.clear()

            self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
