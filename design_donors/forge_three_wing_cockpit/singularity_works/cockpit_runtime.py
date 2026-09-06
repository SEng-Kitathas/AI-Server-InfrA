from __future__ import annotations
# complexity_justified: vessel doctor and unified-front launch planning bridge host runtime, terminal host, and Claude process contracts.
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from typing import Sequence


class TerminalHostKind(str, Enum):
    WINDOWS_TERMINAL = "windows_terminal"
    WEZTERM = "wezterm"
    ALACRITTY = "alacritty"
    CONHOST = "conhost"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class VesselDoctorReport:
    checks: tuple[DoctorCheck, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)








class RelaunchAction(str, Enum):
    NONE = "none"
    LAUNCH_CLAUDE = "launch_claude"
    RELAUNCH_FORGE = "relaunch_forge"
    RESTORE_UNIFIED_FRONT = "restore_unified_front"
    CHECK_HOST = "check_host"


class SessionLifecycleState(str, Enum):
    PLANNED = "planned"
    HUD_ONLY = "hud_only"
    UNIFIED = "unified"
    DEGRADED = "degraded"


@dataclass(frozen=True)
class VesselSessionState:
    lifecycle: SessionLifecycleState
    relaunch_action: RelaunchAction
    anchor_supported: bool
    active_roles: tuple[str, ...]
    failed_roles: tuple[str, ...]
    rationale: str

    def to_stats(self) -> dict[str, str]:
        return {
            "session": self.lifecycle.value,
            "relaunch": self.relaunch_action.value,
            "active_roles": str(len(self.active_roles)),
            "failed_roles": str(len(self.failed_roles)),
        }

class LaunchDisposition(str, Enum):
    LAUNCHED = "launched"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class ProcessLaunchReceipt:
    role: str
    disposition: LaunchDisposition
    command: tuple[str, ...]
    title: str
    detail: str
    pid: int | None = None


@dataclass(frozen=True)
class UnifiedFrontReceipt:
    readiness: VesselReadiness
    unified_front_requested: bool
    unified_front_achieved: bool
    receipts: tuple[ProcessLaunchReceipt, ...]

    def to_stats(self) -> dict[str, str]:
        launched = sum(1 for receipt in self.receipts if receipt.disposition is LaunchDisposition.LAUNCHED)
        failed = sum(1 for receipt in self.receipts if receipt.disposition is LaunchDisposition.FAILED)
        return {
            "vessel_launch": self.readiness.value,
            "front": "unified" if self.unified_front_achieved else "partial",
            "launch_ok": str(launched),
            "launch_fail": str(failed),
        }

class VesselReadiness(str, Enum):
    READY = "ready"
    DEGRADED = "degraded"
    HUD_ONLY = "hud_only"


@dataclass(frozen=True)
class VesselSurfaceState:
    readiness: VesselReadiness
    claude_available: bool
    gpu_terminal: bool
    anchor_supported: bool
    unified_front_possible: bool
    terminal_kind: str
    terminal_executable: str
    claude_target: str

    def to_stats(self) -> dict[str, str]:
        return {
            "vessel": self.readiness.value,
            "claude": self.claude_target or "not-found",
            "terminal": self.terminal_executable or self.terminal_kind,
            "gpu_term": "yes" if self.gpu_terminal else "no",
            "unified_front": "yes" if self.unified_front_possible else "no",
            "anchor": "yes" if self.anchor_supported else "no",
        }

@dataclass(frozen=True)
class ClaudeProcessTarget:
    executable: str
    args: tuple[str, ...] = field(default_factory=tuple)
    title_hint: str = "Claude"


@dataclass(frozen=True)
class TerminalHostSpec:
    kind: TerminalHostKind
    executable: str = ""
    gpu_accelerated: bool = False
    title_supported: bool = False


@dataclass(frozen=True)
class VesselLaunchPlan:
    python_executable: str
    forge_command: tuple[str, ...]
    claude_target: ClaudeProcessTarget | None
    terminal_host: TerminalHostSpec
    project_root: str


def _which_many(candidates: Sequence[str]) -> str | None:
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def _detect_terminal_host() -> TerminalHostSpec:
    if executable := _which_many(['wt', 'wt.exe']):
        return TerminalHostSpec(TerminalHostKind.WINDOWS_TERMINAL, executable, gpu_accelerated=True, title_supported=True)
    if executable := _which_many(['wezterm', 'wezterm.exe']):
        return TerminalHostSpec(TerminalHostKind.WEZTERM, executable, gpu_accelerated=True, title_supported=True)
    if executable := _which_many(['alacritty', 'alacritty.exe']):
        return TerminalHostSpec(TerminalHostKind.ALACRITTY, executable, gpu_accelerated=True, title_supported=True)
    if os.name == 'nt' and (executable := _which_many(['cmd', 'cmd.exe'])):
        return TerminalHostSpec(TerminalHostKind.CONHOST, executable, gpu_accelerated=False, title_supported=True)
    return TerminalHostSpec(TerminalHostKind.UNKNOWN)


