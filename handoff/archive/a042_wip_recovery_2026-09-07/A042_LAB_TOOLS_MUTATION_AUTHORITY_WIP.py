"""Project mutation lease/fence projection and composition helpers."""

from __future__ import annotations

from collections.abc import Callable, Mapping, MutableMapping
from contextlib import contextmanager
from typing import Any, Iterator, TypeAlias

from project_mutation_authority import (
    ProjectMutationAuthorityError,
    acquire_lease,
    consequence_guard,
    inspect_lease,
    release_lease,
    renew_lease,
)

JsonObject: TypeAlias = MutableMapping[str, Any]
ToolPayload: TypeAlias = JsonObject
ToolResult: TypeAlias = JsonObject
MutationRegistrar = Callable[..., Any]


def _str(payload: Mapping[str, Any], key: str, default: str = "") -> str:
    value = payload.get(key, default)
    return default if value is None else str(value).strip()


def _int(payload: Mapping[str, Any], key: str, *, minimum: int | None = None) -> int:
    try:
        value = int(payload.get(key))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{key} must be an integer") from exc
    if minimum is not None and value < minimum:
        raise ValueError(f"{key} must be >= {minimum}")
    return value


def mutation_authority_schema() -> dict[str, object]:
    """Schema for authority carried by a consequence-bearing project mutation."""
    return {
        "type": "object",
        "properties": {
            "lease_id": {"type": "string", "minLength": 1},
            "generation": {"type": "integer", "minimum": 1},
            "owner_id": {"type": "string", "minLength": 1},
            "session_id": {"type": "string"},
        },
        "required": ["lease_id", "generation", "owner_id"],
        "additionalProperties": False,
    }


def mutation_authority_property() -> dict[str, object]:
    return {"mutation_authority": mutation_authority_schema()}


def _raise_as(error_cls: type[Exception], exc: ProjectMutationAuthorityError) -> None:
    raise error_cls(exc.error_code, exc.message, exc.status, **exc.extra) from exc


_AUTHORITY_UNSET = object()


@contextmanager
def project_mutation_scope(
    payload: Mapping[str, Any],
    error_cls: type[Exception],
    *,
    project_id: str | None = None,
    mutation_authority: object = _AUTHORITY_UNSET,
) -> Iterator[dict[str, Any] | None]:
    """Translate the core consequence guard into the native tool error contract.

    Canonical native dispatch carries project mutation authority in its authority
    envelope.  Embedded `mutation_authority` remains a transitional compatibility form
    for direct/internal callers that do not yet have the separate authority plane.
    """
    pid = str(project_id or payload.get("project_id") or "").strip()
    if not pid:
        raise error_cls("BAD_REQUEST", "project_id is required", 400)
    raw = (
        payload.get("mutation_authority")
        if mutation_authority is _AUTHORITY_UNSET
        else mutation_authority
    )
    try:
        with consequence_guard(
            pid,
            mutation_authority=raw if raw is not None else None,
            session_id=_str(payload, "session_id"),
        ) as receipt:
            yield receipt
    except ProjectMutationAuthorityError as exc:
        _raise_as(error_cls, exc)


def _lease_output_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "project_id": {"type": "string"},
            "status": {"type": "string"},
            "generation": {"type": "integer", "minimum": 0},
            "lease_id": {"type": ["string", "null"]},
            "owner_id": {"type": ["string", "null"]},
            "session_id": {"type": ["string", "null"]},
            "client_id": {"type": ["string", "null"]},
            "issued_at": {"type": ["string", "null"]},
            "renewed_at": {"type": ["string", "null"]},
            "expires_at": {"type": ["string", "null"]},
            "released_at": {"type": ["string", "null"]},
            "provenance": {"type": ["string", "null"]},
        },
        "required": ["project_id", "status", "generation"],
        "additionalProperties": True,
    }


def _schema(required: list[str], properties: Mapping[str, object]) -> dict[str, object]:
    return {
        "type": "object",
        "properties": dict(properties),
        "required": required,
        "additionalProperties": False,
    }


