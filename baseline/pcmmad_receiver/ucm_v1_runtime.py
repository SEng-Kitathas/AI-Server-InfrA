"""User Continuity System v1.0 semantic/API layer over the existing Runtime ledger.

The existing ``user_continuity_store`` remains the single authoritative user-
continuity persistence engine.  UCS v1 records are stored as typed envelopes in
that same append-only/hash-chained/CAS ledger and its content-addressed snapshot.
This module supplies the stronger neutral v1 contract: orthogonal fact policy,
identity/referent/decision/control/candidate semantics, bounded fresh-instance
hydration, exact ingress failure taxonomy, and authority firewalls.

It deliberately does not create a second database, project-authority plane,
doctrine authority, or Runtime truth source.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import user_continuity_store as backend

JsonObject = dict[str, Any]

SYSTEM_VERSION = "1.0"
SYSTEM_ARCHIVE_SHA256 = "055a25fd8c02856d2a875aadc714dfa4ff49c0edeb0e63dd4d67415849fd5909"
SYSTEM_CONTRACT_SHA256 = "343a5ef8d8ffd02100464f63bd8bab19dd3b0a90b06283aa4ad2607f9f57faa7"
CORE_BUDGET_BYTES = 12_000
MIN_HEADROOM_BYTES = 2_000
MAX_EVENT_TAIL = 64
MAX_READ_GROUPS = 24
MAX_SEARCH_RESULTS = 100
MAX_CONTEXT_PACKET_BYTES = 64 * 1024
RETRIEVAL_ORDER = ("EXACT_KEY", "SNAPSHOT_SHARD", "LEXICAL_STRUCTURED", "SEMANTIC_LOCATOR", "SOURCE_FALLBACK")

AUTHORITY_TRAITS = (
    "user_owned_continuity",
    "not_project_authority",
    "not_runtime_truth",
    "not_doctrine_authority",
)

REQUIRED_INGRESS_SURFACES = frozenset(
    {
        "CANDIDATE_QUEUE_HEAD",
        "COLLABORATION_CONTRACT",
        "CONTROL_STATE",
        "CORE_SNAPSHOT",
        "DECISION_INDEX",
        "IDENTITY_INDEX",
        "REFERENT_INDEX",
        "SYSTEM_DESCRIPTOR",
        "USER_STORE_HEAD",
        "VERIFICATION_DEBT",
    }
)

CORE_HYDRATION_GROUPS = frozenset(
    {
        "collaboration",
        "control_state",
        "decision_index",
        "global_constraints",
        "high_value_scars",
        "identity",
        "referents",
        "verification_debt",
    }
)
LAZY_HYDRATION_GROUPS = frozenset(
    {"projects", "personal_sensitive", "deployment", "historical", "task_specific"}
)

FACT_LIFECYCLES = frozenset(
    {
        "ACTIVE",
        "HISTORICAL",
        "SUPERSEDED",
        "DEFERRED",
        "REJECTED",
        "UNKNOWN_CURRENTNESS",
        "RETIRED",
        "FORGET_REQUESTED",
        "CONFLICT",
    }
)
CURRENTNESS_STATES = frozenset({"CURRENT", "HISTORICAL", "SUPERSEDED", "CONFLICT", "UNKNOWN", "UNVERIFIED"})
VERIFY_LEVELS = frozenset({"NOT_REQUIRED", "CONDITIONAL", "REQUIRED"})
SOURCE_ROLES = frozenset({"AUTHORITATIVE", "CONTINUITY", "DONOR", "OBSERVATION", "INFERENCE", "SESSION_METADATA"})
SENSITIVITY = frozenset({"NORMAL", "PERSONAL", "SENSITIVE", "SECRET"})
EXPORT_CLASSES = frozenset({"PORTABLE", "USER", "DEPLOYMENT", "PROJECT"})
RELATION_TYPES = frozenset(
    {
        "SUPPORTED_BY",
        "VERIFIED_BY",
        "SUPERSEDES",
        "CONFLICTS_WITH",
        "DERIVED_FROM",
        "CORRECTED_BY_EVIDENCE",
        "REDISCOVERED_FROM",
        "CONCERNS_PROJECT",
        "MATERIALIZED_IN",
    }
)
IDENTITY_KINDS = frozenset(
    {
        "LEGAL_NAME", "GIVEN_NAME", "MIDDLE_NAME", "SURNAME", "PREFERRED_NAME", "NICKNAME",
        "DISPLAY_NAME", "HANDLE", "ALIAS", "TITLE", "LEGACY_SURNAME", "CONTACT_NAME", "OTHER",
    }
)
IDENTITY_STATUSES = frozenset({"ACTIVE", "HISTORICAL", "SUPERSEDED", "CONTEXTUAL", "UNKNOWN_CURRENTNESS"})
IDENTITY_USES = frozenset(
    {"NORMAL_ADDRESS", "LEGAL_REFERENCE", "ACCOUNT_LOOKUP", "PROJECT_ADDRESS", "SIMULATION_TITLE", "EXTERNAL_CONTACT", "SEARCH_ALIAS", "FAMILY_LEGACY", "OTHER"}
)
REFERENT_STATUSES = frozenset({"ACTIVE", "CONTEXTUAL", "HISTORICAL", "SUPERSEDED", "AMBIGUOUS"})
DECISION_STATUSES = frozenset({"ACTIVE", "HISTORICAL", "SUPERSEDED", "DEFERRED", "REJECTED", "CONFLICT"})
CANDIDATE_STATUSES = frozenset({"PENDING_USER_CONFIRMATION", "ACCEPTED", "REJECTED", "EXPIRED"})
WRITE_POSTURES = frozenset({"DIRECT_USER_AUTHORIZED", "PROPOSE_ONLY", "SYSTEM_MAINTENANCE", "DO_NOT_PERSIST", "USER_STATED_DURABLE"})
RECORD_TYPES = frozenset({"FACT", "IDENTITY", "REFERENT", "COLLABORATION_CONTRACT", "MEMORY_CANDIDATE", "SOURCE_MANIFEST", "SOURCE_ASSERTION"})
CONTROL_LOCKS = frozenset({"MEMORY_ADMISSION", "ADAPTIVE_HYDRATION", "COLLABORATION_ADAPTATION"})
RESET_SCOPES = frozenset({"EPHEMERAL_ONLY", "SESSION_ADAPTIVE"})

RECORD_SECTIONS = {
    "FACT": "ucm_facts",
    "IDENTITY": "ucm_identity",
    "REFERENT": "ucm_referents",
    "COLLABORATION_CONTRACT": "ucm_collaboration",
    "MEMORY_CANDIDATE": "ucm_candidates",
    "SOURCE_MANIFEST": "ucm_sources",
    "SOURCE_ASSERTION": "ucm_source_assertions",
    "DECISION": "ucm_decisions",
    "CONTROL_STATE": "ucm_control",
}

SYSTEM_DESCRIPTOR: JsonObject = {
    "schema": "rahl.user-continuity.system-descriptor.v1",
    "system_name": "User Continuity System",
    "short_name": "UCS/UCM",
    "version": SYSTEM_VERSION,
    "authority_traits": list(AUTHORITY_TRAITS),
    "logical_operations": {
        "read": [
            "ucm.describe", "ucm.head", "ucm.read_core", "ucm.read_sections", "ucm.search",
            "ucm.events_tail", "ucm.get_fact", "ucm.resolve_identity", "ucm.resolve_referent",
            "ucm.verification_debt", "ucm.read_decisions", "ucm.read_control_state",
            "ucm.memory_candidates", "ucm.compile_context_packet", "ucm.source_manifest",
        ],
        "write": [
            "ucm.add", "ucm.update", "ucm.supersede", "ucm.verify", "ucm.conflict", "ucm.retire",
            "ucm.rediscover", "ucm.forget_request", "ucm.materialize", "ucm.lock", "ucm.unlock",
            "ucm.session_reset", "ucm.decision_add", "ucm.decision_supersede", "ucm.memory_candidate_confirm",
        ],
        "export": ["ucm.export_filtered"],
    },
    "write_requirements": ["expected_head_seq", "expected_head_hash", "source_instance", "provenance", "post_write_readback"],
    "fresh_instance_required_surfaces": sorted(REQUIRED_INGRESS_SURFACES),
    "core_hydration_default": sorted(CORE_HYDRATION_GROUPS),
    "lazy_hydration_default": sorted(LAZY_HYDRATION_GROUPS),
    "server_integration": "existing authoritative ledger + content-addressed snapshot; canonical UCS v1 semantic adapter",
    "donor_archive_sha256": SYSTEM_ARCHIVE_SHA256,
    "donor_contract_sha256": SYSTEM_CONTRACT_SHA256,
}

INGRESS_CONTRACT: JsonObject = {
    "schema_version": "1.0",
    "system_version": SYSTEM_VERSION,
    "required_surfaces": sorted(REQUIRED_INGRESS_SURFACES),
    "core_budget_bytes": CORE_BUDGET_BYTES,
    "lazy_groups": sorted({"candidate_queue", "decision_history", "deployment", "historical", "personal_sensitive", "projects", "source_evidence", "task_specific"}),
    "failure_taxonomy": {
        "missing_required": "USER_CONTINUITY_INCOMPLETE",
        "stale_snapshot": "UCM_CURRENTNESS_FAILURE",
        "authority_violation": "AUTHORITY_FIREWALL",
        "provenance_failure": "UCM_PROVENANCE_FAILURE",
        "budget_failure": "UCM_CORE_BUDGET_EXCEEDED",
    },
    "authority_firewall": {"not_project_authority": True, "not_doctrine_authority": True},
    "min_headroom_bytes": MIN_HEADROOM_BYTES,
    "budget_scope": "USER_CORE_SURFACES_EXCLUDING_SYSTEM_DESCRIPTOR",
}

_SAFE_KEY = re.compile(r"^[^\x00\r\n]{1,512}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class UcmError(RuntimeError):
    def __init__(self, error_code: str, message: str, status: int = 400, **extra: Any) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status = int(status)
        self.extra = extra


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _ensure_canonical_json_value(value: Any, *, field: str = "payload", max_depth: int = 64, max_nodes: int = 50000) -> None:
    """Reject values that are not portable finite UTF-8 JSON before hashing.

    Python's json module accepts NaN/Infinity and can fail late on lone UTF-16
    surrogates. Iterative validation also bounds nesting/node count so hostile
    payloads fail as contract errors instead of recursion/allocation failures.
    """
    stack: list[tuple[Any, int, str]] = [(value, 0, field)]
    nodes = 0
    while stack:
        item, depth, path = stack.pop()
        nodes += 1
        if nodes > max_nodes:
            raise UcmError("UCM_CONTRACT_INVALID", f"{field} exceeds canonical JSON node limit {max_nodes}", 400)
        if depth > max_depth:
            raise UcmError("UCM_CONTRACT_INVALID", f"{field} exceeds canonical JSON depth limit {max_depth}", 400)
        if item is None or isinstance(item, bool) or isinstance(item, int):
            continue
        if isinstance(item, float):
            if not math.isfinite(item):
                raise UcmError("UCM_CONTRACT_INVALID", f"{path} contains non-finite JSON number", 400)
            continue
        if isinstance(item, str):
            try:
                item.encode("utf-8", "strict")
            except UnicodeEncodeError as exc:
                raise UcmError("UCM_CONTRACT_INVALID", f"{path} contains invalid Unicode surrogate data", 400) from exc
            continue
        if isinstance(item, list):
            for index in range(len(item) - 1, -1, -1):
                stack.append((item[index], depth + 1, f"{path}[{index}]"))
            continue
        if isinstance(item, Mapping):
            for key, child in item.items():
                if not isinstance(key, str):
                    raise UcmError("UCM_CONTRACT_INVALID", f"{path} contains non-string object key", 400)
                try:
                    key.encode("utf-8", "strict")
                except UnicodeEncodeError as exc:
                    raise UcmError("UCM_CONTRACT_INVALID", f"{path} contains invalid Unicode object key", 400) from exc
                stack.append((child, depth + 1, f"{path}.{key}"))
            continue
        raise UcmError("UCM_CONTRACT_INVALID", f"{path} contains non-JSON type {type(item).__name__}", 400)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(value: Any, field: str, *, max_chars: int = 20000) -> str:
    text = str(value or "").strip()
    if not text:
        raise UcmError("UCM_CONTRACT_INVALID", f"{field} is required", 400)
    if len(text) > max_chars:
        raise UcmError("UCM_CONTRACT_INVALID", f"{field} exceeds {max_chars} characters", 400)
    return text


def _key(value: Any, field: str) -> str:
    text = _text(value, field, max_chars=512)
    if not _SAFE_KEY.fullmatch(text):
        raise UcmError("UCM_CONTRACT_INVALID", f"{field} contains invalid characters", 400)
    return text


def _list(value: Any, field: str, *, required: bool = False, unique: bool = False, max_items: int = 128) -> list[Any]:
    if value is None:
        value = []
    if not isinstance(value, list) or len(value) > max_items:
        raise UcmError("UCM_CONTRACT_INVALID", f"{field} must be a list with at most {max_items} items", 400)
    if required and not value:
        raise UcmError("UCM_PROVENANCE_FAILURE", f"{field} requires at least one item", 400)
    if unique and len({_canonical_bytes(x) for x in value}) != len(value):
        raise UcmError("UCM_CONTRACT_INVALID", f"{field} must contain unique items", 400)
    return copy.deepcopy(value)


def _enum(value: Any, field: str, allowed: frozenset[str]) -> str:
    text = _text(value, field, max_chars=128).upper()
    if text not in allowed:
        raise UcmError("UCM_CONTRACT_INVALID", f"{field} must be one of {sorted(allowed)}", 400)
    return text


def _closed(value: Mapping[str, Any], *, required: set[str], allowed: set[str], field: str) -> None:
    missing=sorted(required-set(value))
    extra=sorted(set(value)-allowed)
    if missing or extra:
        raise UcmError("UCM_CONTRACT_INVALID", f"{field} schema mismatch", 400, missing=missing, extra=extra)


def _provenance(items: Any, field: str = "provenance", *, strict: bool = False, require_independence: bool = True) -> list[JsonObject]:
    rows = _list(items, field, required=True, max_items=64)
    out: list[JsonObject] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise UcmError("UCM_PROVENANCE_FAILURE", f"{field}[{idx}] must be an object", 400)
        if strict:
            _closed(row, required={"source_instance","source_artifact","source_pointer","independence_group"}, allowed={"source_instance","source_thread","source_artifact","source_pointer","independence_group"}, field=f"{field}[{idx}]")
        source_instance = _text(row.get("source_instance"), f"{field}[{idx}].source_instance", max_chars=160)
        source_artifact = _text(row.get("source_artifact"), f"{field}[{idx}].source_artifact", max_chars=2000)
        source_pointer = _text(row.get("source_pointer"), f"{field}[{idx}].source_pointer", max_chars=2000)
        independence_raw = str(row.get("independence_group") or "").strip()
        if require_independence and not independence_raw:
            raise UcmError("UCM_PROVENANCE_FAILURE", f"{field}[{idx}].independence_group is required", 400)
        independence = independence_raw or None
        out.append(
            {
                "source_instance": source_instance,
                "source_thread": str(row.get("source_thread") or "").strip() or None,
                "source_artifact": source_artifact,
                "source_pointer": source_pointer,
                "independence_group": independence,
            }
        )
    return out


def _relations(items: Any) -> list[JsonObject]:
    rows = _list(items, "relations", max_items=128)
    out = []
    for idx, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise UcmError("UCM_CONTRACT_INVALID", f"relations[{idx}] must be an object", 400)
        typ = _enum(row.get("type"), f"relations[{idx}].type", RELATION_TYPES)
        out.append({"type": typ, "target": _text(row.get("target"), f"relations[{idx}].target", max_chars=2000)})
    return out


def _assistant_utility(value: Any) -> JsonObject | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise UcmError("UCM_CONTRACT_INVALID", "assistant_utility must be an object", 400)
    _closed(value, required={"why_it_matters","expected_reuse","decision_impact","retrieval_cues","recurrence_count","rediscovery_cost","negative_instruction","unresolved_dependency","contradiction_risk","staleness_risk","hydration_priority","usage"}, allowed={"why_it_matters","expected_reuse","decision_impact","retrieval_cues","recurrence_count","rediscovery_cost","negative_instruction","unresolved_dependency","contradiction_risk","staleness_risk","hydration_priority","usage"}, field="assistant_utility")
    allowed_level = frozenset({"LOW", "MEDIUM", "HIGH"})
    usage = value.get("usage") or {}
    if not isinstance(usage, Mapping):
        raise UcmError("UCM_CONTRACT_INVALID", "assistant_utility.usage must be an object", 400)
    _closed(usage, required={"offered_count","hydrated_count","consumed_count","decision_use_count"}, allowed={"offered_count","hydrated_count","consumed_count","decision_use_count","last_used_at"}, field="assistant_utility.usage")
    out = {
        "why_it_matters": str(value.get("why_it_matters") or ""),
        "expected_reuse": _enum(value.get("expected_reuse"), "assistant_utility.expected_reuse", allowed_level),
        "decision_impact": _enum(value.get("decision_impact"), "assistant_utility.decision_impact", allowed_level),
        "retrieval_cues": [str(x) for x in _list(value.get("retrieval_cues"), "assistant_utility.retrieval_cues", unique=True, max_items=64)],
        "recurrence_count": max(0, int(value.get("recurrence_count") or 0)),
        "rediscovery_cost": _enum(value.get("rediscovery_cost"), "assistant_utility.rediscovery_cost", allowed_level),
        "negative_instruction": bool(value.get("negative_instruction", False)),
        "unresolved_dependency": bool(value.get("unresolved_dependency", False)),
        "contradiction_risk": _enum(value.get("contradiction_risk"), "assistant_utility.contradiction_risk", allowed_level),
        "staleness_risk": _enum(value.get("staleness_risk"), "assistant_utility.staleness_risk", allowed_level),
        "hydration_priority": int(value.get("hydration_priority") or 0),
        "usage": {
            "offered_count": max(0, int(usage.get("offered_count") or 0)),
            "hydrated_count": max(0, int(usage.get("hydrated_count") or 0)),
            "consumed_count": max(0, int(usage.get("consumed_count") or 0)),
            "decision_use_count": max(0, int(usage.get("decision_use_count") or 0)),
            "last_used_at": str(usage.get("last_used_at") or "").strip() or None,
        },
    }
    if out["hydration_priority"] < 0 or out["hydration_priority"] > 100:
        raise UcmError("UCM_CONTRACT_INVALID", "assistant_utility.hydration_priority must be 0-100", 400)
    return out


def validate_fact(value: Any) -> JsonObject:
    if not isinstance(value, Mapping):
        raise UcmError("UCM_CONTRACT_INVALID", "fact must be an object", 400)
    _closed(value, required={"fact_key","value","descriptive_tags","lifecycle","authority","currentness","verification","temporal","provenance","sensitivity","export_class","hydration_groups","relations"}, allowed={"fact_key","value","descriptive_tags","lifecycle","authority","currentness","verification","temporal","provenance","sensitivity","export_class","hydration_groups","relations","assistant_utility"}, field="fact")
    authority = value.get("authority")
    currentness = value.get("currentness")
    verification = value.get("verification")
    temporal = value.get("temporal")
    if not all(isinstance(x, Mapping) for x in (authority, currentness, verification, temporal)):
        raise UcmError("UCM_CONTRACT_INVALID", "fact authority/currentness/verification/temporal must be objects", 400)
    _closed(authority, required={"target_plane","source_role"}, allowed={"target_plane","source_role"}, field="fact.authority")
    _closed(currentness, required={"status"}, allowed={"status","last_verified_at"}, field="fact.currentness")
    _closed(verification, required={"requirement","verified_live","verification_ref"}, allowed={"requirement","verified_live","verification_ref","revalidate_after","revalidate_when"}, field="fact.verification")
    _closed(temporal, required={"recorded_at","asserted_at","observed_at"}, allowed={"recorded_at","asserted_at","observed_at"}, field="fact.temporal")
    target_plane = _text(authority.get("target_plane"), "authority.target_plane", max_chars=160)
    source_role = _enum(authority.get("source_role"), "authority.source_role", SOURCE_ROLES)
    target_upper = target_plane.upper()
    if source_role == "AUTHORITATIVE" and any(token in target_upper for token in ("PROJECT", "RUNTIME", "DEPLOYMENT", "DOCTRINE")):
        raise UcmError("AUTHORITY_FIREWALL", "UCM cannot become project/Runtime/deployment/doctrine authority", 409)
    requirement = _enum(verification.get("requirement"), "verification.requirement", VERIFY_LEVELS)
    if any(token in target_upper for token in ("PROJECT", "RUNTIME", "DEPLOYMENT")) and requirement != "REQUIRED":
        raise UcmError("UCM_VERIFICATION_POLICY_REQUIRED", "project/Runtime/deployment continuity requires explicit REQUIRED live verification", 409)
    verified_live = bool(verification.get("verified_live", False))
    verification_ref = str(verification.get("verification_ref") or "").strip() or None
    out = {
        "fact_key": _key(value.get("fact_key"), "fact_key"),
        "value": copy.deepcopy(value.get("value")),
        "descriptive_tags": [str(x) for x in _list(value.get("descriptive_tags"), "descriptive_tags", unique=True)],
        "lifecycle": _enum(value.get("lifecycle"), "lifecycle", FACT_LIFECYCLES),
        "authority": {"target_plane": target_plane, "source_role": source_role},
        "currentness": {
            "status": _enum(currentness.get("status"), "currentness.status", CURRENTNESS_STATES),
            "last_verified_at": str(currentness.get("last_verified_at") or "").strip() or None,
        },
        "verification": {
            "requirement": requirement,
            "verified_live": verified_live,
            "verification_ref": verification_ref,
            "revalidate_after": str(verification.get("revalidate_after") or "").strip() or None,
            "revalidate_when": [str(x) for x in _list(verification.get("revalidate_when"), "verification.revalidate_when", unique=True)],
        },
        "temporal": {
            "recorded_at": str(temporal.get("recorded_at") or "").strip() or None,
            "asserted_at": str(temporal.get("asserted_at") or "").strip() or None,
            "observed_at": str(temporal.get("observed_at") or "").strip() or None,
        },
        "provenance": _provenance(value.get("provenance"), strict=True),
        "sensitivity": _enum(value.get("sensitivity"), "sensitivity", SENSITIVITY),
        "export_class": _enum(value.get("export_class"), "export_class", EXPORT_CLASSES),
        "hydration_groups": [str(x) for x in _list(value.get("hydration_groups"), "hydration_groups", required=True, unique=True)],
        "relations": _relations(value.get("relations")),
    }
    utility = _assistant_utility(value.get("assistant_utility"))
    if utility is not None:
        out["assistant_utility"] = utility
    # Descriptive tags are intentionally ignored here. Behavioral verification
    # is controlled only by the explicit verification component.
    return out


def verification_requirement(fact: Mapping[str, Any]) -> str:
    return _enum((fact.get("verification") or {}).get("requirement", "CONDITIONAL"), "verification.requirement", VERIFY_LEVELS)


def current_usable(fact: Mapping[str, Any]) -> bool:
    if (fact.get("currentness") or {}).get("status") != "CURRENT":
        return False
    if verification_requirement(fact) == "REQUIRED":
        verification = fact.get("verification") or {}
        return verification.get("verified_live") is True and bool(verification.get("verification_ref"))
    return True


def effective_fact_time(fact: Mapping[str, Any]) -> str | None:
    temporal = fact.get("temporal") or {}
    return temporal.get("observed_at") or temporal.get("asserted_at")


def due_for_revalidation(fact: Mapping[str, Any], *, now_iso: str | None = None, condition_tokens: set[str] | None = None) -> bool:
    now = now_iso or _now()
    verification = fact.get("verification") or {}
    if verification_requirement(fact) == "REQUIRED" and not current_usable(fact):
        return True
    after = verification.get("revalidate_after")
    if after and str(after) <= now:
        return True
    wanted = set(verification.get("revalidate_when") or [])
    return bool(wanted.intersection(condition_tokens or set()))


def evidence_independence_count(fact: Mapping[str, Any]) -> int:
    return len({str(p.get("independence_group")) for p in fact.get("provenance", []) if p.get("independence_group")})


def derive_hydration_score(utility: Mapping[str, Any] | None) -> int:
    value = dict(utility or {})
    score = int(value.get("hydration_priority") or 0)
    score += {"LOW": 0, "MEDIUM": 8, "HIGH": 18}.get(value.get("expected_reuse"), 0)
    score += {"LOW": 0, "MEDIUM": 8, "HIGH": 18}.get(value.get("decision_impact"), 0)
    score += {"LOW": 0, "MEDIUM": 5, "HIGH": 12}.get(value.get("rediscovery_cost"), 0)
    if value.get("negative_instruction"):
        score += 10
    if value.get("unresolved_dependency"):
        score += 8
    if value.get("contradiction_risk") == "HIGH":
        score += 6
    if value.get("staleness_risk") == "HIGH":
        score -= 8
    score += min(int(value.get("recurrence_count") or 0), 10)
    score += min(int((value.get("usage") or {}).get("decision_use_count") or 0), 10)
    return max(0, min(100, score))


def _validate_identity(value: Any) -> JsonObject:
    if not isinstance(value, Mapping):
        raise UcmError("UCM_CONTRACT_INVALID", "identity must be an object", 400)
    _closed(value, required={"identity_key","kind","value","status","use_for","scope","precedence","provenance"}, allowed={"identity_key","kind","value","status","use_for","scope","precedence","valid_from","valid_to","provenance"}, field="identity")
    precedence = int(value.get("precedence") or 0)
    if precedence < 0 or precedence > 100:
        raise UcmError("UCM_CONTRACT_INVALID", "identity precedence must be 0-100", 400)
    uses = [_enum(x, "identity.use_for", IDENTITY_USES) for x in _list(value.get("use_for"), "identity.use_for", required=True, unique=True)]
    return {
        "identity_key": _key(value.get("identity_key"), "identity.identity_key"),
        "kind": _enum(value.get("kind"), "identity.kind", IDENTITY_KINDS),
        "value": _text(value.get("value"), "identity.value", max_chars=1000),
        "status": _enum(value.get("status"), "identity.status", IDENTITY_STATUSES),
        "use_for": uses,
        "scope": [str(x) for x in _list(value.get("scope"), "identity.scope", required=True, unique=True)],
        "precedence": precedence,
        "valid_from": str(value.get("valid_from") or "").strip() or None,
        "valid_to": str(value.get("valid_to") or "").strip() or None,
        "provenance": _provenance(value.get("provenance"), "identity.provenance"),
    }


def _validate_referent(value: Any) -> JsonObject:
    if not isinstance(value, Mapping):
        raise UcmError("UCM_CONTRACT_INVALID", "referent must be an object", 400)
    _closed(value, required={"referent_key","term","meaning","status","scope","precedence","provenance"}, allowed={"referent_key","term","meaning","status","scope","precedence","supersedes","provenance"}, field="referent")
    precedence = int(value.get("precedence") or 0)
    if precedence < 0 or precedence > 100:
        raise UcmError("UCM_CONTRACT_INVALID", "referent precedence must be 0-100", 400)
    return {
        "referent_key": _key(value.get("referent_key"), "referent.referent_key"),
        "term": _text(value.get("term"), "referent.term", max_chars=500),
        "meaning": _text(value.get("meaning"), "referent.meaning", max_chars=8000),
        "status": _enum(value.get("status"), "referent.status", REFERENT_STATUSES),
        "scope": [str(x) for x in _list(value.get("scope"), "referent.scope", required=True, unique=True)],
        "precedence": precedence,
        "supersedes": [str(x) for x in _list(value.get("supersedes"), "referent.supersedes", unique=True)],
        "provenance": _provenance(value.get("provenance"), "referent.provenance", require_independence=False),
    }


def _validate_decision(value: Any) -> JsonObject:
    if not isinstance(value, Mapping):
        raise UcmError("UCM_CONTRACT_INVALID", "decision must be an object", 400)
    _closed(value, required={"decision_id","scope","statement","status","authority_owner","rationale","evidence_refs","alternatives","supersession_triggers","related_fact_keys","provenance"}, allowed={"decision_id","scope","statement","status","authority_owner","rationale","evidence_refs","alternatives","supersession_triggers","related_fact_keys","created_at","provenance"}, field="decision")
    return {
        "decision_id": _key(value.get("decision_id"), "decision.decision_id"),
        "scope": [str(x) for x in _list(value.get("scope"), "decision.scope", required=True, unique=True)],
        "statement": _text(value.get("statement"), "decision.statement", max_chars=8000),
        "status": _enum(value.get("status"), "decision.status", DECISION_STATUSES),
        "authority_owner": _text(value.get("authority_owner"), "decision.authority_owner", max_chars=300),
        "rationale": str(value.get("rationale") or ""),
        "evidence_refs": [str(x) for x in _list(value.get("evidence_refs"), "decision.evidence_refs", max_items=128)],
        "alternatives": [str(x) for x in _list(value.get("alternatives"), "decision.alternatives", max_items=128)],
        "supersession_triggers": [str(x) for x in _list(value.get("supersession_triggers"), "decision.supersession_triggers", max_items=128)],
        "related_fact_keys": [str(x) for x in _list(value.get("related_fact_keys"), "decision.related_fact_keys", max_items=128)],
        "created_at": str(value.get("created_at") or "").strip() or None,
        "provenance": _provenance(value.get("provenance"), "decision.provenance", require_independence=False),
    }


def _validate_candidate(value: Any) -> JsonObject:
    if not isinstance(value, Mapping):
        raise UcmError("UCM_CONTRACT_INVALID", "memory candidate must be an object", 400)
    _closed(value, required={"candidate_id","proposed_fact_key","signal_type","proposal","source_role","write_posture","status","evidence_refs","created_at"}, allowed={"candidate_id","proposed_fact_key","signal_type","proposal","source_role","write_posture","status","evidence_refs","created_at"}, field="memory_candidate")
    source_role = str(value.get("source_role") or "").upper()
    write_posture = str(value.get("write_posture") or "").upper()
    if source_role != "INFERENCE" or write_posture != "PROPOSE_ONLY":
        raise UcmError("AUTHORITY_FIREWALL", "memory candidate must remain inference/PROPOSE_ONLY", 409)
    return {
        "candidate_id": _key(value.get("candidate_id"), "candidate.candidate_id"),
        "proposed_fact_key": _key(value.get("proposed_fact_key"), "candidate.proposed_fact_key"),
        "signal_type": _text(value.get("signal_type"), "candidate.signal_type", max_chars=200),
        "proposal": copy.deepcopy(value.get("proposal")),
        "source_role": "INFERENCE",
        "write_posture": "PROPOSE_ONLY",
        "status": _enum(value.get("status"), "candidate.status", CANDIDATE_STATUSES),
        "evidence_refs": [str(x) for x in _list(value.get("evidence_refs"), "candidate.evidence_refs", max_items=128)],
        "created_at": _text(value.get("created_at"), "candidate.created_at", max_chars=100),
    }


def _validate_control(value: Any) -> JsonObject:
    if not isinstance(value, Mapping):
        raise UcmError("UCM_CONTRACT_INVALID", "control state must be an object", 400)
    _closed(value, required=set(), allowed={"memory_admission_locked","adaptive_hydration_locked","collaboration_adaptation_locked","session_generation","last_reset_at","reset_scope"}, field="control_state")
    scope = str(value.get("reset_scope") or "NONE").upper()
    if scope not in {"NONE", *RESET_SCOPES}:
        raise UcmError("UCM_CONTRACT_INVALID", "invalid reset_scope", 400)
    generation = int(value.get("session_generation") or 0)
    if generation < 0:
        raise UcmError("UCM_CONTRACT_INVALID", "session_generation must be >=0", 400)
    return {
        "memory_admission_locked": bool(value.get("memory_admission_locked", False)),
        "adaptive_hydration_locked": bool(value.get("adaptive_hydration_locked", False)),
        "collaboration_adaptation_locked": bool(value.get("collaboration_adaptation_locked", False)),
        "session_generation": generation,
        "last_reset_at": str(value.get("last_reset_at") or "").strip() or None,
        "reset_scope": scope,
    }


def default_control_state() -> JsonObject:
    return _validate_control({})


def _validate_collaboration(value: Any) -> JsonObject:
    if not isinstance(value, Mapping):
        raise UcmError("UCM_CONTRACT_INVALID", "collaboration contract must be an object", 400)
    _closed(value, required={"contract_key","scope","addressing","control_signals","communication","initiative","correction","teaching","output","authority_boundary","provenance"}, allowed={"contract_key","scope","addressing","control_signals","communication","initiative","correction","teaching","output","authority_boundary","provenance"}, field="collaboration")
    addressing=value.get("addressing"); initiative=value.get("initiative")
    if not isinstance(addressing, Mapping) or not isinstance(initiative, Mapping): raise UcmError("UCM_CONTRACT_INVALID","collaboration addressing/initiative must be objects",400)
    _closed(addressing, required={"identity_use"}, allowed={"identity_use","ceremony"}, field="collaboration.addressing")
    if str(addressing.get("identity_use") or "").upper() not in {"NORMAL_ADDRESS","PROJECT_ADDRESS","SIMULATION_TITLE","OTHER"}: raise UcmError("UCM_CONTRACT_INVALID","invalid collaboration addressing identity_use",400)
    _closed(initiative, required={"level","challenge_when_evidence_warrants","suggest_improvements"}, allowed={"level","challenge_when_evidence_warrants","suggest_improvements"}, field="collaboration.initiative")
    if str(initiative.get("level") or "").upper() not in {"LOW","MODERATE","HIGH"}: raise UcmError("UCM_CONTRACT_INVALID","invalid collaboration initiative level",400)
    boundary = value.get("authority_boundary")
    if not isinstance(boundary, Mapping) or boundary.get("preference_grants_tool_authority") is not False or boundary.get("preference_grants_project_authority") is not False:
        raise UcmError("AUTHORITY_FIREWALL", "collaboration preferences cannot widen tool/project authority", 409)
    controls = _list(value.get("control_signals"), "collaboration.control_signals", max_items=64)
    normalized_controls = []
    for idx, item in enumerate(controls):
        if not isinstance(item, Mapping):
            raise UcmError("UCM_CONTRACT_INVALID", f"control_signals[{idx}] must be an object", 400)
        if item.get("authorization_effect", "NONE") != "NONE":
            raise UcmError("AUTHORITY_FIREWALL", "control signal cannot grant authorization", 409)
        normalized_controls.append({
            "signal": _text(item.get("signal"), f"control_signals[{idx}].signal", max_chars=200),
            "meaning": _text(item.get("meaning"), f"control_signals[{idx}].meaning", max_chars=1000),
            "urgency_implied": bool(item.get("urgency_implied", False)),
            "authorization_effect": "NONE",
        })
    out = copy.deepcopy(dict(value))
    out["contract_key"] = _key(value.get("contract_key"), "collaboration.contract_key")
    out["scope"] = [str(x) for x in _list(value.get("scope"), "collaboration.scope", required=True, unique=True)]
    out["control_signals"] = normalized_controls
    out["authority_boundary"] = {"preference_grants_tool_authority": False, "preference_grants_project_authority": False}
    out["provenance"] = _provenance(value.get("provenance"), "collaboration.provenance")
    return out


def _validate_source_manifest(value: Any) -> JsonObject:
    if not isinstance(value, Mapping):
        raise UcmError("UCM_CONTRACT_INVALID", "source manifest entry must be an object", 400)
    sha = str(value.get("sha256") or "").lower()
    if not _SHA256.fullmatch(sha):
        raise UcmError("UCM_PROVENANCE_FAILURE", "source manifest entry requires exact sha256", 400)
    return {
        "source_key": _key(value.get("source_key") or sha, "source.source_key"),
        "source_instance": _text(value.get("source_instance"), "source.source_instance", max_chars=160),
        "artifact": _text(value.get("artifact"), "source.artifact", max_chars=2000),
        "sha256": sha,
        "bytes": max(0, int(value.get("bytes") or 0)),
        "preservation": _text(value.get("preservation") or "CONTENT_ADDRESSED", "source.preservation", max_chars=200),
        "blob_path": str(value.get("blob_path") or "").strip() or None,
        "coverage": copy.deepcopy(value.get("coverage") or {}),
        "policy_absences": [str(x) for x in _list(value.get("policy_absences"), "source.policy_absences", max_items=128)],
        "source_role": str(value.get("source_role") or "CONTINUITY"),
        "export_class": _enum(value.get("export_class", "USER"), "source.export_class", EXPORT_CLASSES),
    }


def _validate_source_assertion(value: Any) -> JsonObject:
    if not isinstance(value, Mapping):
        raise UcmError("UCM_CONTRACT_INVALID", "source assertion must be an object", 400)
    required={"assertion_id","source_instance","source_artifact","source_pointer","heading_path","line_start","line_end","text","label","currentness_hint","verification_hint","lifecycle_hint","sensitivity_hint","export_class_hint","hydration_group_hint","import_disposition"}
    _closed(value, required=required, allowed=required, field="source_assertion")
    start=int(value.get("line_start") or 0); end=int(value.get("line_end") or 0)
    if start < 1 or end < start:
        raise UcmError("UCM_PROVENANCE_FAILURE", "source assertion line range is invalid", 400)
    disposition=_text(value.get("import_disposition"), "source_assertion.import_disposition", max_chars=100).upper()
    if disposition not in {"USER_INSTANCE","SOURCE_CONTEXT_ONLY"}:
        raise UcmError("UCM_CONTRACT_INVALID", "unknown source assertion import_disposition", 400)
    return {
        "assertion_id": _key(value.get("assertion_id"), "source_assertion.assertion_id"),
        "source_instance": _text(value.get("source_instance"), "source_assertion.source_instance", max_chars=160),
        "source_artifact": _text(value.get("source_artifact"), "source_assertion.source_artifact", max_chars=2000),
        "source_pointer": _text(value.get("source_pointer"), "source_assertion.source_pointer", max_chars=2000),
        "heading_path": str(value.get("heading_path") or ""),
        "line_start": start,
        "line_end": end,
        "text": _text(value.get("text"), "source_assertion.text", max_chars=20000),
        "label": str(value.get("label") or ""),
        "currentness_hint": str(value.get("currentness_hint") or ""),
        "verification_hint": str(value.get("verification_hint") or ""),
        "lifecycle_hint": str(value.get("lifecycle_hint") or ""),
        "sensitivity_hint": str(value.get("sensitivity_hint") or ""),
        "export_class_hint": str(value.get("export_class_hint") or ""),
        "hydration_group_hint": str(value.get("hydration_group_hint") or ""),
        "import_disposition": disposition,
    }


def _validate_record(record_type: str, value: Any) -> JsonObject:
    typ = str(record_type or "").upper()
    if typ == "FACT": return validate_fact(value)
    if typ == "IDENTITY": return _validate_identity(value)
    if typ == "REFERENT": return _validate_referent(value)
    if typ == "COLLABORATION_CONTRACT": return _validate_collaboration(value)
    if typ == "MEMORY_CANDIDATE": return _validate_candidate(value)
    if typ == "SOURCE_MANIFEST": return _validate_source_manifest(value)
    if typ == "SOURCE_ASSERTION": return _validate_source_assertion(value)
    if typ == "DECISION": return _validate_decision(value)
    if typ == "CONTROL_STATE": return _validate_control(value)
    raise UcmError("UCM_CONTRACT_INVALID", f"unsupported record_type: {record_type}", 400)


def _record_key(record_type: str, record: Mapping[str, Any]) -> str:
    typ = record_type.upper()
    fields = {
        "FACT": "fact_key", "IDENTITY": "identity_key", "REFERENT": "referent_key",
        "COLLABORATION_CONTRACT": "contract_key", "MEMORY_CANDIDATE": "candidate_id",
        "SOURCE_MANIFEST": "source_key", "SOURCE_ASSERTION": "assertion_id", "DECISION": "decision_id",
    }
    if typ == "CONTROL_STATE": return "control"
    return _key(record.get(fields[typ]), f"{typ}.key")


def _target(record_type: str, record_key: str) -> str:
    return f"ucm.{record_type.lower()}.{hashlib.sha256(record_key.encode('utf-8')).hexdigest()}"


def _record_section(record_type: str) -> str:
    try: return RECORD_SECTIONS[record_type.upper()]
    except KeyError as exc: raise UcmError("UCM_CONTRACT_INVALID", f"unknown record_type: {record_type}", 400) from exc


def _profile_id(payload: Mapping[str, Any]) -> str:
    try: return backend._profile_id(payload.get("profile_id"))
    except backend.UserContinuityError as exc: raise UcmError(exc.error_code, exc.message, exc.status, **exc.extra) from exc


def _write_posture(payload: Mapping[str, Any]) -> str:
    posture = str(payload.get("write_posture") or "").upper()
    if posture not in WRITE_POSTURES:
        raise UcmError("UCM_WRITE_POSTURE_REQUIRED", f"write_posture must be one of {sorted(WRITE_POSTURES)}", 400)
    return posture


def _source(payload: Mapping[str, Any]) -> JsonObject:
    source_instance = _text(payload.get("source_instance"), "source_instance", max_chars=160)
    actor = str(payload.get("actor") or "").strip().lower()
    if actor not in backend.ACTORS:
        raise UcmError("UCM_PROVENANCE_FAILURE", f"actor must be one of {sorted(backend.ACTORS)}", 400)
    provenance = payload.get("provenance")
    if not isinstance(provenance, Mapping):
        raise UcmError("UCM_PROVENANCE_FAILURE", "provenance object is required for canonical writes", 400)
    artifact = _text(provenance.get("source_artifact"), "provenance.source_artifact", max_chars=2000)
    pointer = _text(provenance.get("source_pointer"), "provenance.source_pointer", max_chars=2000)
    independence = _text(provenance.get("independence_group"), "provenance.independence_group", max_chars=300)
    return {
        "actor": actor,
        "source_instance": source_instance,
        "source_thread": str(provenance.get("source_thread") or payload.get("source_thread") or "").strip() or None,
        "source_event": str(provenance.get("source_event") or payload.get("source_event") or pointer).strip() or None,
        "evidence_independence_group": independence,
        "source_artifact": artifact,
        "source_pointer": pointer,
    }


def _require_cas_fields(payload: Mapping[str, Any]) -> tuple[int, str | None]:
    if "expected_head_seq" not in payload or "expected_head_hash" not in payload:
        raise UcmError("UCM_CAS_REQUIRED", "expected_head_seq and expected_head_hash are mandatory for canonical semantic writes", 409)
    try: seq = int(payload.get("expected_head_seq"))
    except (TypeError, ValueError) as exc: raise UcmError("UCM_CAS_REQUIRED", "expected_head_seq must be an integer", 400) from exc
    if seq < 0: raise UcmError("UCM_CAS_REQUIRED", "expected_head_seq must be >=0", 400)
    raw_hash = payload.get("expected_head_hash")
    if raw_hash in (None, "", "genesis"):
        h = None
    else:
        h = str(raw_hash).lower()
        if not _SHA256.fullmatch(h): raise UcmError("UCM_CAS_REQUIRED", "expected_head_hash must be SHA-256 or null/genesis", 400)
    return seq, h


def _check_cas(state: Mapping[str, Any], seq: int, head_hash: str | None) -> None:
    actual_seq = int(state.get("event_count") or 0)
    actual_hash = state.get("head_hash")
    if seq != actual_seq or head_hash != actual_hash:
        raise UcmError(
            "UCM_CURRENTNESS_FAILURE",
            "expected user-store head does not match authoritative ledger",
            409,
            expected_head_seq=seq,
            expected_head_hash=head_hash,
            current_head_seq=actual_seq,
            current_head_hash=actual_hash,
        )


def _backend_envelope(record_type: str, record: Mapping[str, Any], source: Mapping[str, Any]) -> JsonObject:
    key = _record_key(record_type, record)
    sensitivity = record.get("sensitivity", "NORMAL") if record_type == "FACT" else "NORMAL"
    export_class = record.get("export_class", "USER") if record_type in {"FACT", "SOURCE_MANIFEST"} else "USER"
    try:
        return backend._fact_payload(
            {
                "target": _target(record_type, key),
                "section": _record_section(record_type),
                "class": "UCM_RECORD",
                "status": "ACTIVE",
                "value": copy.deepcopy(record),
                "reason": f"UCS v1 canonical {record_type.lower()} record",
                "provenance": f"{source['source_instance']}::{source['source_artifact']}::{source['source_pointer']}",
                "confidence": "high",
                "requires_live_verification": False,
                "sensitivity": str(sensitivity).lower() if str(sensitivity).lower() in backend.SENSITIVITY else "normal",
                "export_class": export_class,
                "always_load": False,
                "hydration_priority": 100,
            }
        )
    except backend.UserContinuityError as exc:
        raise UcmError(exc.error_code, exc.message, exc.status, **exc.extra) from exc


def _idempotency(payload: Mapping[str, Any]) -> str:
    try: return backend._idempotency_key(dict(payload))
    except backend.UserContinuityError as exc: raise UcmError(exc.error_code, exc.message, exc.status, **exc.extra) from exc


def _fingerprint(operation: str, payload: Mapping[str, Any]) -> str:
    body = {k: copy.deepcopy(v) for k, v in payload.items() if k != "idempotency_key"}
    return backend._sha256_json({"operation": f"UCM_{operation}", "request": body})


def _record_from_state(state: Mapping[str, Any], record_type: str, record_key: str) -> tuple[str, JsonObject, JsonObject]:
    target = _target(record_type, record_key)
    memory_id = backend._active_target_id(dict(state), target)
    if not memory_id:
        raise UcmError("UCM_RECORD_NOT_FOUND", f"{record_type} record not found: {record_key}", 404)
    envelope = copy.deepcopy(state["facts"][memory_id])
    record = envelope.get("value")
    if not isinstance(record, Mapping):
        raise UcmError("UCM_STORE_CORRUPT", f"{record_type} envelope is not a canonical object", 409)
    return memory_id, envelope, copy.deepcopy(dict(record))


def _records_from_state(state: Mapping[str, Any], record_type: str) -> list[JsonObject]:
    section = _record_section(record_type)
    rows=[]
    for envelope in state.get("facts", {}).values():
        if envelope.get("class") != "UCM_RECORD" or envelope.get("section") != section:
            continue
        value=envelope.get("value")
        if isinstance(value, Mapping):
            rows.append(copy.deepcopy(dict(value)))
    return rows


def _ingress_fact_projection(fact: Mapping[str, Any]) -> JsonObject:
    source_refs = [
        f"{row['source_artifact']}#{row['source_pointer']}"
        for row in fact.get("provenance", [])
        if isinstance(row, Mapping) and row.get("source_artifact") and row.get("source_pointer")
    ]
    return {
        "fact_key": fact["fact_key"],
        "value": copy.deepcopy(fact.get("value")),
        "currentness": fact["currentness"]["status"],
        "verification_requirement": fact["verification"]["requirement"],
        "source_refs": source_refs,
        "full_record": f"ucm:FACT:{fact['fact_key']}",
    }


def _ingress_identity_projection(identity: Mapping[str, Any]) -> list[Any]:
    return [identity["identity_key"], identity["status"], int(identity["precedence"])]


def _ingress_referent_projection(referent: Mapping[str, Any]) -> list[Any]:
    return [referent["term"], referent["referent_key"], referent["status"]]


def _ingress_decision_projection(decision: Mapping[str, Any]) -> list[Any]:
    return [decision["decision_id"], decision["status"]]


def _ingress_collaboration_projection(collaboration: Mapping[str, Any] | None) -> JsonObject | None:
    if collaboration is None:
        return None
    return {
        "v": 1,
        "contract_key": collaboration["contract_key"],
        "addressing": copy.deepcopy(collaboration["addressing"]),
        "signals": [
            {
                "signal": item["signal"],
                "urgency_implied": bool(item.get("urgency_implied", False)),
                "authorization_effect": "NONE",
            }
            for item in collaboration.get("control_signals", [])
        ],
        "initiative": copy.deepcopy(collaboration["initiative"]),
        "correction": copy.deepcopy(collaboration.get("correction")),
        "teaching": copy.deepcopy(collaboration.get("teaching")),
        "authority_boundary": copy.deepcopy(collaboration["authority_boundary"]),
        "full": f"ucm:COLLABORATION_CONTRACT:{collaboration['contract_key']}",
    }


def _ingress_candidate_head_from_rows(rows: Sequence[Mapping[str, Any]]) -> JsonObject:
    ordered = sorted(
        ({"candidate_id": row["candidate_id"], "status": row["status"]} for row in rows),
        key=lambda row: row["candidate_id"],
    )
    pending_count = sum(1 for row in ordered if row["status"] == "PENDING_USER_CONFIRMATION")
    return {
        "candidate_count": len(ordered),
        "pending_count": pending_count,
        "queue_sha256": _digest(ordered),
    }


def _budget_surfaces_from_state(state: Mapping[str, Any]) -> JsonObject:
    all_facts=[]
    facts=[]
    for raw in _records_from_state(state,"FACT"):
        fact=validate_fact(raw)
        if not _fact_visible(fact):
            continue
        all_facts.append(fact)
        if set(fact["hydration_groups"]).intersection(CORE_HYDRATION_GROUPS):
            facts.append(fact)
    facts.sort(key=lambda x:(derive_hydration_score(x.get("assistant_utility")),x["fact_key"]),reverse=True)
    identities=[]
    for raw in _records_from_state(state,"IDENTITY"):
        identities.append(_validate_identity(raw))
    identities.sort(key=lambda x:x["identity_key"])
    referents=[]
    for raw in _records_from_state(state,"REFERENT"):
        referents.append(_validate_referent(raw))
    referents.sort(key=lambda x:x["referent_key"])
    decisions=[]
    for raw in _records_from_state(state,"DECISION"):
        decisions.append(_validate_decision(raw))
    decisions.sort(key=lambda x:x["decision_id"])
    collaborations=[_validate_collaboration(x) for x in _records_from_state(state,"COLLABORATION_CONTRACT")]
    collaboration=sorted(collaborations,key=lambda x:x["contract_key"])[-1] if collaborations else None
    candidates=[_validate_candidate(x) for x in _records_from_state(state,"MEMORY_CANDIDATE")]
    controls=[_validate_control(x) for x in _records_from_state(state,"CONTROL_STATE")]; control=controls[-1] if controls else default_control_state()
    source_rows=[_validate_source_manifest(x) for x in _records_from_state(state,"SOURCE_MANIFEST")]; source_rows.sort(key=lambda x:(x["source_instance"],x["artifact"],x["sha256"]))
    user_head={
        "schema":"pcmmad.ucm-user-store-head.v1","system_version":SYSTEM_VERSION,"user_store_id":str(state.get("profile_id") or ""),
        "not_project_authority":True,"not_doctrine_authority":True,"ledger_head_seq":int(state.get("event_count") or 0),
        "ledger_head_hash":state.get("head_hash"),"snapshot_from_seq":int(state.get("event_count") or 0),
    }
    surfaces={
        "CORE_SNAPSHOT":{"snapshot_from_seq":int(state.get("event_count") or 0),"facts":{x["fact_key"]:_ingress_fact_projection(x) for x in facts}},
        "IDENTITY_INDEX":{"v":1,"e":[_ingress_identity_projection(x) for x in identities],"full":"ucm:IDENTITY"},
        "COLLABORATION_CONTRACT":_ingress_collaboration_projection(collaboration),
        "REFERENT_INDEX":{"v":1,"e":[_ingress_referent_projection(x) for x in referents],"full":"ucm:REFERENT"},
        "VERIFICATION_DEBT":_compact_verification_debt(all_facts, snapshot_from_seq=int(state.get("event_count") or 0)),
        "CONTROL_STATE":control,
        "DECISION_INDEX":{"v":1,"e":[_ingress_decision_projection(x) for x in decisions],"full":"ucm:DECISION"},
        "CANDIDATE_QUEUE_HEAD":_ingress_candidate_head_from_rows(candidates),
    }
    user_head.update({
        "core_snapshot_sha256":_digest(surfaces["CORE_SNAPSHOT"]),"identity_index_sha256":_digest(surfaces["IDENTITY_INDEX"]),
        "collaboration_contract_sha256":_digest(surfaces["COLLABORATION_CONTRACT"]),"referent_index_sha256":_digest(surfaces["REFERENT_INDEX"]),
        "decision_index_sha256":_digest(surfaces["DECISION_INDEX"]),"verification_debt_sha256":_digest(surfaces["VERIFICATION_DEBT"]),
        "control_state_sha256":_digest(control),"candidate_queue_head_sha256":_digest(surfaces["CANDIDATE_QUEUE_HEAD"]),
        "source_manifest_sha256":_digest(source_rows),
    })
    return {"USER_STORE_HEAD":user_head,**surfaces}


def _preflight_canonical_core(state: Mapping[str, Any]) -> None:
    packet=_budget_surfaces_from_state(state)
    used=len(_canonical_bytes(packet)); headroom=CORE_BUDGET_BYTES-used
    if used>CORE_BUDGET_BYTES or headroom<MIN_HEADROOM_BYTES:
        raise UcmError("UCM_CORE_BUDGET_EXCEEDED","canonical UCM core would violate the 12 KiB / 2 KiB-headroom ingress contract",409,core_bytes=used,core_budget_bytes=CORE_BUDGET_BYTES,headroom_bytes=headroom,min_headroom_bytes=MIN_HEADROOM_BYTES)


def _replay_receipt(profile_id: str, state: Mapping[str, Any], replay: Mapping[str, Any], semantic_operation: str) -> JsonObject:
    # Response-loss replay is also a safe derived-state recovery point. The
    # authoritative append-only ledger already contains the consequence; if
    # snapshot materialization failed after that append, rebuild the bounded
    # derived cache before reporting replay success.
    currentness = backend._snapshot_currentness(profile_id)
    repaired_snapshot = False
    if not currentness.get("current"):
        backend._materialize_locked(profile_id, dict(state), retain_snapshot_count=2)
        repaired_snapshot = True
    head = backend.ledger_head(profile_id)
    return {
        "ok": True,
        "profile_id": profile_id,
        "replayed": True,
        "semantic_operation": semantic_operation,
        "event_seq": replay.get("event_seq"),
        "event_id": replay.get("event_id"),
        "event_hash": replay.get("event_hash"),
        "ledger_head_seq": head["event_seq"],
        "ledger_head_hash": head["event_hash"],
        "authority_effect": "NONE",
        "post_write_readback": True,
        "derived_snapshot_repaired": repaired_snapshot,
    }


def _append_record(
    payload: Mapping[str, Any], *, record_type: str, record: Mapping[str, Any], semantic_operation: str,
    existing_key: str | None = None, envelope_status: str = "ACTIVE",
) -> JsonObject:
    _ensure_canonical_json_value(payload, field="ucm_write_payload")
    profile_id = _profile_id(payload)
    seq, expected_hash = _require_cas_fields(payload)
    source = _source(payload)
    posture = _write_posture(payload)
    idem = _idempotency(payload)
    fingerprint = _fingerprint(semantic_operation, payload)
    typ = record_type.upper()
    normalized = _validate_record(typ, record)
    key = _record_key(typ, normalized)
    lookup_key = existing_key or key
    with backend._profile_lock(profile_id):
        state = backend._load_verified_state_locked(profile_id)
        replay = backend._check_replay(state, idem, fingerprint)
        if replay is not None:
            return _replay_receipt(profile_id, state, replay, semantic_operation)
        _check_cas(state, seq, expected_hash)
        control = _current_control_from_state(state)
        if control.get("memory_admission_locked") and posture not in {"DIRECT_USER_AUTHORIZED", "SYSTEM_MAINTENANCE"}:
            raise UcmError("UCM_MEMORY_ADMISSION_LOCKED", "automatic/user-implicit durable admission is locked", 409)
        if typ == "MEMORY_CANDIDATE" and semantic_operation == "ADD" and posture != "PROPOSE_ONLY":
            raise UcmError("AUTHORITY_FIREWALL", "new memory candidates must use PROPOSE_ONLY", 409)
        if typ != "MEMORY_CANDIDATE" and posture in {"PROPOSE_ONLY", "DO_NOT_PERSIST"}:
            raise UcmError("AUTHORITY_FIREWALL", f"{posture} cannot create active durable UCM state", 409)
        if typ == "FACT" and posture == "USER_STATED_DURABLE" and normalized.get("sensitivity") in {"SENSITIVE", "SECRET"}:
            raise UcmError("AUTHORITY_FIREWALL", "sensitive ordinary mention requires explicit retention/import authorization", 409)
        if typ == "FACT" and any(str(group).lower().startswith("project") for group in normalized.get("hydration_groups", [])) and posture == "USER_STATED_DURABLE":
            # Project-local content may be retained only as a continuity pointer, never as project authority.
            if "PROJECT" in str((normalized.get("authority") or {}).get("target_plane", "")).upper() and (normalized.get("authority") or {}).get("source_role") == "AUTHORITATIVE":
                raise UcmError("AUTHORITY_FIREWALL", "project-local user continuity cannot become project authority", 409)

        if semantic_operation in {"ADD", "DECISION_ADD"}:
            if backend._active_target_id(state, _target(typ, key)):
                raise UcmError("UCM_RECORD_EXISTS", f"{typ} record already exists: {key}", 409)
            if typ == "COLLABORATION_CONTRACT" and _records_from_state(state, "COLLABORATION_CONTRACT"):
                raise UcmError(
                    "UCM_COLLABORATION_CONFLICT",
                    "a current collaboration contract already exists; change it through an explicit update/supersession path",
                    409,
                )
            envelope = _backend_envelope(typ, normalized, source)
            event_payload = {"fact": envelope, "ucm_operation": semantic_operation, "ucm_record_type": typ, "ucm_record_key": key}
            event, manifest = backend._append_event_locked(
                profile_id, state, operation="ADD", event_payload=event_payload,
                provenance=source, idempotency_key=idem, request_fingerprint=fingerprint, preflight_hook=_preflight_canonical_core, snapshot_retention=2,
            )
            memory_id = envelope["memory_id"]
        else:
            memory_id, envelope, _old = _record_from_state(state, typ, lookup_key)
            patch = {"value": normalized, "status": envelope_status, "updated_at": _now()}
            event_payload = {
                "memory_id": memory_id,
                "patch": patch,
                "ucm_operation": semantic_operation,
                "ucm_record_type": typ,
                "ucm_record_key": key,
            }
            event, manifest = backend._append_event_locked(
                profile_id, state, operation="UPDATE", event_payload=event_payload,
                provenance=source, idempotency_key=idem, request_fingerprint=fingerprint, preflight_hook=_preflight_canonical_core, snapshot_retention=2,
            )
        actual = backend.ledger_head(profile_id)
        if actual["event_seq"] != event["event_seq"] or actual["event_hash"] != event["event_hash"]:
            raise UcmError("UCM_POST_WRITE_READBACK_FAILED", "authoritative ledger head does not match appended event", 500)
        return {
            "ok": True,
            "profile_id": profile_id,
            "replayed": False,
            "semantic_operation": semantic_operation,
            "record_type": typ,
            "record_key": key,
            "memory_id": memory_id,
            "record_sha256": _digest(normalized),
            "event_seq": event["event_seq"],
            "event_id": event["event_id"],
            "event_hash": event["event_hash"],
            "ledger_head_seq": actual["event_seq"],
            "ledger_head_hash": actual["event_hash"],
            "snapshot_from_seq": manifest["snapshot_from_seq"],
            "post_write_readback": True,
            "authority_effect": "NONE",
        }


def _all_envelopes(profile_id: str, sections: Sequence[str] | None = None) -> list[JsonObject]:
    wanted = list(sections or RECORD_SECTIONS.values())
    try:
        read = backend.memory_read({"profile_id": profile_id, "sections": wanted, "include_superseded": True, "ledger_tail": 0})
    except backend.UserContinuityConflict as exc:
        raise UcmError("UCM_CURRENTNESS_FAILURE", exc.message, exc.status, **exc.extra) from exc
    except backend.UserContinuityError as exc:
        raise UcmError(exc.error_code, exc.message, exc.status, **exc.extra) from exc
    rows: list[JsonObject] = []
    for section in wanted:
        rows.extend(copy.deepcopy((read.get("sections", {}).get(section) or {}).get("facts", [])))
    return [row for row in rows if row.get("class") == "UCM_RECORD" and isinstance(row.get("value"), Mapping)]


def _records(profile_id: str, record_type: str) -> list[JsonObject]:
    section = _record_section(record_type)
    return [copy.deepcopy(row["value"]) for row in _all_envelopes(profile_id, [section])]


def _record_exact(profile_id: str, record_type: str, record_key: str) -> JsonObject:
    target = _target(record_type, record_key)
    try:
        read = backend.memory_read({"profile_id": profile_id, "target": target, "include_superseded": True, "ledger_tail": 0})
    except backend.UserContinuityConflict as exc:
        raise UcmError("UCM_CURRENTNESS_FAILURE", exc.message, exc.status, **exc.extra) from exc
    for section in read.get("sections", {}).values():
        for envelope in section.get("facts", []):
            if envelope.get("class") == "UCM_RECORD" and isinstance(envelope.get("value"), Mapping):
                return copy.deepcopy(dict(envelope["value"]))
    raise UcmError("UCM_RECORD_NOT_FOUND", f"{record_type} record not found: {record_key}", 404)


def _current_control_from_state(state: Mapping[str, Any]) -> JsonObject:
    target = _target("CONTROL_STATE", "control")
    mid = backend._active_target_id(dict(state), target)
    if not mid:
        return default_control_state()
    value = state["facts"][mid].get("value")
    return _validate_control(value if isinstance(value, Mapping) else {})


def _current_control(profile_id: str) -> JsonObject:
    records = _records(profile_id, "CONTROL_STATE")
    return _validate_control(records[-1] if records else {})


def _record_digest(record: Mapping[str, Any]) -> str:
    return _digest(record)


def _fact_with_relation(fact: Mapping[str, Any], relation_type: str, target: str) -> JsonObject:
    out = validate_fact(fact)
    rel = {"type": relation_type, "target": target}
    if rel not in out["relations"]:
        out["relations"].append(rel)
    return out


def utility_can_change_truth(_utility: Mapping[str, Any]) -> bool:
    return False


def record_usage(utility: Mapping[str, Any], *, offered: bool=False, hydrated: bool=False, consumed: bool=False, used_in_decision: bool=False, now_iso: str | None=None) -> JsonObject:
    out=_assistant_utility(utility) or {}
    usage=out["usage"]
    if offered: usage["offered_count"] += 1
    if hydrated: usage["hydrated_count"] += 1
    if consumed: usage["consumed_count"] += 1
    if used_in_decision:
        usage["decision_use_count"] += 1
        usage["last_used_at"] = now_iso or _now()
    return out


def automatic_memory_write_allowed(control_state: Mapping[str, Any]) -> bool:
    return control_state.get("memory_admission_locked") is not True


def session_reset_deletes_durable_memory() -> bool:
    return False


def decision_reopen_due(decision: Mapping[str, Any], condition_tokens: set[str]) -> bool:
    return bool(set(decision.get("supersession_triggers") or []).intersection(condition_tokens))


def decision_can_be_project_authority(_decision: Mapping[str, Any]) -> bool:
    return False


def collaboration_can_widen_authority(_contract: Mapping[str, Any]) -> bool:
    return False


def identity_matches_use(entry: Mapping[str, Any], use_for: str, scope: str | None=None) -> bool:
    if entry.get("status") not in {"ACTIVE","CONTEXTUAL"} or use_for not in set(entry.get("use_for") or []): return False
    scopes=set(entry.get("scope") or []); return scope is None or "*" in scopes or scope in scopes


def referent_matches(entry: Mapping[str, Any], term: str, scope: str | None=None) -> bool:
    if str(entry.get("term") or "").casefold()!=str(term).casefold() or entry.get("status") not in {"ACTIVE","CONTEXTUAL"}: return False
    scopes=set(entry.get("scope") or []); return scope is None or "*" in scopes or scope in scopes


def export_allowed(fact: Mapping[str, Any], destination: str) -> bool:
    cls=fact.get("export_class")
    if destination=="NEUTRAL_SYSTEM": return cls=="PORTABLE" and fact.get("sensitivity") not in {"SENSITIVE","SECRET"}
    if destination=="USER_BACKUP": return cls in {"PORTABLE","USER"}
    if destination=="PROJECT_EXPORT": return cls in {"PORTABLE","PROJECT"}
    if destination=="DEPLOYMENT_BACKUP": return cls in {"PORTABLE","USER","PROJECT","DEPLOYMENT"}
    return False


def classify_durable_user_statement(*, semantic_kind: str, durable: bool, sensitivity: str="NORMAL", target_scope: str="GLOBAL_USER", correction_to_existing: bool=False) -> JsonObject:
    if not durable: return {"trigger_type":"EPHEMERAL","signal_origin":"USER_IMPLICIT","target_scope":"EPHEMERAL","proposed_operation":"NO_PERSIST","write_posture":"DO_NOT_PERSIST","reason":"statement classified as short-lived"}
    if target_scope=="PROJECT_LOCAL": return {"trigger_type":"PROJECT_POINTER_CHANGE","signal_origin":"USER_IMPLICIT","target_scope":"PROJECT_LOCAL","proposed_operation":"NO_PERSIST","write_posture":"DO_NOT_PERSIST","reason":"volatile project-local state belongs to project authority"}
    if sensitivity in {"SENSITIVE","SECRET"}: return {"trigger_type":"DURABLE_PERSONAL_FACT","signal_origin":"USER_IMPLICIT","target_scope":target_scope,"proposed_operation":"PROPOSE","write_posture":"PROPOSE_ONLY","reason":"sensitive durable mention requires explicit retention/import authorization"}
    allowed={"PREFERENCE","IDENTITY","STANDING_CONSTRAINT","RECURRING_WORKFLOW","DURABLE_PERSONAL_FACT"}
    if semantic_kind not in allowed: return {"trigger_type":"DURABLE_PERSONAL_FACT","signal_origin":"USER_IMPLICIT","target_scope":target_scope,"proposed_operation":"PROPOSE","write_posture":"PROPOSE_ONLY","reason":"durability plausible but semantic kind does not auto-admit"}
    typ="EXPLICIT_CORRECTION" if correction_to_existing else ("IDENTITY_CHANGE" if semantic_kind=="IDENTITY" else ("EXPLICIT_PREFERENCE_CHANGE" if semantic_kind in {"PREFERENCE","STANDING_CONSTRAINT"} else ("RECURRING_WORKFLOW" if semantic_kind=="RECURRING_WORKFLOW" else "DURABLE_PERSONAL_FACT")))
    return {"trigger_type":typ,"signal_origin":"USER_IMPLICIT","target_scope":target_scope,"proposed_operation":"SUPERSEDE" if correction_to_existing else "ADD","write_posture":"USER_STATED_DURABLE","reason":"direct durable non-sensitive user statement"}


def infer_memory_scope(text: str, trigger_type: str) -> str:
    lower=text.casefold()
    if trigger_type in {"IDENTITY_CHANGE","EXPLICIT_PREFERENCE_CHANGE","EXPLICIT_FORGET"}: return "GLOBAL_USER"
    if any(x in lower for x in ["for all projects","across projects","global rule","standing engineering rule"]): return "GLOBAL_USER"
    if any(x in lower for x in ["this project","project rule","for this repo","for this branch"]): return "PROJECT_LOCAL"
    if "project" in lower and any(x in lower for x in ["remember","pointer","repo","repository"]): return "PROJECT_POINTER"
    return "GLOBAL_USER"


def next_retrieval_strategy(*, previous_strategy: str | None, previous_succeeded: bool) -> str:
    if previous_strategy is None: return RETRIEVAL_ORDER[0]
    if previous_succeeded: return previous_strategy
    try: i=RETRIEVAL_ORDER.index(previous_strategy)
    except ValueError: return RETRIEVAL_ORDER[0]
    return RETRIEVAL_ORDER[min(i+1,len(RETRIEVAL_ORDER)-1)]


def retrieval_strategy_is_truth_authority(_strategy: str) -> bool:
    return False


def describe() -> JsonObject:
    return {
        "ok": True,
        "system_descriptor": copy.deepcopy(SYSTEM_DESCRIPTOR),
        "ingress_contract": copy.deepcopy(INGRESS_CONTRACT),
        "backend": {
            "ledger_schema": backend.LEDGER_SCHEMA,
            "snapshot_schema": backend.SNAPSHOT_SCHEMA,
            "compatibility_surface": "memory.* retained",
            "authority": "existing user_continuity_store ledger",
        },
        "authority_effect": "NONE",
    }


def head(profile_id: str) -> JsonObject:
    pid = backend._profile_id(profile_id)
    try:
        h = backend.ledger_head(pid)
        current = backend._snapshot_currentness(pid)
    except backend.UserContinuityError as exc:
        raise UcmError(exc.error_code, exc.message, exc.status, **exc.extra) from exc
    return {
        "ok": True,
        "profile_id": pid,
        "ledger_head_seq": h["event_seq"],
        "ledger_head_hash": h["event_hash"],
        "snapshot_current": bool(current["current"]),
        "snapshot_from_seq": (current.get("manifest") or {}).get("snapshot_from_seq", 0),
        "authority_traits": list(AUTHORITY_TRAITS),
    }


def add(payload: Mapping[str, Any]) -> JsonObject:
    typ = str(payload.get("record_type") or "FACT").upper()
    if typ not in RECORD_TYPES:
        raise UcmError("UCM_CONTRACT_INVALID", f"ucm.add record_type must be one of {sorted(RECORD_TYPES)}", 400)
    record = payload.get("record")
    if not isinstance(record, Mapping):
        raise UcmError("UCM_CONTRACT_INVALID", "record object is required", 400)
    return _append_record(payload, record_type=typ, record=record, semantic_operation="ADD")


def update(payload: Mapping[str, Any]) -> JsonObject:
    typ = str(payload.get("record_type") or "FACT").upper()
    key = _key(payload.get("record_key"), "record_key")
    profile_id = _profile_id(payload)
    existing = _record_exact(profile_id, typ, key)
    patch = payload.get("patch")
    if not isinstance(patch, Mapping) or not patch:
        raise UcmError("UCM_CONTRACT_INVALID", "patch object is required", 400)
    disallowed_by_type = {
        "FACT": {"fact_key", "value", "authority", "lifecycle", "currentness", "verification", "temporal", "provenance"},
        "IDENTITY": {"identity_key", "value", "kind"},
        "REFERENT": {"referent_key", "term", "meaning"},
        "COLLABORATION_CONTRACT": {"contract_key"},
        "MEMORY_CANDIDATE": {"candidate_id", "status"},
        "SOURCE_MANIFEST": {"source_key", "sha256", "bytes"},
        "SOURCE_ASSERTION": {"assertion_id", "source_instance", "source_artifact", "source_pointer", "line_start", "line_end", "text", "import_disposition"},
    }
    if set(patch).intersection(disallowed_by_type.get(typ, set())):
        raise UcmError("UCM_MATERIAL_CHANGE_REQUIRES_SUPERSEDE", "material identity/value/lifecycle changes require a dedicated semantic transition", 409)
    replacement = copy.deepcopy(existing)
    replacement.update(copy.deepcopy(dict(patch)))
    return _append_record(payload, record_type=typ, record=replacement, semantic_operation="UPDATE", existing_key=key)


def supersede(payload: Mapping[str, Any]) -> JsonObject:
    typ = str(payload.get("record_type") or "FACT").upper()
    key = _key(payload.get("record_key"), "record_key")
    profile_id = _profile_id(payload)
    old = _record_exact(profile_id, typ, key)
    replacement = payload.get("replacement")
    if not isinstance(replacement, Mapping):
        raise UcmError("UCM_CONTRACT_INVALID", "replacement object is required", 400)
    evidence = [str(x) for x in _list(payload.get("evidence_refs"), "evidence_refs", required=True, max_items=128)]
    normalized = _validate_record(typ, replacement)
    if _record_key(typ, normalized) != key:
        raise UcmError("UCM_STABLE_KEY_REQUIRED", "supersession must retain the stable record key", 409)
    if typ == "FACT":
        normalized["lifecycle"] = "ACTIVE"
        normalized = _fact_with_relation(normalized, "SUPERSEDES", _record_digest(old))
        for ref in evidence:
            normalized = _fact_with_relation(normalized, "CORRECTED_BY_EVIDENCE", ref)
    return _append_record(payload, record_type=typ, record=normalized, semantic_operation="SUPERSEDE", existing_key=key)


def verify(payload: Mapping[str, Any]) -> JsonObject:
    profile_id = _profile_id(payload)
    key = _key(payload.get("fact_key"), "fact_key")
    fact = validate_fact(_record_exact(profile_id, "FACT", key))
    verification_ref = _text(payload.get("verification_ref"), "verification_ref", max_chars=2000)
    verified_at = str(payload.get("verified_at") or _now())
    fact["verification"]["verified_live"] = True
    fact["verification"]["verification_ref"] = verification_ref
    fact["currentness"]["status"] = "CURRENT"
    fact["currentness"]["last_verified_at"] = verified_at
    fact = _fact_with_relation(fact, "VERIFIED_BY", verification_ref)
    return _append_record(payload, record_type="FACT", record=fact, semantic_operation="VERIFY", existing_key=key)


def conflict(payload: Mapping[str, Any]) -> JsonObject:
    profile_id = _profile_id(payload); key = _key(payload.get("fact_key"), "fact_key")
    fact = validate_fact(_record_exact(profile_id, "FACT", key))
    evidence = [str(x) for x in _list(payload.get("evidence_refs"), "evidence_refs", required=True, max_items=128)]
    fact["lifecycle"] = "CONFLICT"; fact["currentness"]["status"] = "CONFLICT"
    for ref in evidence: fact = _fact_with_relation(fact, "CONFLICTS_WITH", ref)
    return _append_record(payload, record_type="FACT", record=fact, semantic_operation="CONFLICT", existing_key=key)


def retire(payload: Mapping[str, Any]) -> JsonObject:
    profile_id = _profile_id(payload); key = _key(payload.get("fact_key"), "fact_key")
    fact = validate_fact(_record_exact(profile_id, "FACT", key)); fact["lifecycle"] = "RETIRED"
    return _append_record(payload, record_type="FACT", record=fact, semantic_operation="RETIRE", existing_key=key)


def rediscover(payload: Mapping[str, Any]) -> JsonObject:
    profile_id = _profile_id(payload); key = _key(payload.get("fact_key"), "fact_key")
    old = validate_fact(_record_exact(profile_id, "FACT", key))
    if old["lifecycle"] not in {"RETIRED", "HISTORICAL", "SUPERSEDED"}:
        raise UcmError("UCM_REDISCOVERY_INVALID", "rediscovery requires retired/historical/superseded lineage", 409)
    evidence = [str(x) for x in _list(payload.get("evidence_refs"), "evidence_refs", required=True, max_items=128)]
    fact = copy.deepcopy(old); fact["lifecycle"] = "ACTIVE"; fact["currentness"]["status"] = "UNVERIFIED"
    fact = _fact_with_relation(fact, "REDISCOVERED_FROM", _record_digest(old))
    for ref in evidence: fact = _fact_with_relation(fact, "SUPPORTED_BY", ref)
    return _append_record(payload, record_type="FACT", record=fact, semantic_operation="REDISCOVER", existing_key=key)


def forget_request(payload: Mapping[str, Any]) -> JsonObject:
    if _write_posture(payload) != "DIRECT_USER_AUTHORIZED":
        raise UcmError("AUTHORITY_FIREWALL", "forget_request requires direct user authorization", 409)
    profile_id = _profile_id(payload); key = _key(payload.get("fact_key"), "fact_key")
    fact = validate_fact(_record_exact(profile_id, "FACT", key)); fact["lifecycle"] = "FORGET_REQUESTED"
    return _append_record(payload, record_type="FACT", record=fact, semantic_operation="FORGET_REQUEST", existing_key=key)


def decision_add(payload: Mapping[str, Any]) -> JsonObject:
    decision = payload.get("decision")
    if not isinstance(decision, Mapping): raise UcmError("UCM_CONTRACT_INVALID", "decision object is required", 400)
    return _append_record(payload, record_type="DECISION", record=_validate_decision(decision), semantic_operation="DECISION_ADD")


def decision_supersede(payload: Mapping[str, Any]) -> JsonObject:
    profile_id = _profile_id(payload); key = _key(payload.get("decision_id"), "decision_id")
    old = _validate_decision(_record_exact(profile_id, "DECISION", key))
    replacement = payload.get("replacement")
    if not isinstance(replacement, Mapping): raise UcmError("UCM_CONTRACT_INVALID", "replacement decision is required", 400)
    new = _validate_decision(replacement)
    if new["decision_id"] != key: raise UcmError("UCM_STABLE_KEY_REQUIRED", "decision supersession must retain decision_id", 409)
    evidence = [str(x) for x in _list(payload.get("evidence_refs"), "evidence_refs", required=True, max_items=128)]
    new["status"] = "ACTIVE"; new["evidence_refs"] = list(dict.fromkeys([*new["evidence_refs"], *evidence]))
    return _append_record(payload, record_type="DECISION", record=new, semantic_operation="DECISION_SUPERSEDE", existing_key=key)


def _control_mutation(payload: Mapping[str, Any], mutate) -> JsonObject:
    profile_id = _profile_id(payload)
    try: current = _record_exact(profile_id, "CONTROL_STATE", "control"); exists = True
    except UcmError as exc:
        if exc.error_code != "UCM_RECORD_NOT_FOUND": raise
        current = default_control_state(); exists = False
    new = _validate_control(mutate(copy.deepcopy(current)))
    op = "CONTROL_UPDATE" if exists else "ADD"
    return _append_record(payload, record_type="CONTROL_STATE", record=new, semantic_operation=op, existing_key="control" if exists else None)


def lock(payload: Mapping[str, Any]) -> JsonObject:
    if _write_posture(payload) != "DIRECT_USER_AUTHORIZED": raise UcmError("AUTHORITY_FIREWALL", "ucm.lock requires direct user authorization", 409)
    kind = _enum(payload.get("lock"), "lock", CONTROL_LOCKS)
    field = {"MEMORY_ADMISSION":"memory_admission_locked", "ADAPTIVE_HYDRATION":"adaptive_hydration_locked", "COLLABORATION_ADAPTATION":"collaboration_adaptation_locked"}[kind]
    return _control_mutation(payload, lambda state: {**state, field: True})


def unlock(payload: Mapping[str, Any]) -> JsonObject:
    if _write_posture(payload) != "DIRECT_USER_AUTHORIZED": raise UcmError("AUTHORITY_FIREWALL", "ucm.unlock requires direct user authorization", 409)
    kind = _enum(payload.get("lock"), "lock", CONTROL_LOCKS)
    field = {"MEMORY_ADMISSION":"memory_admission_locked", "ADAPTIVE_HYDRATION":"adaptive_hydration_locked", "COLLABORATION_ADAPTATION":"collaboration_adaptation_locked"}[kind]
    return _control_mutation(payload, lambda state: {**state, field: False})


def session_reset(payload: Mapping[str, Any]) -> JsonObject:
    if _write_posture(payload) != "DIRECT_USER_AUTHORIZED": raise UcmError("AUTHORITY_FIREWALL", "session reset requires direct user authorization", 409)
    scope = _enum(payload.get("scope"), "scope", RESET_SCOPES)
    reset_at = str(payload.get("reset_at") or _now())
    def mutate(state: JsonObject) -> JsonObject:
        state["session_generation"] = int(state.get("session_generation") or 0) + 1
        state["last_reset_at"] = reset_at; state["reset_scope"] = scope
        return state
    receipt = _control_mutation(payload, mutate)
    receipt.update({"reset_scope": scope, "durable_memory_deleted": False, "law": "SESSION_RESET != DURABLE_MEMORY_DELETE"})
    return receipt


def memory_candidate_confirm(payload: Mapping[str, Any]) -> JsonObject:
    if _write_posture(payload) != "DIRECT_USER_AUTHORIZED": raise UcmError("AUTHORITY_FIREWALL", "candidate confirmation requires direct user authorization", 409)
    profile_id = _profile_id(payload); key = _key(payload.get("candidate_id"), "candidate_id")
    candidate = _validate_candidate(_record_exact(profile_id, "MEMORY_CANDIDATE", key))
    if candidate["status"] != "PENDING_USER_CONFIRMATION": raise UcmError("UCM_CANDIDATE_STATE_INVALID", "candidate is not pending", 409)
    candidate["status"] = "ACCEPTED" if bool(payload.get("user_confirmed")) else "REJECTED"
    return _append_record(payload, record_type="MEMORY_CANDIDATE", record=candidate, semantic_operation="MEMORY_CANDIDATE_CONFIRM", existing_key=key)


def _fact_visible(fact: Mapping[str, Any], include_historical: bool = False) -> bool:
    return include_historical or fact.get("lifecycle") not in {"SUPERSEDED", "REJECTED", "RETIRED", "FORGET_REQUESTED"}


def get_fact(profile_id: str, fact_key: str) -> JsonObject:
    return validate_fact(_record_exact(backend._profile_id(profile_id), "FACT", fact_key))


def resolve_identity_from_records(records: Sequence[Mapping[str, Any]], *, use_for: str, scope: str | None = None) -> JsonObject | None:
    use = _enum(use_for, "use_for", IDENTITY_USES)
    candidates = []
    for row in records:
        identity = _validate_identity(row)
        if identity["status"] not in {"ACTIVE", "CONTEXTUAL"} or use not in identity["use_for"]: continue
        scopes = set(identity["scope"])
        if scope is not None and "*" not in scopes and scope not in scopes: continue
        candidates.append(identity)
    candidates.sort(key=lambda x: (int(x["precedence"]), x["identity_key"]), reverse=True)
    if not candidates:
        return None
    top_precedence = int(candidates[0]["precedence"])
    top = [item for item in candidates if int(item["precedence"]) == top_precedence]
    if len({item["value"] for item in top}) > 1:
        raise UcmError(
            "UCM_IDENTITY_AMBIGUOUS",
            "multiple active identity values share the highest applicable precedence",
            409,
            use_for=use,
            scope=scope,
            precedence=top_precedence,
            identity_keys=sorted(item["identity_key"] for item in top),
        )
    return candidates[0]


def resolve_identity(profile_id: str, *, use_for: str, scope: str | None = None) -> JsonObject | None:
    return resolve_identity_from_records(_records(backend._profile_id(profile_id), "IDENTITY"), use_for=use_for, scope=scope)


def resolve_referent(profile_id: str, *, term: str, scope: str | None = None) -> JsonObject | None:
    wanted = _text(term, "term", max_chars=500).casefold(); candidates=[]
    for row in _records(backend._profile_id(profile_id), "REFERENT"):
        ref = _validate_referent(row)
        if ref["term"].casefold() != wanted or ref["status"] not in {"ACTIVE", "CONTEXTUAL"}: continue
        scopes=set(ref["scope"])
        if scope is not None and "*" not in scopes and scope not in scopes: continue
        candidates.append(ref)
    candidates.sort(key=lambda x: (int(x["precedence"]), x["referent_key"]), reverse=True)
    if not candidates:
        return None
    top_precedence = int(candidates[0]["precedence"])
    top = [item for item in candidates if int(item["precedence"]) == top_precedence]
    if len({item["meaning"] for item in top}) > 1:
        raise UcmError(
            "UCM_REFERENT_AMBIGUOUS",
            "multiple active referent meanings share the highest applicable precedence",
            409,
            term=wanted,
            scope=scope,
            precedence=top_precedence,
            referent_keys=sorted(item["referent_key"] for item in top),
        )
    return candidates[0]


def read_decisions(profile_id: str, *, include_historical: bool = False) -> list[JsonObject]:
    rows=[_validate_decision(x) for x in _records(backend._profile_id(profile_id), "DECISION")]
    if not include_historical: rows=[x for x in rows if x["status"] in {"ACTIVE", "DEFERRED", "CONFLICT"}]
    rows.sort(key=lambda x:x["decision_id"]); return rows


def read_control_state(profile_id: str) -> JsonObject:
    return _current_control(backend._profile_id(profile_id))


def memory_candidates(profile_id: str, *, include_closed: bool = False) -> list[JsonObject]:
    rows=[_validate_candidate(x) for x in _records(backend._profile_id(profile_id), "MEMORY_CANDIDATE")]
    if not include_closed: rows=[x for x in rows if x["status"] == "PENDING_USER_CONFIRMATION"]
    rows.sort(key=lambda x:x["candidate_id"]); return rows


def source_manifest(profile_id: str) -> list[JsonObject]:
    rows=[_validate_source_manifest(x) for x in _records(backend._profile_id(profile_id), "SOURCE_MANIFEST")]
    rows.sort(key=lambda x:(x["source_instance"],x["artifact"],x["sha256"])); return rows


def _verification_debt_rows_from_facts(facts: Sequence[Mapping[str, Any]], *, condition_tokens: set[str] | None = None) -> list[JsonObject]:
    debt=[]
    for fact in facts:
        if not _fact_visible(fact):
            continue
        reasons=[]
        if verification_requirement(fact)=="REQUIRED" and not current_usable(fact):
            reasons.append("required_live_verification_missing")
        if due_for_revalidation(fact, condition_tokens=condition_tokens):
            reasons.append("revalidation_due")
        if fact["currentness"]["status"] in {"UNKNOWN","UNVERIFIED","CONFLICT"}:
            reasons.append(f"currentness_{fact['currentness']['status'].lower()}")
        if reasons:
            debt.append({
                "fact_key":fact["fact_key"],
                "reasons":sorted(set(reasons)),
                "currentness":copy.deepcopy(fact["currentness"]),
                "verification":copy.deepcopy(fact["verification"]),
            })
    debt.sort(key=lambda x:x["fact_key"])
    return debt


def _compact_verification_debt(facts: Sequence[Mapping[str, Any]], *, snapshot_from_seq: int) -> JsonObject:
    debt=_verification_debt_rows_from_facts(facts)
    fact_by_key={str(fact["fact_key"]):fact for fact in facts}
    by_plane={"DEPLOYMENT":0,"PROJECT":0,"RUNTIME":0}
    for item in debt:
        fact=fact_by_key.get(str(item["fact_key"])) or {}
        target=str(((fact.get("authority") or {}).get("target_plane") or "")).upper()
        if "DEPLOYMENT" in target:
            by_plane["DEPLOYMENT"]+=1
        elif "PROJECT" in target:
            by_plane["PROJECT"]+=1
        elif "RUNTIME" in target:
            by_plane["RUNTIME"]+=1
    return {
        "schema":"rahl.user-continuity.verification-debt.v1",
        "snapshot_from_seq":int(snapshot_from_seq),
        "required_unverified_count":len(debt),
        "by_plane":by_plane,
        "sample_fact_keys":[str(item["fact_key"]) for item in debt[:8]],
        "full_index":"ucm.verification_debt",
    }


def verification_debt(profile_id: str, *, condition_tokens: set[str] | None = None) -> list[JsonObject]:
    facts=[validate_fact(row) for row in _records(backend._profile_id(profile_id), "FACT")]
    return _verification_debt_rows_from_facts(facts, condition_tokens=condition_tokens)

def _collaboration(profile_id: str) -> JsonObject | None:
    rows=[_validate_collaboration(x) for x in _records(profile_id,"COLLABORATION_CONTRACT")]
    if not rows: return None
    rows.sort(key=lambda x:x["contract_key"]); return rows[-1]


def _identity_index(profile_id: str) -> JsonObject:
    rows=[]
    for raw in _records(profile_id,"IDENTITY"):
        x=_validate_identity(raw); rows.append({k:x[k] for k in ("identity_key","kind","value","status","use_for","scope","precedence")})
    rows.sort(key=lambda x:x["identity_key"]); return {"identities":rows}


def _referent_index(profile_id: str) -> JsonObject:
    rows=[]
    for raw in _records(profile_id,"REFERENT"):
        x=_validate_referent(raw); rows.append({k:x[k] for k in ("referent_key","term","meaning","status","scope","precedence")})
    rows.sort(key=lambda x:x["referent_key"]); return {"referents":rows}


def _decision_index(profile_id: str) -> JsonObject:
    rows=[]
    for x in read_decisions(profile_id,include_historical=True): rows.append({"decision_id":x["decision_id"],"status":x["status"],"statement":x["statement"],"scope":x["scope"]})
    return {"decisions":rows}


def _candidate_head(profile_id: str) -> JsonObject:
    rows=memory_candidates(profile_id,include_closed=True); pending=[x["candidate_id"] for x in rows if x["status"]=="PENDING_USER_CONFIRMATION"]
    return {"count":len(rows),"pending_count":len(pending),"pending_ids":pending}


def _core_facts(profile_id: str) -> dict[str,JsonObject]:
    return {fact["fact_key"]:fact for fact in _core_fact_records(profile_id)}


def _core_fact_records(profile_id: str) -> list[JsonObject]:
    candidates=[]
    for raw in _records(profile_id,"FACT"):
        fact=validate_fact(raw)
        if not _fact_visible(fact): continue
        groups=set(fact["hydration_groups"])
        if not groups.intersection(CORE_HYDRATION_GROUPS): continue
        candidates.append((derive_hydration_score(fact.get("assistant_utility")),fact["fact_key"],fact))
    candidates.sort(key=lambda x:(x[0],x[1]),reverse=True)
    return [fact for _,_,fact in candidates]


def _ingress_identity_index(profile_id: str) -> JsonObject:
    rows=[_validate_identity(raw) for raw in _records(profile_id,"IDENTITY")]
    rows.sort(key=lambda x:x["identity_key"])
    return {"v":1,"e":[_ingress_identity_projection(x) for x in rows],"full":"ucm:IDENTITY"}


def _ingress_referent_index(profile_id: str) -> JsonObject:
    rows=[_validate_referent(raw) for raw in _records(profile_id,"REFERENT")]
    rows.sort(key=lambda x:x["referent_key"])
    return {"v":1,"e":[_ingress_referent_projection(x) for x in rows],"full":"ucm:REFERENT"}


def _ingress_decision_index(profile_id: str) -> JsonObject:
    rows=[_validate_decision(raw) for raw in _records(profile_id,"DECISION")]
    rows.sort(key=lambda x:x["decision_id"])
    return {"v":1,"e":[_ingress_decision_projection(x) for x in rows],"full":"ucm:DECISION"}


def _ingress_candidate_head(profile_id: str) -> JsonObject:
    rows=[_validate_candidate(raw) for raw in _records(profile_id,"MEMORY_CANDIDATE")]
    return _ingress_candidate_head_from_rows(rows)


def _head_surface(profile_id: str) -> JsonObject:
    h=head(profile_id)
    return {"schema":"pcmmad.ucm-user-store-head.v1","system_version":SYSTEM_VERSION,"user_store_id":profile_id,"not_project_authority":True,"not_doctrine_authority":True,"ledger_head_seq":h["ledger_head_seq"],"ledger_head_hash":h["ledger_head_hash"],"snapshot_from_seq":h["snapshot_from_seq"]}


def _build_ingress(profile_id: str) -> JsonObject:
    h=head(profile_id)
    if h["ledger_head_seq"] == 0:
        raise UcmError("USER_CONTINUITY_INCOMPLETE", "user continuity store is not initialized", 409, missing=sorted(REQUIRED_INGRESS_SURFACES - {"SYSTEM_DESCRIPTOR"}))
    if not h["snapshot_current"] or int(h["snapshot_from_seq"] or 0) < int(h["ledger_head_seq"]):
        raise UcmError("UCM_CURRENTNESS_FAILURE", "UCM snapshot trails authoritative ledger head", 409, **h)
    full_core_facts = _core_fact_records(profile_id)
    all_visible_facts=[validate_fact(row) for row in _records(profile_id,"FACT")]
    all_visible_facts=[fact for fact in all_visible_facts if _fact_visible(fact)]
    collaboration = _collaboration(profile_id)
    surfaces: JsonObject = {
        "CORE_SNAPSHOT": {"snapshot_from_seq":h["snapshot_from_seq"],"facts":{x["fact_key"]:_ingress_fact_projection(x) for x in full_core_facts}},
        "IDENTITY_INDEX": _ingress_identity_index(profile_id),
        "COLLABORATION_CONTRACT": _ingress_collaboration_projection(collaboration),
        "REFERENT_INDEX": _ingress_referent_index(profile_id),
        "VERIFICATION_DEBT": _compact_verification_debt(all_visible_facts, snapshot_from_seq=int(h["snapshot_from_seq"] or 0)),
        "CONTROL_STATE": _current_control(profile_id),
        "DECISION_INDEX": _ingress_decision_index(profile_id),
        "CANDIDATE_QUEUE_HEAD": _ingress_candidate_head(profile_id),
    }
    missing=[]
    if surfaces["COLLABORATION_CONTRACT"] is None: missing.append("COLLABORATION_CONTRACT")
    present={"SYSTEM_DESCRIPTOR","USER_STORE_HEAD",*surfaces.keys()}
    missing.extend(sorted(REQUIRED_INGRESS_SURFACES-present))
    if missing: raise UcmError("USER_CONTINUITY_INCOMPLETE","required fresh-instance surfaces are missing",409,missing=sorted(set(missing)))
    if any(not fact.get("provenance") for fact in full_core_facts):
        raise UcmError("UCM_PROVENANCE_FAILURE","required core fact provenance missing",409)
    user_head=_head_surface(profile_id)
    digest_fields={
        "core_snapshot_sha256":_digest(surfaces["CORE_SNAPSHOT"]),"identity_index_sha256":_digest(surfaces["IDENTITY_INDEX"]),
        "collaboration_contract_sha256":_digest(surfaces["COLLABORATION_CONTRACT"]),"referent_index_sha256":_digest(surfaces["REFERENT_INDEX"]),
        "decision_index_sha256":_digest(surfaces["DECISION_INDEX"]),"verification_debt_sha256":_digest(surfaces["VERIFICATION_DEBT"]),
        "control_state_sha256":_digest(surfaces["CONTROL_STATE"]),"candidate_queue_head_sha256":_digest(surfaces["CANDIDATE_QUEUE_HEAD"]),
        "source_manifest_sha256":_digest(source_manifest(profile_id)),
    }
    user_head.update(digest_fields)
    budget_packet={"USER_STORE_HEAD":user_head,**surfaces}
    encoded=_canonical_bytes(budget_packet); used=len(encoded); headroom=CORE_BUDGET_BYTES-used
    if used>CORE_BUDGET_BYTES or headroom<MIN_HEADROOM_BYTES:
        raise UcmError("UCM_CORE_BUDGET_EXCEEDED","fresh-instance user core exceeds budget/headroom contract",409,core_bytes=used,core_budget_bytes=CORE_BUDGET_BYTES,headroom_bytes=headroom,min_headroom_bytes=MIN_HEADROOM_BYTES)
    final_head = head(profile_id)
    if (
        int(final_head.get("ledger_head_seq") or 0) != int(h.get("ledger_head_seq") or 0)
        or final_head.get("ledger_head_hash") != h.get("ledger_head_hash")
        or not final_head.get("snapshot_current")
    ):
        raise UcmError(
            "UCM_CURRENTNESS_FAILURE",
            "UCM authoritative head changed while assembling the fresh-instance core",
            409,
            start_head_seq=h.get("ledger_head_seq"),
            start_head_hash=h.get("ledger_head_hash"),
            final_head_seq=final_head.get("ledger_head_seq"),
            final_head_hash=final_head.get("ledger_head_hash"),
            snapshot_current=final_head.get("snapshot_current"),
        )
    return {
        "schema":"pcmmad.ucm-ingress-packet.v1","system_version":SYSTEM_VERSION,
        "SYSTEM_DESCRIPTOR":copy.deepcopy(SYSTEM_DESCRIPTOR),"USER_STORE_HEAD":user_head,**surfaces,
        "core_bytes":used,"core_budget_bytes":CORE_BUDGET_BYTES,"headroom_bytes":headroom,"min_headroom_bytes":MIN_HEADROOM_BYTES,
        "ingress_status":"PASS","authority_traits":list(AUTHORITY_TRAITS),
    }


def read_core(profile_id: str) -> JsonObject:
    packet=_build_ingress(backend._profile_id(profile_id)); count=len(packet["CORE_SNAPSHOT"]["facts"]); return {"ok":True,**packet,"hydration_telemetry":{"OFFERED":count,"HYDRATED":count,"CONSUMED":0,"USED_IN_DECISION":0,"read_is_nonmutating":True}}


def read_sections(profile_id: str, groups: Sequence[str], *, include_historical: bool=False) -> JsonObject:
    pid=backend._profile_id(profile_id); wanted={str(x) for x in groups}
    if not wanted or len(wanted)>MAX_READ_GROUPS: raise UcmError("UCM_CONTRACT_INVALID",f"groups must contain 1-{MAX_READ_GROUPS} values",400)
    facts={}
    for raw in _records(pid,"FACT"):
        fact=validate_fact(raw)
        if not _fact_visible(fact,include_historical): continue
        if wanted.intersection(set(fact["hydration_groups"])): facts[fact["fact_key"]]=fact
    return {"ok":True,"profile_id":pid,"groups":sorted(wanted),"facts":facts,"count":len(facts),"bounded":True,"authority_effect":"NONE","hydration_telemetry":{"OFFERED":len(facts),"HYDRATED":len(facts),"CONSUMED":0,"USED_IN_DECISION":0,"read_is_nonmutating":True}}


def search(profile_id: str, query: str, *, limit: int=20, include_historical: bool=False) -> JsonObject:
    pid=backend._profile_id(profile_id); q=_text(query,"query",max_chars=500).casefold(); limit=int(limit)
    if limit<1 or limit>MAX_SEARCH_RESULTS: raise UcmError("UCM_CONTRACT_INVALID",f"limit must be 1-{MAX_SEARCH_RESULTS}",400)
    terms=[x for x in re.split(r"\s+",q) if x]; rows=[]
    for raw in _records(pid,"FACT"):
        fact=validate_fact(raw)
        if not _fact_visible(fact,include_historical): continue
        hay=" ".join([fact["fact_key"]," ".join(fact["descriptive_tags"]),json.dumps(fact["value"],ensure_ascii=False,sort_keys=True)," ".join((fact.get("assistant_utility") or {}).get("retrieval_cues") or [])]).casefold()
        hits=sum(1 for term in terms if term in hay)
        if hits: rows.append({"score":hits/max(1,len(terms)),"fact_key":fact["fact_key"],"fact":fact,"search_hit_is_evidentiary_support":False})
    rows.sort(key=lambda x:(-x["score"],x["fact_key"])); return {"ok":True,"query":q,"results":rows[:limit],"count":min(len(rows),limit),"bounded":len(rows)>limit,"law":"SEARCH_HIT != CLAIM_SUPPORT"}


def events_tail(profile_id: str, count: int=20) -> JsonObject:
    pid=backend._profile_id(profile_id); count=max(0,min(int(count),MAX_EVENT_TAIL)); events=backend.read_events(pid); rows=[]
    for event in events:
        payload=event.get("payload") or {}; semantic=payload.get("ucm_operation")
        if semantic:
            rows.append({"event_seq":event["event_seq"],"event_id":event["event_id"],"event_hash":event["event_hash"],"recorded_at":event["timestamp"],"actor":event["actor"],"source_instance":event["source_instance"],"operation":semantic,"record_type":payload.get("ucm_record_type"),"record_key":payload.get("ucm_record_key")})
    return {"ok":True,"profile_id":pid,"events":rows[-count:] if count else [],"count":min(count,len(rows)),"bounded":True}


def compile_context_packet(profile_id: str, *, groups: Sequence[str] | None=None, query: str | None=None, max_bytes: int=12000) -> JsonObject:
    pid=backend._profile_id(profile_id); max_bytes=int(max_bytes)
    if max_bytes<=0 or max_bytes>MAX_CONTEXT_PACKET_BYTES: raise UcmError("UCM_CONTRACT_INVALID",f"max_bytes must be 1-{MAX_CONTEXT_PACKET_BYTES}",400)
    ingress=_build_ingress(pid)
    facts={fact["fact_key"]:copy.deepcopy(fact) for fact in _core_fact_records(pid)}
    if groups:
        facts.update(read_sections(pid,list(groups))["facts"])
    if query:
        for row in search(pid,query,limit=20)["results"]: facts[row["fact_key"]]=row["fact"]
    packet={"facts":facts,"decisions":read_decisions(pid),"contradictions":[x for x in facts.values() if x["lifecycle"]=="CONFLICT"],"verification_debt":verification_debt(pid),"referents":_referent_index(pid)["referents"],"collaboration":_collaboration(pid),"event_tail":events_tail(pid,10)["events"],"source_pointers":source_manifest(pid)}
    encoded=_canonical_bytes(packet)
    if len(encoded)>max_bytes: raise UcmError("CONTEXT_PACKET_BUDGET_EXCEEDED","compiled UCM context packet exceeds explicit budget",409,packet_bytes=len(encoded),budget_bytes=max_bytes)
    return {"ok":True,"packet":packet,"bytes":len(encoded),"budget_bytes":max_bytes,"authority_effect":"NONE","law":"RETRIEVAL_PACKET != AUTHORITY"}


def materialize(payload: Mapping[str, Any]) -> JsonObject:
    profile_id=_profile_id(payload); seq,expected_hash=_require_cas_fields(payload)
    h=backend.ledger_head(profile_id); _check_cas({"event_count":h["event_seq"],"head_hash":h["event_hash"]},seq,expected_hash)
    try:
        compact=backend.memory_compact_snapshot({"profile_id":profile_id,"expected_ledger_head_hash":expected_hash})
        pruning=backend._prune_derived_snapshot_cache(backend._paths(profile_id), backend._load_current_manifest(profile_id) or {}, 2)
        compact["derived_cache_pruning"]=pruning
        compact["derived_snapshot_retention"]=2
    except backend.UserContinuityError as exc: raise UcmError(exc.error_code,exc.message,exc.status,**exc.extra) from exc
    try:
        packet=_build_ingress(profile_id)
        ingress={"status":"PASS","core_bytes":packet["core_bytes"],"headroom_bytes":packet["headroom_bytes"],"taxonomy":None}
    except UcmError as exc:
        if exc.error_code not in {"USER_CONTINUITY_INCOMPLETE","UCM_CURRENTNESS_FAILURE","UCM_PROVENANCE_FAILURE","UCM_CORE_BUDGET_EXCEEDED","AUTHORITY_FIREWALL"}:
            raise
        ingress={"status":"FAIL","taxonomy":exc.error_code,"detail":exc.message,**exc.extra}
    return {"ok":True,"profile_id":profile_id,"snapshot":compact,"ingress":ingress,"authority_effect":"NONE"}


def export_filtered(profile_id: str, destination_class: str) -> JsonObject:
    pid=backend._profile_id(profile_id); destination=str(destination_class or "").upper()
    allowed={"NEUTRAL_SYSTEM":{"PORTABLE"},"USER_BACKUP":{"PORTABLE","USER"},"PROJECT_EXPORT":{"PORTABLE","PROJECT"},"DEPLOYMENT_BACKUP":{"PORTABLE","USER","PROJECT","DEPLOYMENT"}}
    if destination not in allowed: raise UcmError("UCM_CONTRACT_INVALID",f"unknown destination_class: {destination}",400)
    facts=[]
    for raw in _records(pid,"FACT"):
        fact=validate_fact(raw)
        if fact["export_class"] not in allowed[destination]: continue
        if destination=="NEUTRAL_SYSTEM" and fact["sensitivity"] in {"SENSITIVE","SECRET"}: continue
        facts.append(fact)
    user_surfaces={}
    if destination in {"USER_BACKUP","DEPLOYMENT_BACKUP"}:
        user_surfaces={"identities":_identity_index(pid)["identities"],"referents":_referent_index(pid)["referents"],"decisions":read_decisions(pid,include_historical=True),"collaboration":_collaboration(pid),"control_state":_current_control(pid)}
    return {"ok":True,"destination_class":destination,"facts":facts,**user_surfaces,"authority_effect":"NONE","law":"EXPORT_CLASS_IS_A_FILTER_NOT_A_JUDGMENT_CALL"}


def import_source_bytes(profile_id: str, *, original_name: str, data: bytes, source_instance: str, imported_at: str, coverage: Mapping[str,Any] | None=None, export_class: str="USER") -> JsonObject:
    """Internal migration helper; not a public native tool in UCS v1.0."""
    pid=backend._profile_id(profile_id); paths=backend._paths(pid); digest=hashlib.sha256(data).hexdigest(); blob=paths.root/"sources"/"blobs"/"sha256"/digest; blob.parent.mkdir(parents=True,exist_ok=True)
    if blob.exists() and blob.read_bytes()!=data: raise UcmError("UCM_SOURCE_CORRUPT","content-addressed source collision/corruption",409)
    if not blob.exists(): blob.write_bytes(data)
    return {"source_key":digest,"source_instance":source_instance,"artifact":original_name,"sha256":digest,"bytes":len(data),"preservation":"CONTENT_ADDRESSED","blob_path":blob.relative_to(paths.root).as_posix(),"coverage":copy.deepcopy(dict(coverage or {})),"policy_absences":[],"source_role":"CONTINUITY","export_class":export_class,"imported_at":imported_at}
