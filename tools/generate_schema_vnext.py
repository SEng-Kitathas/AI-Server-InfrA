from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "baseline" / "pcmmad_receiver"
OLD = RUNTIME / "pcmmad_lab_action_schema_v10_3_pcmmad_native_protocol_compact_30_router.json"
OUT = RUNTIME / "pcmmad_lab_action_schema_v11_0_capability_microkernel_8.json"

old = json.loads(OLD.read_text(encoding="utf-8"))
authority = old["components"]["schemas"]["RuntimeAuthorityEnvelope"]
project_mutation_authority = old["components"]["schemas"]["ProjectMutationAuthority"]

OBJ = {"type": "object", "additionalProperties": True}
DIGEST = {"type": "string", "pattern": "^[0-9a-f]{64}$"}

lease = {
    "type": "object",
    "required": ["schema", "authority_effect", "law", "expires_at_epoch", "selected", "lease_digest"],
    "properties": {
        "schema": {"type": "string", "enum": ["pcmmad.capability-lease.v1"]},
        "authority_effect": {"type": "string", "enum": ["NONE"]},
        "law": {"type": "string", "enum": ["CAPABILITY_LEASE != CAPABILITY_GRANT"]},
        "project_id": {"type": "string", "nullable": True},
        "issued_at": {"type": "string"},
        "issued_at_epoch": {"type": "number"},
        "expires_at_epoch": {"type": "number"},
        "ttl_seconds": {"type": "integer", "minimum": 10, "maximum": 900},
        "goal_digest": DIGEST,
        "catalog_digest_at_issue": DIGEST,
        "selected": {
            "type": "array",
            "minItems": 1,
            "maxItems": 24,
            "items": {
                "type": "object",
                "required": ["name", "contract_digest"],
                "properties": {"name": {"type": "string"}, "contract_digest": DIGEST},
                "additionalProperties": False,
            },
        },
        "lease_digest": DIGEST,
    },
    "additionalProperties": False,
}

plan_node = {
    "type": "object",
    "required": ["id", "capability"],
    "properties": {
        "id": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_.-]{0,63}$"},
        "capability": {"type": "string", "minLength": 1},
        "arguments": OBJ,
        "depends_on": {"type": "array", "items": {"type": "string"}, "maxItems": 32},
        "expected_contract_digest": DIGEST,
        "when": {
            "type": "object",
            "required": ["ref"],
            "properties": {
                "ref": {"type": "string", "description": "Reference like inspect.result.clean"},
                "equals": {},
                "not_equals": {},
                "exists": {"type": "boolean"},
                "truthy": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,
}

assertion = {
    "type": "object",
    "required": ["ref"],
    "properties": {
        "ref": {"type": "string"},
        "op": {"type": "string", "enum": ["eq", "ne", "in", "truthy", "falsey", "exists"], "default": "eq"},
        "value": {},
    },
    "additionalProperties": False,
}

plan = {
    "type": "object",
    "required": ["schema", "authority_effect", "nodes", "stages", "assertions", "stop_on_error", "max_parallelism", "static_cost_units", "max_cost_units", "cost_semantics", "max_resolved_argument_bytes", "effect_profile_digest", "effect_catalog_digest", "plan_digest"],
    "properties": {
        "schema": {"type": "string", "enum": ["pcmmad.capability-plan.v1"]},
        "authority_effect": {"type": "string", "enum": ["NONE"]},
        "project_id": {"type": "string", "nullable": True},
        "goal": {"type": "string", "nullable": True},
        "nodes": {"type": "array", "minItems": 1, "maxItems": 32, "items": OBJ},
        "stages": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}},
        "assertions": {"type": "array", "maxItems": 32, "items": assertion},
        "stop_on_error": {"type": "boolean"},
        "max_parallelism": {"type": "integer", "minimum": 1, "maximum": 16},
        "static_cost_units": {"type": "integer", "minimum": 1},
        "max_cost_units": {"type": "integer", "minimum": 1, "maximum": 320},
        "cost_semantics": {"type": "string"},
        "max_resolved_argument_bytes": {"type": "integer", "enum": [65536], "description": "Execution-time ceiling after dataflow references resolve. Larger values must travel by result handle rather than inline materialization."},
        "effect_profile_digest": DIGEST,
        "effect_catalog_digest": DIGEST,
        "lease_digest": {"type": "string", "nullable": True},
        "plan_digest": DIGEST,
    },
    "additionalProperties": False,
}

