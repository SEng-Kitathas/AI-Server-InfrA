"""Lab state, session, reflexion, and recovery tool registration surface."""

from __future__ import annotations
from collections.abc import MutableMapping


from dataclasses import dataclass
from typing import Any, Callable, TypeAlias

from .project_mutation_authority import (
    ProjectMutationAuthorityError,
    consequence_guard,
    current_project_mutation_authority,
    validate_consequence_authority,
)
from .server_hardening import run_subprocess_envelope

JsonObject = MutableMapping[str, Any]

ToolPayload: TypeAlias = JsonObject
ToolResult: TypeAlias = JsonObject


def _required_project(error_cls: type[Exception], payload: ToolPayload) -> str:
    project_id = str(payload.get("project_id", "")).strip()
    if not project_id:
        raise error_cls("BAD_REQUEST", "project_id is required", 400)
    return project_id


def _get_str(payload: ToolPayload, key: str, default: str = "") -> str:
    value = payload.get(key, default)
    return default if value is None else str(value)


def _get_bool(payload: ToolPayload, key: str, default: bool = False) -> bool:
    value = payload.get(key, default)
    return value if isinstance(value, bool) else bool(value)


def _get_list(payload: ToolPayload, key: str) -> list[Any]:
    value = payload.get(key)
    return value if isinstance(value, list) else []


def _get_dict(payload: ToolPayload, key: str) -> JsonObject:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def _get_int(payload: ToolPayload, key: str, default: int) -> int:
    try:
        return int(payload.get(key, default))
    except (TypeError, ValueError, OverflowError):
        return default


def _is_ok(payload: ToolPayload) -> bool:
    return _get_bool(payload, "ok", False)


@dataclass(frozen=True)
class LabHealthRequest:
    browser_timeout_seconds: int

    @classmethod
    def from_payload(cls, payload: ToolPayload) -> "LabHealthRequest":
        return cls(
            browser_timeout_seconds=max(1, min(_get_int(payload, "browser_timeout_seconds", 3), 15))
        )


@dataclass(frozen=True)
class SessionStartRequest:
    project_id: str
    title: str
    meta: JsonObject

    @classmethod
    def from_payload(
        cls, ensure_project_layout: Callable[[ToolPayload], str], payload: ToolPayload
    ) -> "SessionStartRequest":
        return cls(
            project_id=ensure_project_layout(payload),
            title=_get_str(payload, "title"),
            meta=_get_dict(payload, "meta"),
        )


@dataclass(frozen=True)
class SessionEndRequest:
    ref: SessionRef
    status: str

    @classmethod
    def from_payload(cls, error_cls: type[Exception], payload: ToolPayload) -> "SessionEndRequest":
        return cls(
            ref=SessionRef.from_payload(error_cls, payload),
            status=_get_str(payload, "status", "closed").strip() or "closed",
        )


@dataclass(frozen=True)
class ApoptosisTriggerRequest:
    project_id: str
    session_id: str
    terminate_running_jobs: bool
    git_reset_hard: bool
    git_clean_fd: bool
    reason: str

    @classmethod
    def from_payload(
        cls, error_cls: type[Exception], payload: ToolPayload
    ) -> "ApoptosisTriggerRequest":
        return cls(
            project_id=_required_project(error_cls, payload),
            session_id=_get_str(payload, "session_id").strip(),
            terminate_running_jobs=_get_bool(payload, "terminate_running_jobs", True),
            git_reset_hard=_get_bool(payload, "git_reset_hard", False),
            git_clean_fd=_get_bool(payload, "git_clean_fd", False),
            reason=_get_str(payload, "reason", "manual trigger"),
        )


@dataclass(frozen=True)
class SessionRef:
    project_id: str
    session_id: str

    @classmethod
    def from_payload(cls, error_cls: type[Exception], payload: ToolPayload) -> "SessionRef":
        project_id = _required_project(error_cls, payload)
        session_id = _get_str(payload, "session_id").strip()
        if not session_id:
            raise error_cls("BAD_REQUEST", "session_id is required", 400)
        return cls(project_id=project_id, session_id=session_id)


