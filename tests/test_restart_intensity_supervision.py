from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESTART_SCRIPT = PROJECT_ROOT / "RESTART_RECEIVER_AND_NGROK.ps1"
POWERSHELL = shutil.which("powershell.exe")


@unittest.skipUnless(os.name == "nt" and POWERSHELL, "Windows PowerShell restart supervision tests")
class RestartIntensitySupervisionTests(unittest.TestCase):
    def _command(
        self,
        root: Path,
        name: str,
        *,
        force: bool = False,
    ) -> list[str]:
        cmd = [
            str(POWERSHELL),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RESTART_SCRIPT),
            "-Action",
            "Restart",
            "-RestartIntensityReservationOnly",
            "-ReceiptPath",
            str(root / name),
        ]
        if force:
            cmd.append("-ForceRestart")
        return cmd

    def _child_env(self, root: Path) -> dict[str, str]:
        env = dict(os.environ)
        env["TEMP"] = str(root)
        env["TMP"] = str(root)
        return env

    def _state_root(self, root: Path) -> Path:
        return root / "pcmmad_restart_receipts"

    def _run(self, root: Path, name: str, **kwargs):
        completed = subprocess.run(
            self._command(root, name, **kwargs),
            cwd=PROJECT_ROOT,
            env=self._child_env(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            check=False,
        )
        receipt_path = root / name
        receipt = None
        if receipt_path.exists():
            receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
        return completed, receipt

    def test_burst_limit_enters_cooldown_and_force_does_not_clear_it(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-restart-intensity-") as td:
            root = Path(td)
            first, r1 = self._run(root, "one.json")
            second, r2 = self._run(root, "two.json")
            third, r3 = self._run(root, "three.json")
            fourth, r4 = self._run(root, "four.json")
            fifth, r5 = self._run(root, "five.json")
            forced, rf = self._run(root, "forced.json", force=True)

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(third.returncode, 0, third.stderr)
            self.assertEqual(r1["stage"], "restart_intensity_reserved")
            self.assertEqual(r1["restart_intensity"]["attempts_before"], 0)
            self.assertEqual(r2["restart_intensity"]["attempts_after"], 2)
            self.assertEqual(r3["restart_intensity"]["attempts_after"], 3)
            self.assertEqual(r3["restart_intensity"]["window_seconds"], 300)
            self.assertEqual(r3["restart_intensity"]["max_attempts"], 3)
            self.assertEqual(r3["restart_intensity"]["cooldown_seconds"], 600)
            self.assertEqual(r1["stopped_receiver_pids"], [])
            self.assertEqual(r2["stopped_ngrok_pids"], [])

            self.assertEqual(fourth.returncode, 75, fourth.stderr)
            self.assertEqual(r4["stage"], "restart_intensity_blocked")
            self.assertEqual(r4["restart_intensity"]["reason"], "restart_intensity_exceeded")
            self.assertIsNotNone(r4["finished_at"])
            cooldown_until = r4["restart_intensity"]["cooldown_until"]
            self.assertTrue(cooldown_until)

            self.assertEqual(fifth.returncode, 75, fifth.stderr)
            self.assertEqual(r5["restart_intensity"]["reason"], "cooldown_active")
            self.assertEqual(r5["restart_intensity"]["cooldown_until"], cooldown_until)

            self.assertEqual(forced.returncode, 0, forced.stderr)
            self.assertTrue(rf["restart_intensity"]["allowed"])
            self.assertTrue(rf["restart_intensity"]["forced"])
            self.assertEqual(rf["restart_intensity"]["cooldown_until"], cooldown_until)

            state = json.loads((self._state_root(root) / "restart_intensity_state.json").read_text(encoding="utf-8-sig"))
            self.assertEqual(len(state["attempts"]), 4)
            self.assertEqual(state["cooldown_until"], cooldown_until)

    def test_expired_attempt_is_pruned_before_reservation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-restart-expired-") as td:
            root = Path(td)
            old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=10)).isoformat()
            state_root = self._state_root(root)
            state_root.mkdir(parents=True, exist_ok=True)
            (state_root / "restart_intensity_state.json").write_text(
                json.dumps(
                    {
                        "schema": "pcmmad.restart-intensity.v1",
                        "attempts": [old],
                        "cooldown_until": None,
                        "updated_at": old,
                    }
                ),
                encoding="utf-8",
            )
            completed, receipt = self._run(root, "fresh.json")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(receipt["restart_intensity"]["attempts_before"], 0)
            self.assertEqual(receipt["restart_intensity"]["attempts_after"], 1)

    def test_corrupt_intensity_state_fails_closed_before_restart_consequence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-restart-corrupt-") as td:
            root = Path(td)
            state_root = self._state_root(root)
            state_root.mkdir(parents=True, exist_ok=True)
            (state_root / "restart_intensity_state.json").write_text("{not-json", encoding="utf-8")
            completed, receipt = self._run(root, "corrupt.json")
            self.assertEqual(completed.returncode, 1)
            self.assertIsNotNone(receipt)
            self.assertEqual(receipt["stage"], "failed")
            self.assertIn("Restart intensity state is unreadable", receipt["error"])
            self.assertEqual(receipt["stopped_receiver_pids"], [])
            self.assertEqual(receipt["stopped_ngrok_pids"], [])

    def test_concurrent_reservations_are_serialized_by_cross_process_lock(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-restart-race-") as td:
            root = Path(td)
            procs = [
                subprocess.Popen(
                    self._command(root, f"race-{idx}.json"),
                    cwd=PROJECT_ROOT,
                    env=self._child_env(root),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                for idx in range(6)
            ]
            results = []
            for proc in procs:
                stdout, stderr = proc.communicate(timeout=20)
                results.append((proc.returncode, stdout, stderr))

            return_codes = sorted(code for code, _stdout, _stderr in results)
            self.assertEqual(return_codes, [0, 0, 0, 75, 75, 75], results)
            receipts = [
                json.loads((root / f"race-{idx}.json").read_text(encoding="utf-8-sig"))
                for idx in range(6)
            ]
            self.assertEqual(sum(1 for receipt in receipts if receipt["restart_intensity"]["allowed"]), 3)
            self.assertEqual(
                sum(1 for receipt in receipts if receipt["stage"] == "restart_intensity_blocked"),
                3,
            )
            state = json.loads((self._state_root(root) / "restart_intensity_state.json").read_text(encoding="utf-8-sig"))
            self.assertEqual(len(state["attempts"]), 3)


if __name__ == "__main__":
    unittest.main()
