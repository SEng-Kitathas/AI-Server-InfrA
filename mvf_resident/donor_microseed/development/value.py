from __future__ import annotations
import math
from typing import Callable
from ..runtime.types import ValueVariableContract, QualificationState

ValueInvalidationCallback = Callable[[str, int, str], None]


def pressure_magnitude_for_value(contract: ValueVariableContract, value: float) -> float:
    """Return distance outside the current viable interval, never a value priority."""
    x = float(value)
    if x < float(contract.viable_low):
        return float(contract.viable_low) - x
    if x > float(contract.viable_high):
        return x - float(contract.viable_high)
    return 0.0


def residual_pressure_after_effect(
    contract: ValueVariableContract, current_value: float, predicted_effect: float
) -> float:
    """Project one already-derived scalar effect against the current value state."""
    return pressure_magnitude_for_value(
        contract,
        float(current_value) + float(predicted_effect),
    )


class ValueVariableRegistry:
    """Currentness registry for constitutional prelingual regulatory variables.

    MS953-977 showed that a bounded signed regulatory pressure can be generated
    internally from current scalar state plus an explicit constitutional viable
    interval. The identity of the variable and its viable interval remain
    supplied constitutional ancestry; this registry does not discover, rewrite,
    or self-qualify what should matter.
    """

    def __init__(self, *, on_invalidate: ValueInvalidationCallback | None = None):
        self.contracts: dict[str, ValueVariableContract] = {}
        self.epochs: dict[str, int] = {}
        self.latest: dict[str, tuple[int, float]] = {}
        self.capability_dependents: dict[str, set[str]] = {}
        self.episode_dependents: dict[str, set[str]] = {}
        self._on_invalidate = on_invalidate

    def register(self, contract: ValueVariableContract) -> None:
        if contract.value_id in self.contracts:
            raise ValueError(f"duplicate value variable: {contract.value_id}")
        if contract.qualification not in {
            QualificationState.QUALIFIED,
            QualificationState.SHADOW_QUALIFIED,
        }:
            raise ValueError("value variable must be externally qualified before registration")
        if not contract.signature_sha256:
            raise ValueError("value variable requires content-bound signature_sha256")
        if not (math.isfinite(contract.viable_low) and math.isfinite(contract.viable_high)):
            raise ValueError("value variable viable bounds must be finite")
        if not contract.viable_low < contract.viable_high:
            raise ValueError("value variable requires viable_low < viable_high")
        self.contracts[contract.value_id] = contract
        self.epochs[contract.value_id] = 0

    def is_current(self, value_id: str, epoch: int | None = None) -> bool:
        contract = self.contracts.get(value_id)
        if contract is None or contract.qualification not in {
            QualificationState.QUALIFIED,
            QualificationState.SHADOW_QUALIFIED,
        }:
            return False
        if epoch is not None and self.epochs.get(value_id, -1) != int(epoch):
            return False
        return True

    def observe(self, value_id: str, value: float, *, epoch: int | None = None) -> dict:
        if not self.is_current(value_id, epoch):
            return {
                "value_id": value_id,
                "status": "UNKNOWN_INCOMPLETE",
                "reason": "VALUE_VARIABLE_NOT_CURRENT",
            }
        x = float(value)
        if not math.isfinite(x):
            return {
                "value_id": value_id,
                "status": "UNKNOWN_INCOMPLETE",
                "reason": "NONFINITE_VALUE_STATE",
            }
        current_epoch = self.epochs[value_id]
        self.latest[value_id] = (current_epoch, x)
        return {
            "value_id": value_id,
            "status": "CURRENT",
            "epoch": current_epoch,
            "value": x,
        }

    def pressure(self, value_id: str) -> dict:
        contract = self.contracts.get(value_id)
        if contract is None or not self.is_current(value_id):
            return {
                "value_id": value_id,
                "status": "UNKNOWN_INCOMPLETE",
                "reason": "VALUE_VARIABLE_NOT_CURRENT",
                "authority": "DERIVED_REGULATORY_PRESSURE_ONLY",
            }
        latest = self.latest.get(value_id)
        if latest is None or latest[0] != self.epochs[value_id]:
            return {
                "value_id": value_id,
                "status": "UNKNOWN_INCOMPLETE",
                "reason": "NO_CURRENT_VALUE_OBSERVATION",
                "epoch": self.epochs[value_id],
                "authority": "DERIVED_REGULATORY_PRESSURE_ONLY",
            }
        epoch, x = latest
        if x < contract.viable_low:
            signed = contract.viable_low - x
            relation = "BELOW_VIABLE_INTERVAL"
        elif x > contract.viable_high:
            signed = contract.viable_high - x
            relation = "ABOVE_VIABLE_INTERVAL"
        else:
            signed = 0.0
            relation = "WITHIN_VIABLE_INTERVAL"
        return {
            "value_id": value_id,
            "status": "CURRENT",
            "epoch": epoch,
            "signed_pressure": signed,
            "pressure_magnitude": abs(signed),
            "relation": relation,
            "authority": "DERIVED_REGULATORY_PRESSURE_ONLY",
            "semantic_goal_authority": "NONE",
            "constitutional_prior_origin": "SUPPLIED_AND_PROVENANCED",
        }

    def bind_capability(self, value_id: str, capability_id: str) -> None:
        if value_id not in self.contracts:
            raise ValueError(f"unknown value variable: {value_id}")
        self.capability_dependents.setdefault(value_id, set()).add(capability_id)

    def bind_episode(self, value_id: str, schema_id: str) -> None:
        if value_id not in self.contracts:
            raise ValueError(f"unknown value variable: {value_id}")
        self.episode_dependents.setdefault(value_id, set()).add(schema_id)

    def change(self, value_id: str, *, reason: str = "VALUE_CONTRACT_CHANGED") -> int:
        if value_id not in self.contracts:
            raise ValueError(f"unknown value variable: {value_id}")
        self.epochs[value_id] = self.epochs.get(value_id, 0) + 1
        contract = self.contracts[value_id]
        contract.qualification = QualificationState.STALE
        contract.currentness = "STALE"
        self.latest.pop(value_id, None)
        if self._on_invalidate is not None:
            self._on_invalidate(value_id, self.epochs[value_id], reason)
        return self.epochs[value_id]

    def snapshot(self) -> dict[str, dict]:
        return {
            vid: {
                "contract": contract.serializable(),
                "epoch": self.epochs.get(vid, 0),
                "latest": None if vid not in self.latest else {
                    "epoch": self.latest[vid][0], "value": self.latest[vid][1]
                },
                "capability_dependents": sorted(self.capability_dependents.get(vid, ())),
                "episode_dependents": sorted(self.episode_dependents.get(vid, ())),
            }
            for vid, contract in sorted(self.contracts.items())
        }
