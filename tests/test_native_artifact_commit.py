from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"baseline"/"pcmmad_receiver"
if str(BASE) not in sys.path: sys.path.insert(0,str(BASE))

import shared_core

def payload(content, *, operation="create", previous=None, key="idem-1", commit="commit-1"):
    row={"project_id":"TXTEST","artifact_class":"continuity.live_shadow","logical_name":"LIVE_SHADOW.md","operation":operation,"content":content,"session_id":"s","commit_id":commit,"idempotency_key":key}
    if previous is not None: row["expected_previous_sha256"]=previous
    return row

def test_transaction_updates_file_manifest_ledger_and_replays(monkeypatch,tmp_path):
    monkeypatch.setattr(shared_core,"PROJECTS_ROOT",tmp_path)
    import legacy_routes as legacy
    first=legacy.commit_artifact_transaction(payload("one\n"),acquire_guard=False)
    assert first["ok"] is True and first["replayed"] is False
    project=tmp_path/"TXTEST"; target=project/"continuity"/"live_shadow"/"LIVE_SHADOW.md"
    assert target.read_text(encoding="utf-8")=="one\n"
    manifest=json.loads((project/"system"/"manifest"/"manifest.json").read_text(encoding="utf-8"))
    rel=first["path"]
    assert manifest["files"][rel]["sha256"]==first["sha256"]
    ledger=(project/"system"/"ledger"/"commits.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(ledger)==1
    replay=legacy.commit_artifact_transaction(payload("one\n"),acquire_guard=False)
    assert replay["replayed"] is True
    second=legacy.commit_artifact_transaction(payload("two\n",operation="update",previous=first["sha256"],key="idem-2",commit="commit-2"),acquire_guard=False)
    assert second["replayed"] is False and target.read_text(encoding="utf-8")=="two\n"
    assert len((project/"system"/"ledger"/"commits.jsonl").read_text(encoding="utf-8").splitlines())==2

def test_native_capability_registered_and_legacy_route_delegates():
    import lab_tools
    assert "project.artifact.commit" in {row["name"] for row in lab_tools.list_tools()}
    src=(Path(__file__).resolve().parents[1]/"baseline"/"pcmmad_receiver"/"legacy_routes.py").read_text(encoding="utf-8")
    tail=src[src.index('@legacy_bp.post("/commit")'):]
    assert "commit_artifact_transaction" in tail
    assert "_finalize_prepared_legacy_commit" not in tail
