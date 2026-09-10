"""Assemble the Flask application from explicit required and optional route families."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Callable

from flask import Blueprint, Flask

from .access_logging import install_access_logging
from .control_plane_models import BlueprintFailureSpec, BootReport, BootRuntimeStatus


class RequiredBlueprintLoadError(RuntimeError):
    """A required route family could not be embodied into the running app."""


@dataclass(frozen=True)
class BlueprintLoadSpec:
    module_name: str
    blueprint_name: str
    required: bool = True


@dataclass(frozen=True)
class RuntimeStartSpec:
    module_name: str
    callable_name: str
    success_field: str
    error_field: str


BLUEPRINTS: tuple[BlueprintLoadSpec, ...] = (
    BlueprintLoadSpec("legacy_routes", "legacy_bp"),
    BlueprintLoadSpec("execution_routes", "execution_bp"),
    BlueprintLoadSpec("power_routes", "power_bp"),
    BlueprintLoadSpec("lab_routes", "lab_bp"),
    BlueprintLoadSpec("transfer_plane", "transfer_bp"),
    BlueprintLoadSpec("research_routes", "research_bp", required=False),
    BlueprintLoadSpec("context_routes", "context_bp", required=False),
    BlueprintLoadSpec("observability", "observability_bp", required=False),
)

RUNTIME_STARTERS: tuple[RuntimeStartSpec, ...] = (
    RuntimeStartSpec(
        "execution_routes",
        "_ensure_scheduler_started",
        "execution_started",
        "execution_error",
    ),
    RuntimeStartSpec(
        "lab_routes",
        "_ensure_batch_executor",
        "lab_executor_started",
        "lab_executor_error",
    ),
)


def _load_blueprint(spec: BlueprintLoadSpec) -> Blueprint:
    module = import_module(spec.module_name)
    blueprint = getattr(module, spec.blueprint_name)
    if not isinstance(blueprint, Blueprint):
        raise TypeError(
            f"{spec.module_name}.{spec.blueprint_name} is not a Flask Blueprint"
        )
    return blueprint


def _record_blueprint_failure(
    app: Flask,
    spec: BlueprintLoadSpec,
    boot_report: BootReport,
    exc: Exception,
) -> None:
    error = f"{type(exc).__name__}: {exc}"
    boot_report.record_failure(
        BlueprintFailureSpec(
            module=spec.module_name,
            blueprint=spec.blueprint_name,
            error=error,
            required=spec.required,
        )
    )
    if spec.required:
        raise RequiredBlueprintLoadError(
            f"required blueprint failed: {spec.module_name}.{spec.blueprint_name}: {error}"
        ) from exc
    app.logger.warning(
        "optional blueprint unavailable: module=%s blueprint=%s error=%s",
        spec.module_name,
        spec.blueprint_name,
        error,
    )


def _register_blueprint(app: Flask, spec: BlueprintLoadSpec, boot_report: BootReport) -> None:
    try:
        blueprint = _load_blueprint(spec)
        app.register_blueprint(blueprint)
        boot_report.record_loaded(module=spec.module_name, blueprint=spec.blueprint_name)
    except Exception as exc:  # boundary: plugin/import failures must become boot evidence
        _record_blueprint_failure(app, spec, boot_report, exc)


def _start_runtime_component(spec: RuntimeStartSpec, status: BootRuntimeStatus) -> None:
    try:
        module = import_module(spec.module_name)
        starter: Callable[[], object] = getattr(module, spec.callable_name)
        starter()
        setattr(status, spec.success_field, True)
    except Exception as exc:  # boundary: degraded runtime is visible through health evidence
        setattr(status, spec.error_field, f"{type(exc).__name__}: {exc}")


def create_app() -> Flask:
    """Create one receiver app; required route-family failures are never silently degraded."""

    app = Flask(__name__)
    install_access_logging(app)
    boot_report = BootReport()
    for spec in BLUEPRINTS:
        _register_blueprint(app, spec, boot_report)

    boot_runtime = BootRuntimeStatus()
    for spec in RUNTIME_STARTERS:
        _start_runtime_component(spec, boot_runtime)

    app.config["PCMMAD_BOOT_REPORT"] = boot_report.to_dict()
    app.config["PCMMAD_BOOT_RUNTIME"] = boot_runtime.to_dict()
    app.config["PCMMAD_BOOT_DEGRADED"] = bool(
        boot_report.degraded() or boot_runtime.degraded()
    )
    return app
