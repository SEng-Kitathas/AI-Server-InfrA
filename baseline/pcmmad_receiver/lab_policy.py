"""Lab policy helpers for risk, authority, and runtime enforcement.

Authority is separate from capability arguments.  New clients should use a
bound approval challenge handle.  Legacy inline approval remains transitional
compatibility only and is deliberately surfaced as such.
"""

from __future__ import annotations

import os
from collections.abc import MutableMapping
from dataclasses import dataclass, field
from typing import Any

from .approval_authority import (
    ApprovalAuthorityError,
    create_challenge,
    validate_and_consume,
)
from .standing_authority import resolve as resolve_standing_authority

JsonObject = MutableMapping[str, Any]


@dataclass
class PolicyDecision:
    allowed: bool
    mode: str
    approved: bool
    reason: str
    warning: str | None = None
    approval_mode: str = "none"
    approval_handle: str | None = None
    error_code: str = "APPROVAL_REQUIRED"
    details: dict[str, Any] = field(default_factory=dict)


def policy_mode() -> str:
    mode = os.environ.get("PCMMAD_LAB_POLICY_MODE", "strict").strip().lower()
    return mode if mode in {"strict", "advisory", "open"} else "strict"


def legacy_inline_approval_enabled() -> bool:
    # Legacy inline approval is unbound to capability contract and arguments.
    # It is retained only as an explicit migration escape hatch; secure default is off.
    raw = os.environ.get("PCMMAD_ALLOW_LEGACY_INLINE_APPROVAL", "0").strip().lower()
    return raw in {"1", "true", "yes", "on", "enabled"}


def _approval_present(approval: Any) -> bool:
    if not isinstance(approval, dict):
        return False
    return bool(
        approval.get("permit") is True
        or str(approval.get("decision", "")).lower() in {"allow", "approve", "approved"}
    )


def _spec_attr(spec: Any, name: str, default: Any) -> Any:
    if hasattr(spec, name):
        return getattr(spec, name)
    if isinstance(spec, dict):
        return spec.get(name, default)
    return default


def _approval_required(spec: Any) -> bool:
    danger_tier = str(_spec_attr(spec, "danger_tier", "medium")).lower()
    return bool(
        _spec_attr(spec, "approval_required", False)
        or danger_tier in {"high", "critical"}
        or _spec_attr(spec, "mutating", False)
    )


def _authority_dict(authority: JsonObject | None) -> dict[str, Any]:
    return dict(authority or {}) if isinstance(authority, dict) else {}


def _bound_approval_decision(
    spec: Any,
    payload: JsonObject,
    authority: dict[str, Any],
    mode: str,
) -> PolicyDecision | None:
    handle = str(authority.get("approval_handle") or "").strip()
    if not handle:
        return None
    try:
        consumed = validate_and_consume(
            handle,
            spec,
            payload,
            permit=authority.get("permit") is True,
            operator_id=str(authority.get("operator_id") or ""),
            provenance=str(authority.get("provenance") or ""),
        )
    except ApprovalAuthorityError as exc:
        return PolicyDecision(
            False,
            mode,
            False,
            exc.message,
            approval_mode="bound_challenge",
            approval_handle=handle,
            error_code=exc.error_code,
            details=exc.extra,
        )
    return PolicyDecision(
        True,
        mode,
        True,
        "target/argument-bound approval challenge validated and consumed",
        approval_mode="bound_challenge",
        approval_handle=str(consumed.get("handle") or handle),
        details={"approval": consumed},
    )


def evaluate_tool_call(
    spec: Any,
    payload: JsonObject,
    authority: JsonObject | None = None,
) -> PolicyDecision:
    mode = policy_mode()
    authority_data = _authority_dict(authority)
    requires_approval = _approval_required(spec)

    bound = _bound_approval_decision(spec, payload, authority_data, mode)
    if bound is not None:
        return bound

    standing = resolve_standing_authority(spec, payload)
    if standing is not None:
        action = str(standing.get("action") or "ask")
        details = {"standing_authority": standing}
        if action == "deny":
            return PolicyDecision(False, "operator", False, "operator standing-authority profile denies this call", approval_mode="standing_authority", error_code="OPERATOR_POLICY_DENIED", details=details)
        if action == "allow":
            return PolicyDecision(True, "operator", True, "operator standing-authority profile permits this call", approval_mode="standing_authority", details=details)
        challenge = create_challenge(spec, payload)
        return PolicyDecision(False, "operator", False, "operator standing-authority profile requires HITL for this call", approval_mode="challenge_required", approval_handle=str(challenge.get("handle") or ""), error_code="APPROVAL_REQUIRED", details={**details, "approval_challenge": challenge})

    if mode == "open":
        return PolicyDecision(True, mode, False, "open mode permits all tool calls")
    if not requires_approval:
        return PolicyDecision(True, mode, False, "tool does not require approval")

    legacy = authority_data.get("legacy_approval")
    if _approval_present(legacy):
        if not legacy_inline_approval_enabled():
            return PolicyDecision(
                False,
                mode,
                False,
                "legacy inline approval is disabled; use a bound approval challenge",
                approval_mode="legacy_inline",
                error_code="LEGACY_APPROVAL_DISABLED",
            )
        return PolicyDecision(
            True,
            mode,
            True,
            "legacy inline approval compatibility path",
            warning=(
                "legacy inline approval is unbound to capability contract/arguments; "
                "migrate client to bound approval challenges"
            ),
            approval_mode="legacy_inline",
        )

    if mode == "advisory":
        return PolicyDecision(
            True,
            mode,
            False,
            "advisory mode permits call without approval",
            warning="approval missing for mutating/high-risk call",
        )

    challenge = create_challenge(spec, payload)
    return PolicyDecision(
        False,
        mode,
        False,
        "explicit approval is required for this exact capability contract and argument set",
        approval_mode="challenge_required",
        approval_handle=str(challenge.get("handle") or ""),
        error_code="APPROVAL_REQUIRED",
        details={"approval_challenge": challenge},
    )
