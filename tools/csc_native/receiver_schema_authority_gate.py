"""Receiver schema authority gate for compact schema and runtime route consistency."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import TypedDict

from strict_json_boundary import write_json_boundary


class RouteInfo(TypedDict):
    rule: str
    endpoint: str
    methods: list[str]


class RuntimeRouteResult(TypedDict):
    ok: bool
    routes: list[RouteInfo]
    error: str | None
    traceback: str | None
    factory_used: str | None


class SchemaGateReport(TypedDict):
    created_at_utc: str
    clean: bool
    schema_policy: str
    baseline_root: str
    package_root: str
    route_import_ok: bool
    factory_used: str | None
    schema_path_count: int
    runtime_route_count: int
    schema_paths_missing_in_runtime_routes: list[str]
    runtime_only_route_count: int
    runtime_only_routes: list[dict[str, str]]
    unclassified_runtime_only_routes: list[str]
    route_result_error: str | None
    route_result_traceback: str | None


@dataclass(frozen=True)
class RouteGateConfig:
    project_root: Path
    baseline_root: Path
    report_path: Path


INTERNAL_ROUTE_CLASSIFICATIONS = MappingProxyType(
    {
        "/context/health": "internal_health_probe",
        "/files/tree": "legacy_convenience_route",
        "/lab/health": "internal_health_probe",
        "/lab/mcp/manifest": "internal_manifest_route",
        "/lab/mounts": "internal_mount_diagnostic",
        "/manifest": "internal_manifest_route",
        "/project/archives/extract": "legacy_archive_route_not_in_compact_schema",
        "/project/archives/inspect": "legacy_archive_route_not_in_compact_schema",
        "/project/checkpoints/create": "legacy_checkpoint_route_not_in_compact_schema",
        "/project/files/read_many": "legacy_batch_file_route_not_in_compact_schema",
        "/project/journal/append": "legacy_journal_route_not_in_compact_schema",
        "/project/journal/read": "legacy_journal_route_not_in_compact_schema",
        "/project/models/inspect": "legacy_model_route_not_in_compact_schema",
        "/project/models/list": "legacy_model_route_not_in_compact_schema",
        "/research/arxiv/paper": "legacy_research_route_not_in_compact_schema",
        "/research/arxiv/search": "legacy_research_route_not_in_compact_schema",
        "/research/health": "internal_health_probe",
        "/static/{filename}": "flask_static_route",
        "/status/{commit_id}": "legacy_status_alias",
    }
)


def _schema_path(config: RouteGateConfig) -> Path:
    package_root = config.baseline_root / "pcmmad_receiver"
    return package_root / "pcmmad_lab_action_schema_v10_3_pcmmad_native_protocol_compact_30_router.json"


def _schema_paths(config: RouteGateConfig) -> set[str]:
    schema = json.loads(_schema_path(config).read_text(encoding="utf-8"))
    paths = schema.get("paths") if isinstance(schema, Mapping) else {}
    return {str(path) for path in paths} if isinstance(paths, Mapping) else set()


def _route_methods(rule: object) -> list[str]:
    methods = getattr(rule, "methods", set())
    return sorted(method for method in methods if method not in {"HEAD", "OPTIONS"})


def _load_app_factory(config: RouteGateConfig) -> tuple[str, object]:
    sys.path.insert(0, str(config.baseline_root))
    sys.path.insert(0, str(config.baseline_root / "pcmmad_receiver"))
    from pcmmad_receiver.app_factory import create_app

    return "pcmmad_receiver.app_factory.create_app", create_app


def _runtime_route_result(config: RouteGateConfig) -> RuntimeRouteResult:
    try:
        factory_name, create_app = _load_app_factory(config)
        app = create_app()
        routes = [
            RouteInfo(rule=str(rule), endpoint=rule.endpoint, methods=_route_methods(rule))
            for rule in sorted(app.url_map.iter_rules(), key=lambda item: str(item))
        ]
        return RuntimeRouteResult(
            ok=True, routes=routes, error=None, traceback=None, factory_used=factory_name
        )
    except (ImportError, AttributeError, RuntimeError, ValueError, OSError) as exc:
        return RuntimeRouteResult(
            ok=False, routes=[], error=str(exc), traceback=None, factory_used=None
        )


def _normalize_runtime_path(path: str) -> str:
    if path == "/static/<path:filename>":
        return "/static/{filename}"
    return re.sub(r"<([^:>/]+:)?([^>/]+)>", r"{\2}", path)


def _runtime_paths(route_result: RuntimeRouteResult) -> set[str]:
    return {_normalize_runtime_path(route["rule"]) for route in route_result["routes"]}


def _runtime_only_routes(runtime_only: set[str]) -> list[dict[str, str]]:
    return [
        {"path": path, "classification": INTERNAL_ROUTE_CLASSIFICATIONS.get(path, "unclassified")}
        for path in sorted(runtime_only)
    ]


def _schema_policy() -> str:
    return (
        "compact 30-action schema authoritative; runtime-only routes " "classified internal/legacy"
    )


def _report(config: RouteGateConfig) -> SchemaGateReport:
    schema_paths = _schema_paths(config)
    route_result = _runtime_route_result(config)
    runtime_paths = _runtime_paths(route_result)
    missing = sorted(schema_paths - runtime_paths)
    runtime_only = runtime_paths - schema_paths
    unclassified = sorted(
        path for path in runtime_only if path not in INTERNAL_ROUTE_CLASSIFICATIONS
    )
    clean = bool(route_result["ok"]) and not missing and not unclassified
    return SchemaGateReport(
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        clean=clean,
        schema_policy=_schema_policy(),
        baseline_root=str(config.baseline_root),
        package_root=str(config.baseline_root / "pcmmad_receiver"),
        route_import_ok=bool(route_result["ok"]),
        factory_used=route_result["factory_used"],
        schema_path_count=len(schema_paths),
        runtime_route_count=len(runtime_paths),
        schema_paths_missing_in_runtime_routes=missing,
        runtime_only_route_count=len(runtime_only),
        runtime_only_routes=_runtime_only_routes(runtime_only),
        unclassified_runtime_only_routes=unclassified,
        route_result_error=route_result["error"],
        route_result_traceback=route_result["traceback"],
    )


def _config() -> RouteGateConfig:
    project_root = Path(__file__).resolve().parents[2]
    return RouteGateConfig(
        project_root=project_root,
        baseline_root=project_root / "baseline",
        report_path=project_root / "reports" / "RECEIVER_SCHEMA_AUTHORITY_GATE_REPORT.json",
    )


def main() -> None:
    config = _config()
    report = _report(config)
    write_json_boundary(config.report_path, report)
    sys.stdout.write(
        json.dumps({"report": str(config.report_path), "clean": report["clean"]}) + "\n"
    )
    if not report["clean"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
