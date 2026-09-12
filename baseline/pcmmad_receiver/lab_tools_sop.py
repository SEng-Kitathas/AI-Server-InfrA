"""SOP/package ingestion lab-tool registration surface."""

from __future__ import annotations

from collections.abc import Callable, MutableMapping
from dataclasses import dataclass
from typing import Any

JsonObject = MutableMapping[str, Any]
SopRegistrar = Callable[..., Any]


@dataclass(frozen=True)
class SopToolDeps:
    error_cls: type[Exception]
    read_required_project_id: Callable[[JsonObject], str]
    ensure_project_layout: Callable[[JsonObject], str]
    resolve_general_path: Callable[..., Any]
    sop_call: Callable[..., JsonObject]
    sop_inspect_package: Callable[..., JsonObject]
    sop_register_package: Callable[..., JsonObject]
    sop_reset_ingestion: Callable[..., JsonObject]
    sop_ingestion_status: Callable[..., JsonObject]
    sop_next_chunk: Callable[..., JsonObject]
    sop_ack_chunk: Callable[..., JsonObject]
    sop_complete_file: Callable[..., JsonObject]
    sop_guard_check: Callable[..., JsonObject]


SOP_INSPECT_SCHEMA={"type":"object","additionalProperties":False,"required":["source_path"],"properties":{"source_path":{"type":"string","minLength":1},"project_id":{"type":"string"}}}
SOP_REGISTER_SCHEMA={"type":"object","additionalProperties":False,"required":["project_id","source_path"],"properties":{"project_id":{"type":"string","minLength":1},"source_path":{"type":"string","minLength":1},"corpus_id":{"type":"string"},"chunk_chars":{"type":"integer","minimum":1},"reset":{"type":"boolean"}}}
SOP_CORPUS_SCHEMA={"type":"object","additionalProperties":False,"required":["project_id","corpus_id"],"properties":{"project_id":{"type":"string","minLength":1},"corpus_id":{"type":"string","minLength":1}}}
SOP_ACK_SCHEMA={"type":"object","additionalProperties":False,"required":["project_id","corpus_id","ack_token"],"properties":{"project_id":{"type":"string","minLength":1},"corpus_id":{"type":"string","minLength":1},"ack_token":{"type":"string","minLength":1},"content_sha256":{"type":"string","pattern":"^[0-9a-f]{64}$"}}}
SOP_COMPLETE_SCHEMA={"type":"object","additionalProperties":False,"required":["project_id","corpus_id","receipt"],"properties":{"project_id":{"type":"string","minLength":1},"corpus_id":{"type":"string","minLength":1},"receipt":{"type":"object"}}}

def _sop_deps(deps: JsonObject) -> SopToolDeps:
    return SopToolDeps(
        error_cls=deps["error_cls"],
        read_required_project_id=deps["read_required_project_id"],
        ensure_project_layout=deps["ensure_project_layout"],
        resolve_general_path=deps["resolve_general_path"],
        sop_call=deps["sop_call"],
        sop_inspect_package=deps["sop_inspect_package"],
        sop_register_package=deps["sop_register_package"],
        sop_reset_ingestion=deps["sop_reset_ingestion"],
        sop_ingestion_status=deps["sop_ingestion_status"],
        sop_next_chunk=deps["sop_next_chunk"],
        sop_ack_chunk=deps["sop_ack_chunk"],
        sop_complete_file=deps["sop_complete_file"],
        sop_guard_check=deps["sop_guard_check"],
    )


def _required_corpus_id(payload: JsonObject, dep: SopToolDeps) -> str:
    corpus_id = str(payload.get("corpus_id", "")).strip()
    if not corpus_id:
        raise dep.error_cls("BAD_REQUEST", "corpus_id is required", 400)
    return corpus_id


def _sop_register_payload(payload: JsonObject, dep: SopToolDeps) -> JsonObject:
    project_id = dep.ensure_project_layout(payload)
    source_path = str(payload.get("source_path", "")).strip()
    if not source_path:
        raise dep.error_cls("BAD_REQUEST", "source_path is required", 400)
    return dep.sop_call(
        dep.sop_register_package,
        project_id,
        source_path,
        corpus_id=str(payload.get("corpus_id", "")).strip() or None,
        chunk_chars=int(payload.get("chunk_chars", 6000)),
        reset=bool(payload.get("reset", False)),
    )


