from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "baseline" / "pcmmad_receiver"
CANONICAL = RUNTIME / "pcmmad_lab_action_schema_v11_0_capability_microkernel_8.json"
OUT = RUNTIME / "pcmmad_lab_action_schema_v11_0_actions_compat_8.json"

canonical = json.loads(CANONICAL.read_text(encoding="utf-8"))
server_url = str(canonical["servers"][0]["url"])

DIGEST = {"type": "string", "description": "Current 64-character lowercase SHA-256 contract/plan digest."}
OBJECT = {"type": "object", "additionalProperties": True}
AUTHORITY = {
    "type": "object",
    "description": "Optional Runtime authority envelope. Authority is separate from arguments and is validated by the server.",
    "additionalProperties": True,
}
LEASE = {
    "type": "object",
    "description": "Capability lease returned by orient. A lease proves discovery/currentness and does not grant authority.",
    "additionalProperties": True,
}
PLAN = {
    "type": "object",
    "description": "Sealed capability plan returned by compose. Plans are authority-neutral and revalidated by execute.",
    "additionalProperties": True,
}

schemas: dict[str, dict] = {
    "OrientRequest": {
        "type": "object",
        "properties": {
            "goal": {"type": "string", "description": "Natural-language goal used only to rank live capabilities."},
            "query": {"type": "string"},
            "project_id": {"type": "string"},
            "capabilities": {"type": "array", "items": {"type": "string"}},
            "categories": {"type": "array", "items": {"type": "string"}},
            "effect_classes": {"type": "array", "items": {"type": "string"}},
            "include_mutating": {"type": "boolean"},
            "detail": {"type": "string", "enum": ["compact", "full"]},
            "max_capabilities": {"type": "integer", "minimum": 1, "maximum": 24},
            "ttl_seconds": {"type": "integer", "minimum": 10, "maximum": 900},
        },
        "additionalProperties": False,
    },
    "InvokeRequest": {
        "type": "object",
        "required": ["capability"],
        "properties": {
            "capability": {"type": "string"},
            "arguments": OBJECT,
            "authority": AUTHORITY,
            "expected_contract_digest": DIGEST,
            "lease": LEASE,
        },
        "additionalProperties": False,
    },
    "FlowBatchRequest": {
        "type": "object",
        "required": ["steps"],
        "properties": {
            "steps": {
                "type": "array",
                "maxItems": 12,
                "items": {
                    "type": "object",
                    "required": ["tool_name", "expected_contract_digest"],
                    "properties": {
                        "id": {"type": "string"},
                        "tool_name": {"type": "string"},
                        "payload": OBJECT,
                        "authority": AUTHORITY,
                        "expected_contract_digest": DIGEST,
                    },
                    "additionalProperties": False,
                },
            },
            "stop_on_error": {"type": "boolean"},
            "parallelism": {"type": "integer", "enum": [1]},
            "background": {"type": "boolean"},
            "project_id": {"type": "string"},
            "store_result": {"type": "boolean"},
            "result_handle_threshold_chars": {"type": "integer"},
            "result_label": {"type": "string"},
        },
        "additionalProperties": False,
    },
    "ComposeRequest": {
        "type": "object",
        "required": ["nodes"],
        "properties": {
            "goal": {"type": "string"},
            "project_id": {"type": "string"},
            "lease": LEASE,
            "nodes": {
                "type": "array",
                "maxItems": 32,
                "items": {
                    "type": "object",
                    "required": ["id", "capability"],
                    "properties": {
                        "id": {"type": "string"},
                        "capability": {"type": "string"},
                        "arguments": OBJECT,
                        "depends_on": {"type": "array", "items": {"type": "string"}},
                        "expected_contract_digest": DIGEST,
                        "when": OBJECT,
                    },
                    "additionalProperties": False,
                },
            },
            "assertions": {"type": "array", "items": OBJECT},
            "stop_on_error": {"type": "boolean"},
            "max_parallelism": {"type": "integer", "minimum": 1, "maximum": 16},
            "max_cost_units": {"type": "integer", "minimum": 1, "maximum": 320, "description": "Caller-declared static plan budget ceiling."},
        },
        "additionalProperties": False,
    },
    "ExecuteRequest": {
        "type": "object",
        "required": ["project_id", "plan", "expected_plan_digest"],
        "properties": {
            "project_id": {"type": "string"},
            "plan": PLAN,
            "expected_plan_digest": DIGEST,
            "authorities": {"type": "object", "additionalProperties": True},
        },
        "additionalProperties": False,
    },
    "ObserveRequest": {
        "type": "object",
        "required": ["kind"],
        "properties": {
            "kind": {"type": "string", "enum": ["lease", "plan", "capability", "effect_profile", "result", "continuation", "job"]},
            "project_id": {"type": "string"},
            "ref": {"type": "string"},
            "capability": {"type": "string"},
            "handle": {"type": "string"},
            "job_id": {"type": "string"},
            "mode": {"type": "string", "enum": ["auto", "metadata", "preview", "range", "status", "progress", "wait", "output"]},
            "lease": LEASE,
            "plan": PLAN,
            "expected_plan_digest": DIGEST,
            "timeout_seconds": {"type": "integer"},
            "max_bytes": {"type": "integer"},
            "offset_bytes": {"type": "integer"},
            "length_bytes": {"type": "integer"},
            "preview_chars": {"type": "integer"},
        },
        "additionalProperties": False,
    },
    "ResumeRequest": {
        "type": "object",
        "required": ["project_id", "continuation_handle", "resume_token"],
        "properties": {
            "project_id": {"type": "string"},
            "continuation_handle": {"type": "string"},
            "resume_token": {"type": "string"},
            "expected_plan_digest": DIGEST,
            "authorities": {"type": "object", "additionalProperties": True},
        },
        "additionalProperties": False,
    },
    "TransferRequest": {
        "type": "object",
        "required": ["action"],
        "properties": {
            "action": {"type": "string", "enum": ["export.create", "chunk.read", "import.create", "chunk.write", "import.finalize", "meta"]},
            "arguments": OBJECT,
            "authority": AUTHORITY,
        },
        "additionalProperties": False,
    },
}