@dataclass(frozen=True)
class SessionNoteRequest:
    ref: SessionRef
    note: str
    note_type: str

    @classmethod
    def from_payload(cls, error_cls: type[Exception], payload: ToolPayload) -> "SessionNoteRequest":
        ref = SessionRef.from_payload(error_cls, payload)
        note = _get_str(payload, "note").strip()
        if not note:
            raise error_cls("BAD_REQUEST", "note is required", 400)
        note_type = _get_str(payload, "note_type", "note").strip() or "note"
        return cls(ref=ref, note=note, note_type=note_type)


@dataclass(frozen=True)
class ReflexionAppendRequest:
    project_id: str
    session_id: str
    title: str
    content: str
    tags: list[str]

    @classmethod
    def from_payload(
        cls, error_cls: type[Exception], payload: ToolPayload
    ) -> "ReflexionAppendRequest":
        project_id = _required_project(error_cls, payload)
        title = _get_str(payload, "title").strip()
        content = _get_str(payload, "content").strip()
        if not title or not content:
            raise error_cls("BAD_REQUEST", "title and content are required", 400)
        return cls(
            project_id=project_id,
            session_id=_get_str(payload, "session_id").strip(),
            title=title,
            content=content,
            tags=[str(item) for item in _get_list(payload, "tags")],
        )


@dataclass(frozen=True)
class ReflexionReadRequest:
    project_id: str
    limit: int

    @classmethod
    def from_payload(
        cls, error_cls: type[Exception], payload: ToolPayload
    ) -> "ReflexionReadRequest":
        project_id = _required_project(error_cls, payload)
        return cls(project_id=project_id, limit=max(1, min(_get_int(payload, "limit", 50), 500)))


@dataclass(frozen=True)
class BridgeStatus:
    ok: bool
    error_code: str | None = None
    message: str | None = None
    status: int | None = None

    @classmethod
    def from_result(cls, payload: ToolPayload) -> "BridgeStatus":
        return cls(
            ok=_get_bool(payload, "ok", False),
            error_code=_get_str(payload, "error_code") or None,
            message=_get_str(payload, "message") or None,
            status=_get_int(payload, "status", 0) or None,
        )

    @classmethod
    def from_exception(cls, exc: Exception) -> "BridgeStatus":
        return cls(
            ok=False,
            error_code=getattr(exc, "error_code", exc.__class__.__name__),
            message=getattr(exc, "message", str(exc)),
            status=getattr(exc, "status", 500),
        )

    def to_dict(self) -> ToolResult:
        data: ToolResult = {"ok": self.ok}
        if self.error_code is not None:
            data["error_code"] = self.error_code
        if self.message is not None:
            data["message"] = self.message
        if self.status is not None:
            data["status"] = self.status
        return data


@dataclass(frozen=True)
class AndonPullRequest:
    project_id: str
    session_id: str
    reason: str
    details: str

    @classmethod
    def from_payload(cls, error_cls: type[Exception], payload: ToolPayload) -> "AndonPullRequest":
        project_id = _required_project(error_cls, payload)
        reason = _get_str(payload, "reason").strip()
        if not reason:
            raise error_cls("BAD_REQUEST", "reason is required", 400)
        return cls(
            project_id=project_id,
            session_id=_get_str(payload, "session_id").strip(),
            reason=reason,
            details=_get_str(payload, "details").strip(),
        )


@dataclass(frozen=True)
class StateToolDeps:
    error_cls: type[Exception]
    tool_router_validation_state: Callable[[], Any]
    policy_mode: Callable[[], str]
    plugin_loads: list[Any]
    plugin_errors: list[Any]
    beautiful_soup: Any
    bridge_call: Callable[..., ToolResult]
    enabled_sources: set[str]
    enabled_hunt_modes: set[str]
    parser_version: str
    get_cache_stats: Callable[[], ToolResult]
    get_index_cache_stats: Callable[[], ToolResult]
    execution_modes: set[str]
    tool_registry: ToolResult
    load_plugins: Callable[[], ToolResult | None]
    plugin_runtime_state: Callable[[], ToolResult]
    ensure_project_layout: Callable[[ToolPayload], str]
    running_jobs: ToolResult
    get_project_root: Callable[[str], Any]
    append_reflexion: Callable[..., Any]
    append_session_note: Callable[..., Any]
    end_session: Callable[..., Any]
    get_session: Callable[..., Any]
    pull_andon: Callable[..., Any]
    read_reflexion: Callable[..., list[Any]]
    start_session: Callable[..., Any]
    utc_now: Callable[[], str]