def _detect_claude_target() -> ClaudeProcessTarget | None:
    executable = _which_many(['claude', 'claude.exe', 'claude-code', 'claude-code.exe'])
    return ClaudeProcessTarget(executable=executable) if executable else None


def run_vessel_doctor(project_root: str | Path) -> VesselDoctorReport:
    root = Path(project_root)
    terminal = _detect_terminal_host()
    claude_target = _detect_claude_target()
    checks = [
        DoctorCheck('project_root', root.exists(), str(root)),
        DoctorCheck('forge_runtime', (root / 'singularity_works' / 'runtime.py').exists(), 'runtime.py present'),
        DoctorCheck('python', bool(sys.executable), sys.executable),
        DoctorCheck('terminal_host', terminal.kind is not TerminalHostKind.UNKNOWN, terminal.executable or 'no preferred terminal found'),
        DoctorCheck('gpu_terminal', terminal.gpu_accelerated, 'preferred gpu terminal available' if terminal.gpu_accelerated else 'fallback terminal only'),
        DoctorCheck('claude_target', claude_target is not None, claude_target.executable if claude_target else 'Claude executable not found'),
    ]
    return VesselDoctorReport(tuple(checks))


def build_vessel_launch_plan(project_root: str | Path) -> VesselLaunchPlan:
    root = Path(project_root)
    terminal = _detect_terminal_host()
    return VesselLaunchPlan(
        python_executable=sys.executable,
        forge_command=(sys.executable, '-m', 'singularity_works.runtime'),
        claude_target=_detect_claude_target(),
        terminal_host=terminal,
        project_root=str(root),
    )


def _host_command(host: TerminalHostSpec, title: str, command: Sequence[str]) -> tuple[str, ...] | None:
    if host.kind is TerminalHostKind.WINDOWS_TERMINAL:
        return (host.executable, 'new-tab', '--title', title, *command)
    if host.kind is TerminalHostKind.WEZTERM:
        return (host.executable, 'start', '--cwd', '.', '--', *command)
    if host.kind is TerminalHostKind.ALACRITTY:
        return (host.executable, '--title', title, '-e', *command)
    if host.kind is TerminalHostKind.CONHOST:
        return (host.executable, '/c', 'start', f'"{title}"', *command)
    return None


