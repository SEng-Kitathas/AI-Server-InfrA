"""Lab tool registry, router helpers, mounted filesystem utilities, and bridge wiring."""

from __future__ import annotations
from dataclasses import dataclass

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from pathlib import Path
from typing import Any
from collections.abc import Iterator, MutableMapping, Callable

from .context_engine import (
    BadPathError,
    ContextPlaneError,
    NotFoundError,
    extract_archive,
    get_index_cache_stats,
    inspect_archive,
    inspect_model,
    list_archives,
    list_files,
    list_models,
    project_root_path,
    read_file,
    rehydrate_context,
    search_files,
)

JsonRecord = MutableMapping[str, Any]
JsonObject = MutableMapping[str, Any]

from .execution_routes import (
    DEFAULT_STDERR_MAX_BYTES,
    DEFAULT_STDOUT_MAX_BYTES,
    DEFAULT_TIMEOUT_SECONDS,
    EXECUTION_MODES,
    MAX_OUTPUT_BYTES,
    MAX_TIMEOUT_SECONDS,
    _RUNNING,
    _finalize,
    _job_dir,
    _read_job,
    _request_optional_positive_int,
    _resolve_cwd,
    _tail_text,
    _write_job,
    submit_execution_job,
    terminate_execution_job,
    ExecutionRequestError,
)
from .lab_plugins import load_plugins
from .lab_policy import PolicyDecision, evaluate_tool_call, policy_mode
from .protocol_policy import evaluate_protocol_tool_call
from .lab_schema_validation import validate_payload_schema
from .lab_tools_browser import register_browser_tools
from .lab_tools_execution import register_execution_tools
from .lab_tools_filesystem import register_filesystem_tools
from .lab_tools_project import register_project_tools
from .lab_tools_state import register_state_tools
from .lab_tools_research import register_research_tools
from .lab_tools_ops import register_ops_tools
from .lab_tools_sop import register_sop_tools
from .lab_tools_semantic import register_semantic_tools
from .lab_tools_doctrine import register_doctrine_tools
from .lab_tools_governance import register_governance_tools
from .lab_tools_protocol import register_protocol_tools
from .lab_tools_continuity import register_continuity_tools
from .lab_tools_icf_ingress import register_icf_ingress_tool
from .lab_tools_res import register_res_tools
from .lab_tools_memory import register_memory_tools
from .lab_tools_ucm import register_ucm_tools
from .lab_tools_mutation_authority import project_mutation_scope, register_mutation_authority_tools
from .project_mutation_authority import (
    ProjectMutationAuthorityError,
    project_mutation_authority_context,
    validate_consequence_authority,
)
from .research_config import ENABLED_HUNT_MODES, ENABLED_SOURCES, PARSER_VERSION
from .research_arxiv import get_cache_stats
from .server_hardening import safe_json_dumps, safe_json_loads
from .runtime_axioms import constitutional_seed
from .lab_results import get_result, store_result, summarize_payload
from .lab_state import (
    append_reflexion,
    append_session_note,
    end_session,
    get_session,
    pull_andon,
    read_reflexion,
    start_session,
)
from .shared_core import (
    TEXT_EXTENSIONS,
    ensure_parent,
    get_mount_roots,
    get_project_root,
    commits_ledger_path_for,
    resolve_target,
    init_project_layout,
    mount_summary,
    resolve_mount_spec,
    sha256_file,
    utc_now,
    validate_project_id,
)
from .sop_ingest import (
    SopError,
    ack_chunk as sop_ack_chunk,
    complete_file as sop_complete_file,
    guard_check as sop_guard_check,
    ingestion_status as sop_ingestion_status,
    inspect_package as sop_inspect_package,
    next_chunk as sop_next_chunk,
    register_package as sop_register_package,
    reset_ingestion as sop_reset_ingestion,
)
from .control_plane_models import (
    CapabilityFamilyCard,
    CompactControlSurfaceDescriptor,
    PluginLoadRecord,
    ServerCapabilityRouterDescriptor,
    ToolCatalogResponse,
    ToolResultEnvelope,
    ToolRouterValidationState,
    ToolSpec,
)

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None


class LabToolError(Exception):
    def __init__(self, error_code: str, message: str, status: int = 400, **extra: Any) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status = status
        self.extra = extra


_TOOL_REGISTRY: dict[str, ToolSpec] = {}
_PLUGIN_LOADS: list[PluginLoadRecord] = []
_PLUGIN_ERRORS: list[str] = []
_PLUGIN_TOOL_SPECS: dict[str, ToolSpec] = {}
_PLUGIN_GENERATION = 0
_PLUGIN_LAST_RELOAD: JsonObject | None = None
_REGISTRY_LOCK = threading.RLock()
_PLUGIN_RELOAD_LOCK = threading.RLock()
_BASE_DIR = Path(__file__).resolve().parent
_TEXT_EXTENSIONS = frozenset(ext.lower() for ext in TEXT_EXTENSIONS)
_DEFAULT_GREP_MAX_FILE_BYTES = 2 * 1024 * 1024


