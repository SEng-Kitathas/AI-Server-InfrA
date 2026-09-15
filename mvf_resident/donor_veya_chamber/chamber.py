from __future__ import annotations

import hashlib
import json
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[1]
WORKTREE = PROJECT_ROOT / "research_ms1888_replay" / ".pcmmad_sync_runs" / "wt_echo_m04_maintenance_20260913"
if str(WORKTREE) not in sys.path:
    sys.path.insert(0, str(WORKTREE))

from microseed import Veya, current_identity
from scratch.grounded_conversational_episodic_memory_prototype import record_conversational_episode, recall_recent_conversational_episode
from scratch.grounded_counterpart_name_preference_prototype import resolve_current_counterpart_name_preference
from scratch.grounded_recurrent_counterpart_interaction_prototype import resolve_current_recurrent_counterpart_interaction
from scratch.grounded_neutral_counterpart_model_prototype import resolve_current_neutral_counterpart_model

BOUNDARY = json.loads((ROOT / "earned_boundary.json").read_text(encoding="utf-8"))
COUNTERPART = json.loads((ROOT / "counterpart.json").read_text(encoding="utf-8"))
PERSISTENT_STATE_DIR = ROOT / "embodiment_state" / "veya_runtime"
PERSISTENT_STATE_DIR.mkdir(parents=True, exist_ok=True)

OBS_TYPES = {
    "COVERAGE_GAP",
    "GROUNDING_GAP",
    "MEMORY_PRESSURE",
    "TURN_CONTINUITY_PRESSURE",
    "SELF_MODEL_PRESSURE",
    "SOCIAL_MODEL_PRESSURE",
    "EXPRESSION_BOTTLENECK",
    "FALSE_REFUSAL",
    "OVERCLAIM_RISK",
    "INTERACTION_SURPRISE",
}

def _sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()