def _state_deps(deps: ToolPayload) -> StateToolDeps:
    return StateToolDeps(
        error_cls=deps["error_cls"],
        tool_router_validation_state=deps["tool_router_validation_state"],
        policy_mode=deps["policy_mode"],
        plugin_loads=deps["plugin_loads"],
        plugin_errors=deps["plugin_errors"],
        beautiful_soup=deps["beautiful_soup"],
        bridge_call=deps["bridge_call"],
        enabled_sources=deps["enabled_sources"],
        enabled_hunt_modes=deps["enabled_hunt_modes"],
        parser_version=deps["parser_version"],
        get_cache_stats=deps["get_cache_stats"],
        get_index_cache_stats=deps["get_index_cache_stats"],
        execution_modes=deps["execution_modes"],
        tool_registry=deps["tool_registry"],
        load_plugins=deps["load_plugins"],
        plugin_runtime_state=deps["plugin_runtime_state"],
        ensure_project_layout=deps["ensure_project_layout"],
        running_jobs=deps["running_jobs"],
        get_project_root=deps["get_project_root"],
        append_reflexion=deps["append_reflexion"],
        append_session_note=deps["append_session_note"],
        end_session=deps["end_session"],
        get_session=deps["get_session"],
        pull_andon=deps["pull_andon"],
        read_reflexion=deps["read_reflexion"],
        start_session=deps["start_session"],
        utc_now=deps["utc_now"],
    )


def _plugin_load_records(dep: StateToolDeps) -> list[Any]:
    return [item.to_dict() if hasattr(item, "to_dict") else item for item in dep.plugin_loads]


def _plugin_runtime_payload(dep: StateToolDeps) -> ToolResult:
    provider = getattr(dep, "plugin_runtime_state", None)
    if callable(provider):
        value = provider()
        return value if isinstance(value, dict) else {}
    # Backward-compatible projection for older dependency fixtures/adapters.
    return {
        "generation": None,
        "plugin_tool_count": None,
        "plugin_load_count": len(getattr(dep, "plugin_loads", []) or []),
        "plugin_error_count": len(getattr(dep, "plugin_errors", []) or []),
        "contract_digest": None,
        "last_reload": None,
    }


def _lab_health_status(dep: StateToolDeps, browser_status: BridgeStatus) -> str:
    if dep.plugin_errors or not browser_status.ok or dep.beautiful_soup is None:
        return "degraded"
    return "online"


def _browser_bridge_status(dep: StateToolDeps, request: LabHealthRequest) -> BridgeStatus:
    try:
        return BridgeStatus.from_result(
            dep.bridge_call("GET", "/health", None, request.browser_timeout_seconds)
        )
    except (dep.error_cls, OSError, RuntimeError, ValueError, TypeError) as exc:
        return BridgeStatus.from_exception(exc)


def _lab_health_payload(payload: ToolPayload, dep: StateToolDeps) -> ToolResult:
    request = LabHealthRequest.from_payload(payload)
    browser_status = _browser_bridge_status(dep, request)
    return {
        "status": _lab_health_status(dep, browser_status),
        "policy_mode": dep.policy_mode(),
        "validation": dep.tool_router_validation_state().to_dict(),
        "tools": len(dep.tool_registry),
        "plugin_loads": _plugin_load_records(dep),
        "plugin_errors": dep.plugin_errors,
        "plugin_runtime": _plugin_runtime_payload(dep),
        "dependencies": {"beautifulsoup4": dep.beautiful_soup is not None},
        "browser_bridge": browser_status.to_dict(),
        "research": {
            "sources": dep.enabled_sources,
            "modes": dep.enabled_hunt_modes,
            "parser_version": dep.parser_version,
            "cache": dep.get_cache_stats(),
        },
        "context_index_cache": dep.get_index_cache_stats(),
        "execution_modes": sorted(dep.execution_modes),
    }


