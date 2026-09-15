# DAEMON INFERENCE / CONVERSATION BLOCKER — 2026-09-15

## Status
SUBSTANTIVE BLOCKER after Daemon persistence/bootstrap qualification.

## Verified facts
- Current native Receiver registry contains only model-artifact management under the model-ish names: `project.models.list` and `project.models.inspect`.
- No native capability matching generative `llm`, `infer`, `chat`, `completion`, or model-execution was discovered in the active 175-capability registry.
- Current Veya chamber source explicitly reports `external_llm_oracle: NONE`.
- Current Veya chamber also explicitly states that the chamber does not itself provide general conversation or world knowledge.
- Historical/design-donor local inference code exists elsewhere in the repository, but current reports state that portable local-inference support was previously removed/unqualified. Presence of donor code != qualified runtime inference.

## Consequence
A HUD text box or HTTP endpoint can be built mechanically, but that would not establish Daemon as a general conversational/proactive cognitive organism. The next high-value bridge is a qualified inference/conversation plane that Daemon can use without making a model vendor or single hosted SDK the source of truth.

## Required properties of next bridge
- provider-neutral inference contract;
- explicit model/runtime identity and currentness;
- bounded context/request/result envelopes;
- streaming or incremental response support for HUD/speech;
- tool/capability invocation bridge that preserves Receiver authority contracts;
- cancellation/timeouts/job ownership;
- model failure/degradation semantics;
- no hidden self-approval or effect authority;
- ability to support proactive Daemon cognition, not only request/response chat;
- longitudinal memory/biography/evidence remains Daemon-owned, not model-provider-owned;
- qualification against general reasoning/learning/transfer goals, not merely fluent text generation.

## Non-solution
Do not fake this bridge by routing HUD chat directly to an arbitrary LLM endpoint and calling that Daemon. The model is a cognitive substrate/resource; Daemon identity, memory, duties, evidence, authority and developmental continuity remain in the Daemon plane.
