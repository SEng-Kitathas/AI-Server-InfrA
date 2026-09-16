from __future__ import annotations
from typing import Callable
from ..runtime.types import EpisodeSchemaContract, QualificationState

EpisodeInvalidationCallback = Callable[[str, int, str], None]


class EpisodeSchemaRegistry:
    """Currentness registry for externally qualified operational episode schemas.

    MS921 showed that a candidate could outlive an unrepresented change in the
    higher-level grouping relation that generated its traces. This registry
    gives that relation an explicit epoch without claiming that Microseed can
    generally construct, identify, or self-qualify episode schemas.
    """

    def __init__(self, *, on_invalidate: EpisodeInvalidationCallback | None = None):
        self.schemas: dict[str, EpisodeSchemaContract] = {}
        self.epochs: dict[str, int] = {}
        self.capability_dependents: dict[str, set[str]] = {}
        self.frame_dependents: dict[str, set[str]] = {}
        self.value_dependents: dict[str, set[str]] = {}
        self.counterparty_dependents: dict[str, set[str]] = {}
        self.coordination_dependents: dict[str, set[str]] = {}
        self._on_invalidate = on_invalidate

    def register(self, schema: EpisodeSchemaContract) -> None:
        if schema.schema_id in self.schemas:
            raise ValueError(f"duplicate episode schema: {schema.schema_id}")
        if schema.qualification not in {
            QualificationState.QUALIFIED,
            QualificationState.SHADOW_QUALIFIED,
        }:
            raise ValueError("episode schema must be externally qualified before registration")
        if not schema.signature_sha256:
            raise ValueError("episode schema requires content-bound signature_sha256")
        self.schemas[schema.schema_id] = schema
        self.epochs[schema.schema_id] = 0
        for frame_id, _ in schema.frame_epochs:
            self.frame_dependents.setdefault(frame_id, set()).add(schema.schema_id)
        for value_id, _ in schema.value_epochs:
            self.value_dependents.setdefault(value_id, set()).add(schema.schema_id)
        for counterparty_id, _ in schema.counterparty_epochs:
            self.counterparty_dependents.setdefault(counterparty_id, set()).add(schema.schema_id)
        for coordination_id, _ in schema.coordination_epochs:
            self.coordination_dependents.setdefault(coordination_id, set()).add(schema.schema_id)

    def bind_capability(self, schema_id: str, capability_id: str) -> None:
        if schema_id not in self.schemas:
            raise ValueError(f"unknown episode schema: {schema_id}")
        self.capability_dependents.setdefault(schema_id, set()).add(capability_id)

    def is_current(self, schema_id: str, epoch: int | None = None) -> bool:
        schema = self.schemas.get(schema_id)
        if schema is None or schema.qualification not in {
            QualificationState.QUALIFIED,
            QualificationState.SHADOW_QUALIFIED,
        }:
            return False
        if epoch is not None and self.epochs.get(schema_id, -1) != int(epoch):
            return False
        return True

    def change(self, schema_id: str, *, reason: str = "EPISODE_SCHEMA_CHANGED") -> int:
        if schema_id not in self.schemas:
            raise ValueError(f"unknown episode schema: {schema_id}")
        self.epochs[schema_id] = self.epochs.get(schema_id, 0) + 1
        schema = self.schemas[schema_id]
        schema.qualification = QualificationState.STALE
        schema.currentness = "STALE"
        if self._on_invalidate is not None:
            self._on_invalidate(schema_id, self.epochs[schema_id], reason)
        return self.epochs[schema_id]

    def invalidate_by_frame(self, frame_id: str, *, reason: str) -> set[str]:
        """Stale episode schemas explicitly bound to a changed lower frame."""
        changed: set[str] = set()
        for schema_id in sorted(self.frame_dependents.get(frame_id, ())):
            if self.is_current(schema_id):
                self.change(schema_id, reason=f"FRAME:{frame_id}:{reason}")
                changed.add(schema_id)
        return changed

    def invalidate_by_value(self, value_id: str, *, reason: str) -> set[str]:
        """Stale episode schemas explicitly bound to a changed value contract."""
        changed: set[str] = set()
        for schema_id in sorted(self.value_dependents.get(value_id, ())):
            if self.is_current(schema_id):
                self.change(schema_id, reason=f"VALUE:{value_id}:{reason}")
                changed.add(schema_id)
        return changed


    def invalidate_by_counterparty(self, counterparty_id: str, *, reason: str) -> set[str]:
        """Stale episode schemas explicitly bound to a changed counterparty premise."""
        changed: set[str] = set()
        for schema_id in sorted(self.counterparty_dependents.get(counterparty_id, ())):
            if self.is_current(schema_id):
                self.change(schema_id, reason=f"COUNTERPARTY:{counterparty_id}:{reason}")
                changed.add(schema_id)
        return changed

    def invalidate_by_coordination(self, coordination_id: str, *, reason: str) -> set[str]:
        """Stale episode schemas explicitly bound to a changed coordination relation."""
        changed: set[str] = set()
        for schema_id in sorted(self.coordination_dependents.get(coordination_id, ())):
            if self.is_current(schema_id):
                self.change(schema_id, reason=f"COORDINATION:{coordination_id}:{reason}")
                changed.add(schema_id)
        return changed

    def snapshot(self) -> dict[str, dict]:
        return {
            sid: {
                "contract": schema.serializable(),
                "epoch": self.epochs.get(sid, 0),
                "capability_dependents": sorted(self.capability_dependents.get(sid, ())),
                "counterparty_dependents_of_schema": [list(x) for x in schema.counterparty_epochs],
                "coordination_dependents_of_schema": [list(x) for x in schema.coordination_epochs],
            }
            for sid, schema in sorted(self.schemas.items())
        }
