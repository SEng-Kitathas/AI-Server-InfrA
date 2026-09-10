"""ICF-CS v1.2 fresh-instance continuity ingress orchestration.

This module composes existing project context, RES, and UCM mechanisms. It does
not create another persistence or authority plane. Session applicability is
explicit because Runtime has no safe basis to guess whether a request is a user
session or which UCM profile belongs to it.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from context_engine import RehydrateRequest, rehydrate_context
from res_runtime import handoff_readiness
from shared_core import get_project_root
from ucm_v1_runtime import UcmError, head as ucm_head, read_core

ICF_CS_VERSION = "1.2"
ICF_CS_STANDARD_REL = "state/doctrine_snapshot/INTENT_CONSTRAINT_FRONTIER_CONTINUITY_STANDARD.md"
ICF_CS_STANDARD_SHA256 = "f966029496fd6e31a76a36a6e967db37ca2147acfa890a880426ae6a7fa79d92"
ICF_CS_ACTIVATION_RECEIPT_SHA256 = "893409f28ea181c60ca9e3681eb9a1a4d08fa279befac4d679d2cfdb958d7279"
RES_FEATURE_COMMIT = "8714dd87d2092e0f4c66f261fcf5cee8b75a0798"
UCM_FEATURE_COMMIT = "f01418c546e449acb3f98f4b64f5b4a7ad3f0960"

SESSION_MODES = {
    "INTERACTIVE_RESEARCH_USER_SESSION": {"res": True, "ucm": True},
    "INTERACTIVE_NONRESEARCH_USER_SESSION": {"res": False, "ucm": True},
    "NONUSER_RESEARCH_AUTOMATION": {"res": True, "ucm": False},
    "NONUSER_NONRESEARCH_AUTOMATION": {"res": False, "ucm": False},
}


class IcfIngressError(RuntimeError):
    def __init__(self, error_code: str, message: str, status: int = 409, **extra: Any) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status = int(status)
        self.extra = extra


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _standard_current(project_root: Path) -> dict[str, Any]:
    path = (project_root / ICF_CS_STANDARD_REL).resolve()
    root = project_root.resolve()
    if root not in [path, *path.parents] or not path.is_file():
        raise IcfIngressError(
            "ICF_CS_CURRENTNESS_FAILURE",
            "current ICF-CS standard is missing from the governed project",
            409,
            expected_path=ICF_CS_STANDARD_REL,
            expected_sha256=ICF_CS_STANDARD_SHA256,
        )
    observed = _sha256(path)
    if observed != ICF_CS_STANDARD_SHA256:
        raise IcfIngressError(
            "ICF_CS_CURRENTNESS_FAILURE",
            "current ICF-CS standard does not match active v1.2 authority",
            409,
            expected_sha256=ICF_CS_STANDARD_SHA256,
            observed_sha256=observed,
            path=str(path),
        )
    return {
        "version": ICF_CS_VERSION,
        "path": str(path),
        "sha256": observed,
        "activation_receipt_sha256": ICF_CS_ACTIVATION_RECEIPT_SHA256,
        "status": "CURRENT",
    }


def _mode(value: str) -> str:
    mode = str(value or "").strip().upper()
    if mode not in SESSION_MODES:
        raise IcfIngressError(
            "ICF_CS_SESSION_MODE_REQUIRED",
            "fresh-instance ingress requires one explicit ICF-CS v1.2 session mode",
            400,
            allowed=sorted(SESSION_MODES),
        )
    return mode


def _applicability(mode: str, *, res_required_by_project: bool) -> dict[str, Any]:
    defaults = SESSION_MODES[mode]
    res_required = bool(defaults["res"] or res_required_by_project)
    ucm_required = bool(defaults["ucm"])
    return {
        "RES": {
            "state": "REQUIRED" if res_required else "NOT_APPLICABLE_WITH_BASIS",
            "basis": (
                "research session or governing project requires RES"
                if res_required
                else "non-research session and no governing project RES override declared"
            ),
        },
        "UCM": {
            "state": "REQUIRED" if ucm_required else "NOT_APPLICABLE_WITH_BASIS",
            "basis": (
                "interactive user session requires user-owned continuity"
                if ucm_required
                else "non-user automation has no user continuity profile to hydrate"
            ),
        },
    }


def rehydrate_icf_v12(
    *,
    project_id: str,
    topic: str,
    session_mode: str,
    ucm_profile_id: str | None = None,
    res_required_by_project: bool = False,
    path: str = ".",
    project_budget_bytes: int | None = None,
    debug: bool = False,
) -> dict[str, Any]:
    pid = str(project_id or "").strip()
    if not pid:
        raise IcfIngressError("BAD_REQUEST", "project_id is required", 400)
    if not str(topic or "").strip():
        raise IcfIngressError("BAD_REQUEST", "topic is required", 400)
    mode = _mode(session_mode)
    root = get_project_root(pid).resolve()
    standard = _standard_current(root)
    applicability = _applicability(mode, res_required_by_project=res_required_by_project)

    if applicability["RES"]["state"] == "REQUIRED":
        res = handoff_readiness(pid, research_intensive=True)
        if not res.get("ready"):
            raise IcfIngressError(
                "HANDOFF_EPISTEMIC_CONTINUITY_INCOMPLETE",
                "required RES is missing, invalid, stale, or not consequence-bound",
                409,
                res_reasons=res.get("reasons") or [],
                res_status=res.get("status"),
            )
    else:
        res = {
            "status": "NOT_APPLICABLE_WITH_BASIS",
            "ready": True,
            "basis": applicability["RES"]["basis"],
            "authority_effect": "NONE",
        }

    if applicability["UCM"]["state"] == "REQUIRED":
        profile = str(ucm_profile_id or "").strip()
        if not profile:
            raise IcfIngressError(
                "USER_CONTINUITY_INCOMPLETE",
                "interactive user-session ingress requires an explicit UCM profile_id",
                409,
            )
        try:
            ucm = read_core(profile)
        except UcmError as exc:
            raise IcfIngressError(exc.error_code, exc.message, exc.status, **exc.extra) from exc
    else:
        if ucm_profile_id:
            raise IcfIngressError(
                "ICF_CS_APPLICABILITY_CONFLICT",
                "non-user session declared UCM not applicable but also supplied a UCM profile",
                409,
            )
        ucm = {
            "status": "NOT_APPLICABLE_WITH_BASIS",
            "ready": True,
            "basis": applicability["UCM"]["basis"],
            "authority_effect": "NONE",
        }

    project_context = rehydrate_context(
        RehydrateRequest(
            topic=str(topic),
            base_root=str(root),
            path=str(path or "."),
            budget_bytes=project_budget_bytes,
            debug=bool(debug),
        )
    )

    # Final consequence readback closes the ingress TOCTOU window across the
    # composed authority/RES/UCM/context reads. The returned packet is bound to
    # the exact end-of-ingress state, not merely the state observed at start.
    standard_after = _standard_current(root)
    if standard_after["sha256"] != standard["sha256"]:
        raise IcfIngressError(
            "ICF_CS_CURRENTNESS_FAILURE",
            "ICF-CS authority bytes changed during fresh-instance rehydration",
            409,
            before_sha256=standard["sha256"],
            after_sha256=standard_after["sha256"],
        )
    if applicability["RES"]["state"] == "REQUIRED":
        res_after = handoff_readiness(pid, research_intensive=True)
        if not res_after.get("ready"):
            raise IcfIngressError(
                "HANDOFF_EPISTEMIC_CONTINUITY_INCOMPLETE",
                "required RES became stale or invalid during fresh-instance rehydration",
                409,
                res_reasons=res_after.get("reasons") or [],
                res_status=res_after.get("status"),
            )
        res = res_after
    if applicability["UCM"]["state"] == "REQUIRED":
        profile = str(ucm_profile_id or "").strip()
        current_head = ucm_head(profile)
        bound_head = ucm.get("USER_STORE_HEAD") or {}
        if (
            int(current_head.get("ledger_head_seq") or 0) != int(bound_head.get("ledger_head_seq") or 0)
            or current_head.get("ledger_head_hash") != bound_head.get("ledger_head_hash")
            or not current_head.get("snapshot_current")
        ):
            raise IcfIngressError(
                "UCM_CURRENTNESS_FAILURE",
                "UCM authoritative head changed during fresh-instance rehydration",
                409,
                packet_head_seq=bound_head.get("ledger_head_seq"),
                packet_head_hash=bound_head.get("ledger_head_hash"),
                current_head_seq=current_head.get("ledger_head_seq"),
                current_head_hash=current_head.get("ledger_head_hash"),
                snapshot_current=current_head.get("snapshot_current"),
            )
    return {
        "schema": "pcmmad.icf-cs.v1.2-ingress.v1",
        "status": "FRESH_INSTANCE_CONTINUITY_READY",
        "project_id": pid,
        "session_mode": mode,
        "icf_cs": standard,
        "applicability": applicability,
        "res": res,
        "ucm": ucm,
        "project_context": project_context,
        "runtime_bindings": {
            "res_feature_commit": RES_FEATURE_COMMIT,
            "ucm_feature_commit": UCM_FEATURE_COMMIT,
        },
        "authority_effect": "NONE",
        "required_next_gate": "OWNING_PLANE_LIVE_VERIFICATION_THEN_LIVE_READBACK_BEFORE_MUTATION",
        "laws": [
            "LIVE_SHADOW != DTS != RES != UCM",
            "MISSING != NOT_APPLICABLE",
            "RES_CONTENT != GOVERNING_DOCTRINE",
            "UCM != PROJECT_AUTHORITY",
            "UCM != RUNTIME_TRUTH",
            "UCM != DOCTRINE_AUTHORITY",
            "RETRIEVAL_PACKET != AUTHORITY",
        ],
    }
