"""Native governed artifact commit capability.

The semantic core currently lives in legacy_routes.commit_artifact_transaction for
compatibility; both native and legacy adapters call that one transaction.
"""
from __future__ import annotations
from typing import Any, Callable
from project_mutation_authority import current_project_mutation_authority


def register_artifact_commit_tools(register_tool: Callable[..., Any], *, error_cls: type[Exception]) -> None:
    @register_tool(
        "project.artifact.commit",
        "Atomically commit one governed project artifact with hash currentness, idempotency recovery, manifest update, and commit-ledger append.",
        "high",
        category="project",
        approval_required=True,
        mutating=True,
        side_effect_class="mutation",
        effect_traits=[
            "durable_mutation",
            "project_mutation_fenced",
            "hash_currentness_guarded",
            "idempotent_replay",
            "updates_manifest",
            "appends_commit_ledger",
            "exact_consequence_readback",
        ],
        input_schema={
            "type":"object",
            "properties":{
                "project_id":{"type":"string","minLength":1},
                "artifact_class":{"type":"string","minLength":1},
                "logical_name":{"type":"string","minLength":1},
                "operation":{"type":"string","enum":["create","update","append"]},
                "content":{"type":"string"},
                "sha256":{"type":"string"},
                "expected_previous_sha256":{"type":"string"},
                "session_id":{"type":"string","minLength":1},
                "commit_id":{"type":"string","minLength":1},
                "idempotency_key":{"type":"string","minLength":1}
            },
            "required":["project_id","artifact_class","logical_name","operation","content","session_id","commit_id","idempotency_key"],
            "additionalProperties":False
        },
    )
    def tool_project_artifact_commit(payload):
        try:
            from legacy_routes import LegacyIdempotencyError, commit_artifact_transaction
            body = dict(payload)
            authority = current_project_mutation_authority()
            if authority is not None:
                body["mutation_authority"] = authority
            return commit_artifact_transaction(body, acquire_guard=False)
        except PermissionError as exc:
            raise error_cls("HASH_MISMATCH", str(exc), 409) from exc
        except ArithmeticError as exc:
            raise error_cls("CONTENT_HASH_INVALID", str(exc), 400) from exc
        except Exception as exc:
            if exc.__class__.__name__ == "LegacyIdempotencyError":
                raise error_cls(getattr(exc,"error_code","IDEMPOTENCY_ERROR"), getattr(exc,"message",str(exc)), getattr(exc,"status",409)) from exc
            raise error_cls("ARTIFACT_COMMIT_FAILED", str(exc), 400) from exc
