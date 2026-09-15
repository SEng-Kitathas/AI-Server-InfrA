from __future__ import annotations

from typing import Any, Iterable

from ..runtime.commitment import (
    RelationalCommitment,
    TernaryCommitment,
    conjoin_required_commitments,
)
from ..runtime.types import Authority, ValueVariableContract
from .action_closure import stable_id as action_stable_id
from .value import residual_pressure_after_effect


def _unknown_coordinate(
    capability_id: str,
    value_id: str,
    reason: str,
    *,
    status: str | None = None,
) -> RelationalCommitment:
    payload: dict[str, Any] = {
        "capability": capability_id,
        "value": value_id,
        "reason": reason,
    }
    if status is not None:
        payload["status"] = status
    return RelationalCommitment(
        action_stable_id("MULTIVALUE-COORD-", payload),
        f"capability:{capability_id}:value:{value_id}",
        TernaryCommitment.UNKNOWN,
        reason=reason,
        qualifiers=(("authority_gain", "NONE"),),
    )


def project_regulatory_effect_license(
    capability_id: str,
    value_id: str,
    *,
    current_value: float,
    current_pressure: float,
    value_epoch: int,
    contract: ValueVariableContract,
    effect_row: dict[str, Any],
) -> RelationalCommitment:
    """Project one current action/value effect into a bounded premise license.

    This is not a value-ranking or utility operation. Under current pressure, an
    effect licenses YES only when it reduces that coordinate's residual pressure.
    An unpressured coordinate licenses YES only when the effect preserves the
    viable interval. The projection never grants execution or truth authority.
    """
    residual = residual_pressure_after_effect(
        contract,
        current_value,
        float(effect_row["effect"]),
    )
    if current_pressure > 0.0:
        if residual < current_pressure:
            stance = TernaryCommitment.YES
            reason = "LOWERS_CURRENT_REGULATORY_PRESSURE"
        elif residual > current_pressure:
            stance = TernaryCommitment.NO
            reason = "WORSENS_CURRENT_REGULATORY_PRESSURE"
        else:
            stance = TernaryCommitment.UNKNOWN
            reason = "NO_DISCRIMINATING_REGULATORY_ADVANTAGE"
    elif residual == 0.0:
        stance = TernaryCommitment.YES
        reason = "PRESERVES_UNPRESSURED_COORDINATE"
    else:
        stance = TernaryCommitment.NO
        reason = "CREATES_NEW_REGULATORY_PRESSURE"

    return RelationalCommitment(
        action_stable_id(
            "MULTIVALUE-COORD-",
            {
                "capability": capability_id,
                "value": value_id,
                "value_epoch": value_epoch,
                "effect": effect_row["effect"],
                "current": current_pressure,
                "residual": residual,
            },
        ),
        f"capability:{capability_id}:value:{value_id}",
        stance,
        reason=reason,
        qualifiers=(
            ("authority_gain", "NONE"),
            ("effect_witness_authority", str(effect_row["authority"])),
            ("effect_episode_schema", str(effect_row["episode_schema_epoch"])),
        ),
        premise_ids=tuple(effect_row["source_trace_ids"]),
    )


