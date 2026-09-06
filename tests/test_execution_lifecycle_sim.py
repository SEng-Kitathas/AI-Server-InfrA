from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.hostile.execution_lifecycle_sim import (
    DeterministicExecutionLifecycleSim,
    SimulationInvariantError,
    discover_failure,
    run_seed,
)


class ExecutionLifecycleSimulationTests(unittest.TestCase):
    def test_current_seed_replays_byte_identical_result(self) -> None:
        first = run_seed(7, 25, scheduler_variant="current")
        second = run_seed(7, 25, scheduler_variant="current")
        self.assertEqual(first, second)
        self.assertEqual(first["seed"], 7)
        self.assertEqual(first["scheduler_variant"], "current")

    def test_bounded_search_rediscovers_pre_a034_and_exactly_replays_failure(self) -> None:
        found = discover_failure(
            scheduler_variant="pre_a034", seed_limit=5, steps=10
        )
        self.assertIsNotNone(found)
        assert found is not None
        self.assertEqual(found["seed"], 0)
        self.assertIn("tick_reconcile_fault", found["failure"])
        self.assertIn("PermissionError", found["failure"])
        self.assertIn("A038_REPLAY_SEED=0", found["failure"])
        self.assertIn('"drain_calls":0', found["failure"])

        failures: list[str] = []
        for _ in range(2):
            with self.assertRaises(SimulationInvariantError) as ctx:
                run_seed(0, 10, scheduler_variant="pre_a034")
            failures.append(str(ctx.exception))
        self.assertEqual(failures[0], failures[1])

    def test_same_seed_schedule_survives_current_scheduler_isolation(self) -> None:
        result = run_seed(0, 40, scheduler_variant="current")
        self.assertEqual(result["seed"], 0)
        self.assertGreaterEqual(result["reconcile_faults"], 1)
        self.assertGreaterEqual(result["final_state"]["drain_calls"], 1)
        self.assertEqual(
            result["final_state"]["telemetry"]["jobs_reconcile_errors"],
            result["reconcile_faults"],
        )

    def test_small_seed_campaign_preserves_current_structural_invariants(self) -> None:
        for seed in range(10):
            with self.subTest(seed=seed):
                result = run_seed(seed, 20, scheduler_variant="current")
                active_ids = {row[0] for row in result["final_state"]["active"]}
                terminal_ids = {row[0] for row in result["final_state"]["terminal"]}
                self.assertFalse(active_ids & terminal_ids)

    def test_invalid_scheduler_variant_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "scheduler_variant"):
            DeterministicExecutionLifecycleSim(1, scheduler_variant="unknown")


if __name__ == "__main__":
    unittest.main()