def _build_tool_spec(
    name: str,
    description: str,
    danger_tier: str,
    metadata: dict[str, Any],
    fn: Callable[[JsonObject], JsonObject],
) -> ToolSpec:
    return ToolSpec(
        name=name,
        description=description,
        danger_tier=danger_tier,
        category=str(metadata.get("category", "general")),
        tags=list(metadata.get("tags") or []),
        approval_required=bool(metadata.get("approval_required", False)),
        mutating=bool(metadata.get("mutating", False)),
        input_schema=metadata.get("input_schema") or {"type": "object"},
        output_schema=metadata.get("output_schema") or {"type": "object"},
        capability_version=str(metadata.get("capability_version", "1")),
        schema_version=str(metadata.get("schema_version", "1")),
        side_effect_class=str(metadata.get("side_effect_class", "")),
        effect_traits=[
            str(item)
            for item in (metadata.get("effect_traits") or [])
            if str(item).strip()
        ],
        idempotency_semantics=str(metadata.get("idempotency_semantics", "")),
        availability_mode=str(metadata.get("availability_mode", "resident")),
        availability_scope=str(metadata.get("availability_scope", "handler")),
        availability_provider_id=str(metadata.get("availability_provider_id", "")),
        availability_provider=metadata.get("availability_provider"),
        handler=fn,
    )


def register_tool(
    name: str,
    description: str,
    danger_tier: str = "medium",
    **metadata: Any,
) -> Callable[[Callable[[JsonObject], JsonObject]], Callable[[JsonObject], JsonObject]]:
    def deco(fn: Callable[[JsonObject], JsonObject]) -> Callable[[JsonObject], JsonObject]:
        spec = _build_tool_spec(name, description, danger_tier, dict(metadata), fn)
        with _REGISTRY_LOCK:
            current = _TOOL_REGISTRY.get(name)
            # Core registration is authoritative over a same-name plugin that was
            # loaded earlier during module bootstrap.
            if current is not None and _PLUGIN_TOOL_SPECS.get(name) is current:
                _PLUGIN_TOOL_SPECS.pop(name, None)
            _TOOL_REGISTRY[name] = spec
        return fn

    return deco


def _plugin_candidate_registrar(
    core_names: set[str], candidate: dict[str, ToolSpec]
) -> Callable[..., Any]:
    def register_candidate(
        name: str,
        description: str,
        danger_tier: str = "medium",
        **metadata: Any,
    ):
        if name in core_names:
            raise RuntimeError(f"plugin capability collides with core tool: {name}")
        if name in candidate:
            raise RuntimeError(f"duplicate plugin capability registration: {name}")

        def deco(fn: Callable[[JsonObject], JsonObject]):
            if name in candidate:
                raise RuntimeError(f"duplicate plugin capability registration: {name}")
            candidate[name] = _build_tool_spec(
                name, description, danger_tier, dict(metadata), fn
            )
            return fn

        return deco

    return register_candidate


def _registry_snapshot() -> dict[str, ToolSpec]:
    with _REGISTRY_LOCK:
        return dict(_TOOL_REGISTRY)


def _safe_tool_card(item: ToolSpec) -> JsonObject:
    return item.to_card()


def list_tools() -> list[JsonObject]:
    registry = _registry_snapshot()
    return [registry[name].to_card() for name in sorted(registry)]


AVAILABILITY_MAX_TOOLS = 32
_AVAILABILITY_STATUSES = {"available", "degraded", "unavailable", "unknown"}


def _bounded_availability_blockers(value: object) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    return [str(item)[:300] for item in list(value)[:16] if str(item).strip()]


def _normalize_availability_probe(spec: ToolSpec, raw: object) -> JsonObject:
    if not isinstance(raw, dict):
        raw = {}
    available_raw = raw.get("available")
    available = available_raw if isinstance(available_raw, bool) else None
    status = str(raw.get("status") or "").strip().lower()
    if status not in _AVAILABILITY_STATUSES:
        status = "available" if available is True else "unavailable" if available is False else "unknown"
    if available is None:
        if status == "available":
            available = True
        elif status == "unavailable":
            available = False
    return {
        "status": status,
        "available": available,
        "blockers": _bounded_availability_blockers(raw.get("blockers")),
        "basis": str(raw.get("basis") or "provider_probe")[:200],
        "checked_at": utc_now(),
    }


def _capability_availability_payload(payload: JsonObject, registry: dict[str, ToolSpec] | None = None) -> JsonObject:
    snapshot = dict(registry or _registry_snapshot())
    names = payload.get("tool_names")
    if not isinstance(names, list) or not names:
        raise LabToolError("BAD_REQUEST", "tool_names must be a non-empty array", 400)
    if len(names) > AVAILABILITY_MAX_TOOLS:
        raise LabToolError(
            "CAPABILITY_AVAILABILITY_LIMIT_EXCEEDED",
            f"tool_names exceeds maximum of {AVAILABILITY_MAX_TOOLS}",
            400,
            requested=len(names),
            maximum=AVAILABILITY_MAX_TOOLS,
        )
    requested: list[str] = []
    seen: set[str] = set()
    for item in names:
        name = str(item).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        requested.append(name)
    unknown = [name for name in requested if name not in snapshot]
    if unknown:
        raise LabToolError(
            "TOOL_NOT_FOUND",
            "one or more requested capabilities are not registered",
            404,
            tool_names=unknown[:16],
        )
    provider_results: dict[str, JsonObject] = {}
    provider_calls = 0
    rows: list[JsonObject] = []
    for name in requested:
        spec = snapshot[name]
        contract = spec.availability_contract
        mode = str(contract.get("mode") or "resident")
        if mode != "dynamic":
            probe = {
                "status": "available" if spec.handler is not None else "unavailable",
                "available": spec.handler is not None,
                "blockers": [] if spec.handler is not None else ["handler_not_registered"],
                "basis": "registered_handler",
                "checked_at": utc_now(),
            }
        elif spec.availability_provider is None:
            probe = {
                "status": "unknown",
                "available": None,
                "blockers": ["availability_provider_not_registered"],
                "basis": "probe_unavailable",
                "checked_at": utc_now(),
            }
        else:
            provider_key = str(spec.availability_provider_id or f"callable:{id(spec.availability_provider)}")
            if provider_key not in provider_results:
                provider_calls += 1
                try:
                    provider_results[provider_key] = _normalize_availability_probe(
                        spec, spec.availability_provider()
                    )
                except Exception as exc:
                    provider_results[provider_key] = {
                        "status": "unknown",
                        "available": None,
                        "blockers": ["availability_probe_failed"],
                        "basis": "provider_probe_exception",
                        "checked_at": utc_now(),
                        "error": str(exc)[:500],
                    }
            probe = dict(provider_results[provider_key])
        rows.append(
            {
                "tool_name": name,
                "registered": spec.handler is not None,
                "mode": mode,
                "scope": str(contract.get("scope") or "handler"),
                "provider_id": contract.get("provider_id"),
                "contract_digest": spec.contract_digest,
                **probe,
            }
        )
    return {
        "count": len(rows),
        "requested_count": len(requested),
        "provider_probe_count": provider_calls,
        "rows": rows,
    }


