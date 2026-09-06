from __future__ import annotations

from typing import Any, Callable
from operator_plane import hud_status, restart_hud

def register(register_tool: Callable[..., Any]) -> None:
    @register_tool(
        "control.hud.status",
        "Inspect receiver-native PCMMAD Operations HUD lifecycle and health.",
        "low",
        category="control",
        tags=["hud","operator","ui","status"],
        side_effect_class="read_probe",
        effect_traits=["reads_process_state", "reads_service_state", "health_probe"],
    )
    def _status(_payload):
        return hud_status()

    @register_tool(
        "control.hud.restart",
        "Restart the receiver-native PCMMAD Operations HUD without restarting the receiver.",
        "medium",
        category="control",
        tags=["hud","operator","ui","restart"],
        mutating=True,
        approval_required=True,
    )
    def _restart(_payload):
        return restart_hud()
