from __future__ import annotations
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"baseline"/"pcmmad_receiver"
if str(BASE) not in sys.path:
    sys.path.insert(0,str(BASE))

import shared_core
import provenance_store as ps


def payload(content, *, operation="create", previous=None, key="idem-1", commit="commit-1", name="LIVE_SHADOW.md"):
    row={
        "project_id":"PROVTEST",
        "artifact_class":"continuity.live_shadow",
        "logical_name":name,
        "operation":operation,
        "content":content,
        "session_id":"s",
        "commit_id":commit,
        "idempotency_key":key,
    }
    if previous is not None:
        row["expected_previous_sha256"]=previous
    return row


def test_governed_commits_emit_project_and_surface_lineage(monkeypatch,tmp_path):
    monkeypatch.setattr(shared_core,"PROJECTS_ROOT",tmp_path)
    import legacy_routes as legacy
    first=legacy.commit_artifact_transaction(payload("one\n"),acquire_guard=False)
    assert first["provenance"]["project_sequence"]==1
    assert first["provenance"]["surface_sequence"]==1
    assert first["provenance"]["previous_project_event_hash"] is None
    second=legacy.commit_artifact_transaction(payload("two\n",operation="update",previous=first["sha256"],key="idem-2",commit="commit-2"),acquire_guard=False)
    assert second["provenance"]["project_sequence"]==2
    assert second["provenance"]["surface_sequence"]==2
    assert second["provenance"]["previous_project_event_hash"]==first["provenance"]["event_hash"]
    assert second["provenance"]["previous_surface_event_hash"]==first["provenance"]["event_hash"]
    replay=legacy.commit_artifact_transaction(payload("two\n",operation="update",previous=first["sha256"],key="idem-2",commit="commit-2"),acquire_guard=False)
    assert replay["replayed"] is True
    assert replay["provenance"]["event_hash"]==second["provenance"]["event_hash"]
    assert len(ps.read_events("PROVTEST"))==2
    assert ps.verify_events("PROVTEST")["ok"] is True
    assert ps.project_root_receipt("PROVTEST")["tree_size"]==2
    assert ps.inclusion_receipt("PROVTEST",2)["verified"] is True
    assert ps.consistency_receipt("PROVTEST",1)["verified"] is True


def test_distinct_surfaces_have_independent_surface_chains(monkeypatch,tmp_path):
    monkeypatch.setattr(shared_core,"PROJECTS_ROOT",tmp_path)
    import legacy_routes as legacy
    a=legacy.commit_artifact_transaction(payload("a\n",name="A.md",key="a",commit="a"),acquire_guard=False)
    b=legacy.commit_artifact_transaction(payload("b\n",name="B.md",key="b",commit="b"),acquire_guard=False)
    assert a["provenance"]["surface_sequence"]==1
    assert b["provenance"]["surface_sequence"]==1
    assert b["provenance"]["previous_surface_event_hash"] is None
    assert b["provenance"]["previous_project_event_hash"]==a["provenance"]["event_hash"]


def test_failed_hash_fence_emits_no_additional_provenance(monkeypatch,tmp_path):
    monkeypatch.setattr(shared_core,"PROJECTS_ROOT",tmp_path)
    import legacy_routes as legacy
    created=legacy.commit_artifact_transaction(payload("one\n"),acquire_guard=False)
    before=list(ps.read_events("PROVTEST"))
    assert len(before)==1
    with pytest.raises(PermissionError):
        legacy.commit_artifact_transaction(
            payload("two\n",operation="update",previous="0"*64,key="bad-fence",commit="bad-fence"),
            acquire_guard=False,
        )
    after=ps.read_events("PROVTEST")
    assert after==before
    assert after[0]["after_sha256"]==created["sha256"]


def test_tamper_or_reorder_is_detected(monkeypatch,tmp_path):
    monkeypatch.setattr(shared_core,"PROJECTS_ROOT",tmp_path)
    import legacy_routes as legacy
    first=legacy.commit_artifact_transaction(payload("one\n"),acquire_guard=False)
    legacy.commit_artifact_transaction(payload("two\n",operation="update",previous=first["sha256"],key="idem-2",commit="commit-2"),acquire_guard=False)
    path=ps.provenance_path_for("PROVTEST")
    rows=path.read_text(encoding="utf-8").splitlines()
    path.write_text(rows[1]+"\n"+rows[0]+"\n",encoding="utf-8")
    assert ps.verify_events("PROVTEST")["ok"] is False


def test_native_provenance_tools_registered():
    import lab_tools
    names={row["name"] for row in lab_tools.list_tools()}
    assert {
        "project.provenance.status",
        "project.provenance.root",
        "project.provenance.inclusion",
        "project.provenance.consistency",
    } <= names