def _lab_tools_reload_payload(dep: StateToolDeps) -> ToolResult:
    before = len(dep.tool_registry)
    reload_receipt = dep.load_plugins()
    return {
        "tool_count": len(dep.tool_registry),
        "tool_count_before": before,
        "plugin_loads": _plugin_load_records(dep),
        "plugin_errors": dep.plugin_errors,
        "plugin_runtime": _plugin_runtime_payload(dep),
        "reload": reload_receipt,
    }


def _register_state_health_tools(register_tool: Callable[..., Any], dep: StateToolDeps) -> None:
    @register_tool(
        "lab.health",
        "Return internal lab subsystem status and registry metadata.",
        "low",
        category="lab",
        side_effect_class="read_probe",
        effect_traits=["reads_runtime_state", "reads_plugin_state", "reads_cache_state", "network_io", "probes_browser_bridge", "bounded_wait"],
    )
    def tool_lab_health(payload: ToolPayload) -> ToolResult:
        return _lab_health_payload(payload, dep)

    @register_tool(
        "lab.tools.reload",
        "Reload tool plugins from the lab_plugins directory.",
        "medium",
        category="lab",
        approval_required=True,
        mutating=True,
        side_effect_class="runtime_mutation",
        effect_traits=["mutates_registry", "loads_code", "changes_capability_surface"],
    )
    def tool_lab_tools_reload(payload: ToolPayload) -> ToolResult:
        return _lab_tools_reload_payload(dep)


def _session_start_payload(payload: ToolPayload, dep: StateToolDeps) -> ToolResult:
    request = SessionStartRequest.from_payload(dep.ensure_project_layout, payload)
    return dep.start_session(request.project_id, title=request.title, meta=request.meta).to_dict()


def _session_get_payload(payload: ToolPayload, dep: StateToolDeps) -> ToolResult:
    ref = SessionRef.from_payload(dep.error_cls, payload)
    try:
        return dep.get_session(ref.project_id, ref.session_id).to_dict()
    except FileNotFoundError:
        raise dep.error_cls("NOT_FOUND", "session not found", 404)


def _session_note_payload(payload: ToolPayload, dep: StateToolDeps) -> ToolResult:
    request = SessionNoteRequest.from_payload(dep.error_cls, payload)
    return dep.append_session_note(
        request.ref.project_id,
        request.ref.session_id,
        request.note,
        note_type=request.note_type,
    ).to_dict()


def _session_end_payload(payload: ToolPayload, dep: StateToolDeps) -> ToolResult:
    request = SessionEndRequest.from_payload(dep.error_cls, payload)
    return dep.end_session(
        request.ref.project_id, request.ref.session_id, status=request.status
    ).to_dict()


def _register_session_start_tool(register_tool: Callable[..., Any], dep: StateToolDeps) -> None:
    @register_tool(
        "lab.session.start",
        "Start a lab session record for a project.",
        "low",
        category="lab",
        mutating=True,
        side_effect_class="mutation",
        effect_traits=["durable_mutation", "project_mutation_fenced", "project_scope_enforced"],
    )
    def tool_lab_session_start(payload: ToolPayload) -> ToolResult:
        return _session_start_payload(payload, dep)


def _register_session_read_tool(register_tool: Callable[..., Any], dep: StateToolDeps) -> None:
    @register_tool("lab.session.get", "Read a lab session record.", "low", category="lab", side_effect_class="read", effect_traits=["reads_project_state", "reads_persistent_state"])
    def tool_lab_session_get(payload: ToolPayload) -> ToolResult:
        return _session_get_payload(payload, dep)


