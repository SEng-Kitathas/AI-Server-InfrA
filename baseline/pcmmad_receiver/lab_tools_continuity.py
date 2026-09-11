"""Continuity convergence classifiers for explicit cross-plane observations.

This module does not merge continuity and does not silently reach into remote/live
planes. Callers bring observations (hashes/commits) with source labels; Runtime
classifies those observations against durable local registration lineage and
exactly-grounded Git ancestry.
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable, MutableMapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .control_plane_models import CommitLedgerRecord, ManifestDocument, ManifestEntryRecord
from .protocol_models import ProtocolEventKind, RuntimeMode
from .protocol_store import build_snapshot as build_protocol_snapshot, read_events as read_protocol_events, record_continuity as record_protocol_continuity, register_artifact as register_protocol_artifact
from .res_runtime import RES_ARTIFACT_CLASS_SNAPSHOT, RES_CANONICAL_SNAPSHOT_PATH, RES_CONTINUITY_KIND, handoff_readiness as res_handoff_readiness, validate_snapshot as validate_res_snapshot
from .server_hardening import run_subprocess_envelope

JsonObject = MutableMapping[str, Any]
Registrar = Callable[..., Any]
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_COMMIT_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")
MAX_OBSERVATIONS = 32
MAX_LINEAGE_TAIL = 16


@dataclass(frozen=True)
class ContinuityDeps:
    error_cls: type[Exception]
    get_project_root: Callable[[str], Path]
    resolve_target: Callable[[str, str, str], Path]
    commits_ledger_path_for: Callable[[str], Path]
    sha256_file: Callable[[Path], str]

@dataclass(frozen=True)
class AdoptionDeps:
    error_cls: type[Exception]
    get_project_root: Callable[[str], Path]
    resolve_target: Callable[[str, str, str], Path]
    commits_ledger_path_for: Callable[[str], Path]
    manifest_path_for: Callable[[str], Path]
    sha256_file: Callable[[Path], str]
    load_json: Callable[[Path, Any], Any]
    save_json_atomic: Callable[[Path, Any], None]
    append_jsonl: Callable[[Path, Any], None]
    utc_now: Callable[[], str]


def _deps(raw: JsonObject) -> ContinuityDeps:
    return ContinuityDeps(
        error_cls=raw["error_cls"],
        get_project_root=raw["get_project_root"],
        resolve_target=raw["resolve_target"],
        commits_ledger_path_for=raw["commits_ledger_path_for"],
        sha256_file=raw["sha256_file"],
    )

def _adoption_deps(raw: JsonObject) -> AdoptionDeps:
    return AdoptionDeps(
        error_cls=raw["error_cls"],
        get_project_root=raw["get_project_root"],
        resolve_target=raw["resolve_target"],
        commits_ledger_path_for=raw["commits_ledger_path_for"],
        manifest_path_for=raw["manifest_path_for"],
        sha256_file=raw["sha256_file"],
        load_json=raw["load_json"],
        save_json_atomic=raw["save_json_atomic"],
        append_jsonl=raw["append_jsonl"],
        utc_now=raw["utc_now"],
    )


def _required_text(payload: JsonObject, key: str, error_cls: type[Exception]) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise error_cls("BAD_REQUEST", f"{key} is required", 400)
    return value


def _sha256(value: object, error_cls: type[Exception], field: str = "sha256") -> str:
    text = str(value or "").strip().lower()
    if not _SHA256_RE.fullmatch(text):
        raise error_cls("BAD_OBSERVATION_SHA256", f"{field} must be exactly 64 hex characters", 400)
    return text


def _claimed_generation(value: object, error_cls: type[Exception]) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise error_cls("BAD_OBSERVATION_GENERATION", "claimed_generation must be a positive integer", 400)
    try:
        generation = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise error_cls("BAD_OBSERVATION_GENERATION", "claimed_generation must be a positive integer", 400) from exc
    if generation <= 0:
        raise error_cls("BAD_OBSERVATION_GENERATION", "claimed_generation must be a positive integer", 400)
    return generation


def _load_registration_lineage(
    project_id: str,
    artifact_class: str,
    logical_name: str,
    dep: ContinuityDeps,
) -> list[JsonObject]:
    ledger = dep.commits_ledger_path_for(project_id)
    if not ledger.exists():
        return []
    transitions: list[JsonObject] = []
    with ledger.open("r", encoding="utf-8") as handle:
        for line_no, raw_line in enumerate(handle, 1):
            text = raw_line.strip()
            if not text:
                continue
            try:
                row = json.loads(text)
            except json.JSONDecodeError as exc:
                raise dep.error_cls(
                    "CONTINUITY_LEDGER_CORRUPT",
                    f"commit ledger line {line_no} is invalid JSON",
                    409,
                    line_no=line_no,
                ) from exc
            if not isinstance(row, dict):
                raise dep.error_cls(
                    "CONTINUITY_LEDGER_CORRUPT",
                    f"commit ledger line {line_no} is not an object",
                    409,
                    line_no=line_no,
                )
            if str(row.get("artifact_class") or "") != artifact_class:
                continue
            if str(row.get("logical_name") or "") != logical_name:
                continue
            sha = str(row.get("sha256") or "").strip().lower()
            if not _SHA256_RE.fullmatch(sha):
                raise dep.error_cls(
                    "CONTINUITY_LEDGER_CORRUPT",
                    f"matching commit ledger line {line_no} has invalid sha256",
                    409,
                    line_no=line_no,
                )
            # Re-registration of identical bytes is not a new content generation.
            if transitions and transitions[-1]["sha256"] == sha:
                continue
            transitions.append(
                {
                    "generation": len(transitions) + 1,
                    "sha256": sha,
                    "time": row.get("time"),
                    "commit_id": row.get("commit_id"),
                    "operation": row.get("operation"),
                }
            )
    return transitions


def _artifact_relation(
    observation: JsonObject,
    *,
    current_sha: str | None,
    current_generation: int,
    registration_current: bool,
    lineage: list[JsonObject],
    error_cls: type[Exception],
) -> JsonObject:
    source = str(observation.get("source") or "").strip()[:200]
    if not source:
        raise error_cls("BAD_REQUEST", "each observation requires source", 400)
    observed_sha = _sha256(observation.get("sha256"), error_cls)
    claimed = _claimed_generation(observation.get("claimed_generation"), error_cls)
    result: JsonObject = {
        "source": source,
        "sha256": observed_sha,
        "claimed_generation": claimed,
        "relation": None,
        "human_conflict_required": False,
    }
    if not registration_current:
        if current_sha == observed_sha:
            result["relation"] = "matches_unregistered_local"
        else:
            result["relation"] = "local_unregistered"
        result["human_conflict_required"] = True
        return result
    if current_sha == observed_sha:
        result["relation"] = "equal_current"
        result["matched_generation"] = current_generation
        return result

    matches = [item for item in lineage if item["sha256"] == observed_sha]
    if matches:
        match = matches[-1]
        result["matched_generation"] = match["generation"]
        if int(match["generation"]) < current_generation:
            result["relation"] = "stale_known_ancestor"
            return result

    if claimed is not None and claimed > current_generation:
        result["relation"] = "ahead_or_divergent_unproven"
        result["human_conflict_required"] = True
    elif claimed is not None:
        result["relation"] = "divergent"
        result["human_conflict_required"] = True
    else:
        result["relation"] = "divergent_or_ahead_unknown"
        result["human_conflict_required"] = True
    return result


def inspect_artifact_lineage(payload: JsonObject, dep: ContinuityDeps) -> JsonObject:
    project_id = _required_text(payload, "project_id", dep.error_cls)
    artifact = payload.get("artifact")
    if not isinstance(artifact, dict):
        raise dep.error_cls("BAD_REQUEST", "artifact must be an object", 400)
    artifact_class = _required_text(artifact, "artifact_class", dep.error_cls)
    logical_name = _required_text(artifact, "logical_name", dep.error_cls)
    try:
        target = dep.resolve_target(project_id, artifact_class, logical_name)
    except ValueError as exc:
        raise dep.error_cls("BAD_ARTIFACT", str(exc), 400) from exc
    lineage = _load_registration_lineage(project_id, artifact_class, logical_name, dep)
    current_sha = dep.sha256_file(target) if target.is_file() else None
    latest_sha = str(lineage[-1]["sha256"]) if lineage else None
    current_generation = int(lineage[-1]["generation"]) if lineage else 0
    registration_current = bool(current_sha is not None and latest_sha == current_sha)
    observations = payload.get("observations") or []
    if not isinstance(observations, list):
        raise dep.error_cls("BAD_REQUEST", "observations must be an array", 400)
    if len(observations) > MAX_OBSERVATIONS:
        raise dep.error_cls("BAD_REQUEST", f"observations limit is {MAX_OBSERVATIONS}", 400)
    observed_results = [
        _artifact_relation(
            observation,
            current_sha=current_sha,
            current_generation=current_generation,
            registration_current=registration_current,
            lineage=lineage,
            error_cls=dep.error_cls,
        )
        for observation in observations
        if isinstance(observation, dict)
    ]
    if len(observed_results) != len(observations):
        raise dep.error_cls("BAD_REQUEST", "each observation must be an object", 400)
    return {
        "project_id": project_id,
        "artifact_class": artifact_class,
        "logical_name": logical_name,
        "path": str(target),
        "exists": target.is_file(),
        "current_sha256": current_sha,
        "latest_registered_sha256": latest_sha,
        "current_generation": current_generation,
        "registration_current": registration_current,
        "lineage_depth": len(lineage),
        "lineage_tail": lineage[-MAX_LINEAGE_TAIL:],
        "observations": observed_results,
    }


def _git(root: Path, args: list[str]) -> JsonObject:
    return run_subprocess_envelope(
        args,
        cwd=root,
        timeout_seconds=10,
        stdout_max_bytes=32768,
        stderr_max_bytes=32768,
    )


def _resolve_grounded_repo(project_root: Path, repo_path: str, error_cls: type[Exception]) -> Path:
    if not repo_path:
        raise error_cls("BAD_REQUEST", "git.repo_path is required", 400)
    raw = Path(repo_path)
    if raw.is_absolute():
        raise error_cls("BAD_PATH", "git.repo_path must be project-relative", 400)
    repo = (project_root / raw).resolve()
    if project_root.resolve() not in [repo, *repo.parents]:
        raise error_cls("BAD_PATH", "git.repo_path escapes project root", 400)
    probe = _git(repo, ["git", "rev-parse", "--show-toplevel"])
    if not probe.get("ok"):
        raise error_cls(
            "GIT_REPO_INVALID",
            str(probe.get("stderr") or probe.get("stdout") or "not a Git repository"),
            409,
        )
    top = Path(str(probe.get("stdout") or "").strip()).resolve()
    if top != repo:
        raise error_cls(
            "GIT_REPO_SCOPE_MISMATCH",
            "requested path is not the exact Git repository root",
            409,
            requested_repo=str(repo),
            git_toplevel=str(top),
        )
    return repo


def _commit_token(value: object, error_cls: type[Exception], *, allow_head: bool = False) -> str:
    token = str(value or "").strip()
    if allow_head and token == "HEAD":
        return token
    if not _GIT_COMMIT_RE.fullmatch(token):
        raise error_cls("BAD_GIT_COMMIT", "Git observations must be 7-64 hex commit ids", 400)
    return token


def _resolve_commit(repo: Path, token: str) -> str | None:
    result = _git(repo, ["git", "rev-parse", "--verify", f"{token}^{{commit}}"])
    if not result.get("ok"):
        return None
    resolved = str(result.get("stdout") or "").strip().lower()
    return resolved if re.fullmatch(r"[0-9a-f]{40,64}", resolved) else None


def _is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool | None:
    result = _git(repo, ["git", "merge-base", "--is-ancestor", ancestor, descendant])
    rc = result.get("return_code")
    if rc == 0:
        return True
    if rc == 1:
        return False
    return None


def inspect_git_relations(payload: JsonObject, dep: ContinuityDeps) -> JsonObject | None:
    git_payload = payload.get("git")
    if git_payload in (None, {}):
        return None
    if not isinstance(git_payload, dict):
        raise dep.error_cls("BAD_REQUEST", "git must be an object", 400)
    project_id = _required_text(payload, "project_id", dep.error_cls)
    project_root = dep.get_project_root(project_id).resolve()
    repo = _resolve_grounded_repo(project_root, str(git_payload.get("repo_path") or ""), dep.error_cls)
    target_token = _commit_token(git_payload.get("target_commit") or "HEAD", dep.error_cls, allow_head=True)
    target = _resolve_commit(repo, target_token)
    if target is None:
        raise dep.error_cls("GIT_TARGET_UNKNOWN", "target Git commit could not be resolved", 409)
    observations = git_payload.get("observations") or []
    if not isinstance(observations, list):
        raise dep.error_cls("BAD_REQUEST", "git.observations must be an array", 400)
    if len(observations) > MAX_OBSERVATIONS:
        raise dep.error_cls("BAD_REQUEST", f"git.observations limit is {MAX_OBSERVATIONS}", 400)
    results: list[JsonObject] = []
    for observation in observations:
        if not isinstance(observation, dict):
            raise dep.error_cls("BAD_REQUEST", "each git observation must be an object", 400)
        source = str(observation.get("source") or "").strip()[:200]
        if not source:
            raise dep.error_cls("BAD_REQUEST", "each git observation requires source", 400)
        token = _commit_token(observation.get("commit"), dep.error_cls)
        resolved = _resolve_commit(repo, token)
        row: JsonObject = {
            "source": source,
            "commit": token,
            "resolved_commit": resolved,
            "relation": None,
            "human_conflict_required": False,
        }
        if resolved is None:
            row["relation"] = "unknown_commit"
            row["human_conflict_required"] = True
        elif resolved == target:
            row["relation"] = "equal_current"
        else:
            older = _is_ancestor(repo, resolved, target)
            newer = _is_ancestor(repo, target, resolved)
            if older is True:
                row["relation"] = "stale_known_ancestor"
            elif newer is True:
                row["relation"] = "ahead_known_descendant"
            elif older is False and newer is False:
                row["relation"] = "divergent"
                row["human_conflict_required"] = True
            else:
                row["relation"] = "git_relation_unknown"
                row["human_conflict_required"] = True
        results.append(row)
    return {
        "repo_path": str(repo.relative_to(project_root)),
        "repo_grounded": True,
        "target_commit": target,
        "observations": results,
    }


def adopt_existing_artifact(payload: JsonObject, dep: AdoptionDeps) -> JsonObject:
    project_id = _required_text(payload, "project_id", dep.error_cls)
    artifact = payload.get("artifact")
    if not isinstance(artifact, dict):
        raise dep.error_cls("BAD_REQUEST", "artifact must be an object", 400)
    artifact_class = _required_text(artifact, "artifact_class", dep.error_cls)
    logical_name = _required_text(artifact, "logical_name", dep.error_cls)
    expected_sha = _sha256(payload.get("expected_sha256"), dep.error_cls, "expected_sha256")
    expected_registered_raw = payload.get("expected_registered_sha256")
    expected_registered = (
        _sha256(expected_registered_raw, dep.error_cls, "expected_registered_sha256")
        if expected_registered_raw not in (None, "") else None
    )
    session_id = str(payload.get("session_id") or "artifact-adoption").strip() or "artifact-adoption"

    target = dep.resolve_target(project_id, artifact_class, logical_name)
    if not target.is_file():
        raise dep.error_cls("ARTIFACT_NOT_FOUND", "artifact target does not exist", 404, path=str(target))
    actual_sha = dep.sha256_file(target)
    if actual_sha != expected_sha:
        raise dep.error_cls(
            "ARTIFACT_SHA_MISMATCH",
            "expected_sha256 does not match current file bytes",
            409,
            expected_sha256=expected_sha,
            current_sha256=actual_sha,
        )

    lineage = _load_registration_lineage(project_id, artifact_class, logical_name, dep)
    latest = lineage[-1] if lineage else None
    latest_sha = str(latest.get("sha256") or "") if latest else None
    latest_generation = int(latest.get("generation") or len(lineage)) if latest else 0
    if latest_sha == actual_sha:
        return {
            "ok": True,
            "project_id": project_id,
            "artifact_class": artifact_class,
            "logical_name": logical_name,
            "path": str(target),
            "sha256": actual_sha,
            "bytes": target.stat().st_size,
            "generation": latest_generation,
            "adopted": False,
            "already_current": True,
            "operation": "adopt",
        }
    if latest_sha is not None:
        if expected_registered is None:
            raise dep.error_cls(
                "REGISTERED_LINEAGE_EXPECTATION_REQUIRED",
                "existing lineage requires expected_registered_sha256 before adoption",
                409,
                latest_registered_sha256=latest_sha,
            )
        if expected_registered != latest_sha:
            raise dep.error_cls(
                "REGISTERED_LINEAGE_MISMATCH",
                "expected_registered_sha256 does not match lineage head",
                409,
                expected_registered_sha256=expected_registered,
                latest_registered_sha256=latest_sha,
            )
    elif expected_registered is not None:
        raise dep.error_cls(
            "REGISTERED_LINEAGE_MISMATCH",
            "expected_registered_sha256 was supplied but no lineage exists",
            409,
            expected_registered_sha256=expected_registered,
            latest_registered_sha256=None,
        )

    project_root = dep.get_project_root(project_id).resolve()
    try:
        rel = str(target.resolve().relative_to(project_root)).replace("\\", "/")
    except ValueError as exc:
        raise dep.error_cls("BAD_ARTIFACT", "artifact target escaped project root", 409) from exc
    now = dep.utc_now()
    size_bytes = target.stat().st_size
    generation = latest_generation + 1
    commit_id = str(payload.get("commit_id") or f"adopt-{generation}-{actual_sha[:12]}").strip()
    idempotency_key = str(payload.get("idempotency_key") or f"adopt:{artifact_class}:{logical_name}:{actual_sha}").strip()

    manifest_path = dep.manifest_path_for(project_id)
    manifest = ManifestDocument.from_dict(dep.load_json(manifest_path, {"files": {}}))
    manifest.files[rel] = ManifestEntryRecord(
        artifact_class=artifact_class,
        sha256=actual_sha,
        bytes=size_bytes,
        updated_at=now,
    )
    manifest.updated_at = now
    dep.save_json_atomic(manifest_path, manifest.to_dict())

    # Recheck exact bytes after metadata mutation and before publishing lineage.
    post_manifest_sha = dep.sha256_file(target)
    if post_manifest_sha != actual_sha:
        raise dep.error_cls(
            "ARTIFACT_CHANGED_DURING_ADOPTION",
            "artifact bytes changed during adoption; lineage was not appended",
            409,
            expected_sha256=actual_sha,
            current_sha256=post_manifest_sha,
        )

    record = CommitLedgerRecord(
        project_id=project_id,
        session_id=session_id,
        commit_id=commit_id,
        idempotency_key=idempotency_key,
        artifact_class=artifact_class,
        logical_name=logical_name,
        operation="adopt",
        path=rel,
        sha256=actual_sha,
        bytes=size_bytes,
        time=now,
    )
    dep.append_jsonl(dep.commits_ledger_path_for(project_id), record)
    final_sha = dep.sha256_file(target)
    if final_sha != actual_sha:
        raise dep.error_cls(
            "ARTIFACT_CHANGED_AFTER_ADOPTION",
            "artifact bytes changed after lineage append; human reconciliation is required",
            409,
            registered_sha256=actual_sha,
            current_sha256=final_sha,
        )
    return {
        "ok": True,
        "project_id": project_id,
        "artifact_class": artifact_class,
        "logical_name": logical_name,
        "path": str(target),
        "sha256": actual_sha,
        "bytes": size_bytes,
        "generation": generation,
        "commit_id": commit_id,
        "idempotency_key": idempotency_key,
        "adopted": True,
        "already_current": False,
        "operation": "adopt",
    }


def reconcile_res_snapshot(payload: JsonObject, dep: AdoptionDeps) -> JsonObject:
    project_id = _required_text(payload, "project_id", dep.error_cls)
    expected_sha = _sha256(payload.get("expected_sha256"), dep.error_cls, "expected_sha256")
    expected_registered_raw = payload.get("expected_registered_sha256")
    expected_registered = (
        _sha256(expected_registered_raw, dep.error_cls, "expected_registered_sha256")
        if expected_registered_raw not in (None, "") else None
    )
    actor = str(payload.get("actor") or "pcmmad-lab").strip() or "pcmmad-lab"
    session_id = str(payload.get("session_id") or "res-reconcile").strip() or "res-reconcile"
    research_intensive = bool(payload.get("research_intensive", True))

    protocol_before = build_protocol_snapshot(project_id)
    if protocol_before.current_mode is not RuntimeMode.BUILD_COMMIT:
        raise dep.error_cls(
            "RES_RECONCILE_BUILD_COMMIT_REQUIRED",
            "RES reconciliation requires protocol mode BUILD_COMMIT; transition mode explicitly before retrying",
            409,
            current_mode=protocol_before.current_mode.value,
        )

    root = dep.get_project_root(project_id).resolve()
    target = (root / RES_CANONICAL_SNAPSHOT_PATH).resolve()
    if root not in [target, *target.parents] or not target.is_file():
        raise dep.error_cls("RES_SNAPSHOT_MISSING", "canonical RES snapshot does not exist", 404, path=str(target))
    try:
        validation = validate_res_snapshot(target.read_text(encoding="utf-8"))
    except Exception as exc:
        raise dep.error_cls("RES_SNAPSHOT_INVALID", "canonical RES snapshot failed validation", 409, error=str(exc)) from exc
    actual_sha = dep.sha256_file(target)
    if actual_sha != expected_sha:
        raise dep.error_cls(
            "ARTIFACT_SHA_MISMATCH",
            "expected_sha256 does not match current RES file bytes",
            409,
            expected_sha256=expected_sha,
            current_sha256=actual_sha,
        )

    readiness_before = res_handoff_readiness(project_id, research_intensive=research_intensive)
    reasons_before = list(readiness_before.get("reasons") or [])
    unsafe = [
        reason for reason in reasons_before
        if reason not in {
            "RES_SNAPSHOT_NOT_REGISTERED",
            "RES_SNAPSHOT_REGISTERED_HASH_STALE",
            "RES_CONTINUITY_EVENT_MISSING",
            "RES_ARTIFACT_NOT_ACKNOWLEDGED_BY_CONTINUITY_LEDGER",
        }
    ]
    if unsafe:
        raise dep.error_cls(
            "RES_RECONCILE_UNSAFE_STATE",
            "RES has semantic/material readiness failures that registration reconciliation must not hide",
            409,
            reasons=unsafe,
            readiness=readiness_before,
        )

    adoption_payload: JsonObject = {
        "project_id": project_id,
        "artifact": {
            "artifact_class": "continuity.research_epistemic_shadow",
            "logical_name": "RESEARCH_EPISTEMIC_SHADOW.md",
        },
        "expected_sha256": actual_sha,
        "session_id": session_id,
    }
    if expected_registered is not None:
        adoption_payload["expected_registered_sha256"] = expected_registered
    adoption = adopt_existing_artifact(adoption_payload, dep)

    canonical_rel = RES_CANONICAL_SNAPSHOT_PATH.replace("\\", "/")
    events = list(read_protocol_events(project_id))
    snapshot_events = [
        event for event in events
        if event.event_kind is ProtocolEventKind.ARTIFACT_REGISTERED
        and event.payload.get("artifact_class") == RES_ARTIFACT_CLASS_SNAPSHOT
        and event.payload.get("path") == canonical_rel
    ]
    latest_snapshot = snapshot_events[-1] if snapshot_events else None
    artifact_event = None
    protocol_registered = False
    if latest_snapshot is None or str(latest_snapshot.payload.get("sha256") or "") != actual_sha:
        artifact_id = str(payload.get("artifact_id") or f"res-canonical-{actual_sha[:16]}").strip()
        artifact_event = register_protocol_artifact(
            project_id,
            artifact_id=artifact_id,
            artifact_class=RES_ARTIFACT_CLASS_SNAPSHOT,
            actor=actor,
            path=canonical_rel,
            sha256=actual_sha,
            sealed=False,
            provenance=[
                "runtime:continuity.res.reconcile",
                f"lineage:{adoption.get('generation')}",
                f"file-sha256:{actual_sha}",
            ],
        )
        protocol_registered = True

    readiness_mid = res_handoff_readiness(project_id, research_intensive=research_intensive)
    mid_reasons = list(readiness_mid.get("reasons") or [])
    unsafe_mid = [
        reason for reason in mid_reasons
        if reason not in {"RES_CONTINUITY_EVENT_MISSING", "RES_ARTIFACT_NOT_ACKNOWLEDGED_BY_CONTINUITY_LEDGER"}
    ]
    if unsafe_mid:
        raise dep.error_cls(
            "RES_RECONCILE_INCOMPLETE",
            "RES remains non-ready for reasons outside continuity acknowledgment",
            409,
            reasons=unsafe_mid,
            readiness=readiness_mid,
        )

    continuity_event = None
    continuity_recorded = False
    if mid_reasons:
        artifact_ref = str(
            (artifact_event.payload.get("artifact_id") if artifact_event is not None else latest_snapshot.payload.get("artifact_id"))
            or ""
        )
        continuity_id = str(payload.get("continuity_id") or f"res-reconcile-{actual_sha[:16]}").strip()
        continuity_event = record_protocol_continuity(
            project_id,
            continuity_id=continuity_id,
            kind=RES_CONTINUITY_KIND,
            summary=(
                "Reconciled canonical RES registration/currentness to exact existing file bytes without rewriting content. "
                f"sha256={actual_sha}"
            ),
            actor=actor,
            artifact_ref=artifact_ref or None,
            open_loops=["Continue governed RES updates only on material epistemic change."],
        )
        continuity_recorded = True

    final_sha = dep.sha256_file(target)
    if final_sha != actual_sha:
        raise dep.error_cls(
            "RES_BYTES_CHANGED_DURING_RECONCILE",
            "RES bytes changed during reconciliation",
            409,
            expected_sha256=actual_sha,
            current_sha256=final_sha,
        )
    readiness_after = res_handoff_readiness(project_id, research_intensive=research_intensive)
    if not bool(readiness_after.get("ready")):
        raise dep.error_cls(
            "RES_RECONCILE_NOT_READY",
            "RES reconciliation completed metadata steps but readiness is still false",
            409,
            readiness=readiness_after,
        )
    return {
        "ok": True,
        "project_id": project_id,
        "path": str(target),
        "sha256": actual_sha,
        "bytes": target.stat().st_size,
        "validation": validation,
        "lineage": adoption,
        "protocol_artifact_registered": protocol_registered,
        "protocol_artifact_sequence": (artifact_event.sequence if artifact_event is not None else (latest_snapshot.sequence if latest_snapshot is not None else None)),
        "continuity_recorded": continuity_recorded,
        "continuity_sequence": continuity_event.sequence if continuity_event is not None else readiness_after.get("latest_res_continuity_sequence"),
        "readiness_before": readiness_before,
        "readiness_after": readiness_after,
        "content_rewritten": False,
    }


def _overall_status(artifact: JsonObject, git: JsonObject | None) -> str:
    if not artifact.get("registration_current"):
        return "local_unregistered"
    rows = list(artifact.get("observations") or [])
    if git:
        rows.extend(git.get("observations") or [])
    if any(bool(row.get("human_conflict_required")) for row in rows):
        return "divergent_or_unproven"
    relations = {str(row.get("relation") or "") for row in rows}
    if "ahead_known_descendant" in relations:
        return "local_stale"
    if "stale_known_ancestor" in relations:
        return "stale_observation"
    return "converged"


def inspect_convergence(payload: JsonObject, dep: ContinuityDeps) -> JsonObject:
    artifact = inspect_artifact_lineage(payload, dep)
    git = inspect_git_relations(payload, dep)
    return {
        "ok": True,
        "project_id": artifact["project_id"],
        "status": _overall_status(artifact, git),
        "artifact": artifact,
        "git": git,
        "semantic_note": (
            "stale_known_ancestor is machine-computable refresh pressure; divergent/unknown relations "
            "remain conflict evidence and are not auto-merged"
        ),
    }


INPUT_SCHEMA: JsonObject = {
    "type": "object",
    "required": ["project_id", "artifact"],
    "additionalProperties": False,
    "properties": {
        "project_id": {"type": "string", "minLength": 1},
        "artifact": {
            "type": "object",
            "required": ["artifact_class", "logical_name"],
            "additionalProperties": False,
            "properties": {
                "artifact_class": {"type": "string", "minLength": 1},
                "logical_name": {"type": "string", "minLength": 1},
            },
        },
        "observations": {
            "type": "array",
            "maxItems": MAX_OBSERVATIONS,
            "items": {
                "type": "object",
                "required": ["source", "sha256"],
                "additionalProperties": False,
                "properties": {
                    "source": {"type": "string", "minLength": 1, "maxLength": 200},
                    "sha256": {"type": "string", "pattern": "^[0-9a-fA-F]{64}$"},
                    "claimed_generation": {"type": ["integer", "null"], "minimum": 1},
                },
            },
        },
        "git": {
            "type": ["object", "null"],
            "additionalProperties": False,
            "required": ["repo_path"],
            "properties": {
                "repo_path": {"type": "string", "minLength": 1},
                "target_commit": {"type": ["string", "null"]},
                "observations": {
                    "type": "array",
                    "maxItems": MAX_OBSERVATIONS,
                    "items": {
                        "type": "object",
                        "required": ["source", "commit"],
                        "additionalProperties": False,
                        "properties": {
                            "source": {"type": "string", "minLength": 1, "maxLength": 200},
                            "commit": {"type": "string", "pattern": "^[0-9a-fA-F]{7,64}$"},
                        },
                    },
                },
            },
        },
    },
}


ADOPT_INPUT_SCHEMA: JsonObject = {
    "type": "object",
    "required": ["project_id", "artifact", "expected_sha256"],
    "additionalProperties": False,
    "properties": {
        "project_id": {"type": "string", "minLength": 1},
        "artifact": {
            "type": "object",
            "required": ["artifact_class", "logical_name"],
            "additionalProperties": False,
            "properties": {
                "artifact_class": {"type": "string", "minLength": 1},
                "logical_name": {"type": "string", "minLength": 1},
            },
        },
        "expected_sha256": {"type": "string", "pattern": "^[0-9a-fA-F]{64}$"},
        "expected_registered_sha256": {"type": ["string", "null"], "pattern": "^[0-9a-fA-F]{64}$"},
        "session_id": {"type": "string", "minLength": 1, "maxLength": 200},
        "commit_id": {"type": "string", "minLength": 1, "maxLength": 200},
        "idempotency_key": {"type": "string", "minLength": 1, "maxLength": 300},
    },
}


RES_RECONCILE_INPUT_SCHEMA: JsonObject = {
    "type": "object",
    "required": ["project_id", "expected_sha256"],
    "additionalProperties": False,
    "properties": {
        "project_id": {"type": "string", "minLength": 1},
        "expected_sha256": {"type": "string", "pattern": "^[0-9a-fA-F]{64}$"},
        "expected_registered_sha256": {"type": ["string", "null"], "pattern": "^[0-9a-fA-F]{64}$"},
        "research_intensive": {"type": "boolean"},
        "actor": {"type": "string", "minLength": 1, "maxLength": 200},
        "session_id": {"type": "string", "minLength": 1, "maxLength": 200},
        "artifact_id": {"type": "string", "minLength": 1, "maxLength": 200},
        "continuity_id": {"type": "string", "minLength": 1, "maxLength": 200},
    },
}


def register_continuity_tools(register_tool: Registrar, **raw_deps: Any) -> None:
    dep = _deps(raw_deps)
    adoption_dep = _adoption_deps(raw_deps)

    @register_tool(
        "continuity.convergence.inspect",
        "Classify explicit continuity hash/commit observations as current, stale-known-ancestor, ahead, or divergent without auto-merging planes.",
        "low",
        category="continuity",
        side_effect_class="read",
        effect_traits=[
            "reads_project_ledger",
            "reads_files",
            "reads_repo_state",
            "project_scope_enforced",
            "requires_exact_repo_identity",
            "source_currentness_check",
            "bounded_output",
        ],
        input_schema=INPUT_SCHEMA,
        output_schema={"type": "object"},
    )
    def tool_continuity_convergence_inspect(payload: JsonObject) -> JsonObject:
        return inspect_convergence(payload, dep)

    @register_tool(
        "continuity.artifact.adopt",
        "Adopt an already-existing exact project artifact into durable lineage without rewriting its bytes; intended for pre-server project migration.",
        "high",
        category="continuity",
        mutating=True,
        approval_required=True,
        side_effect_class="mutation",
        effect_traits=[
            "durable_mutation",
            "writes_project_ledger",
            "writes_manifest",
            "project_scope_enforced",
            "project_mutation_fenced",
            "source_currentness_check",
            "idempotent_when_current",
            "does_not_rewrite_artifact_bytes",
        ],
        input_schema=ADOPT_INPUT_SCHEMA,
        output_schema={"type": "object"},
    )
    def tool_continuity_artifact_adopt(payload: JsonObject) -> JsonObject:
        return adopt_existing_artifact(payload, adoption_dep)

    @register_tool(
        "continuity.res.reconcile",
        "Reconcile an existing canonical RES snapshot across lineage and protocol readiness without rewriting snapshot bytes.",
        "high",
        category="continuity",
        mutating=True,
        approval_required=True,
        side_effect_class="mutation",
        effect_traits=[
            "durable_mutation",
            "writes_project_ledger",
            "writes_manifest",
            "writes_protocol_ledger",
            "project_scope_enforced",
            "project_mutation_fenced",
            "source_currentness_check",
            "idempotent_when_current",
            "does_not_rewrite_artifact_bytes",
            "requires_build_commit_mode",
        ],
        input_schema=RES_RECONCILE_INPUT_SCHEMA,
        output_schema={"type": "object"},
    )
    def tool_continuity_res_reconcile(payload: JsonObject) -> JsonObject:
        return reconcile_res_snapshot(payload, adoption_dep)