flow_step = {
    "type": "object",
    "required": ["tool_name", "expected_contract_digest"],
    "properties": {
        "id": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_.-]{0,63}$", "description": "Required when this or a later step participates in dataflow."},
        "tool_name": {"type": "string", "minLength": 1},
        "payload": {"type": "object", "additionalProperties": True, "description": "Native capability payload. Exact dataflow values use {\"$ref\":\"prior_step.result.field\"}. Refs are payload-only."},
        "authority": {"$ref": "#/components/schemas/RuntimeAuthorityEnvelope"},
        "expected_contract_digest": DIGEST,
    },
    "additionalProperties": False,
}

requests = {
    "FlowBatchRequest": {
        "type": "object",
        "required": ["steps"],
        "properties": {
            "steps": {"type": "array", "minItems": 1, "maxItems": 12, "items": {"$ref": "#/components/schemas/FlowStep"}},
            "stop_on_error": {"type": "boolean", "default": True},
            "parallelism": {"type": "integer", "enum": [1], "default": 1, "description": "v11 Stage-A flow is deliberately sequential. Legacy v10 /lab/batch parallelism remains backward-compatible but is not projected into the v11 Assistant schema until effect witnesses qualify it."},
            "background": {"type": "boolean", "default": False},
            "project_id": {"type": "string", "maxLength": 128, "description": "Required for background result storage."},
            "store_result": {"type": "boolean", "default": False},
            "result_handle_threshold_chars": {"type": "integer", "minimum": 1000, "maximum": 12000},
            "result_label": {"type": "string", "maxLength": 160},
        },
        "additionalProperties": False,
        "description": "Short server-side dataflow over existing native dispatch (max 12 steps). Every step is contract-digest-bound. Backward-only exact refs may flow prior results into later payloads without model round trips. Authority refs are forbidden. v11 Stage-A flow is sequential; use compose/execute for larger statically cost-admitted workflows.",
    },
    "OrientRequest": {
        "type": "object",
        "properties": {
            "goal": {"type": "string", "maxLength": 2000, "description": "Natural-language task goal used only to rank live native capabilities."},
            "query": {"type": "string", "maxLength": 1000},
            "project_id": {"type": "string", "maxLength": 128},
            "capabilities": {"type": "array", "maxItems": 24, "items": {"type": "string"}},
            "categories": {"type": "array", "items": {"type": "string"}},
            "effect_classes": {"type": "array", "items": {"type": "string"}},
            "include_mutating": {"type": "boolean", "default": True},
            "detail": {"type": "string", "enum": ["compact", "full"], "default": "compact"},
            "max_capabilities": {"type": "integer", "minimum": 1, "maximum": 24, "default": 8},
            "ttl_seconds": {"type": "integer", "minimum": 10, "maximum": 900, "default": 300},
        },
        "additionalProperties": False,
    },
    "InvokeRequest": {
        "type": "object",
        "required": ["capability"],
        "properties": {
            "capability": {"type": "string", "minLength": 1},
            "arguments": OBJ,
            "authority": {"$ref": "#/components/schemas/RuntimeAuthorityEnvelope"},
            "expected_contract_digest": DIGEST,
            "lease": {"$ref": "#/components/schemas/CapabilityLease"},
        },
        "additionalProperties": False,
        "description": "Invoke one exact server-native capability. vNext requires either an expected contract digest or a current capability lease. Authority is always separate from capability arguments.",
    },
    "ComposeRequest": {
        "type": "object",
        "required": ["nodes"],
        "properties": {
            "goal": {"type": "string", "maxLength": 2000},
            "project_id": {"type": "string", "maxLength": 128},
            "lease": {"$ref": "#/components/schemas/CapabilityLease"},
            "nodes": {"type": "array", "minItems": 1, "maxItems": 32, "items": {"$ref": "#/components/schemas/PlanNode"}},
            "assertions": {"type": "array", "maxItems": 32, "items": {"$ref": "#/components/schemas/PlanAssertion"}},
            "stop_on_error": {"type": "boolean", "default": True},
            "max_parallelism": {"type": "integer", "minimum": 1, "maximum": 16, "default": 4},
            "max_cost_units": {"type": "integer", "minimum": 1, "maximum": 320, "default": 120},
        },
        "additionalProperties": False,
        "description": "Deterministically validate and seal an authority-neutral typed DAG; goal is metadata only and does not synthesize nodes. Dataflow references use {\"$ref\":\"node_id.result.field\"}. Authority is forbidden in plan nodes. Composition requires a current closed scheduler-effect profile and a statically computable cost within max_cost_units.",
    },
    "ExecuteRequest": {
        "type": "object",
        "required": ["project_id", "plan", "expected_plan_digest"],
        "properties": {
            "project_id": {"type": "string", "minLength": 1, "maxLength": 128},
            "plan": {"$ref": "#/components/schemas/CapabilityPlan"},
            "expected_plan_digest": DIGEST,
            "authorities": {
                "type": "object",
                "additionalProperties": {"$ref": "#/components/schemas/RuntimeAuthorityEnvelope"},
                "description": "Authority envelopes keyed by plan node id; not part of the sealed plan.",
            },
        },
        "additionalProperties": False,
        "description": "Execute a sealed deterministic plan after revalidating every native capability contract, scheduler-effect profile, and static cost bound. Only exact-digest witnessed PARALLEL_READ_VERIFIED nodes may fan out; all others serialize. Long work must lower into native durable execution capabilities.",
    },
    "ObserveRequest": {
        "type": "object",
        "required": ["kind"],
        "properties": {
            "kind": {"type": "string", "enum": ["lease", "plan", "capability", "effect_profile", "result", "continuation", "job"]},
            "project_id": {"type": "string", "maxLength": 128},
            "ref": {"type": "string"},
            "capability": {"type": "string"},
            "handle": {"type": "string"},
            "job_id": {"type": "string"},
            "mode": {"type": "string", "enum": ["auto", "metadata", "preview", "range", "status", "progress", "wait", "output"], "description": "Result: auto|metadata|preview|range. Job: status|progress|wait|output. v11 deliberately does not project full-result materialization; use bounded preview/range or a native escape hatch only when truly necessary."},
            "lease": {"$ref": "#/components/schemas/CapabilityLease"},
            "plan": {"$ref": "#/components/schemas/CapabilityPlan"},
            "expected_plan_digest": DIGEST,
            "timeout_seconds": {"type": "integer", "minimum": 1},
            "max_bytes": {"type": "integer", "minimum": 1},
            "offset_bytes": {"type": "integer", "minimum": 0},
            "length_bytes": {"type": "integer", "minimum": 1, "maximum": 65536},
            "preview_chars": {"type": "integer", "minimum": 200, "maximum": 4000},
        },
        "additionalProperties": False,
    },
    "ResumeRequest": {
        "type": "object",
        "required": ["project_id", "continuation_handle", "resume_token"],
        "properties": {
            "project_id": {"type": "string", "minLength": 1, "maxLength": 128},
            "continuation_handle": {"type": "string", "minLength": 1},
            "resume_token": {"type": "string", "minLength": 16},
            "expected_plan_digest": DIGEST,
            "authorities": {"type": "object", "additionalProperties": {"$ref": "#/components/schemas/RuntimeAuthorityEnvelope"}},
        },
        "additionalProperties": False,
        "description": "Resume a single-use blocked continuation. CONTINUATION != CURRENTNESS: completed replay-safe reads are re-executed; prior effectful/cache-mutating work prevents automatic continuation and requires recovery/recomposition. Continuation grants no authority; authority must be supplied again.",
    },
    "TransferRequest": {
        "type": "object",
        "required": ["action"],
        "properties": {
            "action": {"type": "string", "enum": ["export.create", "chunk.read", "import.create", "chunk.write", "import.finalize", "meta"]},
            "arguments": OBJ,
            "authority": {"$ref": "#/components/schemas/RuntimeAuthorityEnvelope"},
        },
        "additionalProperties": False,
        "description": "Explicit binary/file movement boundary projected over the existing hardened native transfer plane.",
    },
}

