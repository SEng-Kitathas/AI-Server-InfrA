from __future__ import annotations

import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

import lab_tools
import project_mutation_authority as pma
from control_plane_models import ToolSpec


class ProjectMutationChokepointTests(unittest.TestCase):
    def test_native_dispatch_rejects_project_authority_smuggled_in_payload(self) -> None:
        with self.assertRaises(lab_tools.LabToolError) as caught:
            lab_tools.dispatch_tool(
                "lab.capabilities.availability",
                {
                    "tool_names": ["git.status"],
                    "mutation_authority": {
                        "lease_id": "not-authority",
                        "generation": 1,
                        "owner_id": "attacker",
                    },
                },
            )
        self.assertEqual(caught.exception.error_code, "AUTHORITY_IN_CAPABILITY_PAYLOAD")
        self.assertEqual(caught.exception.status, 400)

    def test_canonical_dispatch_consumes_bound_session_from_authority_envelope(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-a042-dispatch-") as td:
            root = Path(td)
            with ExitStack() as stack:
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
                lease = pma.acquire_lease(
                    "p1", expected_generation=0, owner_id="owner-a", session_id="session-a"
                )
                calls: list[dict] = []
                spec = ToolSpec(
                    name="test.project.mutation.fenced",
                    description="A-042 canonical dispatch fence probe",
                    danger_tier="low",
                    category="test",
                    mutating=False,
                    input_schema={
                        "type": "object",
                        "properties": {"project_id": {"type": "string"}},
                        "required": ["project_id"],
                        "additionalProperties": False,
                    },
                    output_schema={"type": "object"},
                    side_effect_class="read",
                    effect_traits=["project_mutation_fenced"],
                    handler=lambda payload: calls.append(dict(payload)) or {"ok": True},
                )
                old = lab_tools._TOOL_REGISTRY.get(spec.name)
                lab_tools._TOOL_REGISTRY[spec.name] = spec
                try:
                    result = lab_tools.dispatch_tool(
                        spec.name,
                        {"project_id": "p1"},
                        authority={
                            "project_mutation": {
                                "lease_id": lease["lease_id"],
                                "generation": lease["generation"],
                                "owner_id": "owner-a",
                                "session_id": "session-a",
                            }
                        },
                    )
                    self.assertTrue(result["ok"])
                    self.assertEqual(calls, [{"project_id": "p1"}])
                finally:
                    if old is None:
                        lab_tools._TOOL_REGISTRY.pop(spec.name, None)
                    else:
                        lab_tools._TOOL_REGISTRY[spec.name] = old

    def test_project_backed_native_mutators_have_one_of_the_authoritative_fences(self) -> None:
        rows = {row["name"]: row for row in lab_tools.list_tools()}
        centrally_fenced = {
            "git.commit", "git.reset_hard", "git.clean",
            "project.files.write", "project.archives.extract",
            "protocol.initialize", "protocol.mode.transition", "protocol.objective.set",
            "protocol.claim.record", "protocol.constraint.record", "protocol.waiver.record",
            "protocol.artifact.register", "protocol.continuity.record", "protocol.promotion.record",
            "verify.gates", "execution.run", "python.run",
            "lab.session.start", "lab.session.note", "lab.session.end",
            "lab.andon.pull", "lab.reflexion.append",
            "sop.package.register", "sop.ingest.reset", "sop.ingest.next_chunk",
            "sop.ingest.ack_chunk", "sop.ingest.complete_file",
        }
        for name in centrally_fenced:
            self.assertIn(name, rows)
            self.assertIn("project_mutation_fenced", rows[name]["effect_traits"], name)

        submit_traits = rows["execution.submit"]["effect_traits"]
        self.assertIn("mutation_authority_validated_before_enqueue", submit_traits)
        self.assertIn("requires_explicit_project_mutation_authority", submit_traits)
        self.assertNotIn("project_mutation_fenced", submit_traits)

        path_fenced = {
            "fs.write", "fs.move", "transfer.import.create",
            "transfer.chunk.write", "transfer.import.finalize",
        }
        for name in path_fenced:
            self.assertIn("path_project_mutation_fenced", rows[name]["effect_traits"], name)

        apoptosis = rows["lab.apoptosis.trigger"]["effect_traits"]
        self.assertIn("two_phase_project_mutation_fenced", apoptosis)
        self.assertNotIn("project_mutation_fenced", apoptosis)

    def test_authority_lifecycle_tools_are_not_recursively_fenced_by_the_lease_they_manage(self) -> None:
        rows = {row["name"]: row for row in lab_tools.list_tools()}
        for name in (
            "project.mutation.inspect", "project.mutation.acquire",
            "project.mutation.renew", "project.mutation.release",
        ):
            self.assertNotIn("project_mutation_fenced", rows[name]["effect_traits"], name)


if __name__ == "__main__":
    unittest.main()