def capability_families() -> list[CapabilityFamilyCard]:
    buckets: dict[str, list[ToolSpec]] = {}
    for spec in _registry_snapshot().values():
        buckets.setdefault(spec.category or "general", []).append(spec)
    families: list[CapabilityFamilyCard] = []
    for name in sorted(buckets):
        specs = buckets[name]
        tag_set = sorted({tag for spec in specs for tag in spec.tags})
        danger_tiers = sorted({str(spec.danger_tier) for spec in specs})
        families.append(
            CapabilityFamilyCard(
                name=name,
                tool_count=len(specs),
                mutating_tools=sum(1 for spec in specs if spec.mutating),
                approval_required_tools=sum(1 for spec in specs if spec.approval_required),
                effective_approval_required_tools=sum(
                    1 for spec in specs if spec.effective_approval_required
                ),
                danger_tiers=danger_tiers,
                tags=tag_set,
            )
        )
    return families


def compact_control_surface_descriptor(
    *, operation_budget: int = 30, action_count: int = 30
) -> CompactControlSurfaceDescriptor:
    return CompactControlSurfaceDescriptor(
        operation_budget=operation_budget,
        action_count=action_count,
        purpose="Compact GPT-safe control surface with bounded imported actions.",
        note=(
            "Schema ceilings are not server ceilings. Use lab dispatch, batch, "
            "and result-handle flows to reach larger server-native capability families."
        ),
    )


def server_native_router_descriptor() -> ServerCapabilityRouterDescriptor:
    return ServerCapabilityRouterDescriptor(
        dispatch_entrypoint="/lab/dispatch",
        batch_entrypoint="/lab/batch",
        result_handle_entrypoint="/lab/results/get",
        larger_server_native_capability_set=True,
        families=capability_families(),
        notes=[
            "The compact schema is intentionally bounded to preserve GPT import compatibility.",
            "The server-native capability set can remain richer than the imported action surface.",
            "Large results may be materialized server-side and retrieved by handle.",
        ],
    )


def tool_catalog_response(
    *, operation_budget: int = 30, action_count: int = 30
) -> ToolCatalogResponse:
    registry = _registry_snapshot()
    tools = [registry[name].to_card() for name in sorted(registry)]
    return ToolCatalogResponse(
        ok=True,
        count=len(tools),
        tools=tools,
        compact_control_surface=compact_control_surface_descriptor(
            operation_budget=operation_budget,
            action_count=action_count,
        ),
        server_native_router=server_native_router_descriptor(),
        validation=_tool_router_validation_state(),
    )


def _plugin_contract_digest(
    specs: dict[str, ToolSpec], records: list[PluginLoadRecord]
) -> str:
    payload = {
        "tools": {name: spec.contract_digest for name, spec in sorted(specs.items())},
        "plugins": [
            {"module": row.module, "path": row.path, "sha256": row.sha256}
            for row in records
        ],
    }
    return hashlib.sha256(
        safe_json_dumps(payload).encode("utf-8")
    ).hexdigest()


