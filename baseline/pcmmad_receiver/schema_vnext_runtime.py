"""PCMMAD schema vNext capability-microkernel adapter runtime.

This module is intentionally an adapter/control algebra over the native Runtime.
It does not own jobs, approvals, projects, artifacts, continuity, transfer state,
or native capability truth. Those remain in their existing server-native planes.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
import re
import secrets
import time
from pathlib import Path
from typing import Any, Mapping

from .lab_results import (
    RESULT_INLINE_SAFE_BYTES,
    RESULT_PREVIEW_MAX_CHARS,
    RESULT_RANGE_MAX_BYTES,
    get_result,
    read_result_range,
    result_metadata,
    result_path,
    store_result,
    summarize_payload,
)
from .lab_tools import LabToolError, dispatch_tool, list_tools
from .server_hardening import safe_json_dumps, to_jsonable
from .scheduler_effect_profile import current_profile as load_current_effect_profile, entry_map as effect_entry_map
from .shared_core import utc_now

JsonObject = dict[str, Any]

SCHEMA_VNEXT_VERSION = "11.0.0-candidate"
ORIENT_DEFAULT_CAPABILITIES = 8
ORIENT_MAX_CAPABILITIES = 24
LEASE_DEFAULT_TTL_SECONDS = 300
LEASE_MAX_TTL_SECONDS = 900
PLAN_MAX_NODES = 32
PLAN_MAX_ASSERTIONS = 32
PLAN_MAX_PARALLELISM = 16
PLAN_MAX_SERIALIZED_BYTES = 65536
PLAN_MAX_RESOLVED_ARGUMENT_BYTES = 65_536
PLAN_DEFAULT_MAX_STATIC_COST_UNITS = 120
PLAN_MAX_STATIC_COST_UNITS = 320
PLAN_INLINE_SAFE_BYTES = 12000
NODE_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
WORD_RE = re.compile(r"[a-z0-9_.-]+")
BLOCKABLE_PRE_EFFECT_ERRORS = frozenset(
    {
        "APPROVAL_REQUIRED",
        "PROJECT_MUTATION_AUTHORITY_REQUIRED",
        "CROSS_PROJECT_MUTATION_AUTHORITY_REQUIRED",
    }
)
TRANSFER_ACTION_MAP = {
    "export.create": "transfer.export.create",
    "chunk.read": "transfer.chunk.read",
    "import.create": "transfer.import.create",
    "chunk.write": "transfer.chunk.write",
    "import.finalize": "transfer.import.finalize",
    "meta": "transfer.meta",
}


def _hash_json(value: Any) -> str:
    canonical = json.dumps(
        to_jsonable(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _cards() -> dict[str, JsonObject]:
    return {str(card.get("name")): dict(card) for card in list_tools()}


def _require_object(value: Any, field: str) -> JsonObject:
    if not isinstance(value, dict):
        raise LabToolError("BAD_REQUEST", f"{field} must be an object", 400)
    return dict(value)


def _require_digest(value: Any, field: str) -> str:
    text = str(value or "").strip().lower()
    if not DIGEST_RE.fullmatch(text):
        raise LabToolError("BAD_REQUEST", f"{field} must be exactly 64 hexadecimal characters", 400)
    return text


def _tokenize(text: Any) -> set[str]:
    return set(WORD_RE.findall(str(text or "").lower()))


def _catalog_digest(cards: Mapping[str, JsonObject]) -> str:
    return _hash_json(
        [
            {"name": name, "contract_digest": cards[name].get("contract_digest")}
            for name in sorted(cards)
        ]
    )


def _compact_card(card: Mapping[str, Any], score: int | None = None) -> JsonObject:
    out: JsonObject = {
        "name": card.get("name"),
        "description": card.get("description"),
        "category": card.get("category"),
        "tags": list(card.get("tags") or []),
        "danger_tier": card.get("danger_tier"),
        "effective_approval_required": bool(card.get("effective_approval_required")),
        "mutating": bool(card.get("mutating")),
        "side_effect_class": card.get("side_effect_class"),
        "effect_traits": list(card.get("effect_traits") or []),
        "idempotency_semantics": card.get("idempotency_semantics"),
        "capability_version": card.get("capability_version"),
        "schema_version": card.get("schema_version"),
        "schema_hash": card.get("schema_hash"),
        "contract_digest": card.get("contract_digest"),
        "availability": dict(card.get("availability") or {}),
        "input_schema": dict(card.get("input_schema") or {"type": "object"}),
    }
    if score is not None:
        out["relevance_score"] = int(score)
    return out


def _full_card(card: Mapping[str, Any], score: int | None = None) -> JsonObject:
    out = dict(card)
    if score is not None:
        out["relevance_score"] = int(score)
    return out


def _score_card(card: Mapping[str, Any], terms: set[str]) -> int:
    if not terms:
        return 0
    name = str(card.get("name") or "").lower()
    category = str(card.get("category") or "").lower()
    tags = {str(item).lower() for item in card.get("tags") or []}
    description_terms = _tokenize(card.get("description"))
    name_terms = _tokenize(name)
    score = 0
    for term in terms:
        if term == name:
            score += 30
        if term == category:
            score += 12
        if term in name_terms:
            score += 10
        elif term in name:
            score += 6
        if term in tags:
            score += 8
        if term in description_terms:
            score += 3
    return score


def _selected_lease_payload(
    *,
    goal: str,
    project_id: str | None,
    selected: list[JsonObject],
    ttl_seconds: int,
    catalog_digest: str,
) -> JsonObject:
    now = time.time()
    lease: JsonObject = {
        "schema": "pcmmad.capability-lease.v1",
        "authority_effect": "NONE",
        "law": "CAPABILITY_LEASE != CAPABILITY_GRANT",
        "goal_digest": _hash_json({"goal": goal, "project_id": project_id}),
        "project_id": project_id,
        "issued_at": utc_now(),
        "issued_at_epoch": now,
        "expires_at_epoch": now + ttl_seconds,
        "ttl_seconds": ttl_seconds,
        "catalog_digest_at_issue": catalog_digest,
        "selected": [
            {
                "name": row["name"],
                "contract_digest": row["contract_digest"],
            }
            for row in selected
        ],
    }
    lease["lease_digest"] = _hash_json(lease)
    return lease


def _scheduler_profile_status() -> JsonObject:
    try:
        profile, verification, _entries = _current_scheduler_profile()
        return {
            "current": True,
            "profile_digest": profile.get("profile_digest"),
            "catalog_digest": verification.get("catalog_digest"),
            "capability_count": verification.get("capability_count"),
            "effect_truth_verified_count": verification.get("effect_truth_verified_count"),
            "parallel_verified_count": verification.get("parallel_verified_count"),
            "resume_replay_verified_count": verification.get("resume_replay_verified_count"),
            "descriptive_traits_scheduler_authority": False,
        }
    except LabToolError as exc:
        return {
            "current": False,
            "error_code": exc.error_code,
            "message": exc.message,
            "descriptive_traits_scheduler_authority": False,
        }


def orient(payload: Mapping[str, Any]) -> JsonObject:
    request = _require_object(dict(payload), "payload")
    goal = str(request.get("goal") or request.get("query") or "").strip()
    explicit = request.get("capabilities") or []
    if explicit is not None and not isinstance(explicit, list):
        raise LabToolError("BAD_REQUEST", "capabilities must be an array", 400)
    categories = {
        str(item).strip().lower()
        for item in (request.get("categories") or [])
        if str(item).strip()
    }
    effect_classes = {
        str(item).strip().lower()
        for item in (request.get("effect_classes") or [])
        if str(item).strip()
    }
    include_mutating = bool(request.get("include_mutating", True))
    detail = str(request.get("detail") or "compact").strip().lower()
    if detail not in {"compact", "full"}:
        raise LabToolError("BAD_REQUEST", "detail must be compact or full", 400)
    limit = max(1, min(int(request.get("max_capabilities") or ORIENT_DEFAULT_CAPABILITIES), ORIENT_MAX_CAPABILITIES))
    ttl = max(10, min(int(request.get("ttl_seconds") or LEASE_DEFAULT_TTL_SECONDS), LEASE_MAX_TTL_SECONDS))
    cards = _cards()
    selected_rows: list[tuple[int, JsonObject]] = []
    if explicit:
        seen: set[str] = set()
        for item in explicit:
            name = str(item or "").strip()
            if not name or name in seen:
                continue
            seen.add(name)
            card = cards.get(name)
            if card is None:
                raise LabToolError("TOOL_NOT_FOUND", f"capability not registered: {name}", 404)
            selected_rows.append((1000, card))
    else:
        terms = _tokenize(goal)
        for card in cards.values():
            if categories and str(card.get("category") or "").lower() not in categories:
                continue
            if effect_classes and str(card.get("side_effect_class") or "").lower() not in effect_classes:
                continue
            if not include_mutating and bool(card.get("mutating")):
                continue
            score = _score_card(card, terms)
            selected_rows.append((score, card))
        selected_rows.sort(key=lambda pair: (-pair[0], str(pair[1].get("name") or "")))
        if terms:
            selected_rows = [pair for pair in selected_rows if pair[0] > 0]
    # Full-detail discovery is larger per card, but explicit capability requests must not be silently truncated.
    # Agents use explicit lists to obtain exact invocation grammar; dropping requested contracts creates hidden capability state.
    if detail == "full" and not explicit:
        limit = min(limit, 8)
    selected_rows = selected_rows[:limit]
    renderer = _full_card if detail == "full" else _compact_card
    rendered = [renderer(card, score) for score, card in selected_rows]
    if not rendered:
        return {
            "ok": True,
            "schema": "pcmmad.schema-vnext.orient.v1",
            "schema_version": SCHEMA_VNEXT_VERSION,
            "goal": goal,
            "count": 0,
            "capabilities": [],
            "lease": None,
            "next_action": "refine goal/query or provide explicit categories/capabilities",
            "scheduler_profile": _scheduler_profile_status(),
            "claim_ceiling": "no relevant capability was selected; no authority granted",
        }
    lease = _selected_lease_payload(
        goal=goal,
        project_id=str(request.get("project_id") or "").strip() or None,
        selected=rendered,
        ttl_seconds=ttl,
        catalog_digest=_catalog_digest(cards),
    )
    return {
        "ok": True,
        "schema": "pcmmad.schema-vnext.orient.v1",
        "schema_version": SCHEMA_VNEXT_VERSION,
        "goal": goal,
        "count": len(rendered),
        "capabilities": rendered,
        "lease": lease,
        "scheduler_profile": _scheduler_profile_status(),
        "claim_ceiling": "capability discovery/currentness context only; no authority granted",
        "law": "CAPABILITY_LEASE != CAPABILITY_GRANT",
    }


def validate_lease(lease_value: Mapping[str, Any]) -> JsonObject:
    lease = _require_object(dict(lease_value), "lease")
    supplied = str(lease.get("lease_digest") or "").strip().lower()
    if not DIGEST_RE.fullmatch(supplied):
        raise LabToolError("CAPABILITY_LEASE_INVALID", "lease_digest is malformed", 400)
    core = dict(lease)
    core.pop("lease_digest", None)
    if _hash_json(core) != supplied:
        raise LabToolError("CAPABILITY_LEASE_INVALID", "lease content digest mismatch", 409)
    expires = float(lease.get("expires_at_epoch") or 0)
    if time.time() > expires:
        raise LabToolError("CAPABILITY_LEASE_EXPIRED", "capability lease expired", 409)
    selected = lease.get("selected") or []
    if not isinstance(selected, list) or not selected:
        raise LabToolError("CAPABILITY_LEASE_INVALID", "lease has no selected capabilities", 409)
    cards = _cards()
    stale: list[JsonObject] = []
    for row in selected:
        if not isinstance(row, dict):
            raise LabToolError("CAPABILITY_LEASE_INVALID", "lease selected entry is invalid", 409)
        name = str(row.get("name") or "")
        current = cards.get(name)
        if current is None:
            stale.append({"name": name, "reason": "not_registered"})
            continue
        expected = str(row.get("contract_digest") or "").lower()
        observed = str(current.get("contract_digest") or "").lower()
        if expected != observed:
            stale.append(
                {
                    "name": name,
                    "reason": "contract_changed",
                    "expected_contract_digest": expected,
                    "current_contract_digest": observed,
                }
            )
    if stale:
        raise LabToolError(
            "CAPABILITY_LEASE_STALE",
            "one or more leased capability contracts changed",
            409,
            stale=stale[:16],
        )
    return {
        "ok": True,
        "current": True,
        "lease_digest": supplied,
        "expires_at_epoch": expires,
        "selected_count": len(selected),
        "catalog_digest_current": _catalog_digest(cards),
        "catalog_digest_at_issue": lease.get("catalog_digest_at_issue"),
    }


def _lease_contract_for(lease: Mapping[str, Any] | None, capability: str) -> str | None:
    if lease is None:
        return None
    validate_lease(lease)
    for row in lease.get("selected") or []:
        if isinstance(row, dict) and row.get("name") == capability:
            return str(row.get("contract_digest") or "") or None
    raise LabToolError(
        "CAPABILITY_NOT_IN_LEASE",
        f"capability {capability!r} is not in the supplied lease",
        409,
    )


def invoke(payload: Mapping[str, Any]) -> JsonObject:
    request = _require_object(dict(payload), "payload")
    capability = str(request.get("capability") or "").strip()
    if not capability:
        raise LabToolError("BAD_REQUEST", "capability is required", 400)
    arguments = request.get("arguments") or {}
    authority = request.get("authority") or {}
    if not isinstance(arguments, dict):
        raise LabToolError("BAD_REQUEST", "arguments must be an object", 400)
    if not isinstance(authority, dict):
        raise LabToolError("BAD_REQUEST", "authority must be an object", 400)
    lease_value = request.get("lease")
    lease = _require_object(lease_value, "lease") if lease_value is not None else None
    expected = request.get("expected_contract_digest")
    lease_expected = _lease_contract_for(lease, capability)
    if lease is not None:
        lease_project = str(lease.get("project_id") or "").strip()
        argument_project = str(arguments.get("project_id") or "").strip()
        if lease_project and argument_project and lease_project != argument_project:
            raise LabToolError(
                "CAPABILITY_LEASE_PROJECT_MISMATCH",
                "invoke project_id differs from supplied advisory lease context",
                409,
                lease_project_id=lease_project,
                requested_project_id=argument_project,
            )
    if expected is None:
        expected = lease_expected
    elif lease_expected is not None and str(expected).strip().lower() != lease_expected.lower():
        raise LabToolError(
            "CAPABILITY_LEASE_CONTRACT_CONFLICT",
            "explicit expected contract digest conflicts with leased contract digest",
            409,
        )
    if expected is None:
        raise LabToolError(
            "EXPECTED_CONTRACT_REQUIRED",
            "vNext invoke requires expected_contract_digest or a current capability lease",
            400,
        )
    return dispatch_tool(
        capability,
        dict(arguments),
        authority=dict(authority),
        expected_contract_digest=_require_digest(expected, "expected_contract_digest"),
    )


def _walk_refs(value: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, dict):
        if set(value) == {"$ref"} and isinstance(value.get("$ref"), str):
            refs.add(str(value["$ref"]))
        else:
            for child in value.values():
                refs.update(_walk_refs(child))
    elif isinstance(value, list):
        for child in value:
            refs.update(_walk_refs(child))
    return refs


def _ref_node_id(ref: str) -> str:
    return str(ref).split(".", 1)[0]


def _current_scheduler_profile() -> tuple[JsonObject, JsonObject, dict[str, JsonObject]]:
    cards = _cards()
    profile, verification = load_current_effect_profile(cards)
    return profile, verification, effect_entry_map(profile)


def _is_parallel_safe_entry(entry: Mapping[str, Any]) -> bool:
    return str(entry.get("schedule_class") or "") == "PARALLEL_READ_VERIFIED"


def _effect_snapshot(entry: Mapping[str, Any]) -> JsonObject:
    return {
        "declared_effect_kind": entry.get("declared_effect_kind"),
        "effect_kind": entry.get("effect_kind"),
        "effect_truth_verified": bool(entry.get("effect_truth_verified")),
        "effect_truth_witness": entry.get("effect_truth_witness"),
        "schedule_class": entry.get("schedule_class"),
        "resume_replay_class": entry.get("resume_replay_class"),
        "static_cost_units": int(entry.get("static_cost_units") or 0),
        "retry_class": entry.get("retry_class"),
        "freshness_classes": list(entry.get("freshness_classes") or []),
        "mutating": bool(entry.get("mutating")),
        "effective_approval_required": bool(entry.get("effective_approval_required")),
        "parallel_witness": entry.get("parallel_witness"),
        "resume_replay_witness": entry.get("resume_replay_witness"),
    }

def _topological_stages(nodes: list[JsonObject]) -> list[list[str]]:
    by_id = {str(node["id"]): node for node in nodes}
    incoming = {node_id: set(map(str, node.get("depends_on") or [])) for node_id, node in by_id.items()}
    stages: list[list[str]] = []
    remaining = set(by_id)
    while remaining:
        ready = sorted(node_id for node_id in remaining if not (incoming[node_id] & remaining))
        if not ready:
            raise LabToolError("PLAN_CYCLE", "plan dependency graph contains a cycle", 400)
        stages.append(ready)
        remaining.difference_update(ready)
    return stages


def _condition_refs(condition: Any) -> set[str]:
    if condition is None:
        return set()
    if not isinstance(condition, dict):
        raise LabToolError("BAD_PLAN", "node when condition must be an object", 400)
    ref = condition.get("ref")
    if not isinstance(ref, str) or not ref.strip():
        raise LabToolError("BAD_PLAN", "node when condition requires ref", 400)
    return {ref.strip()}


def _assertion_refs(assertions: Any) -> set[str]:
    if assertions is None:
        return set()
    if not isinstance(assertions, list) or len(assertions) > PLAN_MAX_ASSERTIONS:
        raise LabToolError("BAD_PLAN", f"assertions must be an array of at most {PLAN_MAX_ASSERTIONS}", 400)
    refs: set[str] = set()
    for item in assertions:
        if not isinstance(item, dict) or not isinstance(item.get("ref"), str):
            raise LabToolError("BAD_PLAN", "each assertion requires a ref", 400)
        refs.add(str(item["ref"]))
    return refs


def compose(payload: Mapping[str, Any]) -> JsonObject:
    request = _require_object(dict(payload), "payload")
    raw_nodes = request.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise LabToolError("BAD_PLAN", "nodes must be a non-empty array", 400)
    if len(raw_nodes) > PLAN_MAX_NODES:
        raise LabToolError("PLAN_LIMIT_EXCEEDED", f"nodes exceeds maximum {PLAN_MAX_NODES}", 400)
    lease_value = request.get("lease")
    lease = _require_object(lease_value, "lease") if lease_value is not None else None
    if lease is not None:
        validate_lease(lease)
        lease_project = str(lease.get("project_id") or "").strip()
        request_project = str(request.get("project_id") or "").strip()
        if lease_project and request_project and lease_project != request_project:
            raise LabToolError(
                "CAPABILITY_LEASE_PROJECT_MISMATCH",
                "compose project_id differs from supplied advisory lease context",
                409,
                lease_project_id=lease_project,
                requested_project_id=request_project,
            )
    cards = _cards()
    effect_profile, effect_verification, effect_entries = _current_scheduler_profile()
    normalized: list[JsonObject] = []
    seen: set[str] = set()
    for raw in raw_nodes:
        node = _require_object(raw, "node")
        node_id = str(node.get("id") or "").strip()
        if not NODE_ID_RE.fullmatch(node_id) or node_id in seen:
            raise LabToolError("BAD_PLAN", f"node id is invalid or duplicate: {node_id!r}", 400)
        seen.add(node_id)
        capability = str(node.get("capability") or "").strip()
        card = cards.get(capability)
        if card is None:
            raise LabToolError("TOOL_NOT_FOUND", f"capability not registered: {capability}", 404)
        arguments = node.get("arguments") or {}
        if not isinstance(arguments, dict):
            raise LabToolError("BAD_PLAN", f"node {node_id} arguments must be an object", 400)
        if "authority" in node:
            raise LabToolError("AUTHORITY_IN_PLAN_FORBIDDEN", "plan nodes cannot carry authority", 400)
        explicit_deps = node.get("depends_on") or []
        if not isinstance(explicit_deps, list):
            raise LabToolError("BAD_PLAN", f"node {node_id} depends_on must be an array", 400)
        refs = _walk_refs(arguments) | _condition_refs(node.get("when"))
        deps = {str(item) for item in explicit_deps if str(item).strip()}
        deps.update(_ref_node_id(ref) for ref in refs)
        if node_id in deps:
            raise LabToolError("PLAN_CYCLE", f"node {node_id} depends on itself", 400)
        expected = node.get("expected_contract_digest")
        lease_expected = _lease_contract_for(lease, capability)
        if lease is not None and lease_expected is None:
            raise LabToolError(
                "CAPABILITY_NOT_IN_LEASE",
                f"capability {capability} is outside the supplied advisory lease scope",
                409,
            )
        if expected is None:
            expected = lease_expected or card.get("contract_digest")
        expected = _require_digest(expected, f"node {node_id} expected_contract_digest")
        if lease_expected is not None and expected != lease_expected.lower():
            raise LabToolError("CAPABILITY_LEASE_CONTRACT_CONFLICT", f"node {node_id} contract conflicts with lease", 409)
        effect_entry = effect_entries.get(capability)
        if effect_entry is None:
            raise LabToolError("EFFECT_PROFILE_STALE", f"capability missing from current scheduler effect profile: {capability}", 409)
        normalized.append(
            {
                "id": node_id,
                "capability": capability,
                "arguments": dict(arguments),
                "depends_on": sorted(deps),
                "expected_contract_digest": expected,
                "parallel_safe": _is_parallel_safe_entry(effect_entry),
                "effect": _effect_snapshot(effect_entry),
                **({"when": dict(node["when"])} if isinstance(node.get("when"), dict) else {}),
            }
        )
    ids = {node["id"] for node in normalized}
    for node in normalized:
        unknown = [dep for dep in node["depends_on"] if dep not in ids]
        if unknown:
            raise LabToolError("BAD_PLAN", f"node {node['id']} depends on unknown nodes", 400, unknown=unknown)
    assertions = request.get("assertions") or []
    assertion_refs = _assertion_refs(assertions)
    unknown_assert_refs = sorted({_ref_node_id(ref) for ref in assertion_refs} - ids)
    if unknown_assert_refs:
        raise LabToolError("BAD_PLAN", "assertion references unknown node", 400, unknown=unknown_assert_refs)
    stages = _topological_stages(normalized)
    static_cost_units = sum(int(node["effect"].get("static_cost_units") or 0) for node in normalized)
    max_cost_units = max(1, min(int(request.get("max_cost_units") or PLAN_DEFAULT_MAX_STATIC_COST_UNITS), PLAN_MAX_STATIC_COST_UNITS))
    if static_cost_units > max_cost_units:
        raise LabToolError(
            "PLAN_COST_EXCEEDED",
            f"static plan cost {static_cost_units} exceeds caller budget {max_cost_units}",
            409,
            static_cost_units=static_cost_units,
            max_cost_units=max_cost_units,
            cost_semantics=effect_profile.get("cost_semantics"),
        )
    plan: JsonObject = {
        "schema": "pcmmad.capability-plan.v1",
        "authority_effect": "NONE",
        "project_id": str(request.get("project_id") or "").strip() or None,
        "goal": str(request.get("goal") or "").strip() or None,
        "nodes": normalized,
        "stages": stages,
        "assertions": assertions,
        "stop_on_error": bool(request.get("stop_on_error", True)),
        "max_parallelism": max(1, min(int(request.get("max_parallelism") or 4), PLAN_MAX_PARALLELISM)),
        "static_cost_units": static_cost_units,
        "max_cost_units": max_cost_units,
        "cost_semantics": effect_profile.get("cost_semantics"),
        "max_resolved_argument_bytes": PLAN_MAX_RESOLVED_ARGUMENT_BYTES,
        "effect_profile_digest": effect_profile.get("profile_digest"),
        "effect_catalog_digest": effect_verification.get("catalog_digest"),
        "lease_digest": lease.get("lease_digest") if lease else None,
    }
    if len(safe_json_dumps(plan).encode("utf-8")) > PLAN_MAX_SERIALIZED_BYTES:
        raise LabToolError(
            "PLAN_TOO_LARGE",
            f"serialized plan exceeds {PLAN_MAX_SERIALIZED_BYTES} bytes",
            400,
        )
    plan["plan_digest"] = _hash_json(plan)
    return {
        "ok": True,
        "schema": "pcmmad.schema-vnext.compose.v1",
        "composed_at": utc_now(),
        "plan": plan,
        "plan_digest": plan["plan_digest"],
        "node_count": len(normalized),
        "stage_count": len(stages),
        "parallel_safe_nodes": [node["id"] for node in normalized if node["parallel_safe"]],
        "effect_profile": {
            "current": True,
            "profile_digest": effect_profile.get("profile_digest"),
            "parallel_verified_count": effect_verification.get("parallel_verified_count"),
            "descriptive_traits_scheduler_authority": False,
        },
        "static_cost_units": static_cost_units,
        "max_cost_units": max_cost_units,
        "authority_required_nodes": [
            node["id"] for node in normalized if node["effect"]["effective_approval_required"]
        ],
        "claim_ceiling": "validated/sealed plan only; not executed and no authority granted",
    }


def _validate_plan(plan_value: Mapping[str, Any], expected_digest: Any | None = None) -> JsonObject:
    plan = _require_object(dict(plan_value), "plan")
    supplied = str(plan.get("plan_digest") or "").strip().lower()
    if not DIGEST_RE.fullmatch(supplied):
        raise LabToolError("PLAN_INVALID", "plan_digest is missing or malformed", 400)
    core = dict(plan)
    core.pop("plan_digest", None)
    observed = _hash_json(core)
    if observed != supplied:
        raise LabToolError("PLAN_INVALID", "plan content digest mismatch", 409)
    if expected_digest is not None and _require_digest(expected_digest, "expected_plan_digest") != supplied:
        raise LabToolError("PLAN_STALE", "expected plan digest does not match supplied plan", 409)
    if str(plan.get("authority_effect") or "").upper() != "NONE":
        raise LabToolError("PLAN_INVALID", "plan authority_effect must remain NONE", 409)
    if len(safe_json_dumps(core).encode("utf-8")) > PLAN_MAX_SERIALIZED_BYTES:
        raise LabToolError("PLAN_TOO_LARGE", f"serialized plan exceeds {PLAN_MAX_SERIALIZED_BYTES} bytes", 400)
    nodes = plan.get("nodes") or []
    if not isinstance(nodes, list) or not nodes or len(nodes) > PLAN_MAX_NODES:
        raise LabToolError("PLAN_INVALID", "plan nodes are missing or exceed limit", 400)
    ids: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            raise LabToolError("PLAN_INVALID", "plan node is not an object", 400)
        node_id = str(node.get("id") or "").strip()
        if not NODE_ID_RE.fullmatch(node_id) or node_id in ids:
            raise LabToolError("PLAN_INVALID", f"plan node id is invalid or duplicate: {node_id!r}", 400)
        ids.add(node_id)
    cards = _cards()
    stale: list[JsonObject] = []
    for node in nodes:
        node_id = str(node["id"])
        if "authority" in node:
            raise LabToolError("AUTHORITY_IN_PLAN_FORBIDDEN", "plan nodes cannot carry authority", 400)
        arguments = node.get("arguments") or {}
        if not isinstance(arguments, dict):
            raise LabToolError("PLAN_INVALID", f"node {node_id} arguments must be an object", 400)
        deps = node.get("depends_on") or []
        if not isinstance(deps, list):
            raise LabToolError("PLAN_INVALID", f"node {node_id} depends_on must be an array", 400)
        dep_set = {str(item) for item in deps if str(item).strip()}
        refs = _walk_refs(arguments) | _condition_refs(node.get("when"))
        required_from_refs = {_ref_node_id(ref) for ref in refs}
        if not required_from_refs.issubset(dep_set):
            raise LabToolError("PLAN_INVALID", f"node {node_id} omits dataflow dependency", 409)
        unknown = sorted(dep_set - ids)
        if unknown or node_id in dep_set:
            raise LabToolError("PLAN_INVALID", f"node {node_id} has invalid dependencies", 400, unknown=unknown)
        name = str(node.get("capability") or "")
        card = cards.get(name)
        if card is None:
            stale.append({"node": node_id, "capability": name, "reason": "not_registered"})
            continue
        expected = str(node.get("expected_contract_digest") or "").lower()
        current = str(card.get("contract_digest") or "").lower()
        if expected != current:
            stale.append({
                "node": node_id,
                "capability": name,
                "reason": "contract_changed",
                "expected_contract_digest": expected,
                "current_contract_digest": current,
            })
    if stale:
        raise LabToolError("PLAN_CAPABILITY_STALE", "one or more native capability contracts changed", 409, stale=stale[:16])
    effect_profile, effect_verification, effect_entries = _current_scheduler_profile()
    if plan.get("effect_profile_digest") != effect_profile.get("profile_digest"):
        raise LabToolError("PLAN_EFFECT_PROFILE_STALE", "sealed plan effect profile differs from current scheduler profile", 409)
    if plan.get("effect_catalog_digest") != effect_verification.get("catalog_digest"):
        raise LabToolError("PLAN_EFFECT_PROFILE_STALE", "sealed plan capability catalog differs from current scheduler profile", 409)
    for node in nodes:
        node_id = str(node["id"])
        name = str(node.get("capability") or "")
        effect_entry = effect_entries.get(name)
        if effect_entry is None:
            raise LabToolError("PLAN_EFFECT_PROFILE_STALE", f"capability missing from current scheduler effect profile: {name}", 409)
        if bool(node.get("parallel_safe")) != _is_parallel_safe_entry(effect_entry):
            raise LabToolError("PLAN_DERIVATION_TAMPERED", f"node {node_id} parallel-safety derivation disagrees with current closed effect profile", 409)
        if node.get("effect") != _effect_snapshot(effect_entry):
            raise LabToolError("PLAN_DERIVATION_TAMPERED", f"node {node_id} effect derivation disagrees with current closed effect profile", 409)
    recomputed_cost = sum(int((node.get("effect") or {}).get("static_cost_units") or 0) for node in nodes)
    stored_cost = int(plan.get("static_cost_units") or -1)
    max_cost = int(plan.get("max_cost_units") or -1)
    if stored_cost != recomputed_cost or max_cost < 1 or max_cost > PLAN_MAX_STATIC_COST_UNITS:
        raise LabToolError("PLAN_DERIVATION_TAMPERED", "stored plan cost metadata disagrees with current closed effect profile", 409)
    if recomputed_cost > max_cost:
        raise LabToolError("PLAN_COST_EXCEEDED", "sealed plan exceeds its own static cost budget", 409, static_cost_units=recomputed_cost, max_cost_units=max_cost)
    if plan.get("cost_semantics") != effect_profile.get("cost_semantics"):
        raise LabToolError("PLAN_DERIVATION_TAMPERED", "stored plan cost semantics differ from current effect profile", 409)
    if int(plan.get("max_resolved_argument_bytes") or -1) != PLAN_MAX_RESOLVED_ARGUMENT_BYTES:
        raise LabToolError(
            "PLAN_DERIVATION_TAMPERED",
            "stored plan resolved-argument ceiling differs from current Runtime contract",
            409,
        )
    recomputed_stages = _topological_stages([dict(node) for node in nodes])
    if plan.get("stages") != recomputed_stages:
        raise LabToolError("PLAN_DERIVATION_TAMPERED", "stored plan stages disagree with dependency graph", 409)
    assertion_refs = _assertion_refs(plan.get("assertions") or [])
    unknown_assert = sorted({_ref_node_id(ref) for ref in assertion_refs} - ids)
    if unknown_assert:
        raise LabToolError("PLAN_INVALID", "assertion references unknown node", 400, unknown=unknown_assert)
    return plan


def _lookup_ref(ref: str, results: Mapping[str, Any]) -> Any:
    parts = str(ref).split(".")
    if not parts or parts[0] not in results:
        raise LabToolError("PLAN_REF_UNRESOLVED", f"reference cannot be resolved: {ref}", 409)
    value: Any = results[parts[0]]
    for part in parts[1:]:
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            raise LabToolError("PLAN_REF_UNRESOLVED", f"reference cannot be resolved: {ref}", 409)
    return value


def _resolve_refs(value: Any, results: Mapping[str, Any]) -> Any:
    if isinstance(value, dict):
        if set(value) == {"$ref"}:
            return _lookup_ref(str(value["$ref"]), results)
        return {str(key): _resolve_refs(child, results) for key, child in value.items()}
    if isinstance(value, list):
        return [_resolve_refs(child, results) for child in value]
    return value


def _condition_true(condition: Mapping[str, Any] | None, results: Mapping[str, Any]) -> bool:
    if not condition:
        return True
    value = _lookup_ref(str(condition.get("ref")), results)
    if "equals" in condition:
        return value == condition.get("equals")
    if "not_equals" in condition:
        return value != condition.get("not_equals")
    if "exists" in condition:
        return bool(condition.get("exists"))
    if "truthy" in condition:
        return bool(value) is bool(condition.get("truthy"))
    return bool(value)


def _assert_plan(assertions: list[Any], results: Mapping[str, Any]) -> None:
    for index, raw in enumerate(assertions):
        item = _require_object(raw, f"assertions[{index}]")
        ref = str(item.get("ref") or "")
        value = _lookup_ref(ref, results)
        op = str(item.get("op") or "eq").lower()
        expected = item.get("value")
        passed = False
        if op == "eq":
            passed = value == expected
        elif op == "ne":
            passed = value != expected
        elif op == "in":
            passed = isinstance(expected, list) and value in expected
        elif op == "truthy":
            passed = bool(value)
        elif op == "falsey":
            passed = not bool(value)
        elif op == "exists":
            passed = True
        else:
            raise LabToolError("BAD_PLAN", f"unsupported assertion op: {op}", 400)
        if not passed:
            raise LabToolError(
                "PLAN_ASSERTION_FAILED",
                f"plan assertion {index} failed",
                409,
                ref=ref,
                op=op,
                expected=expected,
                observed=value,
            )


def _continuation_claim_path(project_id: str, handle: str) -> Path:
    return result_path(project_id, handle).with_suffix(".claimed")


def _node_resume_replay_safe(node: Mapping[str, Any]) -> bool:
    effect = node.get("effect") or {}
    return effect.get("resume_replay_class") == "REEXECUTE_READ_VERIFIED"


def _unsafe_completed_for_continuation(plan: Mapping[str, Any], completed: Mapping[str, Any]) -> list[str]:
    by_id = {str(node.get("id")): node for node in plan.get("nodes") or [] if isinstance(node, dict)}
    unsafe: list[str] = []
    for node_id, result in completed.items():
        if isinstance(result, dict) and result.get("status") == "SKIPPED":
            continue
        node = by_id.get(str(node_id))
        if node is None or not _node_resume_replay_safe(node):
            unsafe.append(str(node_id))
    return sorted(unsafe)


def _blocked_plan_response(
    project_id: str,
    *,
    plan: JsonObject,
    completed: JsonObject,
    blocked_node: JsonObject,
    error: LabToolError,
) -> JsonObject:
    unsafe_completed = _unsafe_completed_for_continuation(plan, completed)
    if unsafe_completed:
        return {
            "ok": False,
            "status": "BLOCKED_RECOVERY_REQUIRED",
            "blocked_node": blocked_node.get("id"),
            "error_code": error.error_code,
            "message": error.message,
            "error": {"status": error.status, "extra": error.extra},
            "completed": completed,
            "unsafe_completed_nodes": unsafe_completed,
            "continuation": None,
            "required_action": "recover/read back prior effects, then recompose from current state",
            "law": "CONTINUATION != CURRENTNESS",
        }
    continuation = _store_continuation(
        project_id,
        plan=plan,
        completed=completed,
        blocked_node=blocked_node,
        error=error,
    )
    return {
        "ok": False,
        "status": "BLOCKED",
        "blocked_node": blocked_node.get("id"),
        "error_code": error.error_code,
        "message": error.message,
        "error": {"status": error.status, "extra": error.extra},
        "completed": completed,
        "continuation": continuation,
        "resume_policy": "REEXECUTE_ALL_COMPLETED_READS",
        "law": "CONTINUATION != CURRENTNESS",
    }


def _store_continuation(
    project_id: str,
    *,
    plan: JsonObject,
    completed: JsonObject,
    blocked_node: JsonObject,
    error: LabToolError,
) -> JsonObject:
    secret = secrets.token_urlsafe(24)
    token_hash = hashlib.sha256(secret.encode("utf-8")).hexdigest()
    payload = {
        "schema": "pcmmad.plan-continuation.v1",
        "status": "BLOCKED",
        "authority_effect": "NONE",
        "plan": plan,
        "completed": completed,
        "completed_freshness": {str(node_id): "STALE_ON_RESUME" for node_id in completed},
        "resume_policy": "REEXECUTE_ALL_COMPLETED_READS",
        "blocked_node_id": blocked_node.get("id"),
        "blocked_error": {
            "error_code": error.error_code,
            "message": error.message,
            "status": error.status,
            "extra": error.extra,
        },
        "resume_token_sha256": token_hash,
    }
    meta = store_result(project_id, payload, label="schema-vnext-continuation", tool_name="schema-vnext.execute")
    return {
        **meta,
        "resume_token": secret,
        "single_use": True,
        "claim_ceiling": "continuation stores control state only; authority must be supplied again and completed reads are re-executed on resume",
        "law": "CONTINUATION != CURRENTNESS",
    }


def _claim_continuation_once(project_id: str, handle: str, token: str, expected_hash: str) -> None:
    if hashlib.sha256(token.encode("utf-8")).hexdigest() != expected_hash:
        raise LabToolError("CONTINUATION_TOKEN_INVALID", "resume token does not match continuation", 403)
    claim = _continuation_claim_path(project_id, handle)
    try:
        fd = os.open(str(claim), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise LabToolError("CONTINUATION_ALREADY_CONSUMED", "continuation is single-use and was already consumed", 409) from exc
    try:
        os.write(fd, safe_json_dumps({"claimed_at": utc_now(), "handle": handle}).encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


def _node_authority(authorities: Mapping[str, Any], node_id: str) -> JsonObject:
    value = authorities.get(node_id) or {}
    if not isinstance(value, dict):
        raise LabToolError("BAD_REQUEST", f"authority for node {node_id} must be an object", 400)
    return dict(value)


def _execute_one(node: JsonObject, results: Mapping[str, Any], authorities: Mapping[str, Any]) -> JsonObject:
    if not _condition_true(node.get("when"), results):
        return {"ok": True, "status": "SKIPPED", "node": node["id"], "reason": "condition_false"}
    arguments = _resolve_refs(node.get("arguments") or {}, results)
    resolved_argument_bytes = len(safe_json_dumps(arguments).encode("utf-8"))
    if resolved_argument_bytes > PLAN_MAX_RESOLVED_ARGUMENT_BYTES:
        raise LabToolError(
            "PLAN_DATAFLOW_ARGUMENT_TOO_LARGE",
            f"resolved node arguments exceed {PLAN_MAX_RESOLVED_ARGUMENT_BYTES} bytes; pass a bounded result handle instead",
            413,
            node=node.get("id"),
            resolved_argument_bytes=resolved_argument_bytes,
            max_resolved_argument_bytes=PLAN_MAX_RESOLVED_ARGUMENT_BYTES,
        )
    return dispatch_tool(
        str(node["capability"]),
        arguments,
        authority=_node_authority(authorities, str(node["id"])),
        expected_contract_digest=str(node["expected_contract_digest"]),
    )


def _execute_plan_core(
    plan: JsonObject,
    *,
    authorities: Mapping[str, Any],
    project_id: str,
    initial_completed: Mapping[str, Any] | None = None,
) -> JsonObject:
    results: JsonObject = dict(initial_completed or {})
    node_map = {str(node["id"]): node for node in plan["nodes"]}
    stop_on_error = bool(plan.get("stop_on_error", True))
    parallelism = max(1, min(int(plan.get("max_parallelism") or 1), PLAN_MAX_PARALLELISM))
    failures: list[JsonObject] = []
    for stage in plan.get("stages") or []:
        pending = [node_map[node_id] for node_id in stage if node_id not in results]
        safe = [node for node in pending if bool(node.get("parallel_safe"))]
        unsafe = [node for node in pending if not bool(node.get("parallel_safe"))]
        if safe:
            with ThreadPoolExecutor(max_workers=min(parallelism, len(safe)), thread_name_prefix="pcmmad-plan-read") as pool:
                futures = {pool.submit(_execute_one, node, dict(results), authorities): node for node in safe}
                for future in as_completed(futures):
                    node = futures[future]
                    try:
                        results[str(node["id"])] = future.result()
                    except LabToolError as exc:
                        if exc.error_code in BLOCKABLE_PRE_EFFECT_ERRORS:
                            return _blocked_plan_response(
                                project_id,
                                plan=plan,
                                completed=results,
                                blocked_node=node,
                                error=exc,
                            )
                        failure = {"node": node["id"], "error_code": exc.error_code, "message": exc.message, "status": exc.status, "extra": exc.extra}
                        failures.append(failure)
                        results[str(node["id"])] = {"ok": False, "status": "FAILED", **failure}
                    except Exception as exc:
                        failure = {"node": node["id"], "error_code": type(exc).__name__, "message": str(exc), "status": 500}
                        failures.append(failure)
                        results[str(node["id"])] = {"ok": False, "status": "FAILED", **failure}
            if failures and stop_on_error:
                break
        for node in unsafe:
            if failures and stop_on_error:
                break
            try:
                results[str(node["id"])] = _execute_one(node, results, authorities)
            except LabToolError as exc:
                if exc.error_code in BLOCKABLE_PRE_EFFECT_ERRORS:
                    return _blocked_plan_response(
                        project_id,
                        plan=plan,
                        completed=results,
                        blocked_node=node,
                        error=exc,
                    )
                failure = {"node": node["id"], "error_code": exc.error_code, "message": exc.message, "status": exc.status, "extra": exc.extra}
                failures.append(failure)
                results[str(node["id"])] = {"ok": False, "status": "FAILED", **failure}
            except Exception as exc:
                failure = {"node": node["id"], "error_code": type(exc).__name__, "message": str(exc), "status": 500}
                failures.append(failure)
                results[str(node["id"])] = {"ok": False, "status": "FAILED", **failure}
    if failures:
        return {"ok": False, "status": "FAILED", "plan_digest": plan["plan_digest"], "results": results, "failures": failures}
    try:
        _assert_plan(list(plan.get("assertions") or []), results)
    except LabToolError as exc:
        if exc.error_code != "PLAN_ASSERTION_FAILED":
            raise
        return {
            "ok": False,
            "status": "POSTCONDITION_FAILED",
            "plan_digest": plan["plan_digest"],
            "results": results,
            "failures": [{"error_code": exc.error_code, "message": exc.message, "status": exc.status, "extra": exc.extra}],
            "warning": "plan is not transactional; prior node consequences are preserved",
        }
    return {"ok": True, "status": "COMPLETED", "plan_digest": plan["plan_digest"], "results": results, "failures": []}


def _compact_failures(failures: Any, *, max_items: int = 8) -> list[JsonObject]:
    if not isinstance(failures, list):
        return []
    out: list[JsonObject] = []
    for raw in failures[:max_items]:
        if not isinstance(raw, dict):
            out.append({"error_code": "UNKNOWN_FAILURE", "message": str(raw)[:500]})
            continue
        item: JsonObject = {
            key: raw.get(key)
            for key in ("node", "error_code", "message", "status")
            if raw.get(key) is not None
        }
        if "message" in item:
            item["message"] = str(item["message"])[:500]
        if raw.get("extra"):
            item["extra_summary"] = summarize_payload(raw.get("extra"), preview_chars=500)
        out.append(item)
    return out


def _bounded_execution_response(project_id: str, response: JsonObject) -> JsonObject:
    raw = safe_json_dumps(response).encode("utf-8")
    if len(raw) <= PLAN_INLINE_SAFE_BYTES:
        return response
    if response.get("status") in {"BLOCKED", "BLOCKED_RECOVERY_REQUIRED"}:
        compact = dict(response)
        completed = compact.pop("completed", {})
        compact["completed_node_ids"] = sorted(completed) if isinstance(completed, dict) else []
        compact["completed_summary"] = summarize_payload(completed, preview_chars=800)
        return compact
    meta = store_result(
        project_id,
        response,
        label="schema-vnext-plan-execution",
        tool_name="schema-vnext.execute",
    )
    compact: JsonObject = {
        "ok": bool(response.get("ok")),
        "status": response.get("status"),
        "plan_digest": response.get("plan_digest"),
        "result_handle": meta,
        "summary": summarize_payload(response, preview_chars=1200),
        "full_available": True,
        "observe_hint": {"kind": "result", "project_id": project_id, "ref": meta["handle"], "mode": "preview"},
    }
    failures = _compact_failures(response.get("failures"))
    if failures:
        compact["failures"] = failures
    return compact


def execute(payload: Mapping[str, Any]) -> JsonObject:
    request = _require_object(dict(payload), "payload")
    project_id = str(request.get("project_id") or "").strip()
    if not project_id:
        raise LabToolError("BAD_REQUEST", "project_id is required for vNext plan execution", 400)
    plan = _validate_plan(_require_object(request.get("plan"), "plan"), request.get("expected_plan_digest"))
    if plan.get("project_id") not in {None, project_id}:
        raise LabToolError("PLAN_PROJECT_MISMATCH", "execution project_id differs from sealed plan project", 409)
    authorities = request.get("authorities") or {}
    if not isinstance(authorities, dict):
        raise LabToolError("BAD_REQUEST", "authorities must be an object keyed by node id", 400)
    return _bounded_execution_response(
        project_id,
        _execute_plan_core(plan, authorities=authorities, project_id=project_id),
    )


def resume(payload: Mapping[str, Any]) -> JsonObject:
    request = _require_object(dict(payload), "payload")
    project_id = str(request.get("project_id") or "").strip()
    handle = str(request.get("continuation_handle") or "").strip()
    token = str(request.get("resume_token") or "")
    if not project_id or not handle or not token:
        raise LabToolError("BAD_REQUEST", "project_id, continuation_handle, and resume_token are required", 400)
    row = get_result(project_id, handle)
    if row.get("label") != "schema-vnext-continuation":
        raise LabToolError("CONTINUATION_INVALID", "result handle is not a schema-vNext continuation", 409)
    state = row.get("payload") or {}
    if not isinstance(state, dict) or state.get("schema") != "pcmmad.plan-continuation.v1":
        raise LabToolError("CONTINUATION_INVALID", "continuation payload is invalid", 409)
    blocked_error = state.get("blocked_error") or {}
    if blocked_error.get("error_code") == "CAPABILITY_CONTRACT_STALE":
        raise LabToolError("PLAN_RECOMPOSE_REQUIRED", "stale capability contract requires plan recomposition", 409)
    plan = _validate_plan(_require_object(state.get("plan"), "continuation plan"), request.get("expected_plan_digest"))
    if plan.get("project_id") not in {None, project_id}:
        raise LabToolError("PLAN_PROJECT_MISMATCH", "resume project_id differs from sealed plan project", 409)
    _claim_continuation_once(project_id, handle, token, str(state.get("resume_token_sha256") or ""))
    authorities = request.get("authorities") or {}
    if not isinstance(authorities, dict):
        raise LabToolError("BAD_REQUEST", "authorities must be an object keyed by node id", 400)
    completed = _require_object(state.get("completed") or {}, "completed")
    unsafe = _unsafe_completed_for_continuation(plan, completed)
    if unsafe:
        raise LabToolError(
            "CONTINUATION_RECOVERY_REQUIRED",
            "continuation contains prior effects that may not be replayed automatically",
            409,
            unsafe_completed_nodes=unsafe,
        )
    # Completed reads are evidence of what was current before the block, not now.
    # Re-run the plan from current state; native approval/currentness binding will
    # force a new challenge if refreshed read outputs change mutation arguments.
    return _bounded_execution_response(
        project_id,
        _execute_plan_core(
            plan,
            authorities=authorities,
            project_id=project_id,
            initial_completed=None,
        ),
    )


def observe(payload: Mapping[str, Any]) -> JsonObject:
    request = _require_object(dict(payload), "payload")
    kind = str(request.get("kind") or "").strip().lower()
    if kind == "lease":
        return {"ok": True, "kind": "lease", "validation": validate_lease(_require_object(request.get("lease"), "lease"))}
    if kind == "plan":
        plan = _validate_plan(_require_object(request.get("plan"), "plan"), request.get("expected_plan_digest"))
        return {"ok": True, "kind": "plan", "current": True, "plan_digest": plan["plan_digest"], "node_count": len(plan["nodes"])}
    if kind == "capability":
        name = str(request.get("ref") or request.get("capability") or "").strip()
        card = _cards().get(name)
        if card is None:
            raise LabToolError("TOOL_NOT_FOUND", f"capability not registered: {name}", 404)
        return {"ok": True, "kind": "capability", "capability": _full_card(card)}
    if kind == "effect_profile":
        profile, verification, entries = _current_scheduler_profile()
        name = str(request.get("ref") or request.get("capability") or "").strip()
        response: JsonObject = {
            "ok": True,
            "kind": "effect_profile",
            "current": True,
            "profile_digest": profile.get("profile_digest"),
            "catalog_digest": verification.get("catalog_digest"),
            "capability_count": verification.get("capability_count"),
            "effect_truth_verified_count": verification.get("effect_truth_verified_count"),
            "parallel_verified_count": verification.get("parallel_verified_count"),
            "resume_replay_verified_count": verification.get("resume_replay_verified_count"),
            "closed_vocabularies": {
                "effect_kinds": list(profile.get("effect_kinds") or []),
                "schedule_classes": list(profile.get("schedule_classes") or []),
                "resume_replay_classes": list(profile.get("resume_replay_classes") or []),
                "retry_classes": list(profile.get("retry_classes") or []),
                "freshness_classes": list(profile.get("freshness_classes") or []),
            },
            "law": "DESCRIPTIVE_EFFECT_TRAITS != SCHEDULER_AUTHORITY",
        }
        if name:
            entry = entries.get(name)
            if entry is None:
                raise LabToolError("TOOL_NOT_FOUND", f"capability not in current effect profile: {name}", 404)
            response["capability"] = entry
        return response
    if kind == "result" or kind == "continuation":
        project_id = str(request.get("project_id") or "").strip()
        handle = str(request.get("ref") or request.get("handle") or "").strip()
        if not project_id or not handle:
            raise LabToolError("BAD_REQUEST", "project_id and result ref are required", 400)
        mode = str(request.get("mode") or "auto").strip().lower()
        if kind == "continuation":
            meta = result_metadata(project_id, handle)
            claim = _continuation_claim_path(project_id, handle)
            return {"ok": True, "kind": "continuation", "claimed": claim.exists(), **meta}
        meta = result_metadata(project_id, handle)
        if mode == "metadata":
            return {"ok": True, "kind": "result", "mode": "metadata", **meta}
        if mode == "range":
            return {
                "ok": True,
                "kind": "result",
                "mode": "range",
                **read_result_range(
                    project_id,
                    handle,
                    offset_bytes=max(0, int(request.get("offset_bytes") or 0)),
                    length_bytes=max(1, min(int(request.get("length_bytes") or 32768), RESULT_RANGE_MAX_BYTES)),
                ),
            }
        row = get_result(project_id, handle)
        if mode == "preview" or (mode == "auto" and int(meta["bytes"]) > RESULT_INLINE_SAFE_BYTES):
            chars = max(200, min(int(request.get("preview_chars") or 1200), RESULT_PREVIEW_MAX_CHARS))
            return {"ok": True, "kind": "result", "mode": "preview", **meta, "summary": summarize_payload(row.get("payload"), preview_chars=chars)}
        if mode not in {"auto", "full"}:
            raise LabToolError("BAD_REQUEST", "result mode must be auto|full|metadata|preview|range", 400)
        return {"ok": True, "kind": "result", "mode": "full", **row}
    if kind == "job":
        project_id = str(request.get("project_id") or "").strip()
        job_id = str(request.get("ref") or request.get("job_id") or "").strip()
        if not project_id or not job_id:
            raise LabToolError("BAD_REQUEST", "project_id and job ref are required", 400)
        mode = str(request.get("mode") or "status").strip().lower()
        tool = {
            "status": "execution.status",
            "progress": "execution.progress",
            "wait": "execution.wait",
            "output": "execution.output",
        }.get(mode)
        if tool is None:
            raise LabToolError("BAD_REQUEST", "job mode must be status|progress|wait|output", 400)
        card = _cards()[tool]
        arguments: JsonObject = {"project_id": project_id, "job_id": job_id}
        if mode in {"wait", "output"}:
            if request.get("timeout_seconds") is not None:
                arguments["timeout_seconds"] = int(request.get("timeout_seconds"))
            if request.get("max_bytes") is not None:
                arguments["max_bytes"] = int(request.get("max_bytes"))
        return dispatch_tool(tool, arguments, expected_contract_digest=str(card["contract_digest"]))
    raise LabToolError("BAD_REQUEST", "kind must be lease|plan|capability|effect_profile|result|continuation|job", 400)


def transfer(payload: Mapping[str, Any]) -> JsonObject:
    request = _require_object(dict(payload), "payload")
    action = str(request.get("action") or "").strip().lower()
    native = TRANSFER_ACTION_MAP.get(action)
    if native is None:
        raise LabToolError("BAD_REQUEST", f"unsupported transfer action: {action}", 400)
    arguments = request.get("arguments") or {}
    authority = request.get("authority") or {}
    if not isinstance(arguments, dict) or not isinstance(authority, dict):
        raise LabToolError("BAD_REQUEST", "arguments and authority must be objects", 400)
    card = _cards()[native]
    return dispatch_tool(
        native,
        dict(arguments),
        authority=dict(authority),
        expected_contract_digest=str(card["contract_digest"]),
    )