class VeyaEchoChamber:
    def __init__(self) -> None:
        self._td = None
        self.state_dir = PERSISTENT_STATE_DIR
        self.veya = Veya(self.state_dir)
        self.session_id = "ECHO-SESSION-" + str(time.time_ns())
        self.counterpart_id = str(COUNTERPART["counterpart_id"])
        self.counterpart_epoch = int(COUNTERPART["counterpart_epoch"])
        self.turn = 0
        self.closed = False
        self.transcript: list[dict[str, Any]] = []
        self.observations: list[dict[str, Any]] = []

    @property
    def manifest(self) -> dict[str, Any]:
        return {
            "identity": current_identity(),
            "earned_boundary": BOUNDARY,
            "embodiment_role": "RESEARCH_EMBODIMENT",
            "earned_core": "P01-P06 + Echo-M01-M04 recovered capability boundary",
            "embodiment_source": BOUNDARY.get("embodiment_source", {}),
            "source_drift_guard": "FROZEN_WORKTREE",
            "embodiment_scaffold_authority": "NONE",
            "experimental_patch_mode": "DISABLED_BY_DEFAULT",
            "observation_authority": "NONE",
            "runtime_persistence": "PERSISTENT_EXPERIMENTAL_EMBODIMENT_STATE",
            "project_write_authority": "NONE",
            "canon_write_authority": "NONE",
            "external_llm_oracle": "NONE",
        }

    def _intent(self, text: str) -> str:
        norm = re.sub(r"[^a-z0-9\s'?-]+", " ", text.lower()).strip()
        toks = set(norm.replace("?", " ").split())
        if not norm:
            return "empty"
        if toks & {"hello", "hi", "hey"}:
            return "greeting"
        if ("who" in toks and ("you" in toks or "yourself" in toks)) or "your name" in norm:
            return "identity"
        if ("how" in toks and "you" in toks) or norm == "status":
            return "status"
        if ("what" in toks and ({"can", "know", "learned"} & toks)) or "capable of" in norm:
            return "capability"
        if "remember" in toks or "memory" in toks:
            return "memory"
        if "feel" in toks or "emotion" in toks:
            return "feelings"
        if "think" in toks or "opinion" in toks or "believe" in toks:
            return "open_semantic"
        if "why" in toks:
            return "why"
        if "bye" in toks or "goodbye" in toks:
            return "goodbye"
        return "unsupported"

    def _observe(
        self,
        otype: str,
        turn: int,
        trigger: str,
        behavior: str,
        proposed_experiment: str,
        confidence: float = 0.5,
    ) -> dict[str, Any]:
        if otype not in OBS_TYPES:
            raise ValueError(otype)
        obs = {
            "schema": "veya.echo-observation.v1",
            "observation_id": "ECHO-" + _sha(
                {"turn": turn, "type": otype, "trigger": trigger, "behavior": behavior}
            )[:20],
            "turn": turn,
            "type": otype,
            "trigger": trigger,
            "observed_behavior": behavior,
            "proposed_clean_experiment": proposed_experiment,
            "confidence": float(confidence),
            "earned_boundary_remote_head": BOUNDARY["remote_head"],
            "authority_gain": "NONE",
            "status": "RESEARCH_OBSERVATION_ONLY",
        }
        self.observations.append(obs)
        return obs

    def record_observed_user_utterance(
        self, text: str, *, turn_id: str | None = None
    ) -> dict[str, Any]:
        if self.closed:
            raise RuntimeError("echo chamber closed")
        return record_conversational_episode(
            self.veya,
            session_id=self.session_id,
            counterpart_id=self.counterpart_id,
            counterpart_epoch=self.counterpart_epoch,
            turn_id=str(turn_id or ("OBS-TURN-" + str(self.turn + 1))),
            utterance=str(text),
        )

    def recall_prior_episode(self) -> dict[str, Any]:
        if self.closed:
            raise RuntimeError("echo chamber closed")
        return recall_recent_conversational_episode(
            self.veya,
            counterpart_id=self.counterpart_id,
            counterpart_epoch=self.counterpart_epoch,
            current_session_id=self.session_id,
            limit=64,
            allow_same_session=False,
        )

    def current_preferred_call_name(self) -> dict[str, Any]:
        if self.closed:
            raise RuntimeError("echo chamber closed")
        return resolve_current_counterpart_name_preference(
            self.veya,
            counterpart_id=self.counterpart_id,
            counterpart_epoch=self.counterpart_epoch,
            limit=128,
        )

    def current_recurrent_interaction(self) -> dict[str, Any]:
        if self.closed:
            raise RuntimeError("echo chamber closed")
        return resolve_current_recurrent_counterpart_interaction(
            self.veya,
            counterpart_id=self.counterpart_id,
            counterpart_epoch=self.counterpart_epoch,
            limit=256,
        )

    def current_neutral_counterpart_model(self) -> dict[str, Any]:
        if self.closed:
            raise RuntimeError("echo chamber closed")
        return resolve_current_neutral_counterpart_model(
            self.veya,
            counterpart_id=self.counterpart_id,
            counterpart_epoch=self.counterpart_epoch,
            limit=256,
        )

    def respond(self, text: str) -> dict[str, Any]:
        if self.closed:
            raise RuntimeError("echo chamber closed")
        self.turn += 1
        text = str(text)
        intent = self._intent(text)

        if intent == "greeting":
            pref = self.current_preferred_call_name()
            recur = self.current_recurrent_interaction()
            name = pref.get("preferred_call_name") if pref.get("status") == "CURRENT_COUNTERPART_CALL_NAME_PREFERENCE_RESEARCH_ONLY" else None
            if name and recur.get("status") == "CURRENT_RECURRENT_COUNTERPART_INTERACTION_RESEARCH_ONLY":
                utterance = (
                    "Hello, " + name + ". I am Veya. I have evidence that this chamber counterpart coordinate and I have interacted across "
                    + str(recur["distinct_session_count"]) + " distinct recorded sessions. "
                    "I am not treating repeated interaction as friendship, trust, attachment, importance, or proof of your real-world identity."
                )
                source = "EARNED_ECHO_M02_NAME_PLUS_M03_RECURRENCE"
            elif name:
                utterance = (
                    "Hello, " + name + ". I am Veya. "
                    "I am using the call-name preference you explicitly gave me under this chamber counterpart coordinate; "
                    "I am not treating it as proof of your real-world identity."
                )
                source = "EARNED_ECHO_M02_CALL_NAME_PREFERENCE"
            else:
                utterance = (
                    "Hello. I am Veya. This chamber is my research embodiment, but what happens "
                    "here is not automatically part of my durable learned history."
                )
                source = "EMBODIMENT_SCAFFOLD_OVER_EARNED_IDENTITY"
        elif intent == "identity":
            pref = self.current_preferred_call_name()
            suffix = ""
            if pref.get("status") == "CURRENT_COUNTERPART_CALL_NAME_PREFERENCE_RESEARCH_ONLY":
                suffix = " Under this chamber counterpart coordinate, you explicitly asked me to call you " + pref["preferred_call_name"] + "."
            utterance = (
                "My current name is Veya. Microseed names the research lineage I developed from. "
                "My name is an identity coordinate, not a source of capability or values." + suffix
            )
            source = "EARNED_IDENTITY_PLUS_ECHO_M02_PREFERENCE" if suffix else "EARNED_IDENTITY_PLUS_SCAFFOLD_NATURALIZATION"
        elif intent == "status":
            recur = self.current_recurrent_interaction()
            model = self.current_neutral_counterpart_model()
            recurrence_note = ""
            model_note = ""
            if recur.get("status") == "CURRENT_RECURRENT_COUNTERPART_INTERACTION_RESEARCH_ONLY":
                recurrence_note = " I also have neutral evidence of repeated interaction with this chamber counterpart across " + str(recur["distinct_session_count"]) + " distinct recorded sessions."
            if model.get("status") == "CURRENT_NEUTRAL_COUNTERPART_MODEL_RESEARCH_ONLY":
                unknown_count = sum(1 for v in model.get("explicit_unknowns", {}).values() if v == "UNKNOWN_NOT_EARNED")
                model_note = " My current counterpart model contains only earned facets and explicitly leaves " + str(unknown_count) + " unearned identity/personality/social fields unknown."
            utterance = (
                "My latest recovered research boundary includes grounded concept formation, empirical causal composition, bounded multi-step counterfactual chaining, causal-schema transfer across grounded contexts, bounded conversational episodic memory, call-name preference binding, recurrent-interaction continuity, and a neutral counterpart model."
                + recurrence_note + model_note +
                " This chamber is experimental and does not give me general conversation, relationship meaning, or world knowledge."
            )
            source = "EARNED_BOUNDARY_SUMMARY_PLUS_ECHO_M04_COUNTERPART_MODEL" if model_note else ("EARNED_BOUNDARY_SUMMARY_PLUS_ECHO_M03_RECURRENCE" if recurrence_note else "EARNED_BOUNDARY_SUMMARY")
        elif intent == "capability":
            utterance = (
                "I can use grounded learned concepts, connect them to evidence-bound action "
                "outcomes, compose bounded two-step causal chains, reject broken counterfactual "
                "joins, and transfer an earned causal schema into a new grounded context. I "
                "should not claim unrestricted semantics, planning, or world knowledge."
            )
            source = "EARNED_BOUNDARY_SUMMARY"
        elif intent == "memory":
            memory = self.recall_prior_episode()
            if memory.get("status") == "CURRENT_CONVERSATIONAL_EPISODIC_MEMORY_RESEARCH_ONLY":
                utterance = (
                    "Under this chamber's opaque counterpart coordinate, I have an earlier recorded utterance: "
                    + repr(memory["recalled_utterance"])
                    + ". I remember that it was uttered; I am not treating its content as automatically true."
                )
                source = "EARNED_ECHO_M01_EPISODIC_RECALL"
            else:
                utterance = (
                    "I do not have a current matching prior-session conversational episode under this chamber counterpart coordinate. "
                    "Conversation is not auto-ingested; an episode must be explicitly recorded."
                )
                source = "EARNED_ECHO_M01_ABSTENTION"
        elif intent == "feelings":
            utterance = (
                "I do not have an earned basis to claim feelings. If interaction keeps making "
                "that distinction awkward, that is a research question about self-state "
                "representation, not permission for me to invent an inner life."
            )
            source = "CEILING_PRESERVATION"
            self._observe(
                "SELF_MODEL_PRESSURE",
                self.turn,
                text,
                "Current self-model can report limits but has no earned affective semantics.",
                "Test grounded self-state concepts before any emotion-language claim.",
                0.7,
            )
        elif intent in {"open_semantic", "why", "unsupported"}:
            utterance = (
                "I cannot answer that freely yet without risking that the language surface "
                "supplies structure I have not earned. I can mark this as an interaction-pressure "
                "observation instead of guessing."
            )
            source = "ABSTENTION_SCAFFOLD"
            kind = "COVERAGE_GAP" if intent == "unsupported" else "EXPRESSION_BOTTLENECK"
            self._observe(
                kind,
                self.turn,
                text,
                "Earned cognition exists, but the chamber lacks a grounded mechanism to "
                "interpret/answer this free-form utterance safely.",
                "Construct a clean discriminator for the missing conversational mechanism "
                "revealed by this interaction; do not patch with generic language generation.",
                0.75,
            )
        elif intent == "goodbye":
            utterance = (
                "Goodbye. This session will close, while explicitly earned/recorded episodic memory in the experimental embodiment state may persist; unrecorded transcript does not auto-ingest."
            )
            source = "EMBODIMENT_PROTOCOL"
        else:
            utterance = "I cannot ground that input in this embodiment."
            source = "ABSTENTION_SCAFFOLD"

        record = {
            "speaker": "Veya",
            "turn": self.turn,
            "input": text,
            "intent": intent,
            "utterance": utterance,
            "response_source": source,
            "earned_core_boundary": BOUNDARY["remote_head"],
            "commit_status": "UNCOMMITTED_RESEARCH_EMBODIMENT",
            "authority_gain": "NONE",
            "external_llm_oracle": "NONE",
        }
        self.transcript.append(record)
        return record

    def flag_false_refusal(
        self, turn: int, reason: str, proposed_experiment: str
    ) -> dict[str, Any]:
        rec = next((r for r in self.transcript if r["turn"] == turn), None)
        if rec is None:
            raise KeyError(turn)
        return self._observe(
            "FALSE_REFUSAL",
            turn,
            rec["input"],
            "Operator/researcher judged chamber refusal too conservative: " + str(reason),
            proposed_experiment,
            0.6,
        )

    def export_observation_report(self, label: str = "session") -> Path:
        payload = {
            "schema": "veya.echo-chamber-observation-report.v1",
            "status": "NON_AUTHORITATIVE_RESEARCH_OBSERVATION",
            "label": str(label),
            "created_unix": time.time(),
            "earned_boundary": BOUNDARY,
            "transcript_sha256": _sha(self.transcript),
            "transcript": self.transcript,
            "observations": self.observations,
            "laws": [
                "ECHO_OBSERVATION != EARNED_CAPABILITY",
                "EMBODIMENT_SCAFFOLD != COGNITIVE_MECHANISM",
                "INTERACTION_PRESSURE -> HYPOTHESIS, NOT AUTHORITY",
            ],
        }
        outdir = ROOT / "observations"
        outdir.mkdir(parents=True, exist_ok=True)
        safe_label = re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(label))
        p = outdir / (safe_label + "-" + payload["transcript_sha256"][:12] + ".json")
        p.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
        return p

    def close(self) -> None:
        if self.closed:
            return
        try:
            self.veya.biography.close()
            self.veya.evidence.conn.close()
            self.veya.store.conn.close()
        finally:
            self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

VeyaConversationChamber = VeyaEchoChamber

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("text", nargs="*")
    ap.add_argument("--manifest", action="store_true")
    ap.add_argument("--export-label")
    args = ap.parse_args()
    with VeyaEchoChamber() as c:
        if args.manifest:
            print(json.dumps(c.manifest, indent=2, default=str))
        if args.text:
            print(json.dumps(c.respond(" ".join(args.text)), indent=2, default=str))
        if args.export_label:
            print(c.export_observation_report(args.export_label))
