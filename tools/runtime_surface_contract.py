"""Verify the promoted PCMMAD route, native-tool, protocol, and GPT surface counts."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "baseline" / "pcmmad_receiver"
REPORT = ROOT / "reports" / "PCMMAD_RUNTIME_SURFACE_CONTRACT.json"
SCHEMA = RUNTIME / "pcmmad_lab_action_schema_v10_3_pcmmad_native_protocol_compact_30_router.json"


def _prepare_isolated_roots() -> None:
    base = Path(tempfile.mkdtemp(prefix="pcmmad_surface_contract_"))
    os.environ.setdefault("PCMMAD_ROOT", str(base / "root"))
    os.environ.setdefault("PCMMAD_PROJECTS_ROOT", str(base / "root" / "projects"))
    os.environ.setdefault("PCMMAD_SYSTEM_ROOT", str(base / "root" / "system"))
    os.environ.setdefault("PCMMAD_SANDBOX_ROOT", str(base / "root" / "sandbox"))
    os.environ.setdefault("PCMMAD_TEMP_ROOT", str(base / "temp"))
    os.environ.setdefault("GITHOME_API_KEY", "surface-contract-test-key")


def main() -> None:
    _prepare_isolated_roots()
    sys.path.insert(0, str(ROOT / "baseline"))
    sys.path.insert(0, str(RUNTIME))
    from pcmmad_receiver.app_factory import create_app
    from pcmmad_receiver.lab_tools import list_tools

    app = create_app()
    routes = sorted(str(rule) for rule in app.url_map.iter_rules())
    tools = list_tools()
    tool_names = sorted(str(item["name"]) for item in tools)
    protocol_tools = [name for name in tool_names if name.startswith("protocol.")]
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    operation_ids = [
        operation["operationId"]
        for path_item in schema["paths"].values()
        for operation in path_item.values()
        if isinstance(operation, dict) and "operationId" in operation
    ]
    checks = {
        "runtime_routes_at_least_49": len(routes) >= 49,
        "registered_tools_at_least_87": len(tool_names) >= 87,
        "protocol_tools_exactly_12": len(protocol_tools) == 12,
        "custom_gpt_operations_exactly_30": len(operation_ids) == 30,
        "custom_gpt_operation_ids_unique": len(set(operation_ids)) == 30,
    }
    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "clean": all(checks.values()),
        "checks": checks,
        "runtime_route_count": len(routes),
        "registered_tool_count": len(tool_names),
        "protocol_tool_count": len(protocol_tools),
        "custom_gpt_operation_count": len(operation_ids),
        "routes": routes,
        "protocol_tools": protocol_tools,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(REPORT), "clean": report["clean"], "counts": {
        "routes": len(routes), "tools": len(tool_names), "protocol_tools": len(protocol_tools), "operations": len(operation_ids)
    }}, indent=2))
    raise SystemExit(0 if report["clean"] else 1)


if __name__ == "__main__":
    main()
