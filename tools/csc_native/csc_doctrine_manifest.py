"""CSC doctrine manifest helper for collecting governed doctrine and invariant surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from csc_runtime_bindings import get_bindings

BINDINGS = get_bindings()
PROJECT_ROOT = BINDINGS.target_project_root
DOCS_ROOT = BINDINGS.docs_root


@dataclass(frozen=True)
class RequiredDocument:
    path: Path
    required_phrases: tuple[str, ...]


@dataclass(frozen=True)
class DoctrineAuthority:
    authority_id: str
    title: str
    source_kind: str
    source_ref: str


@dataclass(frozen=True)
class DoctrineRequirement:
    requirement_id: str
    normalized_class: str
    title: str
    authorities: tuple[str, ...]
    expectation: str
    enforcement_kind: tuple[str, ...]
    promotion_blocking: bool


@dataclass(frozen=True)
class HolonSpec:
    subsystem_id: str
    file_path: Path
    purpose: str
    boundary: str
    interface: str
    invariants: tuple[str, ...]
    hazards: tuple[str, ...]
    required_signals: tuple[str, ...]


TRI_AUTHORITIES: tuple[DoctrineAuthority, ...] = (
    DoctrineAuthority(
        "receiver_project",
        "PCMMAD Receiver V29 project bindings",
        "local_doctrine",
        "docs/receiver_doctrine/00_RECEIVER_PROJECT_BINDINGS.md",
    ),
    DoctrineAuthority(
        "receiver_sop",
        "Receiver ingress and evaluation SOP",
        "local_sop",
        "docs/receiver_sop/01_RECEIVER_INGRESS_AND_EVALUATION_SOP.md",
    ),
    DoctrineAuthority(
        "omega_local",
        "CODEX OMEGA v2.0",
        "local_doctrine",
        "docs/ergo_foundations/CODEX_OMEGA_BIBLE.md",
    ),
    DoctrineAuthority(
        "unified_local",
        "UNIFIED CODE STANDARDS DOCTRINE v1.2",
        "local_doctrine",
        "docs/ergo_foundations/UNIFIED_CODE_STANDARDS_DOCTRINE_v1.2.md",
    ),
    DoctrineAuthority("csc_sop", "CSC SOP set", "local_sop", "docs/csc_sop/"),
)

REQUIRED_LOCAL_CSC_DOCS: tuple[RequiredDocument, ...] = (
    RequiredDocument(
        DOCS_ROOT / "00_CSC_START_AND_AUTHORITY.md",
        ("# 00 — CSC START AND AUTHORITY", "## Purpose"),
    ),
    RequiredDocument(
        DOCS_ROOT / "05_CSC_REQUIRED_SOP_SET.md",
        ("# 05 — CSC REQUIRED SOP SET", "## Required Local CSC SOP Documents"),
    ),
    RequiredDocument(
        DOCS_ROOT / "09_CSC_SOP_FRESHNESS_AND_MUTATION_LAG_SOP.md",
        ("# 09 — CSC SOP FRESHNESS AND MUTATION-LAG SOP", "## Required checks"),
    ),
    RequiredDocument(
        DOCS_ROOT / "10_CSC_GENERAL_GUIDE_AND_UNIVERSALIZATION.md",
        ("# 10 — CSC GENERAL GUIDE AND UNIVERSALIZATION", "## Universalization rule"),
    ),
    RequiredDocument(
        DOCS_ROOT / "11_CSC_SERVER_EXECUTION_METHODOLOGY_FOR_UNRELIABLE_PLANES.md",
        (
            "# 11 — CSC SERVER EXECUTION METHODOLOGY FOR UNRELIABLE PLANES",
            "## Purpose",
            "## Core rule",
        ),
    ),
    RequiredDocument(
        PROJECT_ROOT / "docs" / "receiver_doctrine" / "00_RECEIVER_PROJECT_BINDINGS.md",
        (
            "PCMMAD Receiver V29 Project Bindings",
            "Extracted package code is controlled evidence until promoted.",
        ),
    ),
    RequiredDocument(
        PROJECT_ROOT / "docs" / "receiver_sop" / "01_RECEIVER_INGRESS_AND_EVALUATION_SOP.md",
        ("Receiver Ingress and Evaluation SOP", "Promotion boundary"),
    ),
    RequiredDocument(
        PROJECT_ROOT / "spec" / "PCMMAD_RECEIVER_V29_NATIVE_PROTOCOL_SPEC.md",
        ("PCMMAD Receiver V29 Native Protocol Release Candidate Spec", "Required gates"),
    ),
    RequiredDocument(
        PROJECT_ROOT / "docs" / "protocol" / "NATIVE_PROTOCOL_CONTRACT.md",
        ("PCMMAD native runtime protocol contract", "Authoritative body and sidecar", "Proportionate rigor"),
    ),
    RequiredDocument(
        PROJECT_ROOT / "docs" / "pcmmad_doctrine" / "PCMMAD_CANONICAL_RUNTIME_SPECIFICATION.md",
        ("PCMMAD Canonical Runtime Specification", "Canonical State Objects", "Mode Gate"),
    ),
    RequiredDocument(
        PROJECT_ROOT / "reports" / "INITIAL_EXTRACTION_MANIFEST.json",
        ("entry_count", "PCMMAD_receiver(2).zip"),
    ),
    RequiredDocument(
        PROJECT_ROOT / "reports" / "INITIAL_PACKAGE_EVALUATION.json",
        ("module_count", "compileall_returncode"),
    ),
)

REQUIRED_REPAIRED_ARCHIVE_FILES: tuple[str, ...] = ()
REPAIRED_ARCHIVE_ROOT = PROJECT_ROOT / "data" / "imports"

TRI_DOCTRINE_REQUIREMENTS: tuple[DoctrineRequirement, ...] = (
    DoctrineRequirement(
        "REQ_RECEIVER_INGRESS",
        "receiver_ingress_and_evidence_boundary",
        "Receiver ingress and evidence boundary",
        ("csc_sop",),
        (
            "Archive contents must be extracted, inventoried, and evaluated "
            "as controlled evidence before promotion."
        ),
        ("sop", "coverage", "pdver"),
        True,
    ),
    DoctrineRequirement(
        "REQ_RECEIVER_VERIFICATION",
        "receiver_compile_and_static_evaluation",
        "Receiver compile and static evaluation",
        ("csc_sop",),
        (
            "Extracted receiver package must pass static compile verification "
            "and produce an evaluation report."
        ),
        ("verification", "coverage"),
        True,
    ),
    DoctrineRequirement(
        "REQ_RECEIVER_FINALIZER",
        "receiver_finalizer_and_doctrine_gate",
        "Receiver finalizer and doctrine gate",
        ("csc_sop",),
        (
            "The receiver lab must end tasks through finalizer clean status "
            "or exact blocker reporting."
        ),
        ("verification", "coverage"),
        True,
    ),
    DoctrineRequirement(
        "REQ_PROTOCOL_TYPED_STATE",
        "pcmmad_typed_runtime_state",
        "Typed PCMMAD runtime state",
        ("receiver_project", "unified_local"),
        "Objective, constraint, continuity, claim, artifact, promotion, mode, rigor, evidence, and waiver state must be structurally represented.",
        ("coverage", "verification", "pdver"),
        True,
    ),
    DoctrineRequirement(
        "REQ_PROTOCOL_APPEND_ONLY",
        "pcmmad_append_only_protocol",
        "Append-only protocol history",
        ("receiver_project", "csc_sop"),
        "Protocol mutation must append verifiable events and preserve supersession rather than silently rewriting history.",
        ("coverage", "verification", "sop"),
        True,
    ),
    DoctrineRequirement(
        "REQ_PROTOCOL_MODE_GATE",
        "pcmmad_discourse_build_mode_gate",
        "Discourse/build mode gate",
        ("receiver_project", "omega_local"),
        "Initialized projects must expose an explicit, compatibility-aware mode gate for specimen mutation and promotion.",
        ("coverage", "verification"),
        True,
    ),
    DoctrineRequirement(
        "REQ_PROTOCOL_PROMOTION_EVIDENCE",
        "pcmmad_promotion_evidence_and_waivers",
        "Promotion evidence and waiver discipline",
        ("receiver_project", "unified_local", "csc_sop"),
        "Promotion must apply proportionate, freshness-aware evidence thresholds and reject inactive or expired waivers.",
        ("coverage", "verification", "pdver"),
        True,
    ),
)

HOLON_SPECS: tuple[HolonSpec, ...] = (
    HolonSpec(
        "receiver_runtime",
        PROJECT_ROOT / "baseline" / "pcmmad_receiver" / "server.py",
        "Promoted PCMMAD receiver process entrypoint.",
        "Authenticated local authority-plane boundary.",
        "Flask application process.",
        ("server entrypoint", "Flask app factory", "typed environment bind configuration"),
        ("required route-family failure", "schema drift", "global interpreter drift"),
        ("create_app", "SERVER_CONFIG", "app.run"),
    ),
    HolonSpec(
        "receiver_action_schema",
        PROJECT_ROOT
        / "baseline"
        / "pcmmad_receiver"
        / "pcmmad_lab_action_schema_v10_3_pcmmad_native_protocol_compact_30_router.json",
        "Compact action schema/router for PCMMAD receiver tools.",
        "Custom GPT import boundary.",
        "OpenAPI 3.0.3 JSON schema.",
        ("openapi", "paths", "components", "exactly 30 unique operation IDs"),
        ("tool/schema mismatch", "stale ngrok URL"),
        ("openapi", "paths", "10.3.0"),
    ),
    HolonSpec(
        "receiver_evaluation_report",
        PROJECT_ROOT / "reports" / "INITIAL_PACKAGE_EVALUATION.json",
        "Static package evaluation output.",
        "Evaluation boundary.",
        "JSON report.",
        ("module_count", "compileall_returncode"),
        ("evaluation drift",),
        ("module_count", "compileall_returncode"),
    ),
    HolonSpec(
        "pcmmad_native_protocol",
        PROJECT_ROOT / "baseline" / "pcmmad_receiver" / "protocol_store.py",
        "Append-only typed PCMMAD runtime protocol and derived state projection.",
        "Project-scoped governance and mode boundary.",
        "Server-native protocol tools behind /lab/dispatch.",
        ("hash-chained ledger", "typed state", "proportionate rigor", "mode gate", "waiver lineage"),
        ("silent history rewrite", "mode leakage", "stale evidence", "expired waiver authorization"),
        ("verify_events", "evaluate_mode_gate", "record_promotion", "record_waiver"),
    ),
    HolonSpec(
        "task_finalizer",
        PROJECT_ROOT / "system" / "finalize_task.py",
        "Run CSC and finalize receiver lab tasks.",
        "Finalization boundary.",
        "CLI script.",
        ("csc output", "final_clean"),
        ("silent success",),
        ("csc_output_root", "final_clean"),
    ),
)


def required_document_status(document: RequiredDocument) -> tuple[bool, tuple[str, ...]]:
    if not document.path.exists():
        return False, document.required_phrases
    text = document.path.read_text(encoding="utf-8", errors="ignore")
    missing = tuple(phrase for phrase in document.required_phrases if phrase not in text)
    return len(missing) == 0, missing


def authority_status(authority: DoctrineAuthority) -> bool:
    if authority.source_ref.endswith("/"):
        return (PROJECT_ROOT / authority.source_ref).exists()
    return (PROJECT_ROOT / authority.source_ref).exists()