def _load_plugins() -> JsonObject:
    global _PLUGIN_GENERATION, _PLUGIN_LAST_RELOAD
    with _PLUGIN_RELOAD_LOCK:
        live_before = _registry_snapshot()
        previous_plugin_specs = dict(_PLUGIN_TOOL_SPECS)
        core_registry = {
            name: spec
            for name, spec in live_before.items()
            if previous_plugin_specs.get(name) is not spec
        }
        candidate: dict[str, ToolSpec] = {}
        before_digest = _plugin_contract_digest(
            previous_plugin_specs, list(_PLUGIN_LOADS)
        )
        try:
            records = load_plugins(
                _BASE_DIR,
                _plugin_candidate_registrar(set(core_registry), candidate),
            )
        except Exception as exc:
            _PLUGIN_ERRORS.clear()
            _PLUGIN_ERRORS.append(str(exc))
            receipt = {
                "committed": False,
                "generation": _PLUGIN_GENERATION,
                "tool_count_before": len(live_before),
                "tool_count_after": len(live_before),
                "plugin_tool_count": len(previous_plugin_specs),
                "plugin_contract_digest": before_digest,
                "error": str(exc),
                "time": utc_now(),
            }
            _PLUGIN_LAST_RELOAD = receipt
            return receipt

        merged = dict(core_registry)
        merged.update(candidate)
        old_modules = {row.module for row in _PLUGIN_LOADS}
        new_modules = {row.module for row in records}
        with _REGISTRY_LOCK:
            _TOOL_REGISTRY.clear()
            _TOOL_REGISTRY.update(merged)
            _PLUGIN_TOOL_SPECS.clear()
            _PLUGIN_TOOL_SPECS.update(candidate)
            _PLUGIN_LOADS.clear()
            _PLUGIN_LOADS.extend(records)
            _PLUGIN_ERRORS.clear()
            _PLUGIN_GENERATION += 1
        for module_name in old_modules - new_modules:
            sys.modules.pop(module_name, None)
        after_digest = _plugin_contract_digest(candidate, records)
        receipt = {
            "committed": True,
            "generation": _PLUGIN_GENERATION,
            "tool_count_before": len(live_before),
            "tool_count_after": len(merged),
            "plugin_tool_count": len(candidate),
            "plugin_contract_digest_before": before_digest,
            "plugin_contract_digest": after_digest,
            "changed": before_digest != after_digest,
            "time": utc_now(),
        }
        _PLUGIN_LAST_RELOAD = receipt
        return receipt


_load_plugins()


def _plugin_runtime_state() -> JsonObject:
    with _REGISTRY_LOCK:
        plugin_specs = dict(_PLUGIN_TOOL_SPECS)
        records = list(_PLUGIN_LOADS)
        generation = _PLUGIN_GENERATION
        last_reload = dict(_PLUGIN_LAST_RELOAD) if isinstance(_PLUGIN_LAST_RELOAD, dict) else None
    return {
        "generation": generation,
        "plugin_tool_count": len(plugin_specs),
        "plugin_load_count": len(records),
        "plugin_error_count": len(_PLUGIN_ERRORS),
        "contract_digest": _plugin_contract_digest(plugin_specs, records),
        "last_reload": last_reload,
    }


def _tool_validation_mode() -> str:
    mode = os.environ.get("PCMMAD_TOOL_VALIDATION_MODE", "connected_only").strip().lower()
    if mode not in {"connected_only", "strict"}:
        return "connected_only"
    return mode


def _tool_router_validation_state() -> ToolRouterValidationState:
    connected = bool(_TOOL_REGISTRY)
    api_valid = connected
    reason = None
    if not connected:
        reason = "Tool router has no registered tools."
    return ToolRouterValidationState(
        api_valid=api_valid,
        connected=connected,
        validation_mode=_tool_validation_mode(),
        checked_at=utc_now(),
        reason=reason,
    )


def _raise_validation_error(code: str, message: str, status: int) -> None:
    raise LabToolError(code, message, status)


def _validate_payload_schema(
    tool_name: str, schema: JsonObject | None, payload: JsonObject
) -> None:
    validate_payload_schema(tool_name, schema, payload, raise_error=_raise_validation_error)


def _dispatch_spec(tool_name: str) -> ToolSpec:
    with _REGISTRY_LOCK:
        spec = _TOOL_REGISTRY.get(tool_name)
    if spec:
        return spec
    raise LabToolError(
        "UNKNOWN_TOOL",
        f"Unknown tool: {tool_name}",
        404,
        available_tools=[tool["name"] for tool in list_tools()],
    )


def _dispatch_decision(
    tool_name: str,
    spec: ToolSpec,
    payload: JsonObject,
    authority: JsonObject | None,
) -> PolicyDecision:
    decision = evaluate_tool_call(spec, payload, authority)
    if decision.allowed:
        return decision
    raise LabToolError(
        decision.error_code or "APPROVAL_REQUIRED",
        decision.reason,
        403,
        tool=tool_name,
        policy_mode=decision.mode,
        danger_tier=spec.danger_tier,
        approval_mode=decision.approval_mode,
        approval_handle=decision.approval_handle,
        **decision.details,
    )


def _dispatch_protocol_decision(tool_name: str, spec: ToolSpec, payload: JsonObject):
    decision = evaluate_protocol_tool_call(spec, payload)
    if decision.allowed:
        return decision
    raise LabToolError(
        "PROTOCOL_MODE_REQUIRED",
        decision.warning or decision.reason,
        409,
        tool=tool_name,
        protocol_policy_mode=decision.policy_mode,
        mutation_domain=decision.mutation_domain.value,
        current_mode=decision.current_mode,
    )


def _merge_warnings(*warnings: str | None) -> str | None:
    present = [item for item in warnings if item]
    return "; ".join(present) if present else None


def _project_mutation_fenced(spec: ToolSpec) -> bool:
    return "project_mutation_fenced" in set(spec.effect_traits or [])


def _preflight_present_project_mutation_authority(
    spec: ToolSpec, arguments: JsonObject, authority_data: JsonObject
) -> None:
    """Reject stale/invalid supplied project authority before consuming approval.

    Missing project mutation authority intentionally remains a later consequence-time
    concern so an unapproved request can still receive its exact bound approval
    challenge. When a caller does present project authority, validating its current
    generation/ownership is independent of approval consumption and must fail first
    if stale.
    """
    if not _project_mutation_fenced(spec):
        return
    mutation_authority = authority_data.get("project_mutation")
    if mutation_authority is None:
        return
    project_id = str(arguments.get("project_id") or "").strip()
    if not project_id:
        return
    try:
        validate_consequence_authority(
            project_id,
            mutation_authority=mutation_authority,
            session_id=str(arguments.get("session_id") or "").strip(),
        )
    except ProjectMutationAuthorityError as exc:
        raise LabToolError(exc.error_code, exc.message, exc.status, **exc.extra) from exc