operations = [
    ("/lab/vnext/orient", "orientCapabilities", "Orient to relevant live capabilities", "OrientRequest"),
    ("/lab/vnext/invoke", "invokeCapability", "Invoke one current native capability", "InvokeRequest"),
    ("/lab/batch", "flowCapabilities", "Run a bounded sequential native capability flow", "FlowBatchRequest"),
    ("/lab/vnext/compose", "composePlan", "Compose and seal a bounded capability plan", "ComposeRequest"),
    ("/lab/vnext/execute", "executePlan", "Execute a sealed plan with separate authority", "ExecuteRequest"),
    ("/lab/vnext/observe", "observeRuntime", "Observe a bounded Runtime object", "ObserveRequest"),
    ("/lab/vnext/resume", "resumeContinuation", "Resume a single-use blocked continuation", "ResumeRequest"),
    ("/lab/vnext/transfer", "transferData", "Move binary or file data through transfer tickets", "TransferRequest"),
]

paths: dict[str, dict] = {}
for path, operation_id, summary, request_name in operations:
    paths[path] = {
        "post": {
            "operationId": operation_id,
            "summary": summary,
            "requestBody": {
                "required": True,
                "content": {"application/json": {"schema": schemas[request_name]}},
            },
            "responses": {
                "200": {"description": "Successful bounded Runtime response", "content": {"application/json": {"schema": OBJECT}}},
                "400": {"description": "Malformed or invalid request"},
                "401": {"description": "Authentication required"},
                "403": {"description": "Authority or approval required"},
                "404": {"description": "Runtime object not found"},
                "409": {"description": "Currentness, plan, lease, or continuation conflict"},
            },
        }
    }

schema = {
    "openapi": "3.0.3",
    "info": {
        "title": "PCMMAD Laboratory Runtime Actions",
        "version": "11.0.0-actions-compat",
        "description": "Importer-conservative eight-operation Custom GPT Actions projection. The server-side canonical v11 schema remains authoritative for validation and currentness.",
    },
    "servers": [{"url": server_url}],
    "security": [{"ApiKeyAuth": []}],
    "paths": paths,
    "components": {
        "securitySchemes": {
            "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-GitHome-Key"}
        }
    },
}

OUT.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"path": str(OUT), "operations": len(operations), "bytes": OUT.stat().st_size}, indent=2))
