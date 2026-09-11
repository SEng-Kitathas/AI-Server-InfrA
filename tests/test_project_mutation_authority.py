from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

import project_mutation_authority as pma


class _Clock:
    def __init__(self, value: datetime | None = None) -> None:
        self.value = value or datetime(2026, 9, 6, 20, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += timedelta(seconds=seconds)


class ProjectMutationAuthorityTests(unittest.TestCase):
    def _patched_project(self, root: Path, clock: _Clock | None = None) -> ExitStack:
        stack = ExitStack()
        stack.enter_context(
            patch.object(pma, "get_project_root", side_effect=lambda project_id: root / project_id)
        )
        stack.enter_context(
            patch.object(
                pma,
                "init_project_layout",
                side_effect=lambda project_id: (root / project_id).mkdir(parents=True, exist_ok=True)
                or (root / project_id),
            )
        )
        if clock is not None:
            stack.enter_context(patch.object(pma, "_now", side_effect=clock))
            stack.enter_context(
                patch.object(pma, "utc_now", side_effect=lambda: clock().isoformat())
            )
        return stack

    def test_acquire_conflict_generation_fence_release_reacquire(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-a042-") as td:
            root = Path(td)
            with self._patched_project(root):
                first = pma.acquire_lease(
                    "p1",
                    expected_generation=0,
                    owner_id="owner-a",
                    session_id="session-a",
                )
                self.assertEqual(first["generation"], 1)
                self.assertEqual(first["status"], pma.LEASE_STATUS_ACTIVE)

                with self.assertRaises(pma.ProjectMutationAuthorityError) as stale:
                    pma.acquire_lease(
                        "p1",
                        expected_generation=0,
                        owner_id="owner-b",
                        session_id="session-b",
                    )
                self.assertEqual(stale.exception.error_code, "PROJECT_MUTATION_GENERATION_STALE")

                with self.assertRaises(pma.ProjectMutationAuthorityError) as busy:
                    pma.acquire_lease(
                        "p1",
                        expected_generation=1,
                        owner_id="owner-b",
                        session_id="session-b",
                    )
                self.assertEqual(busy.exception.error_code, "PROJECT_MUTATION_LEASE_BUSY")
                self.assertIsNone(busy.exception.extra["current_lease"]["lease_id"])

                released = pma.release_lease(
                    "p1",
                    lease_id=str(first["lease_id"]),
                    generation=1,
                    owner_id="owner-a",
                    session_id="session-a",
                )
                self.assertEqual(released["status"], pma.LEASE_STATUS_RELEASED)

                second = pma.acquire_lease(
                    "p1",
                    expected_generation=1,
                    owner_id="owner-b",
                    session_id="session-b",
                )
                self.assertEqual(second["generation"], 2)
                self.assertNotEqual(second["lease_id"], first["lease_id"])

                with self.assertRaises(pma.ProjectMutationAuthorityError) as fenced:
                    with pma.mutation_guard(
                        "p1",
                        lease_id=str(first["lease_id"]),
                        generation=1,
                        owner_id="owner-a",
                        session_id="session-a",
                    ):
                        pass
                self.assertEqual(fenced.exception.error_code, "PROJECT_MUTATION_LEASE_FENCED")

    def test_wrong_owner_or_bound_session_is_rejected_and_blank_owner_cannot_bypass(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-a042-owner-") as td:
            root = Path(td)
            with self._patched_project(root):
                lease = pma.acquire_lease(
                    "p1",
                    expected_generation=0,
                    owner_id="owner-a",
                    session_id="session-a",
                )
                args = dict(
                    project_id="p1",
                    lease_id=str(lease["lease_id"]),
                    generation=int(lease["generation"]),
                )
                with self.assertRaises(pma.ProjectMutationAuthorityError) as missing_owner:
                    pma.renew_lease(**args, owner_id="", session_id="session-a")
                self.assertEqual(
                    missing_owner.exception.error_code, "PROJECT_MUTATION_OWNER_REQUIRED"
                )

                with self.assertRaises(pma.ProjectMutationAuthorityError) as wrong_owner:
                    pma.release_lease(**args, owner_id="owner-b", session_id="session-a")
                self.assertEqual(
                    wrong_owner.exception.error_code, "PROJECT_MUTATION_OWNER_MISMATCH"
                )

                with self.assertRaises(pma.ProjectMutationAuthorityError) as blank_session:
                    with pma.mutation_guard(**args, owner_id="owner-a", session_id=""):
                        pass
                self.assertEqual(
                    blank_session.exception.error_code, "PROJECT_MUTATION_SESSION_MISMATCH"
                )

                with self.assertRaises(pma.ProjectMutationAuthorityError) as wrong_session:
                    with pma.mutation_guard(
                        **args, owner_id="owner-a", session_id="session-b"
                    ):
                        pass
                self.assertEqual(
                    wrong_session.exception.error_code, "PROJECT_MUTATION_SESSION_MISMATCH"
                )

                with pma.mutation_guard(
                    **args, owner_id="owner-a", session_id="session-a"
                ) as receipt:
                    self.assertEqual(receipt["owner_id"], "owner-a")

    def test_expiry_allows_takeover_but_old_generation_cannot_mutate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-a042-expiry-") as td:
            root = Path(td)
            clock = _Clock()
            with self._patched_project(root, clock):
                first = pma.acquire_lease(
                    "p1",
                    expected_generation=0,
                    owner_id="owner-a",
                    session_id="session-a",
                    ttl_seconds=10,
                )
                clock.advance(11)
                expired = pma.inspect_lease("p1")
                self.assertEqual(expired["status"], pma.LEASE_STATUS_EXPIRED)
                self.assertEqual(expired["generation"], 1)

                second = pma.acquire_lease(
                    "p1",
                    expected_generation=1,
                    owner_id="owner-b",
                    session_id="session-b",
                    ttl_seconds=10,
                )
                self.assertEqual(second["generation"], 2)

                with self.assertRaises(pma.ProjectMutationAuthorityError) as fenced:
                    pma.renew_lease(
                        "p1",
                        lease_id=str(first["lease_id"]),
                        generation=1,
                        owner_id="owner-a",
                        session_id="session-a",
                    )
                self.assertEqual(fenced.exception.error_code, "PROJECT_MUTATION_LEASE_FENCED")

    def test_integrity_and_shape_corruption_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-a042-corrupt-") as td:
            root = Path(td)
            with self._patched_project(root):
                pma.acquire_lease(
                    "p1", expected_generation=0, owner_id="owner-a", session_id="session-a"
                )
                path = pma._state_path("p1")
                row = json.loads(path.read_text(encoding="utf-8"))
                row["owner_id"] = "tampered"
                path.write_text(json.dumps(row), encoding="utf-8")
                with self.assertRaises(pma.ProjectMutationAuthorityError) as integrity:
                    pma.inspect_lease("p1")
                self.assertEqual(
                    integrity.exception.error_code,
                    "PROJECT_MUTATION_LEASE_INTEGRITY_INVALID",
                )

                row["integrity_hash"] = pma._integrity_hash(row)
                row["generation"] = "not-an-int"
                row["integrity_hash"] = pma._integrity_hash(row)
                path.write_text(json.dumps(row), encoding="utf-8")
                with self.assertRaises(pma.ProjectMutationAuthorityError) as malformed:
                    pma.inspect_lease("p1")
                self.assertEqual(
                    malformed.exception.error_code, "PROJECT_MUTATION_LEASE_INVALID"
                )

    def test_compatibility_session_guard_never_inherits_active_fenced_authority(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-a042-compat-") as td:
            root = Path(td)
            with self._patched_project(root):
                with pma.compatibility_session_guard("p1", session_id="legacy-a") as lease:
                    self.assertIsNone(lease)

                pma.acquire_lease(
                    "p1",
                    expected_generation=0,
                    owner_id="owner-a",
                    session_id="legacy-a",
                )
                # A restarted client may reuse the same textual session_id.  Session
                # equality therefore cannot inherit the active generation-fenced lease.
                for session_id in ("legacy-a", "legacy-b"):
                    with self.assertRaises(pma.ProjectMutationAuthorityError) as blocked:
                        with pma.compatibility_session_guard("p1", session_id=session_id):
                            pass
                    self.assertEqual(
                        blocked.exception.error_code, "PROJECT_MUTATION_AUTHORITY_REQUIRED"
                    )
                    self.assertIsNone(
                        blocked.exception.extra["current_lease"]["lease_id"]
                    )

    def test_lease_token_is_returned_once_hashed_at_rest_and_redacted_from_inspection(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-a042-secret-") as td:
            root = Path(td)
            with self._patched_project(root):
                acquired = pma.acquire_lease(
                    "p1", expected_generation=0, owner_id="owner-a", session_id="session-a"
                )
                token = str(acquired["lease_id"])
                self.assertTrue(token)
                inspected = pma.inspect_lease("p1")
                self.assertIsNone(inspected["lease_id"])
                persisted = json.loads(pma._state_path("p1").read_text(encoding="utf-8"))
                self.assertNotIn("lease_id", persisted)
                self.assertEqual(len(str(persisted["lease_id_hash"])), 64)
                self.assertNotIn(token, pma._state_path("p1").read_text(encoding="utf-8"))

    def test_state_lock_remains_available_for_renew_during_long_consequence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-a042-renew-") as td:
            root = Path(td)
            with self._patched_project(root):
                lease = pma.acquire_lease(
                    "p1", expected_generation=0, owner_id="owner-a", session_id="session-a"
                )
                args = dict(
                    project_id="p1",
                    lease_id=str(lease["lease_id"]),
                    generation=1,
                    owner_id="owner-a",
                    session_id="session-a",
                )
                with pma.mutation_guard(**args):
                    renewed = pma.renew_lease(**args, ttl_seconds=120)
                    self.assertEqual(renewed["generation"], 1)
                    self.assertEqual(renewed["status"], pma.LEASE_STATUS_ACTIVE)

    def test_runtime_bound_follow_on_may_finish_after_expiry_only_before_takeover(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-a042-followon-") as td:
            root = Path(td)
            clock = _Clock()
            with self._patched_project(root, clock):
                first = pma.acquire_lease(
                    "p1",
                    expected_generation=0,
                    owner_id="owner-a",
                    session_id="session-a",
                    ttl_seconds=10,
                )
                binding = {
                    "project_id": "p1",
                    "generation": 1,
                    "owner_id": "owner-a",
                    "session_id": "session-a",
                }
                clock.advance(11)
                with self.assertRaises(pma.ProjectMutationAuthorityError) as strict_expired:
                    with pma.runtime_bound_mutation_guard("p1", binding):
                        pass
                self.assertEqual(
                    strict_expired.exception.error_code, "PROJECT_MUTATION_LEASE_NOT_ACTIVE"
                )

                with pma.runtime_bound_mutation_guard(
                    "p1", binding, allow_expired_same_generation=True
                ) as receipt:
                    self.assertEqual(receipt["generation"], 1)
                    self.assertEqual(receipt["status"], pma.LEASE_STATUS_EXPIRED)

                second = pma.acquire_lease(
                    "p1",
                    expected_generation=1,
                    owner_id="owner-b",
                    session_id="session-b",
                )
                self.assertEqual(second["generation"], 2)
                with self.assertRaises(pma.ProjectMutationAuthorityError) as fenced:
                    with pma.runtime_bound_mutation_guard(
                        "p1", binding, allow_expired_same_generation=True
                    ):
                        pass
                self.assertEqual(fenced.exception.error_code, "PROJECT_MUTATION_LEASE_FENCED")

    def test_runtime_bound_worker_binding_is_fenced_after_takeover(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-a042-worker-fence-") as td:
            root = Path(td)
            with self._patched_project(root):
                first = pma.acquire_lease(
                    "p1", expected_generation=0, owner_id="owner-a", session_id="session-a"
                )
                binding = {
                    "project_id": "p1",
                    "generation": 1,
                    "owner_id": "owner-a",
                    "session_id": "session-a",
                }
                pma.release_lease(
                    "p1",
                    lease_id=str(first["lease_id"]),
                    generation=1,
                    owner_id="owner-a",
                    session_id="session-a",
                )
                pma.acquire_lease(
                    "p1", expected_generation=1, owner_id="owner-b", session_id="session-b"
                )
                with self.assertRaises(pma.ProjectMutationAuthorityError) as fenced:
                    with pma.runtime_bound_mutation_guard("p1", binding):
                        pass
                self.assertEqual(fenced.exception.error_code, "PROJECT_MUTATION_LEASE_FENCED")

    def test_cross_process_guard_is_released_when_holder_process_is_killed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-a042-crash-") as td:
            root = Path(td)
            code = r'''
import sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import project_mutation_authority as pma
root=Path(sys.argv[2])
pma.get_project_root=lambda project_id: root/project_id
pma.init_project_layout=lambda project_id: (root/project_id).mkdir(parents=True, exist_ok=True) or (root/project_id)
with pma._project_guard("p1", timeout_seconds=1.0):
    print("READY", flush=True)
    time.sleep(60)
'''
            child = subprocess.Popen(
                [sys.executable, "-c", code, str(RUNTIME_ROOT.parent), str(root)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                ready = child.stdout.readline().strip() if child.stdout else ""
                self.assertEqual(ready, "READY")
                child.kill()
                child.wait(timeout=5)
                with self._patched_project(root):
                    lease = pma.acquire_lease(
                        "p1",
                        expected_generation=0,
                        owner_id="owner-after-crash",
                        session_id="session-after-crash",
                    )
                self.assertEqual(lease["generation"], 1)
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=5)

    def test_simultaneous_process_clients_yield_exactly_one_generation_one_owner(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-a042-race-") as td:
            root = Path(td)
            gate = root / "GO"
            code = r'''
import json, sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import project_mutation_authority as pma
root=Path(sys.argv[2]); gate=Path(sys.argv[3]); owner=sys.argv[4]
pma.get_project_root=lambda project_id: root/project_id
pma.init_project_layout=lambda project_id: (root/project_id).mkdir(parents=True, exist_ok=True) or (root/project_id)
print("READY", flush=True)
while not gate.exists(): time.sleep(0.005)
try:
    row=pma.acquire_lease("p1", expected_generation=0, owner_id=owner, session_id=owner)
    print(json.dumps({"ok":True,"owner":owner,"generation":row["generation"],"lease_id":row["lease_id"]}), flush=True)
except pma.ProjectMutationAuthorityError as exc:
    print(json.dumps({"ok":False,"owner":owner,"error_code":exc.error_code}), flush=True)
'''
            children = [
                subprocess.Popen(
                    [
                        sys.executable,
                        "-c",
                        code,
                        str(RUNTIME_ROOT.parent),
                        str(root),
                        str(gate),
                        owner,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                for owner in ("tab-a", "tab-b")
            ]
            try:
                for child in children:
                    self.assertEqual(child.stdout.readline().strip(), "READY")
                gate.write_text("go", encoding="utf-8")
                results = []
                for child in children:
                    line = child.stdout.readline().strip()
                    child.wait(timeout=10)
                    results.append(json.loads(line))
                winners = [row for row in results if row["ok"]]
                losers = [row for row in results if not row["ok"]]
                self.assertEqual(len(winners), 1, results)
                self.assertEqual(winners[0]["generation"], 1)
                self.assertEqual(len(losers), 1, results)
                self.assertIn(
                    losers[0]["error_code"],
                    {"PROJECT_MUTATION_GENERATION_STALE", "PROJECT_MUTATION_LEASE_BUSY"},
                )
            finally:
                for child in children:
                    if child.poll() is None:
                        child.kill()
                        child.wait(timeout=5)

    def test_long_mutation_guard_holds_exclusion_past_lease_expiry_until_exit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-a042-long-") as td:
            root = Path(td)
            clock = _Clock()
            with self._patched_project(root, clock):
                lease = pma.acquire_lease(
                    "p1",
                    expected_generation=0,
                    owner_id="owner-a",
                    session_id="session-a",
                    ttl_seconds=10,
                )
                with pma.mutation_guard(
                    "p1",
                    lease_id=str(lease["lease_id"]),
                    generation=1,
                    owner_id="owner-a",
                    session_id="session-a",
                ):
                    clock.advance(20)
                    # Expiry does not revoke the already-held cross-process mutation
                    # exclusion mid-consequence.  No second guarded writer can enter
                    # until this context releases the file lock.
                    self.assertEqual(clock().timestamp(), (datetime(2026, 9, 6, 20, 0, tzinfo=timezone.utc) + timedelta(seconds=20)).timestamp())

                expired = pma.inspect_lease("p1")
                self.assertEqual(expired["status"], pma.LEASE_STATUS_EXPIRED)
                takeover = pma.acquire_lease(
                    "p1",
                    expected_generation=1,
                    owner_id="owner-b",
                    session_id="session-b",
                )
                self.assertEqual(takeover["generation"], 2)

    def test_distinct_projects_hold_leases_and_mutation_guards_concurrently(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-a042-multiproject-") as td:
            root = Path(td)
            with self._patched_project(root):
                leases = {
                    project_id: pma.acquire_lease(
                        project_id,
                        expected_generation=0,
                        owner_id=f"owner-{project_id}",
                        session_id=f"session-{project_id}",
                    )
                    for project_id in ("p1", "p2")
                }
                entered = {"p1": threading.Event(), "p2": threading.Event()}
                release = threading.Event()
                errors: list[BaseException] = []

                def worker(project_id: str) -> None:
                    try:
                        lease = leases[project_id]
                        with pma.mutation_guard(
                            project_id,
                            lease_id=str(lease["lease_id"]),
                            generation=1,
                            owner_id=f"owner-{project_id}",
                            session_id=f"session-{project_id}",
                            timeout_seconds=0.5,
                        ):
                            entered[project_id].set()
                            release.wait(timeout=2)
                    except BaseException as exc:  # pragma: no cover - surfaced below
                        errors.append(exc)

                threads = [threading.Thread(target=worker, args=(project_id,), daemon=True) for project_id in ("p1", "p2")]
                for thread in threads:
                    thread.start()
                self.assertTrue(entered["p1"].wait(timeout=1))
                self.assertTrue(entered["p2"].wait(timeout=1), "distinct projects must not serialize on a global mutation guard")
                self.assertTrue(pma.observe_lease("p1")["consequence_guard"]["active"])
                self.assertTrue(pma.observe_lease("p2")["consequence_guard"]["active"])
                release.set()
                for thread in threads:
                    thread.join(timeout=2)
                    self.assertFalse(thread.is_alive())
                self.assertEqual(errors, [])
                self.assertFalse(pma.observe_lease("p1")["consequence_guard"]["active"])
                self.assertFalse(pma.observe_lease("p2")["consequence_guard"]["active"])


if __name__ == "__main__":
    unittest.main()