def _dispatch_result(tool_name: str, spec: ToolSpec, payload: JsonObject) -> JsonObject:
    if spec.handler is None:
        raise LabToolError("BAD_TOOL_HANDLER", f"Tool {tool_name} has no handler", 500)
    result = spec.handler(payload)
    if not isinstance(result, dict):
        raise LabToolError("BAD_TOOL_RESULT", f"Tool {tool_name} returned non-object result", 500)
    return _maybe_offload_large_result(tool_name, payload, result)


def _requires_router_connection(spec: ToolSpec) -> bool:
    return spec.category in {"browser", "procedure", "web"}


def _split_authority(
    payload: JsonObject | None, authority: JsonObject | None
) -> tuple[JsonObject, JsonObject]:
    arguments: JsonObject = dict(payload or {})
    authority_data: JsonObject = dict(authority or {})
    if "mutation_authority" in arguments:
        raise LabToolError(
            "AUTHORITY_IN_CAPABILITY_PAYLOAD",
            "project mutation authority belongs in the top-level Runtime authority envelope",
            400,
        )
    embedded_approval = arguments.pop("approval", None)
    embedded_handle = arguments.pop("approval_handle", None)
    # Transitional compatibility: old clients carried approval inside tool args.
    if embedded_approval is not None and "legacy_approval" not in authority_data:
        authority_data["legacy_approval"] = embedded_approval
    if embedded_handle is not None and "approval_handle" not in authority_data:
        authority_data["approval_handle"] = embedded_handle
    # A top-level `approval` member is also treated as the legacy form.
    if "approval" in authority_data and "legacy_approval" not in authority_data:
        authority_data["legacy_approval"] = authority_data.pop("approval")
    return arguments, authority_data


def _assert_expected_contract_digest(
    spec: ToolSpec, expected_contract_digest: str | None
) -> None:
    if expected_contract_digest is None:
        return
    expected = str(expected_contract_digest).strip().lower()
    if (
        len(expected) != 64
        or any(ch not in "0123456789abcdef" for ch in expected)
    ):
        raise LabToolError(
            "BAD_EXPECTED_CONTRACT_DIGEST",
            "expected_contract_digest must be exactly 64 hexadecimal characters",
            400,
        )
    current = str(spec.contract_digest).strip().lower()
    if expected != current:
        raise LabToolError(
            "CAPABILITY_CONTRACT_STALE",
            "capability contract changed after client discovery",
            409,
            expected_contract_digest=expected,
            current_contract_digest=current,
            capability=spec.name,
        )


def dispatch_tool(
    tool_name: str,
    payload: JsonObject | None,
    *,
    authority: JsonObject | None = None,
    expected_contract_digest: str | None = None,
) -> JsonObject:
    spec = _dispatch_spec(tool_name)
    # Contract currentness is checked immediately after exact native tool resolution.
    # A stale invocation must fail before provider work, schema/protocol checks,
    # approval issuance/consumption, mutation fencing, or handler consequence.
    _assert_expected_contract_digest(spec, expected_contract_digest)
    router_validation = _tool_router_validation_state()
    if _requires_router_connection(spec) and (
        not router_validation.api_valid or not router_validation.connected
    ):
        raise LabToolError(
            "API_NOT_CONNECTED",
            "Tool router is not connected/valid.",
            503,
            validation=router_validation.to_dict(),
        )
    arguments, authority_data = _split_authority(payload, authority)
    if router_validation.validation_mode == "strict":
        _validate_payload_schema(tool_name, spec.input_schema, arguments)
    # Protocol eligibility and any supplied project-mutation authority are checked
    # before consuming single-use approval authority. Independent stale authority
    # must not burn an otherwise-valid approval challenge.
    protocol_decision = _dispatch_protocol_decision(tool_name, spec, arguments)
    _preflight_present_project_mutation_authority(spec, arguments, authority_data)
    decision = _dispatch_decision(tool_name, spec, arguments, authority_data)
    with project_mutation_authority_context(authority_data.get("project_mutation")):
        if _project_mutation_fenced(spec):
            with project_mutation_scope(
                arguments,
                LabToolError,
                mutation_authority=authority_data.get("project_mutation"),
            ):
                result = _dispatch_result(tool_name, spec, arguments)
        else:
            result = _dispatch_result(tool_name, spec, arguments)
    return ToolResultEnvelope(
        ok=True,
        tool=tool_name,
        danger_tier=spec.danger_tier,
        policy_mode=decision.mode,
        approved=decision.approved,
        time=utc_now(),
        result=result,
        warning=_merge_warnings(decision.warning, protocol_decision.warning),
        approval_mode=decision.approval_mode if decision.approved else None,
        approval_handle=decision.approval_handle if decision.approved else None,
    ).to_dict()


def _normalize_project_path(payload: JsonObject) -> str:
    p = payload.get("path")
    return "." if not p else str(p)


