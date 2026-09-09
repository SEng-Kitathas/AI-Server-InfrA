"""Research Epistemic Shadow (RES) deterministic policy/projection mechanics.

RES remains project continuity, not a parallel database, execution plane, or
authority source.  Durable mutation/history uses the existing project/protocol/
artifact machinery; this module validates the RES-specific semantic contract and
derives bounded readiness/projection results from those existing surfaces.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from protocol_models import ProtocolEventKind
from protocol_store import build_snapshot, read_events
from shared_core import get_project_root, sha256_file

JsonObject = dict[str, Any]

RES_ARTIFACT_CLASS_SNAPSHOT = "continuity.res.snapshot"
RES_ARTIFACT_CLASS_ADDENDUM = "continuity.res.addendum"
RES_CONTINUITY_KIND = "RESEARCH_EPISTEMIC_SHADOW"
RES_CANONICAL_SNAPSHOT_PATH = "continuity/research_epistemic_shadow/RESEARCH_EPISTEMIC_SHADOW.md"

TRUTH_STATES = (
    "VERIFIED",
    "OBSERVED",
    "INFERRED",
    "HYPOTHESIZED",
    "INTUITION_SIGNAL",
    "UNKNOWN",
    "REJECTED_DEMOTED",
)
TRUTH_STATE_SET = frozenset(TRUTH_STATES)

TRANSITION_KINDS = frozenset({"CREATE", "PROMOTE", "DEMOTE", "SUPERSEDE", "REAFFIRM"})

REQUIRED_SECTIONS = (
    "Project / Research Identity",
    "Governing Intent",
    "Governing Laws / Guards",
    "Current Empirical Boundary",
    "Major Discoveries",
    "Candidate Invariants / Mechanisms",
    "Silent Implications / Structurally Inferred Consequences",
    "Reasoning / Causal / Temporal Model",
    "Intuitions / Extrapolations / Research Signals",
    "Negative Space / Missing Shape",
    "Representation / Coordinate Questions",
    "Cross-Domain / Cross-Project Implications",
    "Applications Already Derived",
    "Rejected Overreads / Demotions",
    "Open Hypotheses and Competing Explanations",
    "Highest-Value Research Holes",
    "Prospective Discriminators / Hostile Experiments",
    "Operational Risks",
    "Source / Artifact Spine",
    "Claim Ceiling",
    "Delta Since Previous RES",
    "Research Re-entry / Exact Next Move",
)

MATERIAL_EVENT_CLASSES = frozenset(
    {
        "SUBSTANTIAL_RESEARCH_COMPLETION",
        "IMPORTANT_EXPERIMENT_RESULT",
        "MECHANISM_OR_INVARIANT_INFERENCE",
        "CAUSAL_REINTERPRETATION",
        "HYPOTHESIS_PROMOTION",
        "HYPOTHESIS_DEMOTION",
        "CONTRADICTION",
        "COORDINATE_OR_ONTOLOGY_PROBLEM",
        "NEGATIVE_SPACE_BOUNDARY",
        "CROSS_PROJECT_IMPLICATION",
        "IMPORTANT_SOURCE_INGESTION",
        "FRONTIER_MOVEMENT",
        "RESEARCH_HANDOFF_CHECKPOINT",
    }
)

MATERIAL_PROTOCOL_EVENTS = frozenset(
    {
        ProtocolEventKind.CLAIM_RECORDED,
        ProtocolEventKind.PROMOTION_RECORDED,
    }
)

_HEADING_RE = re.compile(r"^##\s+(\d+)\.\s+(.+?)\s*$")
_TRUTH_PREFIX_RE = re.compile(r"^\s*`([A-Z][A-Z0-9_]*)`\s*(?:—|-)\s+")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ResPolicyError(ValueError):
    def __init__(self, code: str, message: str, *, status: int = 400, extra: Mapping[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = int(status)
        self.extra = dict(extra or {})


def _fail(code: str, message: str, *, status: int = 400, **extra: Any) -> None:
    raise ResPolicyError(code, message, status=status, extra=extra)


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _required_text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        _fail("RES_ADDENDUM_INVALID", f"{field} is required")
    return text


def _string_list(value: Any, field: str, *, required: bool = False) -> list[str]:
    if value is None:
        value = []
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        _fail("RES_ADDENDUM_INVALID", f"{field} must be a list of non-empty strings")
    result = [item.strip() for item in value]
    if required and not result:
        _fail("RES_PROVENANCE_REQUIRED", f"{field} must contain at least one reference")
    return result


def _normalize_claim(raw: Any, *, prior_claim: Mapping[str, Any] | None = None) -> JsonObject:
    if not isinstance(raw, Mapping):
        _fail("RES_ADDENDUM_INVALID", "claims must be objects")
    claim_id = _required_text(raw.get("claim_id"), "claim_id")
    statement = _required_text(raw.get("statement"), "statement")
    status = _required_text(raw.get("truth_status"), "truth_status").upper()
    if status not in TRUTH_STATE_SET:
        _fail("RES_TRUTH_STATE_INVALID", f"unsupported RES truth state: {status}", allowed=list(TRUTH_STATES))
    provenance = _string_list(raw.get("provenance_refs"), "provenance_refs", required=True)
    evidence = _string_list(raw.get("evidence_refs"), "evidence_refs")
    if status in {"VERIFIED", "OBSERVED", "REJECTED_DEMOTED"} and not evidence:
        _fail("RES_EVIDENCE_REQUIRED", f"{status} claims require evidence_refs")

    transition = str(raw.get("transition_kind") or ("CREATE" if prior_claim is None else "")).strip().upper()
    if transition not in TRANSITION_KINDS:
        _fail("RES_TRANSITION_REQUIRED", "existing claims require an explicit RES transition_kind", allowed=sorted(TRANSITION_KINDS))
    if prior_claim is None and transition != "CREATE":
        _fail("RES_TRANSITION_INVALID", "a new claim must use CREATE")
    if prior_claim is not None and transition == "CREATE":
        _fail("RES_TRANSITION_INVALID", "an existing claim cannot silently restart with CREATE")
    if prior_claim is not None and transition == "REAFFIRM" and status != str(prior_claim.get("truth_status")):
        _fail("RES_TRANSITION_INVALID", "REAFFIRM cannot change truth_status")
    if transition == "DEMOTE" and status != "REJECTED_DEMOTED":
        _fail("RES_TRANSITION_INVALID", "DEMOTE must preserve the canonical REJECTED_DEMOTED state")
    if transition in {"PROMOTE", "DEMOTE", "SUPERSEDE"} and not evidence:
        _fail("RES_TRANSITION_EVIDENCE_REQUIRED", f"{transition} requires evidence_refs")
    if transition == "PROMOTE" and status in {"UNKNOWN", "REJECTED_DEMOTED", "INTUITION_SIGNAL"}:
        _fail("RES_TRANSITION_INVALID", f"PROMOTE cannot target {status}")

    previous_claim_digest = str(raw.get("previous_claim_digest") or "").strip().lower() or None
    if prior_claim is not None:
        expected = str(prior_claim.get("claim_digest") or "")
        if not previous_claim_digest or previous_claim_digest != expected:
            _fail("RES_CLAIM_CURRENTNESS_STALE", "existing claim transition must bind the exact prior claim_digest", expected_claim_digest=expected)
    elif previous_claim_digest is not None:
        _fail("RES_TRANSITION_INVALID", "CREATE must not supply previous_claim_digest")

    normalized = {
        "claim_id": claim_id,
        "statement": statement,
        "truth_status": status,
        "transition_kind": transition,
        "previous_claim_digest": previous_claim_digest,
        "provenance_refs": provenance,
        "evidence_refs": evidence,
    }
    normalized["claim_digest"] = digest(normalized)
    return normalized


def validate_addendum(addendum: Mapping[str, Any], *, prior_projection: Mapping[str, Any] | None = None) -> JsonObject:
    if not isinstance(addendum, Mapping):
        _fail("RES_ADDENDUM_INVALID", "addendum must be an object")
    if str(addendum.get("authority_effect") or "NONE").strip().upper() != "NONE":
        _fail("RES_AUTHORITY_FIREWALL", "RES addenda cannot grant or promote governing authority", status=409)
    schema = str(addendum.get("schema") or "pcmmad.res-addendum.v1")
    if schema != "pcmmad.res-addendum.v1":
        _fail("RES_ADDENDUM_INVALID", "unsupported RES addendum schema")
    addendum_id = _required_text(addendum.get("addendum_id"), "addendum_id")
    event_class = _required_text(addendum.get("material_event_class"), "material_event_class").upper()
    if event_class not in MATERIAL_EVENT_CLASSES:
        _fail("RES_MATERIAL_EVENT_INVALID", f"unknown material epistemic event class: {event_class}", allowed=sorted(MATERIAL_EVENT_CLASSES))
    prior_head = str(addendum.get("prior_addendum_digest") or "").strip().lower() or None
    if prior_head is not None and not _SHA256_RE.fullmatch(prior_head):
        _fail("RES_ADDENDUM_INVALID", "prior_addendum_digest must be SHA-256 or null")

    prior = dict(prior_projection or {})
    expected_head = str(prior.get("addendum_head_digest") or "").strip().lower() or None
    if expected_head != prior_head:
        _fail("RES_ADDENDUM_CURRENTNESS_STALE", "addendum does not bind the current projected addendum head", status=409, expected_addendum_digest=expected_head)
    prior_claims = dict(prior.get("claims") or {})
    raw_claims = addendum.get("claims")
    if not isinstance(raw_claims, list) or not raw_claims:
        _fail("RES_ADDENDUM_INVALID", "claims must be a non-empty list")
    normalized_claims: list[JsonObject] = []
    seen: set[str] = set()
    for raw in raw_claims:
        cid = str(raw.get("claim_id") or "") if isinstance(raw, Mapping) else ""
        if cid in seen:
            _fail("RES_ADDENDUM_INVALID", f"duplicate claim_id in addendum: {cid}")
        seen.add(cid)
        normalized_claims.append(_normalize_claim(raw, prior_claim=prior_claims.get(cid)))

    body = {
        "schema": schema,
        "addendum_id": addendum_id,
        "material_event_class": event_class,
        "prior_addendum_digest": prior_head,
        "claims": normalized_claims,
        "authority_effect": "NONE",
    }
    body["addendum_digest"] = digest(body)
    return body


def project_addenda(addenda: Sequence[Mapping[str, Any]]) -> JsonObject:
    projection: JsonObject = {
        "schema": "pcmmad.res-projection.v1",
        "state": "EMPTY",
        "addendum_count": 0,
        "addendum_head_digest": None,
        "claims": {},
        "history": [],
        "authority_effect": "NONE",
        "claim_ceiling": "RES_PROJECTION != GOVERNING_DOCTRINE",
    }
    seen_addenda: set[str] = set()
    for raw in addenda:
        normalized = validate_addendum(raw, prior_projection=projection)
        adigest = normalized["addendum_digest"]
        if adigest in seen_addenda:
            _fail("RES_ADDENDUM_DUPLICATE", "duplicate addendum digest")
        seen_addenda.add(adigest)
        for claim in normalized["claims"]:
            projection["claims"][claim["claim_id"]] = claim
        projection["history"].append(
            {
                "addendum_id": normalized["addendum_id"],
                "addendum_digest": adigest,
                "prior_addendum_digest": normalized["prior_addendum_digest"],
                "material_event_class": normalized["material_event_class"],
                "claim_digests": [claim["claim_digest"] for claim in normalized["claims"]],
            }
        )
        projection["addendum_count"] += 1
        projection["addendum_head_digest"] = adigest
        projection["state"] = "PROJECTED"
    projection["projection_digest"] = digest({k: v for k, v in projection.items() if k != "projection_digest"})
    return projection


def validate_snapshot(markdown: str) -> JsonObject:
    text = str(markdown or "")
    if not text.strip():
        _fail("RES_SNAPSHOT_INVALID", "snapshot content is required")
    if "Form: `RES CONSOLIDATED SNAPSHOT`" not in text and "Form: RES CONSOLIDATED SNAPSHOT" not in text:
        _fail("RES_SNAPSHOT_INVALID", "snapshot must identify itself as RES CONSOLIDATED SNAPSHOT")
    if "RES_CONTENT != GOVERNING_DOCTRINE" not in text:
        _fail("RES_AUTHORITY_FIREWALL", "snapshot must preserve RES_CONTENT != GOVERNING_DOCTRINE", status=409)

    headings: list[tuple[int, str]] = []
    truth_counts = {state: 0 for state in TRUTH_STATES}
    unknown_prefixes: list[str] = []
    for line in text.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            headings.append((int(match.group(1)), match.group(2).strip()))
        prefix = _TRUTH_PREFIX_RE.match(line)
        if prefix:
            token = prefix.group(1)
            if token in TRUTH_STATE_SET:
                truth_counts[token] += 1
            else:
                unknown_prefixes.append(token)
    expected = list(enumerate(REQUIRED_SECTIONS, start=1))
    if headings != expected:
        _fail("RES_SNAPSHOT_SECTION_INVALID", "snapshot must contain all 22 canonical sections exactly once and in order", expected=expected, observed=headings)
    if unknown_prefixes:
        _fail("RES_TRUTH_STATE_INVALID", "snapshot contains non-canonical truth-state prefixes", invalid=sorted(set(unknown_prefixes)))
    if sum(truth_counts.values()) == 0:
        _fail("RES_SNAPSHOT_INVALID", "snapshot contains no explicit canonical truth-state claims")
    return {
        "schema": "pcmmad.res-snapshot-validation.v1",
        "state": "VALID",
        "required_section_count": len(REQUIRED_SECTIONS),
        "observed_section_count": len(headings),
        "truth_state_counts": truth_counts,
        "content_utf8_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "authority_effect": "NONE",
        "claim_ceiling": "RES_CONTENT != GOVERNING_DOCTRINE",
    }


def classify_material_change(event_class: str, *, material: bool = True) -> JsonObject:
    name = str(event_class or "").strip().upper()
    if name == "RESEARCH_HANDOFF_CHECKPOINT":
        disposition = "RES_UPDATE_REQUIRED"
    elif name in MATERIAL_EVENT_CLASSES and material:
        disposition = "RES_UPDATE_REQUIRED"
    elif name in MATERIAL_EVENT_CLASSES:
        disposition = "RES_UPDATE_RECOMMENDED"
    else:
        disposition = "NO_RES_UPDATE"
    return {
        "schema": "pcmmad.res-materiality.v1",
        "event_class": name,
        "material": bool(material),
        "disposition": disposition,
        "authority_effect": "NONE",
    }


def _event_material(event: Any) -> bool:
    if event.event_kind in MATERIAL_PROTOCOL_EVENTS:
        return True
    if event.event_kind is ProtocolEventKind.ARTIFACT_REGISTERED:
        artifact_class = str(event.payload.get("artifact_class") or "")
        return artifact_class.startswith("research.") or artifact_class.startswith("evidence.")
    return False


def handoff_readiness(project_id: str, *, research_intensive: bool = True) -> JsonObject:
    if not research_intensive:
        return {
            "schema": "pcmmad.res-handoff-readiness.v1",
            "project_id": project_id,
            "status": "NOT_APPLICABLE",
            "ready": True,
            "authority_effect": "NONE",
        }
    root = get_project_root(project_id).resolve()
    snapshot_path = (root / RES_CANONICAL_SNAPSHOT_PATH).resolve()
    reasons: list[str] = []
    snapshot_validation: JsonObject | None = None
    if root not in [snapshot_path, *snapshot_path.parents]:
        reasons.append("RES_PATH_ESCAPED_PROJECT")
    elif not snapshot_path.is_file():
        reasons.append("RES_SNAPSHOT_MISSING")
    else:
        try:
            snapshot_validation = validate_snapshot(snapshot_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ResPolicyError):
            reasons.append("RES_SNAPSHOT_INVALID")

    events = list(read_events(project_id))
    protocol_snapshot = build_snapshot(project_id, events)
    canonical_rel = RES_CANONICAL_SNAPSHOT_PATH.replace("\\", "/")
    material_events = [event for event in events if _event_material(event)]
    latest_material_event = material_events[-1] if material_events else None
    latest_material = latest_material_event.sequence if latest_material_event else None
    latest_res_continuity = max(
        (event.sequence for event in events if event.event_kind is ProtocolEventKind.CONTINUITY_RECORDED and str(event.payload.get("kind") or "") == RES_CONTINUITY_KIND),
        default=None,
    )

    snapshot_events = [
        event for event in events
        if event.event_kind is ProtocolEventKind.ARTIFACT_REGISTERED
        and event.payload.get("artifact_class") == RES_ARTIFACT_CLASS_SNAPSHOT
        and event.payload.get("path") == canonical_rel
    ]
    latest_snapshot_event = snapshot_events[-1] if snapshot_events else None
    current_artifact = dict(latest_snapshot_event.payload) if latest_snapshot_event else None
    if latest_snapshot_event is None:
        reasons.append("RES_SNAPSHOT_NOT_REGISTERED")
    elif snapshot_path.is_file():
        registered_sha = str(latest_snapshot_event.payload.get("sha256") or "")
        actual_sha = sha256_file(snapshot_path)
        if not registered_sha or registered_sha != actual_sha:
            reasons.append("RES_SNAPSHOT_REGISTERED_HASH_STALE")

    addendum_by_id: dict[str, Any] = {}
    for event in events:
        if event.event_kind is ProtocolEventKind.ARTIFACT_REGISTERED and event.payload.get("artifact_class") == RES_ARTIFACT_CLASS_ADDENDUM:
            addendum_by_id[str(event.payload.get("artifact_id") or event.event_id)] = event
    addendum_events = sorted(addendum_by_id.values(), key=lambda event: event.sequence)
    addendum_objects: list[Mapping[str, Any]] = []
    for event in addendum_events:
        rel = str(event.payload.get("path") or "")
        target = (root / rel).resolve()
        if root not in [target, *target.parents] or not target.is_file():
            reasons.append("RES_ADDENDUM_ARTIFACT_MISSING")
            continue
        if str(event.payload.get("sha256") or "") != sha256_file(target):
            reasons.append("RES_ADDENDUM_REGISTERED_HASH_STALE")
            continue
        try:
            obj = json.loads(target.read_text(encoding="utf-8"))
            if not isinstance(obj, Mapping):
                raise ValueError("addendum must be object")
            addendum_objects.append(obj)
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
            reasons.append("RES_ADDENDUM_INVALID")
    addendum_projection: JsonObject | None = None
    if addendum_objects:
        try:
            addendum_projection = project_addenda(addendum_objects)
        except ResPolicyError:
            reasons.append("RES_ADDENDUM_CHAIN_INVALID")

    latest_res_artifact = max(
        [event.sequence for event in snapshot_events + addendum_events],
        default=None,
    )
    latest_snapshot_sequence = latest_snapshot_event.sequence if latest_snapshot_event else None
    latest_addendum_sequence = addendum_events[-1].sequence if addendum_events else None
    if (
        latest_material_event is not None
        and latest_addendum_sequence is not None
        and (latest_snapshot_sequence is None or latest_snapshot_sequence < latest_material_event.sequence)
        and latest_addendum_sequence >= latest_material_event.sequence
        and addendum_objects
    ):
        expected_refs = {
            f"protocol:event:{latest_material_event.event_hash}",
            f"protocol:event_id:{latest_material_event.event_id}",
        }
        observed_refs: set[str] = set()
        for claim in addendum_objects[-1].get("claims", []):
            if isinstance(claim, Mapping):
                observed_refs.update(str(x) for x in claim.get("provenance_refs", []) if x)
                observed_refs.update(str(x) for x in claim.get("evidence_refs", []) if x)
        if not (expected_refs & observed_refs):
            reasons.append("RES_ADDENDUM_MATERIAL_EVENT_UNBOUND")
    if latest_res_continuity is None:
        reasons.append("RES_CONTINUITY_EVENT_MISSING")
    if latest_material is not None and (latest_res_artifact is None or latest_res_artifact < latest_material):
        reasons.append("RES_STALE_AFTER_MATERIAL_PROTOCOL_CHANGE")
    if latest_res_artifact is not None and (latest_res_continuity is None or latest_res_continuity < latest_res_artifact):
        reasons.append("RES_ARTIFACT_NOT_ACKNOWLEDGED_BY_CONTINUITY_LEDGER")

    # The snapshot is a project continuity surface; protocol registration is a
    # currentness/readback witness, never doctrine or mutation authority.
    ready = not reasons
    return {
        "schema": "pcmmad.res-handoff-readiness.v1",
        "project_id": project_id,
        "status": "HANDOFF_READY" if ready else "HANDOFF_EPISTEMIC_CONTINUITY_INCOMPLETE",
        "ready": ready,
        "snapshot": snapshot_validation,
        "registered_snapshot": current_artifact,
        "addendum_projection": addendum_projection,
        "latest_res_continuity_sequence": latest_res_continuity,
        "latest_res_artifact_sequence": latest_res_artifact,
        "latest_material_protocol_sequence": latest_material,
        "handoff_update_trigger": "RES_UPDATE_REQUIRED",
        "reasons": sorted(set(reasons)),
        "authority_effect": "NONE",
        "claim_ceiling": "RES_HANDOFF_READY != PROJECT_MUTATION_AUTHORITY",
    }