def _register_session_note_tool(register_tool: Callable[..., Any], dep: StateToolDeps) -> None:
    @register_tool(
        "lab.session.note",
        "Append a note to a lab session.",
        "medium",
        category="lab",
        mutating=True,
        side_effect_class="mutation",
        effect_traits=["durable_mutation", "project_mutation_fenced", "project_scope_enforced"],
    )
    def tool_lab_session_note(payload: ToolPayload) -> ToolResult:
        return _session_note_payload(payload, dep)


def _register_session_end_tool(register_tool: Callable[..., Any], dep: StateToolDeps) -> None:
    @register_tool(
        "lab.session.end",
        "Close or otherwise mark the state of a lab session.",
        "medium",
        category="lab",
        mutating=True,
        side_effect_class="mutation",
        effect_traits=["durable_mutation", "project_mutation_fenced", "project_scope_enforced"],
    )
    def tool_lab_session_end(payload: ToolPayload) -> ToolResult:
        return _session_end_payload(payload, dep)


def _register_session_tools(register_tool: Callable[..., Any], dep: StateToolDeps) -> None:
    _register_session_start_tool(register_tool, dep)
    _register_session_read_tool(register_tool, dep)
    _register_session_note_tool(register_tool, dep)
    _register_session_end_tool(register_tool, dep)


def _andon_payload(payload: ToolPayload, dep: StateToolDeps) -> ToolResult:
    request = AndonPullRequest.from_payload(dep.error_cls, payload)
    return dep.pull_andon(
        request.project_id,
        {"session_id": request.session_id, "reason": request.reason, "details": request.details},
    ).to_dict()


def _reflexion_append_payload(payload: ToolPayload, dep: StateToolDeps) -> ToolResult:
    request = ReflexionAppendRequest.from_payload(dep.error_cls, payload)
    return dep.append_reflexion(
        request.project_id,
        {
            "session_id": request.session_id,
            "title": request.title,
            "content": request.content,
            "tags": request.tags,
        },
    ).to_dict()


def _reflexion_read_payload(payload: ToolPayload, dep: StateToolDeps) -> ToolResult:
    request = ReflexionReadRequest.from_payload(dep.error_cls, payload)
    rows = dep.read_reflexion(request.project_id, limit=request.limit)
    return {
        "project_id": request.project_id,
        "count": len(rows),
        "entries": [row.to_dict() for row in rows],
    }


def _register_reflexion_tools(register_tool: Callable[..., Any], dep: StateToolDeps) -> None:
    @register_tool(
        "lab.andon.pull",
        "Record an andon event and pause the session.",
        "medium",
        category="lab",
        mutating=True,
        side_effect_class="mutation",
        effect_traits=["durable_mutation", "project_mutation_fenced", "project_scope_enforced"],
    )
    def tool_lab_andon_pull(payload: ToolPayload) -> ToolResult:
        return _andon_payload(payload, dep)

    @register_tool(
        "lab.reflexion.append",
        "Append a lessons-learned/reflexion record.",
        "medium",
        category="lab",
        mutating=True,
        side_effect_class="mutation",
        effect_traits=["durable_mutation", "project_mutation_fenced", "project_scope_enforced"],
    )
    def tool_lab_reflexion_append(payload: ToolPayload) -> ToolResult:
        return _reflexion_append_payload(payload, dep)

    @register_tool("lab.reflexion.read", "Read recent reflexion entries.", "low", category="lab", side_effect_class="read", effect_traits=["reads_project_state", "reads_persistent_state", "bounded_results"])
    def tool_lab_reflexion_read(payload: ToolPayload) -> ToolResult:
        return _reflexion_read_payload(payload, dep)


def _terminate_running_jobs(dep: StateToolDeps) -> list[str]:
    terminated: list[str] = []
    for job_id, proc in list(dep.running_jobs.items()):
        try:
            proc.kill()
            terminated.append(job_id)
        except (OSError, RuntimeError, ValueError):
            terminated.append(f"{job_id}:kill_failed")
        finally:
            dep.running_jobs.pop(job_id, None)
    return terminated