def _context_wrap(fn: Callable[[], object]) -> JsonObject:
    try:
        result = fn()
        if hasattr(result, "to_dict"):
            result = result.to_dict()
        if not isinstance(result, dict):
            raise LabToolError(
                "BAD_CONTEXT_RESULT",
                f"Context-plane operation returned {type(result).__name__}, expected object",
                500,
            )
        return result
    except BadPathError as e:
        raise LabToolError(e.error_code, str(e), 400)
    except NotFoundError as e:
        raise LabToolError(e.error_code, str(e), 404)
    except ContextPlaneError as e:
        raise LabToolError(e.error_code, str(e), 400)


def _exec_env(payload: JsonObject) -> dict[str, str]:
    env = os.environ.copy()
    for env_key, env_value in (payload.get("env") or payload.get("env_allowlist") or {}).items():
        if isinstance(env_key, str) and isinstance(env_value, str):
            env[env_key] = env_value
    return env


def _read_required_project_id(payload: JsonObject) -> str:
    project_id = str(payload.get("project_id", "")).strip()
    if not project_id:
        raise LabToolError("BAD_REQUEST", "project_id is required", 400)
    return validate_project_id(project_id)


def _ensure_project_layout(payload: JsonObject) -> str:
    project_id = _read_required_project_id(payload)
    init_project_layout(project_id)
    return project_id


def _read_text_preview(path: Path, max_bytes: int) -> tuple[str, bool, int]:
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    with path.open("rb") as handle:
        data = handle.read(max_bytes + 1)
    truncated = len(data) > max_bytes
    if truncated:
        data = data[:max_bytes]
    return data.decode("utf-8", errors="replace"), truncated, path.stat().st_size


def _iter_text_lines_bounded(path: Path, max_scan_bytes: int) -> Iterator[tuple[str, int]]:
    bytes_seen = 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            bytes_seen += len(line.encode("utf-8", errors="replace"))
            if bytes_seen > max_scan_bytes:
                return bytes_seen, True
            yield line.rstrip("\n"), bytes_seen
    return bytes_seen, False


def _stream_grep(
    path: Path, query: str, limit: int, max_file_bytes: int
) -> tuple[list[JsonObject], bool, bool]:
    hits: list[JsonObject] = []
    lowered = query.lower()
    iterator = _iter_text_lines_bounded(path, max_file_bytes)
    partial_scan = False
    skipped_oversized = False
    line_number = 0
    try:
        while True:
            item = next(iterator)
            if not isinstance(item, tuple) or len(item) != 2:
                continue
            line_number += 1
            line, _ = item
            if lowered in line.lower():
                hits.append({"path": str(path), "line": line_number, "text": line[:500]})
                if len(hits) >= limit:
                    partial_scan = True
                    break
    except StopIteration as stop:
        result = stop.value
        if isinstance(result, tuple) and len(result) == 2:
            _, skipped_oversized = result
    return hits, partial_scan, skipped_oversized


def _bounded_zip_entry_text(zf: zipfile.ZipFile, name: str, max_entry_bytes: int) -> JsonObject:
    info = zf.getinfo(name)
    if info.is_dir():
        return {"ok": False, "entry_name": str(name), "error": "entry is a directory"}
    with zf.open(info, "r") as handle:
        data = handle.read(max_entry_bytes + 1)
    truncated = len(data) > max_entry_bytes or info.file_size > max_entry_bytes
    if truncated:
        data = data[:max_entry_bytes]
    return {
        "ok": True,
        "entry_name": str(name),
        "bytes": len(data),
        "original_bytes": info.file_size,
        "truncated": truncated,
        "content": data.decode("utf-8", errors="replace"),
    }


def _resolve_general_path(payload: JsonObject, key: str = "path") -> Path:
    project_id = str(payload.get("project_id", "")).strip() or None
    path_raw = str(payload.get(key, "")).strip()
    if not path_raw:
        raise LabToolError("BAD_REQUEST", f"{key} is required", 400)
    try:
        default_root = get_project_root(project_id) if project_id else None
        return resolve_mount_spec(path_raw, default_root=default_root, allow_absolute=True)
    except (OSError, ValueError, TypeError) as e:
        raise LabToolError("BAD_PATH", str(e), 400)


def _ensure_within_allowed(path: Path) -> Path:
    allowed = [p.resolve() for p in get_mount_roots()]
    resolved = path.resolve()
    if not any(root == resolved or root in resolved.parents for root in allowed):
        raise LabToolError(
            "BAD_PATH", "resolved path escapes mounted roots", 400, mounts=mount_summary()
        )
    return resolved


@dataclass(frozen=True)
class PayloadIntSpec:
    key: str
    default: int
    minimum: int
    maximum: int


@dataclass(frozen=True)
class BridgePostSpec:
    endpoint: str
    fields: tuple[str, ...] | list[str]
    timeout_default: int = 30
    timeout_max: int = 120


def _bridge_base_url() -> str:
    return os.environ.get("PCMMAD_BROWSER_BRIDGE_URL", "http:" + "//127.0.0.1:4471").rstrip("/")


def _bridge_call(
    method: str, path: str, payload: JsonObject | None = None, timeout_seconds: int = 30
) -> JsonObject:
    url = _bridge_base_url() + path
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = safe_json_dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, headers=headers, data=data, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            raw = resp.read()
            text = raw.decode("utf-8", errors="replace")
            try:
                return safe_json_loads(text) if text else {"ok": True}
            except (TypeError, ValueError):
                return {"ok": True, "raw": text, "status": getattr(resp, "status", 200)}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise LabToolError("BROWSER_BRIDGE_HTTP_ERROR", f"{e.code}: {body}", e.code)
    except (OSError, RuntimeError, ValueError, TypeError, urllib.error.URLError) as e:
        raise LabToolError("BROWSER_BRIDGE_UNAVAILABLE", str(e), 502, base_url=_bridge_base_url())


