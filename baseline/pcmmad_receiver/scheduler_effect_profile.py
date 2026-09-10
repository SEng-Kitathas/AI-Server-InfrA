"""Closed scheduler-effect profile for schema vNext planning.

Descriptive ToolSpec.effect_traits are intentionally NOT scheduler inputs.  A
native capability may have many descriptive traits; automatic scheduling uses
only this closed profile, bound to the capability contract digest.  Unknown or
stale capabilities fail closed for compose/execute while orient/invoke remain
available.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .lab_tools import LabToolError
from .server_hardening import safe_json_dumps, to_jsonable

JsonObject = dict[str, Any]

PROFILE_SCHEMA = "pcmmad.scheduler-effect-profile.v1"
PROFILE_FILENAME = "scheduler_effect_profile_v1.json"
PROFILE_PATH = Path(__file__).with_name(PROFILE_FILENAME)

EFFECT_KINDS = frozenset(
    {
        "UNVERIFIED",
        "READ_LOCAL",
        "READ_EXTERNAL",
        "READ_CACHE",
        "MUTATION",
        "EXECUTION",
        "RUNTIME_MUTATION",
        "RECONCILE",
        "AUTHORITY_MUTATION",
        "EPHEMERAL_MUTATION",
        "EXTERNAL_INTERACTION",
    }
)
SCHEDULE_CLASSES = frozenset({"SERIAL", "PARALLEL_READ_VERIFIED"})
RESUME_REPLAY_CLASSES = frozenset({"RECOMPOSE_REQUIRED", "REEXECUTE_READ_VERIFIED"})
RETRY_CLASSES = frozenset({"SAFE_REPEAT", "IDEMPOTENT", "CONSEQUENCE_READBACK", "UNSAFE_RETRY"})
FRESHNESS_CLASSES = frozenset(
    {
        "CAPABILITY_CONTRACT",
        "PROJECT_STATE",
        "USER_CONTINUITY",
        "EXTERNAL_STATE",
        "RUNTIME_STATE",
        "RESULT_STATE",
    }
)

SIDE_EFFECT_TO_KIND = {
    "read": "READ_LOCAL",
    "read_probe": "READ_LOCAL",
    "external_read": "READ_EXTERNAL",
    "read_cache": "READ_CACHE",
    "mutation": "MUTATION",
    "execution": "EXECUTION",
    "runtime_mutation": "RUNTIME_MUTATION",
    "reconcile": "RECONCILE",
    "authority_mutation": "AUTHORITY_MUTATION",
    "ephemeral_mutation": "EPHEMERAL_MUTATION",
    "external_interaction": "EXTERNAL_INTERACTION",
}

STATIC_COST_UNITS = {
    "READ_LOCAL": 1,
    "READ_EXTERNAL": 4,
    "READ_CACHE": 2,
    "MUTATION": 4,
    "EXECUTION": 8,
    "RUNTIME_MUTATION": 10,
    "RECONCILE": 6,
    "AUTHORITY_MUTATION": 10,
    "EPHEMERAL_MUTATION": 3,
    "EXTERNAL_INTERACTION": 6,
    "UNVERIFIED": 10,
}

# Parallel scheduling is opt-in by exact capability contract.  An entry here
# must be backed by a dedicated concurrency/effect-truth test.  Empty is a
# valid production state: server-side dataflow still saves round trips while
# all plan nodes serialize conservatively.
EFFECT_TRUTH_VERIFICATION_WITNESSES: dict[str, dict[str, str]] = {}
PARALLEL_VERIFICATION_WITNESSES: dict[str, dict[str, str]] = {}
RESUME_REPLAY_VERIFICATION_WITNESSES: dict[str, dict[str, str]] = {}


def _hash_json(value: Any) -> str:
    canonical = json.dumps(
        to_jsonable(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def catalog_digest(cards: Mapping[str, Mapping[str, Any]]) -> str:
    return _hash_json(
        [
            {
                "name": name,
                "contract_digest": str(cards[name].get("contract_digest") or ""),
            }
            for name in sorted(cards)
        ]
    )


def retry_class(card: Mapping[str, Any]) -> str:
    value = str(card.get("idempotency_semantics") or "").strip().lower()
    if value == "safe_repeat":
        return "SAFE_REPEAT"
    if value in {"idempotent", "idempotent_with_key"}:
        return "IDEMPOTENT"
    if value in {"consequence_check_before_retry", "readback_before_retry"}:
        return "CONSEQUENCE_READBACK"
    return "UNSAFE_RETRY"


def freshness_classes(card: Mapping[str, Any], effect_kind: str, *, effect_truth_verified: bool) -> list[str]:
    if not effect_truth_verified:
        # Unknown effect truth means currentness obligations may live on any plane.
        # Conservative metadata cannot be used to omit a necessary reread.
        return sorted(FRESHNESS_CLASSES)
    classes = {"CAPABILITY_CONTRACT"}
    category = str(card.get("category") or "").lower()
    if category in {"project", "git", "protocol", "continuity", "doctrine", "governance", "sop"}:
        classes.add("PROJECT_STATE")
    if category == "memory" or str(card.get("name") or "").startswith("ucm."):
        classes.add("USER_CONTINUITY")
    if effect_kind in {"READ_EXTERNAL", "EXTERNAL_INTERACTION"}:
        classes.add("EXTERNAL_STATE")
    if category in {"execution", "lab", "control"} or effect_kind == "RUNTIME_MUTATION":
        classes.add("RUNTIME_STATE")
    if category in {"result", "transfer"}:
        classes.add("RESULT_STATE")
    return sorted(classes)


def derive_entry(card: Mapping[str, Any]) -> JsonObject:
    name = str(card.get("name") or "").strip()
    side_effect = str(card.get("side_effect_class") or "").strip().lower()
    declared_effect_kind = SIDE_EFFECT_TO_KIND.get(side_effect)
    if not name or declared_effect_kind is None:
        raise LabToolError(
            "EFFECT_PROFILE_UNCLASSIFIED",
            f"capability has unclassified declared effect: {name or '<unnamed>'} / {side_effect or '<missing>'}",
            409,
        )
    contract_digest = str(card.get("contract_digest") or "").strip().lower()
    truth_witness = EFFECT_TRUTH_VERIFICATION_WITNESSES.get(name)
    effect_truth_verified = False
    effect_kind = "UNVERIFIED"
    if truth_witness and truth_witness.get("contract_digest") == contract_digest:
        witnessed_kind = str(truth_witness.get("effect_kind") or "").strip().upper()
        if witnessed_kind not in EFFECT_KINDS or witnessed_kind == "UNVERIFIED":
            raise LabToolError("EFFECT_PROFILE_INVALID", f"effect-truth witness has invalid effect kind for {name}", 409)
        if witnessed_kind != declared_effect_kind:
            raise LabToolError(
                "EFFECT_PROFILE_DECLARATION_MISMATCH",
                f"verified effect truth disagrees with declared side_effect_class for {name}",
                409,
                declared_effect_kind=declared_effect_kind,
                witnessed_effect_kind=witnessed_kind,
            )
        effect_truth_verified = True
        effect_kind = witnessed_kind

    witness = PARALLEL_VERIFICATION_WITNESSES.get(name)
    schedule_class = "SERIAL"
    if witness and witness.get("contract_digest") == contract_digest:
        if not effect_truth_verified or effect_kind not in {"READ_LOCAL", "READ_EXTERNAL"}:
            raise LabToolError(
                "EFFECT_PROFILE_INVALID",
                f"parallel witness exists without verified read effect truth for {name}",
                409,
            )
        schedule_class = "PARALLEL_READ_VERIFIED"

    replay_witness = RESUME_REPLAY_VERIFICATION_WITNESSES.get(name)
    resume_replay_class = "RECOMPOSE_REQUIRED"
    if replay_witness and replay_witness.get("contract_digest") == contract_digest:
        if (
            not effect_truth_verified
            or effect_kind not in {"READ_LOCAL", "READ_EXTERNAL"}
            or retry_class(card) != "SAFE_REPEAT"
        ):
            raise LabToolError(
                "EFFECT_PROFILE_INVALID",
                f"resume-replay witness exists without verified safe-repeat read effect truth for {name}",
                409,
            )
        resume_replay_class = "REEXECUTE_READ_VERIFIED"

    return {
        "name": name,
        "contract_digest": contract_digest,
        "declared_effect_kind": declared_effect_kind,
        "effect_kind": effect_kind,
        "effect_truth_verified": effect_truth_verified,
        "effect_truth_witness": dict(truth_witness) if effect_truth_verified else None,
        "schedule_class": schedule_class,
        "resume_replay_class": resume_replay_class,
        "static_cost_units": int(STATIC_COST_UNITS[effect_kind]),
        "retry_class": retry_class(card),
        "freshness_classes": freshness_classes(card, effect_kind, effect_truth_verified=effect_truth_verified),
        "mutating": bool(card.get("mutating")),
        "effective_approval_required": bool(card.get("effective_approval_required")),
        "parallel_witness": dict(witness) if schedule_class == "PARALLEL_READ_VERIFIED" else None,
        "resume_replay_witness": dict(replay_witness) if resume_replay_class == "REEXECUTE_READ_VERIFIED" else None,
    }


def build_profile(cards: Mapping[str, Mapping[str, Any]]) -> JsonObject:
    entries = [derive_entry(cards[name]) for name in sorted(cards)]
    body: JsonObject = {
        "schema": PROFILE_SCHEMA,
        "catalog_digest": catalog_digest(cards),
        "capability_count": len(entries),
        "effect_kinds": sorted(EFFECT_KINDS),
        "schedule_classes": sorted(SCHEDULE_CLASSES),
        "resume_replay_classes": sorted(RESUME_REPLAY_CLASSES),
        "retry_classes": sorted(RETRY_CLASSES),
        "freshness_classes": sorted(FRESHNESS_CLASSES),
        "cost_semantics": "static admission units; exact/computable but not a wall-time SLA",
        "descriptive_effect_traits_are_scheduler_authority": False,
        "declared_effect_class_is_effect_truth": False,
        "unverified_effect_cost_units": STATIC_COST_UNITS["UNVERIFIED"],
        "parallel_default": "SERIAL",
        "entries": entries,
    }
    body["profile_digest"] = _hash_json(body)
    return body


def load_profile(path: Path = PROFILE_PATH) -> JsonObject:
    if not path.is_file():
        raise LabToolError("EFFECT_PROFILE_MISSING", f"scheduler effect profile missing: {path}", 409)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LabToolError("EFFECT_PROFILE_INVALID", f"scheduler effect profile is unreadable: {exc}", 409) from exc
    if not isinstance(value, dict):
        raise LabToolError("EFFECT_PROFILE_INVALID", "scheduler effect profile must be an object", 409)
    return value


def verify_profile(profile: Mapping[str, Any], cards: Mapping[str, Mapping[str, Any]]) -> JsonObject:
    supplied = dict(profile)
    digest = str(supplied.get("profile_digest") or "").strip().lower()
    core = dict(supplied)
    core.pop("profile_digest", None)
    if _hash_json(core) != digest:
        raise LabToolError("EFFECT_PROFILE_INVALID", "scheduler effect profile digest mismatch", 409)
    if supplied.get("schema") != PROFILE_SCHEMA:
        raise LabToolError("EFFECT_PROFILE_INVALID", "scheduler effect profile schema mismatch", 409)
    if supplied.get("descriptive_effect_traits_are_scheduler_authority") is not False:
        raise LabToolError("EFFECT_PROFILE_INVALID", "descriptive effect traits may not become scheduler authority", 409)
    if supplied.get("declared_effect_class_is_effect_truth") is not False:
        raise LabToolError("EFFECT_PROFILE_INVALID", "declared side-effect class may not become verified effect truth by assertion", 409)
    if supplied.get("unverified_effect_cost_units") != STATIC_COST_UNITS["UNVERIFIED"]:
        raise LabToolError("EFFECT_PROFILE_INVALID", "unverified effect cost floor drift", 409)
    if supplied.get("effect_kinds") != sorted(EFFECT_KINDS):
        raise LabToolError("EFFECT_PROFILE_INVALID", "closed effect-kind vocabulary drift", 409)
    if supplied.get("schedule_classes") != sorted(SCHEDULE_CLASSES):
        raise LabToolError("EFFECT_PROFILE_INVALID", "closed schedule-class vocabulary drift", 409)
    if supplied.get("resume_replay_classes") != sorted(RESUME_REPLAY_CLASSES):
        raise LabToolError("EFFECT_PROFILE_INVALID", "closed resume-replay vocabulary drift", 409)
    if supplied.get("retry_classes") != sorted(RETRY_CLASSES):
        raise LabToolError("EFFECT_PROFILE_INVALID", "closed retry-class vocabulary drift", 409)
    if supplied.get("freshness_classes") != sorted(FRESHNESS_CLASSES):
        raise LabToolError("EFFECT_PROFILE_INVALID", "closed freshness vocabulary drift", 409)
    if supplied.get("catalog_digest") != catalog_digest(cards):
        raise LabToolError("EFFECT_PROFILE_STALE", "scheduler effect profile catalog digest is stale", 409)
    rows = supplied.get("entries")
    if not isinstance(rows, list) or int(supplied.get("capability_count") or -1) != len(cards):
        raise LabToolError("EFFECT_PROFILE_INVALID", "scheduler effect profile capability count mismatch", 409)
    by_name = {str(row.get("name")): row for row in rows if isinstance(row, dict)}
    if set(by_name) != set(cards) or len(by_name) != len(rows):
        raise LabToolError("EFFECT_PROFILE_INVALID", "scheduler effect profile must exactly cover the live capability catalog", 409)
    for name in sorted(cards):
        expected = derive_entry(cards[name])
        observed = by_name[name]
        if observed != expected:
            raise LabToolError(
                "EFFECT_PROFILE_STALE",
                f"effect profile entry differs from current closed derivation for {name}",
                409,
                capability=name,
            )
    return {
        "ok": True,
        "current": True,
        "profile_digest": digest,
        "catalog_digest": supplied["catalog_digest"],
        "capability_count": len(cards),
        "effect_truth_verified_count": sum(1 for row in rows if row.get("effect_truth_verified") is True),
        "parallel_verified_count": sum(1 for row in rows if row.get("schedule_class") == "PARALLEL_READ_VERIFIED"),
        "resume_replay_verified_count": sum(1 for row in rows if row.get("resume_replay_class") == "REEXECUTE_READ_VERIFIED"),
        "descriptive_trait_scheduler_authority": False,
    }


def current_profile(cards: Mapping[str, Mapping[str, Any]], path: Path = PROFILE_PATH) -> tuple[JsonObject, JsonObject]:
    profile = load_profile(path)
    verification = verify_profile(profile, cards)
    return profile, verification


def entry_map(profile: Mapping[str, Any]) -> dict[str, JsonObject]:
    return {str(row["name"]): dict(row) for row in profile.get("entries") or [] if isinstance(row, dict)}
