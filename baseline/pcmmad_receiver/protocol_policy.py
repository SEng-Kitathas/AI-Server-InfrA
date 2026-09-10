"""Optional PCMMAD mode-gate enforcement for server-native tool dispatch.

Legacy projects remain fully usable. Once a project has a protocol ledger, the
runtime can make the discourse/build boundary advisory or strict without
expanding the Custom GPT action schema.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .protocol_models import MutationDomain
from .protocol_store import evaluate_mode_gate
from .shared_core import get_project_root, validate_project_id


@dataclass(frozen=True)
class ProtocolPolicyDecision:
    allowed: bool
    policy_mode: str
    mutation_domain: MutationDomain
    reason: str
    warning: str | None = None
    current_mode: str | None = None


def protocol_policy_mode() -> str:
    value = os.environ.get("PCMMAD_PROTOCOL_POLICY_MODE", "advisory").strip().lower()
    return value if value in {"off", "advisory", "strict"} else "advisory"


def protocol_ledger_path(project_id: str) -> Path:
    return get_project_root(validate_project_id(project_id)) / "system" / "protocol" / "events.jsonl"


def protocol_is_initialized(project_id: str) -> bool:
    return protocol_ledger_path(project_id).is_file()


def mutation_domain_for_tool(spec: Any) -> MutationDomain:
    if not bool(getattr(spec, "mutating", False)):
        return MutationDomain.READ
    category = str(getattr(spec, "category", "general"))
    name = str(getattr(spec, "name", ""))
    if category == "protocol" or name.startswith("protocol."):
        return MutationDomain.GOVERNANCE
    governance_prefixes = (
        "session.",
        "reflexion.",
        "andon.",
        "sop.",
        "doctrine.",
        "project.journal.",
        "project.checkpoint.",
        "project.state.",
    )
    if name.startswith(governance_prefixes):
        return MutationDomain.GOVERNANCE
    return MutationDomain.SPECIMEN


def evaluate_protocol_tool_call(spec: Any, payload: dict[str, Any]) -> ProtocolPolicyDecision:
    mode = protocol_policy_mode()
    domain = mutation_domain_for_tool(spec)
    if mode == "off" or domain in {MutationDomain.READ, MutationDomain.GOVERNANCE}:
        return ProtocolPolicyDecision(True, mode, domain, "protocol mode gate not required")

    project_id = str(payload.get("project_id", "")).strip()
    if not project_id or not protocol_is_initialized(project_id):
        return ProtocolPolicyDecision(
            True,
            mode,
            domain,
            "project has no initialized protocol ledger; legacy behavior preserved",
        )

    gate = evaluate_mode_gate(project_id, domain, actor="pcmmad.mode-gate")
    if gate["allowed"]:
        return ProtocolPolicyDecision(
            True,
            mode,
            domain,
            str(gate["reason"]),
            current_mode=str(gate["current_mode"]),
        )
    warning = (
        f"PCMMAD mode {gate['current_mode']} does not permit {domain.value} mutation; "
        f"allowed modes: {', '.join(gate['allowed_modes'])}"
    )
    if mode == "strict":
        return ProtocolPolicyDecision(
            False,
            mode,
            domain,
            str(gate["reason"]),
            warning=warning,
            current_mode=str(gate["current_mode"]),
        )
    return ProtocolPolicyDecision(
        True,
        mode,
        domain,
        "advisory mode preserves execution but surfaces the mode violation",
        warning=warning,
        current_mode=str(gate["current_mode"]),
    )