def _bounded_payload_int(payload: JsonObject, spec: PayloadIntSpec) -> int:
    raw = payload.get(spec.key, spec.default)
    try:
        value = int(raw)
    except (TypeError, ValueError, OverflowError) as exc:
        raise LabToolError("BAD_REQUEST", f"{spec.key} must be an integer", 400) from exc
    return max(spec.minimum, min(value, spec.maximum))


def _bridge_payload_subset(payload: JsonObject, fields: tuple[str, ...] | list[str]) -> JsonObject:
    return {field: payload[field] for field in fields if field in payload}


def _bridge_timeout(
    payload: JsonObject,
    *,
    default: int,
    maximum: int,
    key: str = "timeout_seconds",
) -> int:
    return _bounded_payload_int(
        payload, PayloadIntSpec(key=key, default=default, minimum=1, maximum=maximum)
    )


def _bridge_browser_post(payload: JsonObject, spec: BridgePostSpec) -> JsonObject:
    return _bridge_call(
        "POST",
        spec.endpoint,
        _bridge_payload_subset(payload, spec.fields),
        _bridge_timeout(payload, default=spec.timeout_default, maximum=spec.timeout_max),
    )


def _bridge_browser_get(
    endpoint: str,
    payload: JsonObject,
    *,
    timeout_default: int = 10,
    timeout_max: int = 30,
) -> JsonObject:
    return _bridge_call(
        "GET",
        endpoint,
        None,
        _bridge_timeout(payload, default=timeout_default, maximum=timeout_max),
    )


def _maybe_offload_large_result(
    tool_name: str, payload: JsonObject, result: JsonObject
) -> JsonObject:
    project_id = str(payload.get("project_id", "")).strip()
    force = bool(payload.get("store_result", False))
    try:
        raw = safe_json_dumps(result)
    except (TypeError, ValueError):
        return result
    threshold = int(payload.get("result_handle_threshold_chars", 12000))
    if project_id and (force or len(raw) > threshold):
        meta = store_result(
            project_id,
            result,
            label=str(payload.get("result_label", tool_name)),
            tool_name=tool_name,
        )
        return {
            "stored": True,
            "handle": meta["handle"],
            "bytes": meta["bytes"],
            "sha256": meta["sha256"],
            "summary": summarize_payload(result),
        }
    return result


def _sop_call(fn: Callable[..., JsonObject], *args: Any, **kwargs: Any) -> JsonObject:
    try:
        return fn(*args, **kwargs)
    except SopError as e:
        raise LabToolError(e.code, e.message, 400, **e.extra)


register_state_tools(
    register_tool,
    error_cls=LabToolError,
    tool_router_validation_state=_tool_router_validation_state,
    policy_mode=policy_mode,
    plugin_loads=_PLUGIN_LOADS,
    plugin_errors=_PLUGIN_ERRORS,
    beautiful_soup=BeautifulSoup,
    bridge_call=_bridge_call,
    enabled_sources=ENABLED_SOURCES,
    enabled_hunt_modes=ENABLED_HUNT_MODES,
    parser_version=PARSER_VERSION,
    get_cache_stats=get_cache_stats,
    get_index_cache_stats=get_index_cache_stats,
    execution_modes=EXECUTION_MODES,
    tool_registry=_TOOL_REGISTRY,
    load_plugins=_load_plugins,
    plugin_runtime_state=_plugin_runtime_state,
    ensure_project_layout=_ensure_project_layout,
    running_jobs=_RUNNING,
    get_project_root=get_project_root,
    append_reflexion=append_reflexion,
    append_session_note=append_session_note,
    end_session=end_session,
    get_session=get_session,
    pull_andon=pull_andon,
    read_reflexion=read_reflexion,
    start_session=start_session,
    utc_now=utc_now,
)

register_mutation_authority_tools(
    register_tool,
    error_cls=LabToolError,
)

register_project_tools(
    register_tool,
    error_cls=LabToolError,
    context_wrap=_context_wrap,
    normalize_project_path=_normalize_project_path,
    project_root_path=project_root_path,
    list_files=list_files,
    read_file=read_file,
    search_files=search_files,
    rehydrate_context=rehydrate_context,
    list_models=list_models,
    inspect_model=inspect_model,
    list_archives=list_archives,
    inspect_archive=inspect_archive,
    extract_archive=extract_archive,
    ensure_project_layout=_ensure_project_layout,
    get_project_root=get_project_root,
    ensure_parent=ensure_parent,
    sha256_file=sha256_file,
    utc_now=utc_now,
    request_optional_positive_int=_request_optional_positive_int,
    ensure_within_allowed=_ensure_within_allowed,
    resolve_general_path=_resolve_general_path,
    bounded_zip_entry_text=_bounded_zip_entry_text,
    iter_tree=lambda *args, **kwargs: __import__("power_routes")._iter_tree(*args, **kwargs),
)


def _submit_execution_job_for_lab(payload: JsonObject):
    try:
        return submit_execution_job(payload, require_mutation_authority=True)
    except ExecutionRequestError as exc:
        raise LabToolError(exc.error_code, exc.message, exc.status, **exc.extra) from exc