def compose_multi_value_action_licenses(
    requested_value_ids: Iterable[str],
    effect_rows: dict[tuple[str, str], dict[str, Any]],
    current_values: dict[str, dict[str, Any]],
    current_capability_ids: Iterable[str],
) -> dict[str, Any]:
    """Compose current action/value premises without persistence or ranking.

    `current_values` is a current read-only snapshot prepared by the entity. Each
    entry carries the scalar value, pressure magnitude, epoch, and current value
    contract. `effect_rows` must already have passed current ancestry filtering.
    """
    requested = tuple(str(value_id) for value_id in requested_value_ids)
    action_ids = sorted(
        set(current_capability_ids)
        & {capability_id for capability_id, _ in effect_rows}
    )

    coordinate_commitments: dict[str, list[RelationalCommitment]] = {}
    action_commitments: dict[str, RelationalCommitment] = {}

    for capability_id in action_ids:
        coordinates: list[RelationalCommitment] = []
        for value_id in requested:
            effect_row = effect_rows.get((capability_id, value_id))
            if effect_row is None:
                coordinates.append(_unknown_coordinate(
                    capability_id,
                    value_id,
                    "CURRENT_VALUE_BOUND_EFFECT_UNAVAILABLE",
                ))
                continue
            if effect_row.get("status") != "CURRENT_EFFECT":
                status = str(effect_row.get("status", "EFFECT_EVIDENCE_UNRESOLVED"))
                coordinates.append(_unknown_coordinate(
                    capability_id,
                    value_id,
                    status,
                    status=status,
                ))
                continue

            current = current_values.get(value_id)
            if current is None:
                coordinates.append(_unknown_coordinate(
                    capability_id,
                    value_id,
                    "REGULATORY_VALUE_STATE_NOT_CURRENT",
                ))
                continue

            coordinates.append(project_regulatory_effect_license(
                capability_id,
                value_id,
                current_value=float(current["value"]),
                current_pressure=float(current["pressure_magnitude"]),
                value_epoch=int(current["epoch"]),
                contract=current["contract"],
                effect_row=effect_row,
            ))

        coordinate_commitments[capability_id] = coordinates
        action_commitments[capability_id] = conjoin_required_commitments(
            coordinates,
            commitment_id=action_stable_id(
                "MULTIVALUE-ACTION-",
                {
                    "capability": capability_id,
                    "premises": [row.commitment_id for row in coordinates],
                },
            ),
            target_id=f"capability:{capability_id}:whole-current-value-frame",
            reason_prefix="MULTIVALUE_REQUIRED_PREMISE",
        )

    licensed = sorted(
        capability_id
        for capability_id, commitment in action_commitments.items()
        if commitment.licenses_yes()
    )
    if len(licensed) == 1:
        chosen = licensed[0]
        overall = RelationalCommitment(
            action_stable_id("MULTIVALUE-UNIQUE-", {"capability": chosen}),
            f"capability:{chosen}:candidate-next-action",
            TernaryCommitment.YES,
            reason="UNIQUE_CONJUNCTIVELY_LICENSED_ACTION",
            qualifiers=(
                ("authority_gain", "NONE"),
                ("execution_authority", "NONE"),
                ("selection", "UNIQUE_SURVIVOR_ONLY"),
            ),
            premise_ids=(action_commitments[chosen].commitment_id,),
        )
        status = "UNIQUE_ACTION_LICENSE"
    else:
        overall = RelationalCommitment(
            action_stable_id("MULTIVALUE-ABSTAIN-", {"licensed": licensed}),
            "action:next",
            TernaryCommitment.UNKNOWN,
            reason=(
                "MULTIPLE_LAWFUL_ACTIONS_NO_RANKING_AUTHORITY"
                if len(licensed) > 1
                else "NO_FULLY_LICENSED_ACTION"
            ),
            qualifiers=(
                ("authority_gain", "NONE"),
                ("execution_authority", "NONE"),
                ("selection", "ABSTAIN_ON_NONUNIQUE"),
            ),
            premise_ids=tuple(
                action_commitments[capability_id].commitment_id
                for capability_id in licensed
            ),
        )
        status = "UNKNOWN_ACTION_SELECTION"

    return {
        "status": status,
        "overall_commitment": overall.serializable(),
        "licensed_action_ids": licensed,
        "action_commitments": {
            capability_id: commitment.serializable()
            for capability_id, commitment in action_commitments.items()
        },
        "coordinate_commitments": {
            capability_id: [row.serializable() for row in rows]
            for capability_id, rows in coordinate_commitments.items()
        },
        "authority": Authority.NONE.value,
        "execution_authority": Authority.NONE.value,
        "semantic_value_priority_authority": Authority.NONE.value,
        "persistence": "NONE",
    }
