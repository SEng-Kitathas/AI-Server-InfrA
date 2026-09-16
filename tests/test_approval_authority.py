from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT))

import approval_authority as aa
from control_plane_models import ToolSpec


def spec(name: str = "service.restart", version: str = "1", schema_version: str = "1") -> ToolSpec:
    return ToolSpec(
        name=name,
        description="test",
        danger_tier="high",
        approval_required=True,
        capability_version=version,
        schema_version=schema_version,
        input_schema={"type": "object", "properties": {"target": {"type": "string"}}},
        output_schema={"type": "object"},
        side_effect_class="mutation",
        effect_traits=["service_control"],
    )


class ApprovalAuthorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root_patch = patch.object(aa, "SYSTEM_ROOT", Path(self.temp.name))
        self.root_patch.start()

    def tearDown(self) -> None:
        self.root_patch.stop()
        self.temp.cleanup()

    def test_exact_binding_consumes_single_use_challenge(self) -> None:
        s = spec()
        args = {"target": "service:A", "force": False}
        challenge = aa.create_challenge(s, args)
        consumed = aa.validate_and_consume(
            challenge["handle"], s, args, permit=True, operator_id="operator", provenance="hud"
        )
        self.assertEqual(consumed["status"], aa.APPROVAL_STATUS_CONSUMED)
        self.assertEqual(consumed["target"], {"target": "service:A"})
        self.assertEqual(consumed["consumer"]["operator_id"], "operator")

    def test_changed_arguments_or_target_are_rejected_without_consuming(self) -> None:
        s = spec()
        challenge = aa.create_challenge(s, {"target": "service:A", "force": False})
        with self.assertRaises(aa.ApprovalAuthorityError) as caught:
            aa.validate_and_consume(
                challenge["handle"], s, {"target": "service:B", "force": False}, permit=True
            )
        self.assertEqual(caught.exception.error_code, "APPROVAL_ARGUMENTS_MISMATCH")
        self.assertEqual(aa.inspect_challenge(challenge["handle"])["status"], aa.APPROVAL_STATUS_ACTIVE)

    def test_different_capability_is_rejected(self) -> None:
        challenge = aa.create_challenge(spec("service.restart"), {"target": "service:A"})
        with self.assertRaises(aa.ApprovalAuthorityError) as caught:
            aa.validate_and_consume(
                challenge["handle"], spec("fs.write"), {"target": "service:A"}, permit=True
            )
        self.assertEqual(caught.exception.error_code, "APPROVAL_CAPABILITY_MISMATCH")

    def test_contract_drift_is_rejected(self) -> None:
        original = spec(version="1")
        challenge = aa.create_challenge(original, {"target": "service:A"})
        changed = spec(version="2")
        with self.assertRaises(aa.ApprovalAuthorityError) as caught:
            aa.validate_and_consume(challenge["handle"], changed, {"target": "service:A"}, permit=True)
        self.assertEqual(caught.exception.error_code, "APPROVAL_CONTRACT_STALE")

    def test_replay_is_rejected(self) -> None:
        s = spec()
        args = {"target": "service:A"}
        challenge = aa.create_challenge(s, args)
        aa.validate_and_consume(challenge["handle"], s, args, permit=True)
        with self.assertRaises(aa.ApprovalAuthorityError) as caught:
            aa.validate_and_consume(challenge["handle"], s, args, permit=True)
        self.assertEqual(caught.exception.error_code, "APPROVAL_ALREADY_CONSUMED")

    def test_handle_alone_does_not_authorize(self) -> None:
        s = spec()
        args = {"target": "service:A"}
        challenge = aa.create_challenge(s, args)
        with self.assertRaises(aa.ApprovalAuthorityError) as caught:
            aa.validate_and_consume(challenge["handle"], s, args, permit=False)
        self.assertEqual(caught.exception.error_code, "APPROVAL_CONFIRMATION_REQUIRED")

    def test_expired_challenge_is_rejected_and_marked_expired(self) -> None:
        s = spec()
        args = {"target": "service:A"}
        challenge = aa.create_challenge(s, args, ttl_seconds=30)
        future = datetime.now(timezone.utc) + timedelta(minutes=2)
        with patch.object(aa, "_now", return_value=future):
            with self.assertRaises(aa.ApprovalAuthorityError) as caught:
                aa.validate_and_consume(challenge["handle"], s, args, permit=True)
        self.assertEqual(caught.exception.error_code, "APPROVAL_EXPIRED")
        self.assertEqual(aa.inspect_challenge(challenge["handle"])["status"], aa.APPROVAL_STATUS_EXPIRED)

    def test_tampered_record_fails_integrity(self) -> None:
        s = spec()
        challenge = aa.create_challenge(s, {"target": "service:A"})
        path = aa._path(challenge["handle"])
        row = json.loads(path.read_text(encoding="utf-8"))
        row["arguments_digest"] = "0" * 64
        path.write_text(json.dumps(row), encoding="utf-8")
        with self.assertRaises(aa.ApprovalAuthorityError) as caught:
            aa.inspect_challenge(challenge["handle"])
        self.assertEqual(caught.exception.error_code, "APPROVAL_INTEGRITY_INVALID")


if __name__ == "__main__":
    unittest.main()