def _sop_ack_payload(payload: JsonObject, dep: SopToolDeps) -> JsonObject:
    project_id = dep.read_required_project_id(payload)
    corpus_id = _required_corpus_id(payload, dep)
    ack_token = str(payload.get("ack_token", "")).strip()
    if not ack_token:
        raise dep.error_cls("BAD_REQUEST", "corpus_id and ack_token are required", 400)
    return dep.sop_call(
        dep.sop_ack_chunk,
        project_id,
        corpus_id,
        ack_token,
        content_sha256=str(payload.get("content_sha256", "")).strip() or None,
    )


def _sop_complete_payload(payload: JsonObject, dep: SopToolDeps) -> JsonObject:
    project_id = dep.read_required_project_id(payload)
    corpus_id = _required_corpus_id(payload, dep)
    receipt = payload.get("receipt")
    if not isinstance(receipt, dict):
        raise dep.error_cls("BAD_REQUEST", "corpus_id and receipt object are required", 400)
    return dep.sop_call(dep.sop_complete_file, project_id, corpus_id, receipt)


def _register_sop_package_tools(register_tool: SopRegistrar, dep: SopToolDeps) -> None:
    @register_tool(
        "sop.package.inspect",
        (
            "Inspect a SOP/package archive, verify manifest+ledger+merkle "
            "integrity, and derive traversal order."
        ),
        "medium",
        category="sop",
        side_effect_class="read",
        effect_traits=[
            "reads_files",
            "verifies_integrity",
            "hashes_content",
            "bounded_package_preflight",
        ],
        input_schema=SOP_INSPECT_SCHEMA,
    )
    def tool_sop_package_inspect(payload: JsonObject) -> JsonObject:
        path = dep.resolve_general_path(payload, "source_path")
        return dep.sop_call(dep.sop_inspect_package, path)

    @register_tool(
        "sop.package.register",
        "Register a SOP/package archive inside the lab and initialize chunked ingestion state.",
        "high",
        category="sop",
        approval_required=True,
        mutating=True,
        side_effect_class="mutation",
        effect_traits=[
            "durable_mutation",
            "registers_corpus",
            "verifies_integrity",
            "creates_ingestion_state",
            "project_mutation_fenced",
            "project_scope_enforced",
        ],
        input_schema=SOP_REGISTER_SCHEMA,
    )
    def tool_sop_package_register(payload: JsonObject) -> JsonObject:
        return _sop_register_payload(payload, dep)


def _register_sop_reset_tool(register_tool: SopRegistrar, dep: SopToolDeps) -> None:
    @register_tool(
        "sop.ingest.reset",
        "Reset a registered SOP/package ingestion cursor back to the beginning.",
        "high",
        category="sop",
        approval_required=True,
        mutating=True,
        side_effect_class="mutation",
        effect_traits=[
            "durable_mutation",
            "resets_ingestion_cursor",
            "clears_ingestion_progress",
            "project_mutation_fenced",
            "project_scope_enforced",
        ],
        input_schema=SOP_CORPUS_SCHEMA,
    )
    def tool_sop_ingest_reset(payload: JsonObject) -> JsonObject:
        return dep.sop_call(
            dep.sop_reset_ingestion,
            dep.ensure_project_layout(payload),
            _required_corpus_id(payload, dep),
        )


def _register_sop_status_read_tool(register_tool: SopRegistrar, dep: SopToolDeps) -> None:
    @register_tool(
        "sop.ingest.status",
        "Read SOP/package ingestion status, current file cursor, and proceed-gate readiness.",
        "low",
        category="sop",
        side_effect_class="read",
        effect_traits=["reads_state", "non_initializing"],
        input_schema=SOP_CORPUS_SCHEMA,
    )
    def tool_sop_ingest_status(payload: JsonObject) -> JsonObject:
        return dep.sop_call(
            dep.sop_ingestion_status,
            dep.read_required_project_id(payload),
            _required_corpus_id(payload, dep),
        )


