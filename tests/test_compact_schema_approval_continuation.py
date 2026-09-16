from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "baseline" / "pcmmad_receiver" / "pcmmad_lab_action_schema_v10_3_pcmmad_native_protocol_compact_30_router.json"

def test_dispatch_schema_exposes_safe_approval_continuation_contract():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    dispatch = schema["paths"]["/lab/dispatch"]["post"]
    req = schema["components"]["schemas"]["LabDispatchRequest"]
    assert "authority" in req["properties"]
    assert "expected_contract_digest" in req["properties"]
    error = schema["components"]["schemas"]["ErrorEnvelope"]
    assert error["additionalProperties"] is True
    assert error["properties"]["approval_challenge"]["$ref"].endswith("/ApprovalChallenge")
    assert error["properties"]["continuation"]["$ref"].endswith("/ApprovalContinuation")
    cont = schema["components"]["schemas"]["ApprovalContinuation"]
    assert cont["properties"]["kind"]["enum"] == ["resubmit_exact_tool_call"]
    auth = cont["properties"]["authority_template"]
    assert auth["properties"]["permit"]["enum"] == [False]
    assert cont["properties"]["permit_must_be_set_true_by_approver"]["enum"] == [True]
    assert cont["properties"]["single_use"]["enum"] == [True]
    assert "non-authorizing" in dispatch["description"]
    assert "expected_contract_digest" in dispatch["description"]
