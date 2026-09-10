from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASELINE_ROOT = PROJECT_ROOT / "baseline"
sys.path.insert(0, str(BASELINE_ROOT))

import lab_state
import shared_core


class LabStateDurabilityHostileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pcmmad-lab-state-hostile-")
        self.root = Path(self.temp.name)
        self.project_id = "alpha"
        self.project = self.root / self.project_id
        self.project.mkdir(parents=True)
        self.patch = patch.object(lab_state, "get_project_root", side_effect=lambda _pid: self.project)
        self.patch.start()

    def tearDown(self) -> None:
        self.patch.stop()
        self.temp.cleanup()

    def test_session_metadata_publication_is_atomic(self) -> None:
        with patch.object(lab_state, "save_json_atomic", wraps=shared_core.save_json_atomic) as atomic:
            session = lab_state.start_session(self.project_id, "goal", {"mode": "manual"})
            closed = lab_state.end_session(self.project_id, session.session_id)
        self.assertEqual(closed.status, "closed")
        self.assertGreaterEqual(atomic.call_count, 2)

    def test_note_append_uses_durable_journal_without_snapshot_rewrite(self) -> None:
        session = lab_state.start_session(self.project_id, "goal", {"mode": "manual"})
        snapshot = lab_state._session_path(self.project_id, session.session_id)
        before = snapshot.read_bytes()
        with patch.object(lab_state, "append_jsonl", wraps=shared_core.append_jsonl) as append, patch.object(
            lab_state, "save_json_atomic", wraps=shared_core.save_json_atomic
        ) as atomic:
            observed = lab_state.append_session_note(self.project_id, session.session_id, "note")
        append.assert_called_once()
        atomic.assert_not_called()
        self.assertEqual(snapshot.read_bytes(), before)
        self.assertEqual([row.note for row in observed.notes], ["note"])
        journal = lab_state._session_notes_path(self.project_id, session.session_id)
        self.assertEqual(len(journal.read_text(encoding="utf-8").splitlines()), 1)

    def test_many_notes_are_o1_writes_against_bounded_snapshot(self) -> None:
        session = lab_state.start_session(self.project_id, "goal", {"mode": "manual"})
        snapshot = lab_state._session_path(self.project_id, session.session_id)
        before = snapshot.read_bytes()
        for index in range(100):
            lab_state.append_session_note(self.project_id, session.session_id, f"note-{index}")
        self.assertEqual(snapshot.read_bytes(), before)
        observed = lab_state.get_session(self.project_id, session.session_id)
        self.assertEqual(len(observed.notes), 100)
        self.assertEqual(observed.notes[-1].note, "note-99")

    def test_two_thread_notes_cannot_lose_update(self) -> None:
        session = lab_state.start_session(self.project_id, "goal", {"mode": "manual"})
        errors: list[BaseException] = []

        def writer(note: str) -> None:
            try:
                lab_state.append_session_note(self.project_id, session.session_id, note)
            except BaseException as exc:  # pragma: no cover - diagnostic collection
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(note,)) for note in ("a", "b")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertFalse(errors, errors)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        persisted = lab_state.get_session(self.project_id, session.session_id)
        self.assertEqual({row.note for row in persisted.notes}, {"a", "b"})
        self.assertEqual(len(persisted.notes), 2)

    def test_two_process_notes_cannot_lose_update(self) -> None:
        session = lab_state.start_session(self.project_id, "goal", {"mode": "manual"})
        gate = self.root / "GO"
        code = r'''
import sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import lab_state
root=Path(sys.argv[2]); project_id=sys.argv[3]; session_id=sys.argv[4]; note=sys.argv[5]; gate=Path(sys.argv[6])
lab_state.get_project_root=lambda _pid: root/project_id
print("READY", flush=True)
while not gate.exists(): time.sleep(0.005)
lab_state.append_session_note(project_id, session_id, note)
print("DONE", flush=True)
'''
        children = [
            subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    code,
                    str(BASELINE_ROOT),
                    str(self.root),
                    self.project_id,
                    session.session_id,
                    note,
                    str(gate),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for note in ("a", "b")
        ]
        try:
            for child in children:
                self.assertEqual(child.stdout.readline().strip(), "READY")
            gate.write_text("go", encoding="utf-8")
            for child in children:
                self.assertEqual(child.stdout.readline().strip(), "DONE")
                child.wait(timeout=10)
                self.assertEqual(child.returncode, 0, child.stderr.read())
        finally:
            for child in children:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=5)
        persisted = lab_state.get_session(self.project_id, session.session_id)
        self.assertEqual({row.note for row in persisted.notes}, {"a", "b"})
        self.assertEqual(len(persisted.notes), 2)

    def test_shared_jsonl_append_serializes_cross_process_writers(self) -> None:
        path = self.root / "shared.jsonl"
        code = r'''
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from shared_core import append_jsonl
path=Path(sys.argv[2]); worker=sys.argv[3]
for index in range(25):
    append_jsonl(path, {"worker": worker, "index": index, "blob": "x" * 4096})
'''
        children = [
            subprocess.Popen(
                [sys.executable, "-c", code, str(BASELINE_ROOT), str(path), f"w{index}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for index in range(4)
        ]
        try:
            for child in children:
                child.wait(timeout=30)
                self.assertEqual(child.returncode, 0, child.stderr.read())
        finally:
            for child in children:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=5)
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 100)
        self.assertEqual(len({(row["worker"], row["index"]) for row in rows}), 100)

    def test_corrupt_note_journal_is_visible_not_silently_skipped(self) -> None:
        session = lab_state.start_session(self.project_id, "goal", {"mode": "manual"})
        lab_state.append_session_note(self.project_id, session.session_id, "good")
        with lab_state._session_notes_path(self.project_id, session.session_id).open("a", encoding="utf-8") as handle:
            handle.write("{broken\n")
        with self.assertRaisesRegex(ValueError, "session note journal corrupt"):
            lab_state.get_session(self.project_id, session.session_id)

    def test_andon_projection_failure_returns_recorded_stop_without_masking_original_error(self) -> None:
        session = lab_state.start_session(self.project_id, "goal", {"mode": "manual"})
        lab_state._session_path(self.project_id, session.session_id).write_text("{broken", encoding="utf-8")
        row = lab_state.pull_andon(
            self.project_id,
            {"reason": "stop", "session_id": session.session_id},
        )
        self.assertTrue(row.stop_recorded)
        self.assertFalse(row.session_pause_projected)
        self.assertIn("JSON", row.session_update_error or "")
        lines = lab_state._andon_path(self.project_id).read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["reason"], "stop")

    def test_andon_uses_shared_durable_append(self) -> None:
        with patch.object(lab_state, "append_jsonl", wraps=shared_core.append_jsonl) as append:
            row = lab_state.pull_andon(self.project_id, {"reason": "stop"})
        self.assertTrue(row.stop_recorded)
        append.assert_called_once()


if __name__ == "__main__":
    unittest.main()