operations = [
    ("/lab/vnext/orient", "orientCapabilities", "Orient to the smallest relevant live capability set", "OrientRequest"),
    ("/lab/vnext/invoke", "invokeCapability", "Invoke one exact current native capability", "InvokeRequest"),
    ("/lab/batch", "flowCapabilities", "Run bounded server-side native dataflow without model round trips", "FlowBatchRequest"),
    ("/lab/vnext/compose", "composePlan", "Compose and seal an authority-neutral typed capability plan", "ComposeRequest"),
    ("/lab/vnext/execute", "executePlan", "Execute a sealed current plan with separate node authority", "ExecuteRequest"),
    ("/lab/vnext/observe", "observeRuntime", "Observe a Runtime job/result/plan/lease/capability/continuation", "ObserveRequest"),
    ("/lab/vnext/resume", "resumeContinuation", "Resume one single-use blocked plan continuation", "ResumeRequest"),
    ("/lab/vnext/transfer", "transferData", "Move binary/file data through the hardened transfer plane", "TransferRequest"),
]

paths = {}
for path, operation_id, summary, request_name in operations:
    paths[path] = {
        "post": {
            "operationId": operation_id,
            "summary": summary,
            "description": {
                "orientCapabilities": "Task-relative discovery and expiring capability lease. Discovery/currentness only; grants no authority.",
                "invokeCapability": "Currentness-bound single-capability fast path and deliberate escape hatch when the uniform resource algebra cannot express a native capability. Capability arguments and Runtime authority remain distinct.",
                "flowCapabilities": "First-class Stage-A dataflow projection over existing /lab/batch. Short flows are sequential, exact-contract-bound, and max 12 steps; backward-only refs flow prior results into later payloads and authority refs are forbidden. Legacy batch parallelism is intentionally not projected into v11.",
                "composePlan": "Build a bounded deterministic DAG from native capabilities, derive dataflow dependencies, bind native contract/effect-profile digests, and statically admit cost and seal a 65,536-byte resolved-argument ceiling. Goal text never synthesizes executable nodes. Does not execute.",
                "executePlan": "Revalidate sealed plan/native contracts/effect profile/cost; only exact-witness parallel reads may fan out. All other nodes serialize. Blocked continuations never preserve stale reads as currentness.",
                "observeRuntime": "Unified bounded observation over canonical Runtime references without inventing adapter-owned jobs/results.",
                "resumeContinuation": "Consume a blocked continuation once. Replay-safe completed reads are re-executed; any prior uncertain/effectful work requires recovery and recomposition rather than automatic replay.",
                "transferData": "Stable adapter projection over native transfer tickets/chunks/finalization; transfer state remains server-native.",
            }[operation_id],
            "requestBody": {
                "required": True,
                "content": {"application/json": {"schema": {"$ref": f"#/components/schemas/{request_name}"}}},
            },
            "responses": {
                "200": {"description": "Bounded Runtime response", "content": {"application/json": {"schema": {"type": "object", "additionalProperties": True}}}},
                "400": {"description": "Malformed request/plan/schema"},
                "401": {"description": "Authentication required"},
                "403": {"description": "Invalid continuation/authority token"},
                "404": {"description": "Referenced native Runtime object not found"},
                "409": {"description": "Currentness/authority/plan/continuation conflict"},
            },
        }
    }

schema = {
    "openapi": "3.0.3",
    "info": {
        "title": "PCMMAD Laboratory Runtime Capability Microkernel",
        "version": "11.0.0-candidate",
        "description": (
            "Eight-operation Assistant-facing control algebra over the wider server-native PCMMAD Laboratory Runtime. "
            "The schema is not Runtime authority. Native capabilities remain dynamically discoverable/currentness-bound; "
            "plans and leases grant no authority; durable jobs/results/transfers remain owned by existing Runtime planes."
        ),
    },
    "servers": old["servers"],
    "security": old["security"],
    "paths": paths,
    "components": {
        "securitySchemes": old["components"]["securitySchemes"],
        "schemas": {
            "RuntimeAuthorityEnvelope": authority,
            "ProjectMutationAuthority": project_mutation_authority,
            "FlowStep": flow_step,
            "CapabilityLease": lease,
            "PlanNode": plan_node,
            "PlanAssertion": assertion,
            "CapabilityPlan": plan,
            **requests,
        },
    },
}

OUT.write_text(json.dumps(schema, indent=2, sort_keys=False) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"path": str(OUT), "operations": len(operations), "bytes": OUT.stat().st_size}, indent=2))
