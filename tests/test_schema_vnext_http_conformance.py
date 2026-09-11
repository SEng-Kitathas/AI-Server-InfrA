from __future__ import annotations

import json
import os
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "baseline"))

from pcmmad_receiver import approval_authority as aa
from pcmmad_receiver import execution_routes as er
from pcmmad_receiver import lab_tools
from pcmmad_receiver import lab_tools_execution as lte
from pcmmad_receiver.execution_routes import ExecutionRequestError
from pcmmad_receiver import shared_core
from pcmmad_receiver.app_factory import create_app


class SchemaVNextHttpConformanceTests(unittest.TestCase):
    def setUp(self) -> None:
        er._shutdown_scheduler()
        self.temp = tempfile.TemporaryDirectory(prefix="pcmmad-v11-http-")
        self.root = Path(self.temp.name)
        self.old_projects = shared_core.PROJECTS_ROOT
        shared_core.PROJECTS_ROOT = self.root / "projects"
        self.approval_patch = patch.object(aa, "SYSTEM_ROOT", self.root / "system")
        self.approval_patch.start()
        self.env_patch = patch.dict(
            os.environ,
            {
                "GITHOME_API_KEY": "v11-http-test-key",
                "PCMMAD_LAB_POLICY_MODE": "strict",
                "PCMMAD_ALLOW_LEGACY_INLINE_APPROVAL": "0",
                "PCMMAD_ACCESS_LOG": "1",
            },
            clear=False,
        )
        self.env_patch.start()
        self.app = create_app()
        self.client = self.app.test_client()
        self.headers = {"X-GitHome-Key": "v11-http-test-key"}

    def tearDown(self) -> None:
        er._shutdown_scheduler()
        self.env_patch.stop()
        self.approval_patch.stop()
        shared_core.PROJECTS_ROOT = self.old_projects
        self.temp.cleanup()

    def post(self, path: str, payload: object):
        return self.client.post(path, json=payload, headers=self.headers)

    def test_malformed_json_is_receiver_json_error_envelope(self) -> None:
        response = self.client.post(
            "/lab/vnext/orient",
            data=b"{broken",
            content_type="application/json",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.get_json()["error_code"], "BAD_JSON")

    def test_non_json_media_type_is_rejected_before_parse(self) -> None:
        response = self.client.post(
            "/lab/vnext/orient",
            data=b'{"goal":"x"}',
            content_type="text/plain",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 415)
        self.assertEqual(response.get_json()["error_code"], "UNSUPPORTED_MEDIA_TYPE")

    def test_request_body_ceiling_rejects_before_schema_walk(self) -> None:
        response = self.client.post(
            "/lab/vnext/orient",
            data=b'{"goal":"' + (b"x" * (1024 * 1024)) + b'"}',
            content_type="application/json",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.get_json()["error_code"], "REQUEST_TOO_LARGE")

    def test_top_level_additional_properties_rejected(self) -> None:
        response = self.post(
            "/lab/vnext/orient",
            {"capabilities": ["project.mutation.inspect"], "evil": 1},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error_code"], "BAD_REQUEST")
        self.assertIn("unknown fields: evil", response.get_json()["message"])

    def test_nested_plan_node_additional_properties_rejected_through_ref(self) -> None:
        response = self.post(
            "/lab/vnext/compose",
            {
                "project_id": "p",
                "nodes": [
                    {
                        "id": "a",
                        "capability": "project.mutation.inspect",
                        "arguments": {"project_id": "p"},
                        "evil": 1,
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error_code"], "BAD_REQUEST")
        self.assertIn("payload.nodes[0]", response.get_json()["message"])

    def test_orient_max_items_and_max_length_are_enforced(self) -> None:
        too_many = self.post(
            "/lab/vnext/orient",
            {"capabilities": ["project.mutation.inspect"] * 25},
        )
        self.assertEqual(too_many.status_code, 400)
        self.assertIn("at most 24", too_many.get_json()["message"])
        too_long = self.post("/lab/vnext/orient", {"goal": "x" * 2001})
        self.assertEqual(too_long.status_code, 400)
        self.assertIn("at most 2000", too_long.get_json()["message"])

    def test_pattern_is_enforced_for_expected_contract_digest(self) -> None:
        response = self.post(
            "/lab/vnext/invoke",
            {
                "capability": "project.mutation.inspect",
                "arguments": {"project_id": "p"},
                "expected_contract_digest": "g" * 64,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error_code"], "BAD_REQUEST")
        self.assertIn("pattern", response.get_json()["message"])

    def test_schema_valued_additional_properties_validate_authority_map(self) -> None:
        composed = self.post(
            "/lab/vnext/compose",
            {
                "project_id": "p",
                "nodes": [
                    {
                        "id": "a",
                        "capability": "project.mutation.inspect",
                        "arguments": {"project_id": "p"},
                    }
                ],
            },
        ).get_json()
        plan = composed["plan"]
        response = self.post(
            "/lab/vnext/execute",
            {
                "project_id": "p",
                "plan": plan,
                "expected_plan_digest": plan["plan_digest"],
                "authorities": {"a": {"permit": True, "evil": 1}},
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error_code"], "BAD_REQUEST")
        self.assertIn("evil", response.get_json()["message"])

    def test_native_union_type_is_enforced_through_v11_invoke(self) -> None:
        # Native argument-schema validation is controlled by the native router's
        # strict validation mode; v11 must preserve that contract rather than
        # silently inventing a second validation authority.
        with patch.dict(os.environ, {"PCMMAD_TOOL_VALIDATION_MODE": "strict"}, clear=False):
            orient = self.post(
                "/lab/vnext/orient",
                {"capabilities": ["continuity.ingress.rehydrate"]},
            )
            self.assertEqual(orient.status_code, 200)
            card = orient.get_json()["capabilities"][0]
            response = self.post(
                "/lab/vnext/invoke",
                {
                    "capability": "continuity.ingress.rehydrate",
                    "arguments": {
                        "project_id": "p",
                        "topic": "x",
                        "session_mode": "NONUSER_NONRESEARCH_AUTOMATION",
                        "ucm_profile_id": {"not": "a string or null"},
                    },
                    "expected_contract_digest": card["contract_digest"],
                },
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error_code"], "BAD_REQUEST")
        self.assertIn("declared types", response.get_json()["message"])

    def test_invalid_transfer_ticket_preserves_not_found_semantics(self) -> None:
        response = self.post(
            "/lab/vnext/transfer",
            {"action": "meta", "arguments": {"ticket": "missing"}},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error_code"], "NOT_FOUND")

    def _approved_invoke(self, capability: str, arguments: dict, *, patches=()):
        orient = self.post("/lab/vnext/orient", {"capabilities": [capability]})
        self.assertEqual(orient.status_code, 200)
        card = orient.get_json()["capabilities"][0]
        first = self.post(
            "/lab/vnext/invoke",
            {"capability": capability, "arguments": arguments, "expected_contract_digest": card["contract_digest"]},
        )
        self.assertEqual(first.status_code, 403)
        challenge = first.get_json()["approval_challenge"]
        authority = {"approval_handle": challenge["handle"], "permit": True, "operator_id": "warfort-http"}
        stack = []
        try:
            for cm in patches:
                stack.append(cm); cm.__enter__()
            return self.post(
                "/lab/vnext/invoke",
                {"capability": capability, "arguments": arguments, "authority": authority, "expected_contract_digest": card["contract_digest"]},
            )
        finally:
            for cm in reversed(stack): cm.__exit__(None, None, None)

    def test_execution_submit_without_project_authority_fails_before_enqueue(self) -> None:
        arguments = {"project_id": "p", "command": ["python", "-c", "print('x')"], "idempotency_key": "no-authority"}
        with patch.object(lab_tools, "submit_execution_job") as submit:
            response = self._approved_invoke("execution.submit", arguments)
        self.assertEqual(response.status_code, 423)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.get_json()["error_code"], "PROJECT_MUTATION_AUTHORITY_REQUIRED")
        submit.assert_not_called()

    def test_execution_idempotency_conflict_is_structured_409_not_raw_500(self) -> None:
        arguments = {"project_id": "p", "command": ["python", "-c", "print('different')"], "idempotency_key": "same-key"}
        authority = {"project_id": "p", "mode": "lease", "generation": 1, "owner_id": "owner", "lease_id": "lease"}
        conflict = ExecutionRequestError(
            "IDEMPOTENCY_KEY_CONFLICT",
            "idempotency_key already used for a different execution payload",
            409,
            existing_job_id="job-existing",
        )
        response = self._approved_invoke(
            "execution.submit",
            arguments,
            patches=(
                patch.object(lte, "current_project_mutation_authority", return_value=authority),
                patch.object(lte, "submission_mutation_binding", return_value=nullcontext()),
                patch.object(lab_tools, "submit_execution_job", side_effect=conflict),
            ),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.content_type, "application/json")
        body = response.get_json()
        self.assertEqual(body["error_code"], "IDEMPOTENCY_KEY_CONFLICT")
        self.assertEqual(body["existing_job_id"], "job-existing")
        self.assertNotIn("Internal Server Error", response.get_data(as_text=True))

    def test_real_orient_and_invoke_still_work(self) -> None:
        orient = self.post(
            "/lab/vnext/orient",
            {"project_id": "p", "capabilities": ["project.mutation.inspect"]},
        )
        self.assertEqual(orient.status_code, 200)
        lease = orient.get_json()["lease"]
        invoked = self.post(
            "/lab/vnext/invoke",
            {
                "capability": "project.mutation.inspect",
                "arguments": {"project_id": "p"},
                "lease": lease,
            },
        )
        self.assertEqual(invoked.status_code, 200)
        self.assertEqual(invoked.get_json()["result"]["status"], "UNOWNED")


if __name__ == "__main__":
    unittest.main()