def register_mutation_authority_tools(
    register_tool: MutationRegistrar,
    *,
    error_cls: type[Exception],
) -> None:
    project = {"project_id": {"type": "string", "minLength": 1}}
    common = {
        **project,
        "lease_id": {"type": "string", "minLength": 1},
        "generation": {"type": "integer", "minimum": 1},
        "owner_id": {"type": "string", "minLength": 1},
        "session_id": {"type": "string"},
        "client_id": {"type": "string"},
        "ttl_seconds": {"type": "integer", "minimum": 10, "maximum": 900},
        "provenance": {"type": "string"},
    }
    output_schema = _lease_output_schema()

    def translate(fn: Callable[[], ToolResult]) -> ToolResult:
        try:
            return fn()
        except ProjectMutationAuthorityError as exc:
            _raise_as(error_cls, exc)
        except ValueError as exc:
            raise error_cls("BAD_REQUEST", str(exc), 400) from exc

    @register_tool(
        "project.mutation.inspect",
        "Inspect current project mutation lease/generation authority; expiry may be reconciled.",
        "medium",
        category="project",
        tags=["project", "authority", "lease", "generation", "currentness"],
        mutating=True,
        side_effect_class="reconcile",
        effect_traits=[
            "reads_project_authority",
            "may_reconcile_expiry",
            "project_scope_enforced",
            "bounded_output",
        ],
        input_schema=_schema(["project_id"], project),
        output_schema=output_schema,
    )
    def tool_project_mutation_inspect(payload: ToolPayload) -> ToolResult:
        project_id = _str(payload, "project_id")
        return translate(lambda: inspect_lease(project_id))

    @register_tool(
        "project.mutation.acquire",
        "Acquire the next fenced project mutation generation for one owner/client campaign.",
        "high",
        category="project",
        tags=["project", "authority", "lease", "generation", "fence"],
        mutating=True,
        side_effect_class="authority_mutation",
        effect_traits=[
            "durable_mutation",
            "mutates_project_authority",
            "cross_process_exclusion",
            "generation_fence",
            "bounded_ttl",
        ],
        input_schema=_schema(
            ["project_id", "expected_generation", "owner_id"],
            {
                **common,
                "expected_generation": {"type": "integer", "minimum": 0},
            },
        ),
        output_schema=output_schema,
    )
    def tool_project_mutation_acquire(payload: ToolPayload) -> ToolResult:
        return translate(
            lambda: acquire_lease(
                _str(payload, "project_id"),
                expected_generation=_int(payload, "expected_generation", minimum=0),
                owner_id=_str(payload, "owner_id"),
                session_id=_str(payload, "session_id"),
                client_id=_str(payload, "client_id"),
                ttl_seconds=(
                    _int(payload, "ttl_seconds", minimum=1)
                    if payload.get("ttl_seconds") not in (None, "")
                    else None
                ),
                provenance=_str(payload, "provenance"),
            )
        )

    @register_tool(
        "project.mutation.renew",
        "Renew a currently active fenced project mutation lease.",
        "high",
        category="project",
        tags=["project", "authority", "lease", "renewal"],
        mutating=True,
        side_effect_class="authority_mutation",
        effect_traits=[
            "durable_mutation",
            "mutates_project_authority",
            "requires_current_generation",
            "bounded_ttl",
        ],
        input_schema=_schema(
            ["project_id", "lease_id", "generation", "owner_id"], common
        ),
        output_schema=output_schema,
    )
    def tool_project_mutation_renew(payload: ToolPayload) -> ToolResult:
        return translate(
            lambda: renew_lease(
                _str(payload, "project_id"),
                lease_id=_str(payload, "lease_id"),
                generation=_int(payload, "generation", minimum=1),
                owner_id=_str(payload, "owner_id"),
                session_id=_str(payload, "session_id"),
                ttl_seconds=(
                    _int(payload, "ttl_seconds", minimum=1)
                    if payload.get("ttl_seconds") not in (None, "")
                    else None
                ),
            )
        )

    @register_tool(
        "project.mutation.release",
        "Release a currently active fenced project mutation lease without rewinding generation.",
        "high",
        category="project",
        tags=["project", "authority", "lease", "release", "fence"],
        mutating=True,
        side_effect_class="authority_mutation",
        effect_traits=[
            "durable_mutation",
            "mutates_project_authority",
            "requires_current_generation",
            "generation_monotonic",
        ],
        input_schema=_schema(
            ["project_id", "lease_id", "generation", "owner_id"], common
        ),
        output_schema=output_schema,
    )
    def tool_project_mutation_release(payload: ToolPayload) -> ToolResult:
        return translate(
            lambda: release_lease(
                _str(payload, "project_id"),
                lease_id=_str(payload, "lease_id"),
                generation=_int(payload, "generation", minimum=1),
                owner_id=_str(payload, "owner_id"),
                session_id=_str(payload, "session_id"),
            )
        )
