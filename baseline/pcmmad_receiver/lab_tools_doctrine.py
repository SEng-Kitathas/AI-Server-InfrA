"""Doctrine/invariant lab-tool registration surface."""

from __future__ import annotations
from collections.abc import MutableMapping

from pathlib import Path
from typing import Any, Callable

from lab_tool_primitives import ToolPayload, ToolResult, payload_optional_int, payload_str
from server_hardening import safe_json_loads

JsonObject = MutableMapping[str, Any]
DoctrineRegistrar = Callable[
    ..., Callable[[Callable[[ToolPayload], ToolResult]], Callable[[ToolPayload], ToolResult]]
]

INVARIANT_ROOT = Path(__file__).resolve().parents[2] / "docs" / "universal_invariants"
MANIFEST_PATH = INVARIANT_ROOT / "UNIVERSAL_INVARIANT_MANIFEST.json"
GUIDE_PATH = INVARIANT_ROOT / "UNIVERSAL_CSC_DOCTRINE_CODE_STYLE_GUIDE.md"


def _load_manifest() -> JsonObject:
    if not MANIFEST_PATH.exists():
        return {"ok": False, "error": "manifest not found", "path": str(MANIFEST_PATH)}
    return safe_json_loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def _register_invariant_status(register_tool: DoctrineRegistrar) -> None:
    @register_tool(
        "doctrine.invariants.status",
        "Report universal CSC/doctrine/code-style invariant pack status.",
        "low",
        category="doctrine",
        tags=["csc", "doctrine", "style", "invariants"],
        side_effect_class="read",
        effect_traits=["reads_files", "reads_doctrine_state"],
    )
    def tool_doctrine_invariants_status(payload: ToolPayload) -> ToolResult:
        manifest = _load_manifest()
        return {
            "root": str(INVARIANT_ROOT),
            "manifest_path": str(MANIFEST_PATH),
            "guide_path": str(GUIDE_PATH),
            "manifest_exists": MANIFEST_PATH.exists(),
            "guide_exists": GUIDE_PATH.exists(),
            "manifest": manifest,
        }


def _register_invariant_read(register_tool: DoctrineRegistrar, error_cls: type[Exception]) -> None:
    @register_tool(
        "doctrine.invariants.read",
        "Read the universal CSC/doctrine/code-style invariant guide or manifest.",
        "low",
        category="doctrine",
        tags=["csc", "doctrine", "style", "invariants"],
        side_effect_class="read",
        effect_traits=["reads_files", "reads_doctrine_state"],
    )
    def tool_doctrine_invariants_read(payload: ToolPayload) -> ToolResult:
        target = payload_str(payload, "target", "guide").strip().lower()
        max_bytes = payload_optional_int(payload, "max_bytes")
        path = MANIFEST_PATH if target in {"manifest", "json"} else GUIDE_PATH
        if not path.exists():
            raise error_cls("NOT_FOUND", f"invariant target not found: {path}", 404)
        data = path.read_bytes()
        truncated = False
        if max_bytes is not None and max_bytes > 0 and len(data) > max_bytes:
            data = data[:max_bytes]
            truncated = True
        return {
            "target": target,
            "path": str(path),
            "bytes": path.stat().st_size,
            "truncated": truncated,
            "content": data.decode("utf-8", errors="replace"),
        }


def _register_invariant_search(
    register_tool: DoctrineRegistrar, error_cls: type[Exception]
) -> None:
    @register_tool(
        "doctrine.invariants.search",
        "Search within the universal CSC/doctrine/code-style invariant guide and source index.",
        "low",
        category="doctrine",
        tags=["csc", "doctrine", "style", "invariants", "search"],
        side_effect_class="read",
        effect_traits=["reads_files", "reads_doctrine_state", "bounded_results"],
    )
    def tool_doctrine_invariants_search(payload: ToolPayload) -> ToolResult:
        query = payload_str(payload, "query", "").strip().lower()
        if not query:
            raise error_cls("BAD_REQUEST", "query is required", 400)
        limit = payload_optional_int(payload, "limit") or 50
        hits: list[JsonObject] = []
        for path in [GUIDE_PATH, MANIFEST_PATH]:
            text = _read_text(path)
            for idx, line in enumerate(text.splitlines(), start=1):
                if query in line.lower():
                    hits.append({"path": str(path), "line": idx, "text": line[:1000]})
                    if len(hits) >= limit:
                        return {"query": query, "count": len(hits), "hits": hits, "partial": True}
        return {"query": query, "count": len(hits), "hits": hits, "partial": False}


def register_doctrine_tools(
    register_tool: DoctrineRegistrar, *, error_cls: type[Exception]
) -> None:
    _register_invariant_status(register_tool)
    _register_invariant_read(register_tool, error_cls)
    _register_invariant_search(register_tool, error_cls)
