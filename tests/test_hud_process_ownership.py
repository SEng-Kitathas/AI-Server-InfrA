from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

import operator_plane as op


@unittest.skipUnless(os.name == "nt", "Windows HUD process ownership tests")
class HudProcessOwnershipTests(unittest.TestCase):
    def test_hud_process_identity_recognizes_known_server_and_venv_launcher_parent(self) -> None:
        server = Path(r"E:\runtime\operator_hud\server.py")
        listener = {
            "pid": 200,
            "parent_pid": 100,
            "executable_path": r"C:\Python312\python.exe",
            "creation_date": "L2",
            "command_fingerprint": "listener-fp",
            "command_line": f'"C:\\Python312\\python.exe" "{server}"',
        }
        parent = {
            "pid": 100,
            "parent_pid": 50,
            "executable_path": r"E:\venv\Scripts\python.exe",
            "creation_date": "P1",
            "command_fingerprint": "parent-fp",
            "command_line": f'"E:\\venv\\Scripts\\python.exe" "{server}"',
        }
        with patch.object(op, "_hud_server_candidates", return_value=[(server, "receiver_local")]), patch.object(
            op, "_process_info", side_effect=lambda pid: listener if pid == 200 else parent if pid == 100 else None
        ):
            identity = op._hud_process_identity(200)
        self.assertTrue(identity["recognized"])
        self.assertEqual(identity["running_server_path"], str(server))
        self.assertEqual(identity["running_server_source"], "receiver_local")
        self.assertEqual(identity["listener"]["pid"], 200)
        self.assertEqual(identity["kill_root"]["pid"], 100)

    def test_healthy_meta_on_unrecognized_port_owner_is_not_owned_or_ok(self) -> None:
        unowned = {
            "recognized": False,
            "listener": {"pid": 777},
            "running_server_path": None,
            "running_server_source": None,
            "kill_root": None,
        }
        with patch.object(op, "resolve_hud_server", return_value=(Path("preferred.py"), "receiver_local")), patch.object(
            op, "_port_open", return_value=True
        ), patch.object(op, "_port_owner_pid", return_value=777), patch.object(
            op, "_hud_process_identity", return_value=unowned
        ), patch.object(
            op, "_http_meta", return_value=(True, {"ok": True, "hud": "PCMMAD Operations HUD"}, None)
        ):
            status = op.hud_status()
        self.assertTrue(status["healthy"])
        self.assertFalse(status["owned"])
        self.assertFalse(status["ok"])
        self.assertIn("unrecognized process", status["reason"])

    def test_receiver_local_process_with_valid_meta_is_owned_and_healthy(self) -> None:
        preferred = Path(r"E:\preferred\server.py")
        identity = {
            "recognized": True,
            "listener": {"pid": 10},
            "running_server_path": str(preferred),
            "running_server_source": "receiver_local",
            "kill_root": {"pid": 10},
        }
        with patch.object(op, "resolve_hud_server", return_value=(preferred, "receiver_local")), patch.object(
            op, "_port_open", return_value=True
        ), patch.object(op, "_port_owner_pid", return_value=10), patch.object(
            op, "_hud_process_identity", return_value=identity
        ), patch.object(
            op, "_http_meta", return_value=(True, {"ok": True, "hud": "PCMMAD Operations HUD"}, None)
        ):
            status = op.hud_status()
        self.assertTrue(status["healthy"])
        self.assertTrue(status["owned"])
        self.assertTrue(status["ok"])
        self.assertEqual(status["running_server_source"], "receiver_local")

    def test_legacy_rahl_hud_is_not_a_candidate(self) -> None:
        with patch.dict("os.environ", {"PCMMAD_HUD_SERVER": ""}, clear=False), patch.object(
            op, "RECEIVER_LOCAL_HUD", Path(r"Z:\missing\operator_hud\server.py")
        ):
            candidates = op._hud_server_candidates()
        self.assertEqual(candidates, [])
        self.assertEqual(op.resolve_hud_server()[1] if candidates else "missing", "missing")

    def test_stop_refuses_unrecognized_port_owner_without_taskkill(self) -> None:
        status = {"listener_pid": 777, "owned": False, "process_identity": {}}
        with patch.object(op, "hud_status", return_value=status), patch.object(op.subprocess, "run") as run:
            with self.assertRaises(RuntimeError) as caught:
                op.stop_hud()
        self.assertIn("HUD_PROCESS_IDENTITY_MISMATCH", str(caught.exception))
        run.assert_not_called()

    def test_stop_refuses_pid_reuse_or_identity_change_before_kill(self) -> None:
        identity = {
            "listener": {"pid": 200, "creation_date": "A", "command_fingerprint": "x"},
            "kill_root": {"pid": 100, "creation_date": "B", "command_fingerprint": "y"},
        }
        status = {"listener_pid": 200, "owned": True, "process_identity": identity}
        with patch.object(op, "hud_status", return_value=status), patch.object(
            op, "_identity_matches", side_effect=[True, False]
        ), patch.object(op.subprocess, "run") as run:
            with self.assertRaises(RuntimeError) as caught:
                op.stop_hud()
        self.assertIn("HUD_PROCESS_IDENTITY_STALE", str(caught.exception))
        run.assert_not_called()

    def test_stop_kills_verified_launcher_root_not_arbitrary_listener_only(self) -> None:
        identity = {
            "listener": {"pid": 200, "creation_date": "A", "command_fingerprint": "x"},
            "kill_root": {"pid": 100, "creation_date": "B", "command_fingerprint": "y"},
        }
        status = {"listener_pid": 200, "owned": True, "process_identity": identity}
        cp = SimpleNamespace(returncode=0)
        with patch.object(op, "hud_status", return_value=status), patch.object(
            op, "_identity_matches", return_value=True
        ), patch.object(op.subprocess, "run", return_value=cp) as run, patch.object(
            op, "_port_open", return_value=False
        ):
            result = op.stop_hud(timeout_seconds=1)
        self.assertTrue(result["ok"])
        self.assertEqual(result["stopped_root_pid"], 100)
        command = run.call_args.args[0]
        self.assertEqual(command[:3], ["taskkill", "/PID", "100"])

    def test_start_binds_hud_to_actual_receiver_host_and_port(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            server = Path(td) / "server.py"
            server.write_text("print('x')", encoding="utf-8")
            proc = SimpleNamespace(pid=4321, poll=lambda: None)
            states = iter(
                [
                    {"ok": False},
                    {"ok": True, "running_server_path": str(server.resolve())},
                ]
            )
            with patch.dict(
                os.environ,
                {
                    "PCMMAD_BIND_HOST": "127.0.0.1",
                    "PCMMAD_BIND_PORT": "8799",
                    "PCMMAD_HUD_PORT": "5091",
                },
                clear=False,
            ):
                os.environ.pop("PCMMAD_RECEIVER_BASE", None)
                with patch.object(op, "hud_status", side_effect=lambda: next(states)), patch.object(
                    op, "resolve_hud_server", return_value=(server, "receiver_local")
                ), patch.object(op, "_port_open", return_value=False), patch.object(
                    op.subprocess, "Popen", return_value=proc
                ) as popen:
                    out = op.ensure_hud_running(wait_seconds=1)
            self.assertEqual(out["action"], "started")
            env = popen.call_args.kwargs["env"]
            self.assertEqual(env["PCMMAD_RECEIVER_BASE"], "http://127.0.0.1:8799")

    def test_start_identity_mismatch_cleans_our_launcher_without_killing_other_listener(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            server = Path(td) / "server.py"
            server.write_text("print('x')", encoding="utf-8")
            other = Path(td) / "other.py"
            other.write_text("print('y')", encoding="utf-8")
            proc = SimpleNamespace(pid=4321, poll=lambda: None)
            states = iter(
                [
                    {"ok": False},
                    {"ok": True, "running_server_path": str(other)},
                ]
            )
            cp = SimpleNamespace(returncode=0)
            with patch.object(op, "hud_status", side_effect=lambda: next(states)), patch.object(
                op, "resolve_hud_server", return_value=(server, "receiver_local")
            ), patch.object(op, "_port_open", return_value=False), patch.object(
                op.subprocess, "Popen", return_value=proc
            ), patch.object(op.subprocess, "run", return_value=cp) as run:
                with self.assertRaises(RuntimeError) as caught:
                    op.ensure_hud_running(wait_seconds=1)
            self.assertIn("identity mismatch", str(caught.exception).lower())
            taskkills = [call.args[0] for call in run.call_args_list if call.args and call.args[0][0] == "taskkill"]
            self.assertEqual(len(taskkills), 1)
            self.assertEqual(taskkills[0][2], "4321")


if __name__ == "__main__":
    unittest.main()
