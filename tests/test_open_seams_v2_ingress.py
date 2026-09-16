from __future__ import annotations
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"baseline"/"pcmmad_receiver"
sys.path.insert(0,str(BASE))

def app(monkeypatch):
    monkeypatch.setenv("GITHOME_API_KEY","test-key")
    monkeypatch.setenv("PCMMAD_WORKLOAD_IDENTITY_MODE","optional")
    from app_factory import create_app
    obj=create_app();obj.config.update(TESTING=True)
    return obj

def headers(): return {"X-GitHome-Key":"test-key"}

def test_vnext_routes_recovered(monkeypatch):
    rules={r.rule for r in app(monkeypatch).url_map.iter_rules()}
    expected={"/lab/vnext/orient","/lab/vnext/invoke","/lab/batch","/lab/vnext/compose","/lab/vnext/execute","/lab/vnext/observe","/lab/vnext/resume","/lab/vnext/transfer"}
    assert expected.issubset(rules)

def test_current_orient_executes(monkeypatch):
    c=app(monkeypatch).test_client()
    r=c.post("/lab/vnext/orient",headers=headers(),json={"goal":"health status","include_mutating":False,"detail":"compact","max_capabilities":3,"ttl_seconds":60})
    assert r.status_code==200,r.get_data(as_text=True)
    body=r.get_json()
    assert body["ok"] is True
    assert body["schema"]=="pcmmad.schema-vnext.orient.v1"

def test_malformed_current_gets_shape(monkeypatch):
    c=app(monkeypatch).test_client()
    r=c.post("/lab/vnext/invoke",headers=headers(),json={"legacy_tool":"x"})
    assert r.status_code==400
    body=r.get_json()
    assert body["error_code"]=="INGRESS_CORRECTION"
    assert body["correction"]["operation_id"]=="invokeCapability"
    assert "capability" in body["correction"]["required"]

def test_malformed_flow_gets_shape(monkeypatch):
    c=app(monkeypatch).test_client()
    r=c.post("/lab/batch",headers=headers(),json={"legacy_steps":[]})
    assert r.status_code==400
    assert r.get_json()["error_code"]=="INGRESS_CORRECTION"

def test_legacy_gets_canonical_shape(monkeypatch):
    c=app(monkeypatch).test_client()
    r=c.post("/lab/orient",headers=headers(),json={})
    assert r.status_code==400
    body=r.get_json()
    assert body["classification"]=="RECOGNIZED_LEGACY_ROUTE"
    assert body["correction"]["canonical_path"]=="/lab/vnext/orient"

def test_wrong_method_gets_shape(monkeypatch):
    c=app(monkeypatch).test_client()
    r=c.get("/lab/vnext/orient",headers=headers())
    assert r.status_code==405
    assert r.get_json()["classification"]=="WRONG_METHOD"

def test_compose_uses_current_effect_profile(monkeypatch):
    c=app(monkeypatch).test_client()
    orient=c.post("/lab/vnext/orient",headers=headers(),json={"goal":"","include_mutating":False,"detail":"compact","max_capabilities":1,"ttl_seconds":60})
    assert orient.status_code==200
    body=orient.get_json()
    assert body["count"]>=1
    card=body["capabilities"][0]
    compose=c.post("/lab/vnext/compose",headers=headers(),json={"nodes":[{"id":"n1","capability":card["name"],"arguments":{},"expected_contract_digest":card["contract_digest"]}],"max_parallelism":1})
    assert compose.status_code==200,compose.get_data(as_text=True)
    assert compose.get_json()["ok"] is True

def test_self_admission_still_forbidden():
    from mvf_resident.governance import ResidentGovernance
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        with ResidentGovernance(Path(d)) as g:
            try:
                g.self_admit("x")
            except PermissionError as exc:
                assert "RESIDENT_SELF_QUALIFICATION_FORBIDDEN" in str(exc)
            else:
                raise AssertionError("self admission unexpectedly allowed")


def test_current_catalog_builds_closed_effect_profile():
    from lab_tools import list_tools
    from scheduler_effect_profile import build_profile
    cards={str(row.get("name")):dict(row) for row in list_tools()}
    profile=build_profile(cards)
    assert profile["capability_count"]==len(cards)
    assert {row["name"] for row in profile["entries"]}==set(cards)

def test_unknown_declared_effect_label_fails_closed_not_open():
    from scheduler_effect_profile import derive_entry
    card={
        "name":"future.read.reconcile",
        "side_effect_class":"read_reconcile",
        "contract_digest":"0"*64,
        "idempotency_semantics":"safe_repeat",
        "category":"execution",
        "mutating":False,
        "effective_approval_required":False,
    }
    row=derive_entry(card)
    assert row["declared_effect_kind"]=="UNVERIFIED"
    assert row["effect_kind"]=="UNVERIFIED"
    assert row["effect_truth_verified"] is False
    assert row["schedule_class"]=="SERIAL"
    assert row["resume_replay_class"]=="RECOMPOSE_REQUIRED"
    assert set(row["freshness_classes"])=={
        "CAPABILITY_CONTRACT","PROJECT_STATE","USER_CONTINUITY",
        "EXTERNAL_STATE","RUNTIME_STATE","RESULT_STATE"
    }