register_execution_tools(
    register_tool,
    error_cls=LabToolError,
    request_optional_positive_int=_request_optional_positive_int,
    resolve_cwd=_resolve_cwd,
    exec_env=_exec_env,
    finalize_job=_finalize,
    read_job=_read_job,
    tail_text=_tail_text,
    execution_modes=EXECUTION_MODES,
    max_output_bytes=MAX_OUTPUT_BYTES,
    default_timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
    default_stdout_max_bytes=DEFAULT_STDOUT_MAX_BYTES,
    default_stderr_max_bytes=DEFAULT_STDERR_MAX_BYTES,
    max_timeout_seconds=MAX_TIMEOUT_SECONDS,
    submit_job=_submit_execution_job_for_lab,
    terminate_job=terminate_execution_job,
    utc_now=utc_now,
)

register_continuity_tools(
    register_tool,
    error_cls=LabToolError,
    get_project_root=get_project_root,
    resolve_target=resolve_target,
    commits_ledger_path_for=commits_ledger_path_for,
    sha256_file=sha256_file,
)

register_icf_ingress_tool(
    register_tool,
    error_cls=LabToolError,
)

register_res_tools(
    register_tool,
    error_cls=LabToolError,
)

register_memory_tools(
    register_tool,
    error_cls=LabToolError,
)

register_ucm_tools(
    register_tool,
    error_cls=LabToolError,
)

register_ops_tools(
    register_tool,
    error_cls=LabToolError,
    get_project_root=get_project_root,
    resolve_cwd=_resolve_cwd,
    exec_env=_exec_env,
    append_reflexion=append_reflexion,
    beautiful_soup=BeautifulSoup,
)

register_research_tools(
    register_tool,
    error_cls=LabToolError,
)

register_filesystem_tools(
    register_tool,
    error_cls=LabToolError,
    resolve_general_path=_resolve_general_path,
    ensure_within_allowed=_ensure_within_allowed,
    request_optional_positive_int=_request_optional_positive_int,
    read_text_preview=_read_text_preview,
    stream_grep=_stream_grep,
    text_extensions=_TEXT_EXTENSIONS,
    default_grep_max_file_bytes=_DEFAULT_GREP_MAX_FILE_BYTES,
    mount_summary=mount_summary,
    get_project_root=get_project_root,
    resolve_mount_spec=resolve_mount_spec,
)

register_sop_tools(
    register_tool,
    error_cls=LabToolError,
    read_required_project_id=_read_required_project_id,
    ensure_project_layout=_ensure_project_layout,
    resolve_general_path=_resolve_general_path,
    sop_call=_sop_call,
    sop_inspect_package=sop_inspect_package,
    sop_register_package=sop_register_package,
    sop_reset_ingestion=sop_reset_ingestion,
    sop_ingestion_status=sop_ingestion_status,
    sop_next_chunk=sop_next_chunk,
    sop_ack_chunk=sop_ack_chunk,
    sop_complete_file=sop_complete_file,
    sop_guard_check=sop_guard_check,
)

register_semantic_tools(
    register_tool,
    error_cls=LabToolError,
)

register_doctrine_tools(
    register_tool,
    error_cls=LabToolError,
)

register_governance_tools(
    register_tool,
    error_cls=LabToolError,
)

register_protocol_tools(
    register_tool,
    error_cls=LabToolError,
)

register_browser_tools(
    register_tool,
    bridge_call=_bridge_call,
    bridge_payload_subset=_bridge_payload_subset,
    bridge_timeout=lambda payload, default, maximum: _bridge_timeout(
        payload, default=default, maximum=maximum
    ),
    error_cls=LabToolError,
)


@register_tool(
    "lab.capabilities.availability",
    "Probe current execution availability for explicitly requested native capabilities without changing their contracts or invoking the capabilities themselves.",
    "low",
    category="lab",
    tags=["capabilities", "availability", "currentness", "discovery"],
    side_effect_class="read_probe",
    effect_traits=["reads_runtime_state", "probes_dependencies", "deduplicates_provider_probes", "bounded_results", "does_not_invoke_target_capability"],
    input_schema={
        "type": "object",
        "properties": {
            "tool_names": {
                "type": "array",
                "minItems": 1,
                "maxItems": AVAILABILITY_MAX_TOOLS,
                "items": {"type": "string", "minLength": 1},
            }
        },
        "required": ["tool_names"],
        "additionalProperties": False,
    },
    output_schema={
        "type": "object",
        "properties": {
            "count": {"type": "integer"},
            "requested_count": {"type": "integer"},
            "provider_probe_count": {"type": "integer"},
            "rows": {"type": "array"},
        },
        "required": ["count", "requested_count", "provider_probe_count", "rows"],
    },
)
def tool_capabilities_availability(payload: JsonObject) -> JsonObject:
    return _capability_availability_payload(payload)



def tool_lab_health() -> JsonRecord:
    """Compatibility health surface expected by lab_routes."""
    return {
        "ok": True,
        "status": "online",
        "tool_count": len(_registry_snapshot()),
        "plugin_load_count": len(_PLUGIN_LOADS),
        "plugin_error_count": len(_PLUGIN_ERRORS),
        "plugin_generation": _PLUGIN_GENERATION,
        "plugin_last_reload": _PLUGIN_LAST_RELOAD,
        "validation_mode": _tool_validation_mode(),
        "constitutional_seed": constitutional_seed(),
    }