def _register_sop_guard_tool(register_tool: SopRegistrar, dep: SopToolDeps) -> None:
    @register_tool(
        "sop.guard.check",
        (
            "Return whether the registered SOP/package has been fully "
            "integrity-verified and completely ingested. Use before proceeding "
            "to governed work."
        ),
        "low",
        category="sop",
        side_effect_class="read",
        effect_traits=[
            "reads_state",
            "revalidates_source_currentness",
            "verifies_integrity",
            "proceed_gate",
            "non_initializing",
        ],
        input_schema=SOP_CORPUS_SCHEMA,
    )
    def tool_sop_guard_check(payload: JsonObject) -> JsonObject:
        return dep.sop_call(
            dep.sop_guard_check,
            dep.read_required_project_id(payload),
            _required_corpus_id(payload, dep),
        )


def _register_sop_status_tools(register_tool: SopRegistrar, dep: SopToolDeps) -> None:
    _register_sop_reset_tool(register_tool, dep)
    _register_sop_status_read_tool(register_tool, dep)
    _register_sop_guard_tool(register_tool, dep)


def _register_sop_next_chunk_tool(register_tool: SopRegistrar, dep: SopToolDeps) -> None:
    @register_tool(
        "sop.ingest.next_chunk",
        (
            "Return the next required chunk from the registered SOP/package "
            "traversal order. Does not allow skipping ahead."
        ),
        "medium",
        category="sop",
        mutating=True,
        side_effect_class="ephemeral_mutation",
        effect_traits=[
            "durable_mutation",
            "issues_chunk_authority",
            "updates_ingestion_cursor_state",
            "idempotent_replay_while_unacked",
            "revalidates_source_file_hash",
            "project_mutation_fenced",
            "project_scope_enforced",
        ],
        input_schema=SOP_CORPUS_SCHEMA,
    )
    def tool_sop_ingest_next_chunk(payload: JsonObject) -> JsonObject:
        return dep.sop_call(
            dep.sop_next_chunk,
            dep.read_required_project_id(payload),
            _required_corpus_id(payload, dep),
        )


def _register_sop_ack_chunk_tool(register_tool: SopRegistrar, dep: SopToolDeps) -> None:
    @register_tool(
        "sop.ingest.ack_chunk",
        "Acknowledge the currently issued SOP/package chunk before the next chunk may be served.",
        "medium",
        category="sop",
        mutating=True,
        side_effect_class="mutation",
        effect_traits=[
            "durable_mutation",
            "advances_ingestion_cursor",
            "requires_chunk_hash_confirmation",
            "project_mutation_fenced",
            "project_scope_enforced",
        ],
        input_schema=SOP_ACK_SCHEMA,
    )
    def tool_sop_ingest_ack_chunk(payload: JsonObject) -> JsonObject:
        return _sop_ack_payload(payload, dep)


def _register_sop_complete_file_tool(register_tool: SopRegistrar, dep: SopToolDeps) -> None:
    @register_tool(
        "sop.ingest.complete_file",
        (
            "Complete the current SOP/package file by submitting a receipt "
            "that matches package metadata. This is the proceed-gate between files."
        ),
        "medium",
        category="sop",
        mutating=True,
        side_effect_class="mutation",
        effect_traits=[
            "durable_mutation",
            "records_file_completion",
            "requires_metadata_bound_receipt",
            "project_mutation_fenced",
            "project_scope_enforced",
        ],
        input_schema=SOP_COMPLETE_SCHEMA,
    )
    def tool_sop_ingest_complete_file(payload: JsonObject) -> JsonObject:
        return _sop_complete_payload(payload, dep)


def _register_sop_chunk_tools(register_tool: SopRegistrar, dep: SopToolDeps) -> None:
    _register_sop_next_chunk_tool(register_tool, dep)
    _register_sop_ack_chunk_tool(register_tool, dep)
    _register_sop_complete_file_tool(register_tool, dep)


def register_sop_tools(register_tool: SopRegistrar, **deps: Any) -> None:
    dep = _sop_deps(deps)
    _register_sop_package_tools(register_tool, dep)
    _register_sop_status_tools(register_tool, dep)
    _register_sop_chunk_tools(register_tool, dep)