def _apoptosis_git_actions(request: ApoptosisTriggerRequest, dep: StateToolDeps) -> list[str]:
    actions: list[str] = []
    root = dep.get_project_root(request.project_id)
    if request.git_reset_hard:
        reset_result = run_subprocess_envelope(
            ["git", "reset", "--hard", "HEAD"],
            cwd=root,
            timeout_seconds=None,
            stdout_max_bytes=None,
            stderr_max_bytes=None,
        )
        actions.append("git_reset_hard" if reset_result.get("ok") else "git_reset_hard_failed")
    if request.git_clean_fd:
        clean_result = run_subprocess_envelope(
            ["git", "clean", "-fd"],
            cwd=root,
            timeout_seconds=None,
            stdout_max_bytes=None,
            stderr_max_bytes=None,
        )
        actions.append("git_clean_fd" if clean_result.get("ok") else "git_clean_fd_failed")
    return actions


def _end_apoptosis_session(
    request: ApoptosisTriggerRequest, payload: ToolPayload, dep: StateToolDeps, actions: list[str]
) -> None:
    session_id = _get_str(payload, "session_id").strip()
    if not session_id:
        return
    try:
        dep.end_session(request.project_id, session_id, status="apoptosis")
    except (OSError, RuntimeError, ValueError, TypeError):
        actions.append("session_end_failed")


def _apoptosis_payload(payload: ToolPayload, dep: StateToolDeps) -> ToolResult:
    request = ApoptosisTriggerRequest.from_payload(dep.error_cls, payload)
    authority = current_project_mutation_authority()
    session_id = _get_str(payload, "session_id").strip()
    try:
        validate_consequence_authority(
            request.project_id, mutation_authority=authority, session_id=session_id
        )
    except ProjectMutationAuthorityError as exc:
        raise dep.error_cls(exc.error_code, exc.message, exc.status, **exc.extra) from exc

    actions: list[str] = []
    terminated: list[str] = []
    if request.terminate_running_jobs:
        terminated = _terminate_running_jobs(dep)
        actions.append("terminate_running_jobs")

    try:
        with consequence_guard(
            request.project_id,
            mutation_authority=authority,
            session_id=session_id,
        ):
            actions.extend(_apoptosis_git_actions(request, dep))
            _end_apoptosis_session(request, payload, dep, actions)
            dep.append_reflexion(
                request.project_id,
                {
                    "title": "software_apoptosis",
                    "content": request.reason,
                    "tags": ["apoptosis", "recovery"],
                },
            )
    except ProjectMutationAuthorityError as exc:
        raise dep.error_cls(exc.error_code, exc.message, exc.status, **exc.extra) from exc
    return {
        "project_id": request.project_id,
        "actions": actions,
        "terminated_jobs": terminated,
        "time": dep.utc_now(),
    }


def _register_apoptosis_tool(register_tool: Callable[..., Any], dep: StateToolDeps) -> None:
    @register_tool(
        "lab.apoptosis.trigger",
        "Terminate jobs and optionally hard-reset repo state after repeated failure.",
        "critical",
        category="lab",
        approval_required=True,
        mutating=True,
        side_effect_class="mutation",
        effect_traits=[
            "durable_mutation",
            "two_phase_project_mutation_fenced",
            "requires_explicit_project_mutation_authority_when_leased",
            "terminates_processes_before_project_consequence",
        ],
    )
    def tool_lab_apoptosis_trigger(payload: ToolPayload) -> ToolResult:
        return _apoptosis_payload(payload, dep)


def register_state_tools(
    register_tool: (
        Callable[
            ...,
            Callable[[Callable[[ToolPayload], ToolResult]], Callable[[ToolPayload], ToolResult]],
        ]
        | Callable[..., Any]
    ),
    **deps: Any,
) -> None:
    dep = _state_deps(deps)
    _register_state_health_tools(register_tool, dep)
    _register_session_tools(register_tool, dep)
    _register_reflexion_tools(register_tool, dep)
    _register_apoptosis_tool(register_tool, dep)
