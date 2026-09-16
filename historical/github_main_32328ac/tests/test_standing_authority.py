from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

from pcmmad_receiver import approval_authority as aa
from pcmmad_receiver import standing_authority as sa
from pcmmad_receiver.lab_policy import evaluate_tool_call
from pcmmad_receiver.control_plane_models import ToolSpec


def spec(name: str = "execution.run", *, category: str = "execution", danger: str = "high", approval: bool = True, mutating: bool = False, effects=None) -> ToolSpec:
    return ToolSpec(
        name=name, description="test", category=category, danger_tier=danger,
        approval_required=approval, mutating=mutating,
        input_schema={"type":"object"}, output_schema={"type":"object"},
        side_effect_class="execution", effect_traits=list(effects or ["executes_code"]),
    )


class StandingAuthorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.p1 = patch.object(sa, "SYSTEM_ROOT", self.root)
        self.p2 = patch.object(aa, "SYSTEM_ROOT", self.root)
        self.p1.start(); self.p2.start()

    def tearDown(self) -> None:
        self.p2.stop(); self.p1.stop(); self.temp.cleanup()

    def test_standing_mode_allows_static_high_risk_without_challenge(self) -> None:
        sa.save_profile({"project_id":"P","mode":"standing"})
        d=evaluate_tool_call(spec(), {"project_id":"P"}, {})
        self.assertTrue(d.allowed)
        self.assertEqual(d.mode, "operator")
        self.assertEqual(d.approval_mode, "standing_authority")

    def test_universal_standing_profile_applies_when_project_has_no_profile(self) -> None:
        sa.save_profile({"project_id":sa.UNIVERSAL_PROJECT_ID,"mode":"standing"})
        d=evaluate_tool_call(spec(), {"project_id":"UNSEEN-PROJECT"}, {})
        self.assertTrue(d.allowed)
        self.assertEqual(d.approval_mode, "standing_authority")
        self.assertEqual(d.details["standing_authority"]["scope"], "universal")
        self.assertEqual(d.details["standing_authority"]["profile_project_id"], sa.UNIVERSAL_PROJECT_ID)

    def test_project_profile_overrides_universal_profile(self) -> None:
        sa.save_profile({"project_id":sa.UNIVERSAL_PROJECT_ID,"mode":"standing"})
        sa.save_profile({"project_id":"P","mode":"hitl"})
        d=evaluate_tool_call(spec(), {"project_id":"P"}, {})
        self.assertFalse(d.allowed)
        self.assertEqual(d.error_code, "APPROVAL_REQUIRED")
        self.assertEqual(d.details["standing_authority"]["scope"], "project")
        self.assertEqual(d.details["standing_authority"]["profile_project_id"], "P")

    def test_hitl_selector_overrides_standing_default_allow(self) -> None:
        sa.save_profile({"project_id":"P","mode":"standing","ask":{"capabilities":["execution.terminate"]}})
        d=evaluate_tool_call(spec("execution.terminate", danger="critical"), {"project_id":"P","job_id":"fake"}, {})
        self.assertFalse(d.allowed)
        self.assertEqual(d.error_code, "APPROVAL_REQUIRED")
        self.assertEqual(d.details["standing_authority"]["matched"]["pattern"], "execution.terminate")
        self.assertTrue(d.approval_handle.startswith("apr-"))

    def test_deny_wins_over_hitl_and_allow(self) -> None:
        sa.save_profile({"project_id":"P","mode":"standing","allow":{"capabilities":["git.*"]},"ask":{"capabilities":["git.push"]},"deny":{"capabilities":["git.push"]}})
        d=evaluate_tool_call(spec("git.push", category="git"), {"project_id":"P"}, {})
        self.assertFalse(d.allowed)
        self.assertEqual(d.error_code, "OPERATOR_POLICY_DENIED")
        self.assertEqual(d.details["standing_authority"]["action"], "deny")

    def test_hitl_mode_asks_by_default_even_when_server_metadata_is_low_risk(self) -> None:
        sa.save_profile({"project_id":"P","mode":"hitl"})
        d=evaluate_tool_call(spec("project.files.read", category="project", danger="low", approval=False), {"project_id":"P"}, {})
        self.assertFalse(d.allowed)
        self.assertEqual(d.error_code, "APPROVAL_REQUIRED")

    def test_no_profile_preserves_existing_strict_server_policy(self) -> None:
        d=evaluate_tool_call(spec(), {"project_id":"P"}, {})
        self.assertFalse(d.allowed)
        self.assertEqual(d.mode, "strict")
        self.assertEqual(d.error_code, "APPROVAL_REQUIRED")

    def test_profile_round_trip_and_selector_prefixes(self) -> None:
        saved=sa.save_profile({"project_id":"P","mode":"custom","default_action":"allow","ask":{"categories":["git"],"effect_traits":["durable_mutation"],"danger_tiers":["critical"]}})
        loaded=sa.load_profile("P")
        self.assertEqual(loaded["mode"], "custom")
        self.assertEqual(loaded["ask"]["categories"], ["git"])
        self.assertEqual(sa.resolve(spec("x",category="git",danger="low",approval=False,effects=[]), {"project_id":"P"})["action"], "ask")
        self.assertTrue(sa.delete_profile("P"))
        self.assertIsNone(sa.load_profile("P"))


    def test_universal_profile_applies_to_projects_without_specific_profile(self) -> None:
        sa.save_profile({"project_id":sa.UNIVERSAL_PROJECT_ID,"mode":"standing"})
        for project_id in ("P","OTHER"):
            d=evaluate_tool_call(spec(), {"project_id":project_id}, {})
            self.assertTrue(d.allowed)
            self.assertEqual(d.approval_mode, "standing_authority")
            self.assertEqual(d.details["standing_authority"]["scope"], "universal")
            self.assertEqual(d.details["standing_authority"]["profile_project_id"], sa.UNIVERSAL_PROJECT_ID)

    def test_project_profile_overrides_universal_profile(self) -> None:
        sa.save_profile({"project_id":sa.UNIVERSAL_PROJECT_ID,"mode":"standing"})
        sa.save_profile({"project_id":"P","mode":"hitl"})
        d=evaluate_tool_call(spec(), {"project_id":"P"}, {})
        self.assertFalse(d.allowed)
        self.assertEqual(d.error_code, "APPROVAL_REQUIRED")
        self.assertEqual(d.details["standing_authority"]["scope"], "project")
        other=evaluate_tool_call(spec(), {"project_id":"OTHER"}, {})
        self.assertTrue(other.allowed)
        self.assertEqual(other.details["standing_authority"]["scope"], "universal")

    def test_universal_profile_does_not_apply_to_unscoped_calls(self) -> None:
        sa.save_profile({"project_id":sa.UNIVERSAL_PROJECT_ID,"mode":"standing"})
        d=evaluate_tool_call(spec(), {}, {})
        self.assertFalse(d.allowed)
        self.assertEqual(d.error_code, "APPROVAL_REQUIRED")

    def test_allow_all_suppresses_ask_but_preserves_explicit_deny(self):
        sa.save_profile({'project_id':'P','mode':'allow_all','ask':{'capabilities':['execution.*']},'deny':{'capabilities':['execution.terminate']}})
        run=evaluate_tool_call(spec('execution.run',mutating=True,approval=True),{'project_id':'P'}, {})
        self.assertTrue(run.allowed);self.assertEqual(run.approval_mode,'standing_authority');self.assertEqual(run.details['standing_authority']['mode'],'allow_all')
        term=evaluate_tool_call(spec('execution.terminate',mutating=True,approval=True),{'project_id':'P'}, {})
        self.assertFalse(term.allowed);self.assertEqual(term.error_code,'OPERATOR_POLICY_DENIED')

    def test_universal_allow_all_applies_when_project_profile_absent(self):
        sa.save_profile({'project_id':sa.UNIVERSAL_PROJECT_ID,'mode':'allow_all'})
        d=evaluate_tool_call(spec('execution.run',mutating=True,approval=True),{'project_id':'OTHER'}, {})
        self.assertTrue(d.allowed);self.assertEqual(d.details['standing_authority']['scope'],'universal');self.assertEqual(d.details['standing_authority']['mode'],'allow_all')

if __name__ == "__main__":
    unittest.main()