def _spawn_in_terminal(host: TerminalHostSpec, title: str, command: Sequence[str], cwd: str) -> ProcessLaunchReceipt:
    argv = _host_command(host, title, command)
    if argv is None:
        return ProcessLaunchReceipt(
            role=title,
            disposition=LaunchDisposition.SKIPPED,
            command=tuple(command),
            title=title,
            detail='no supported terminal host',
        )
    try:
        proc = subprocess.Popen(argv, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
    except Exception as exc:
        return ProcessLaunchReceipt(
            role=title,
            disposition=LaunchDisposition.FAILED,
            command=tuple(argv),
            title=title,
            detail=f'launch failed: {exc}',
        )
    return ProcessLaunchReceipt(
        role=title,
        disposition=LaunchDisposition.LAUNCHED,
        command=tuple(argv),
        title=title,
        detail='launched',
        pid=proc.pid,
    )


def plan_unified_front(plan: VesselLaunchPlan) -> UnifiedFrontReceipt:
    receipts: list[ProcessLaunchReceipt] = [
        ProcessLaunchReceipt(
            role='Singularity Works Forge',
            disposition=LaunchDisposition.SKIPPED,
            command=tuple(plan.forge_command),
            title='Singularity Works Forge',
            detail='planned launch',
        )
    ]
    if plan.claude_target is not None:
        receipts.append(
            ProcessLaunchReceipt(
                role=plan.claude_target.title_hint,
                disposition=LaunchDisposition.SKIPPED,
                command=(plan.claude_target.executable, *plan.claude_target.args),
                title=plan.claude_target.title_hint,
                detail='planned launch',
            )
        )
    readiness = VesselReadiness.READY if plan.claude_target is not None and plan.terminal_host.kind is not TerminalHostKind.UNKNOWN else VesselReadiness.HUD_ONLY if plan.terminal_host.kind is not TerminalHostKind.UNKNOWN else VesselReadiness.DEGRADED
    unified = plan.claude_target is not None and plan.terminal_host.kind is not TerminalHostKind.UNKNOWN
    return UnifiedFrontReceipt(readiness=readiness, unified_front_requested=True, unified_front_achieved=unified, receipts=tuple(receipts))


def launch_claude_vessel(plan: VesselLaunchPlan) -> UnifiedFrontReceipt:
    receipts: list[ProcessLaunchReceipt] = []
    forge_receipt = _spawn_in_terminal(plan.terminal_host, 'Singularity Works Forge', plan.forge_command, plan.project_root)
    receipts.append(forge_receipt)
    if plan.claude_target is not None:
        claude_command = (plan.claude_target.executable, *plan.claude_target.args)
        claude_receipt = _spawn_in_terminal(plan.terminal_host, plan.claude_target.title_hint, claude_command, plan.project_root)
        receipts.append(claude_receipt)
    readiness = VesselReadiness.DEGRADED
    if any(r.role == 'Singularity Works Forge' and r.disposition is LaunchDisposition.LAUNCHED for r in receipts):
        readiness = VesselReadiness.HUD_ONLY
    if len(receipts) >= 2 and all(r.disposition is LaunchDisposition.LAUNCHED for r in receipts[:2]):
        readiness = VesselReadiness.READY
    unified = len(receipts) >= 2 and all(r.disposition is LaunchDisposition.LAUNCHED for r in receipts[:2])
    return UnifiedFrontReceipt(
        readiness=readiness,
        unified_front_requested=True,
        unified_front_achieved=unified,
        receipts=tuple(receipts),
    )


def evaluate_vessel_surface(project_root: str | Path, *, anchor_supported: bool) -> VesselSurfaceState:
    doctor = run_vessel_doctor(project_root)
    plan = build_vessel_launch_plan(project_root)
    claude_available = plan.claude_target is not None
    gpu_terminal = plan.terminal_host.gpu_accelerated
    unified_front_possible = claude_available and plan.terminal_host.kind is not TerminalHostKind.UNKNOWN
    readiness = (
        VesselReadiness.READY if doctor.passed and unified_front_possible
        else VesselReadiness.HUD_ONLY if doctor.passed
        else VesselReadiness.DEGRADED
    )
    return VesselSurfaceState(
        readiness=readiness,
        claude_available=claude_available,
        gpu_terminal=gpu_terminal,
        anchor_supported=anchor_supported,
        unified_front_possible=unified_front_possible,
        terminal_kind=plan.terminal_host.kind.value,
        terminal_executable=plan.terminal_host.executable,
        claude_target=plan.claude_target.executable if plan.claude_target else "",
    )


def derive_session_state(surface: VesselSurfaceState, receipt: UnifiedFrontReceipt) -> VesselSessionState:
    active_roles = tuple(r.role for r in receipt.receipts if r.disposition is LaunchDisposition.LAUNCHED)
    failed_roles = tuple(r.role for r in receipt.receipts if r.disposition is LaunchDisposition.FAILED)
    if receipt.unified_front_achieved:
        return VesselSessionState(
            lifecycle=SessionLifecycleState.UNIFIED,
            relaunch_action=RelaunchAction.NONE,
            anchor_supported=surface.anchor_supported,
            active_roles=active_roles,
            failed_roles=failed_roles,
            rationale='forge and claude front achieved',
        )
    if surface.claude_available and receipt.readiness is VesselReadiness.HUD_ONLY:
        return VesselSessionState(
            lifecycle=SessionLifecycleState.HUD_ONLY,
            relaunch_action=RelaunchAction.RESTORE_UNIFIED_FRONT if surface.anchor_supported else RelaunchAction.CHECK_HOST,
            anchor_supported=surface.anchor_supported,
            active_roles=active_roles,
            failed_roles=failed_roles,
            rationale='claude is available but unified front not yet achieved',
        )
    if not surface.claude_available and receipt.readiness is VesselReadiness.HUD_ONLY:
        return VesselSessionState(
            lifecycle=SessionLifecycleState.HUD_ONLY,
            relaunch_action=RelaunchAction.LAUNCH_CLAUDE if surface.anchor_supported else RelaunchAction.CHECK_HOST,
            anchor_supported=surface.anchor_supported,
            active_roles=active_roles,
            failed_roles=failed_roles,
            rationale='forge is viable but claude target missing',
        )
    if receipt.readiness is VesselReadiness.DEGRADED:
        return VesselSessionState(
            lifecycle=SessionLifecycleState.DEGRADED,
            relaunch_action=RelaunchAction.CHECK_HOST,
            anchor_supported=surface.anchor_supported,
            active_roles=active_roles,
            failed_roles=failed_roles,
            rationale='host terminal or launch substrate degraded',
        )
    return VesselSessionState(
        lifecycle=SessionLifecycleState.PLANNED,
        relaunch_action=RelaunchAction.NONE,
        anchor_supported=surface.anchor_supported,
        active_roles=active_roles,
        failed_roles=failed_roles,
        rationale='vessel planned but not yet launched',
    )


@dataclass(frozen=True)
class PersistedVesselSession:
    updated_at: str
    lifecycle: str
    relaunch_action: str
    anchor_supported: bool
    active_roles: tuple[str, ...]
    failed_roles: tuple[str, ...]
    rationale: str
    front_readiness: str
    front_achieved: bool

    @classmethod
    def from_session(cls, session: VesselSessionState, receipt: UnifiedFrontReceipt) -> "PersistedVesselSession":
        return cls(
            updated_at=datetime.now(timezone.utc).isoformat(),
            lifecycle=session.lifecycle.value,
            relaunch_action=session.relaunch_action.value,
            anchor_supported=session.anchor_supported,
            active_roles=session.active_roles,
            failed_roles=session.failed_roles,
            rationale=session.rationale,
            front_readiness=receipt.readiness.value,
            front_achieved=receipt.unified_front_achieved,
        )


def vessel_session_state_path(project_root: str | Path) -> Path:
    from .cilnx_bridge import cilnx_session_state_path
    return cilnx_session_state_path(project_root)


def persist_vessel_session_state(project_root: str | Path, session: VesselSessionState, receipt: UnifiedFrontReceipt) -> Path:
    from .cilnx_bridge import persist_cockpit_session_state
    payload = PersistedVesselSession.from_session(session, receipt)
    return persist_cockpit_session_state(project_root, dict(payload.__dict__))


def load_vessel_session_state(project_root: str | Path) -> PersistedVesselSession | None:
    from .cilnx_bridge import load_cockpit_session_state
    raw = load_cockpit_session_state(project_root)
    if raw is None:
        return None
    return PersistedVesselSession(
        updated_at=str(raw.get('updated_at', '') or ''),
        lifecycle=str(raw.get('lifecycle', 'planned')),
        relaunch_action=str(raw.get('relaunch_action', 'none')),
        anchor_supported=bool(raw.get('anchor_supported', False)),
        active_roles=tuple(raw.get('active_roles', [])),
        failed_roles=tuple(raw.get('failed_roles', [])),
        rationale=str(raw.get('rationale', '')),
        front_readiness=str(raw.get('front_readiness', 'degraded')),
        front_achieved=bool(raw.get('front_achieved', False)),
    )


def vessel_state_path(project_root: str | Path) -> Path:
    return vessel_session_state_path(project_root)


def load_persisted_vessel_session(project_root: str | Path) -> PersistedVesselSession | None:
    return load_vessel_session_state(project_root)


def persist_vessel_session(project_root: str | Path, session: VesselSessionState, receipt: UnifiedFrontReceipt) -> PersistedVesselSession:
    persist_vessel_session_state(project_root, session, receipt)
    loaded = load_vessel_session_state(project_root)
    if loaded is None:
        raise RuntimeError('persisted vessel session missing after write')
    return loaded


@dataclass(frozen=True)
class VesselRecoveryState:
    persisted: bool
    previous_lifecycle: str
    current_lifecycle: str
    recommended_action: RelaunchAction
    reason: str

    def to_stats(self) -> dict[str, str]:
        return {
            "recovery": self.recommended_action.value,
            "prev_session": self.previous_lifecycle or "none",
        }


def derive_recovery_state(previous: PersistedVesselSession | None, current: VesselSessionState, surface: VesselSurfaceState) -> VesselRecoveryState:
    if previous is None:
        return VesselRecoveryState(
            persisted=False,
            previous_lifecycle='',
            current_lifecycle=current.lifecycle.value,
            recommended_action=current.relaunch_action,
            reason='no prior vessel session persisted',
        )
    if previous.lifecycle == 'unified' and current.lifecycle.value != 'unified':
        action = RelaunchAction.RESTORE_UNIFIED_FRONT if surface.anchor_supported else RelaunchAction.CHECK_HOST
        reason = 'previous session achieved unified front but current session regressed'
        return VesselRecoveryState(True, previous.lifecycle, current.lifecycle.value, action, reason)
    if previous.lifecycle == 'hud_only' and current.lifecycle.value == 'hud_only' and not surface.claude_available:
        return VesselRecoveryState(True, previous.lifecycle, current.lifecycle.value, RelaunchAction.LAUNCH_CLAUDE, 'repeated hud-only state with missing claude target')
    if previous.anchor_supported and not surface.anchor_supported:
        return VesselRecoveryState(True, previous.lifecycle, current.lifecycle.value, RelaunchAction.CHECK_HOST, 'anchor capability regressed since previous session')
    return VesselRecoveryState(True, previous.lifecycle, current.lifecycle.value, current.relaunch_action, 'current session remains doctrinally consistent with persisted state')
