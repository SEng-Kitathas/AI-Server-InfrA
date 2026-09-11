from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "baseline"))

from pcmmad_receiver import approval_authority as aa
from pcmmad_receiver import lab_tools
from pcmmad_receiver.control_plane_models import ToolSpec
from pcmmad_receiver.project_mutation_authority import ProjectMutationAuthorityError


class DispatchAuthorityOrderingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root_patch = patch.object(aa, "SYSTEM_ROOT", Path(self.temp.name))
        self.root_patch.start()
        self.env_patch = patch.dict(os.environ, {"PCMMAD_LAB_POLICY_MODE": "strict"}, clear=False)
        self.env_patch.start()
        self.original_registry = dict(lab_tools._TOOL_REGISTRY)
        self.calls: list[dict] = []
        def handler(payload):
            self.calls.append(dict(payload))
            return {"received": dict(payload)}
        lab_tools._TOOL_REGISTRY["test.fenced"] = ToolSpec(
            name="test.fenced", description="approval/project-authority ordering test",
            danger_tier="high", category="test", approval_required=True, mutating=True,
            capability_version="1",
            input_schema={"type":"object","properties":{"project_id":{"type":"string"},"value":{"type":"integer"}},"required":["project_id"],"additionalProperties":False},
            output_schema={"type":"object"}, side_effect_class="mutation",
            effect_traits=["project_mutation_fenced","durable_mutation"], handler=handler)
    def tearDown(self) -> None:
        lab_tools._TOOL_REGISTRY.clear(); lab_tools._TOOL_REGISTRY.update(self.original_registry)
        self.env_patch.stop(); self.root_patch.stop(); self.temp.cleanup()
    def test_stale_project_authority_fails_before_single_use_approval_consumption(self) -> None:
        args={"project_id":"alpha","value":1}
        with self.assertRaises(lab_tools.LabToolError) as missing:
            lab_tools.dispatch_tool("test.fenced",args)
        self.assertEqual(missing.exception.error_code,"APPROVAL_REQUIRED")
        challenge=missing.exception.extra["approval_challenge"]
        self.assertEqual(aa.inspect_challenge(challenge["handle"])["status"],"ACTIVE")
        stale=ProjectMutationAuthorityError("PROJECT_MUTATION_LEASE_NOT_ACTIVE","project has no active mutation lease",423,extra={"current_lease":{"status":"EXPIRED","generation":1}})
        with patch.object(lab_tools,"validate_consequence_authority",side_effect=stale):
            with self.assertRaises(lab_tools.LabToolError) as caught:
                lab_tools.dispatch_tool("test.fenced",args,authority={"approval_handle":challenge["handle"],"permit":True,"project_mutation":{"lease_id":"stale","generation":1,"owner_id":"owner"}})
        self.assertEqual(caught.exception.error_code,"PROJECT_MUTATION_LEASE_NOT_ACTIVE")
        self.assertEqual(caught.exception.status,423)
        self.assertEqual(self.calls,[])
        self.assertEqual(aa.inspect_challenge(challenge["handle"])["status"],"ACTIVE")

if __name__ == "__main__": unittest.main()
