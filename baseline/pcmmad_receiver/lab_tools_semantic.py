"""Semantic/Monster dual-retriever lab-tool registration surface.

The semantic plane is intentionally a thin runtime adapter over externally stored
semantic indexes/corpora.  It resolves and reports those resources explicitly;
it does not pretend that the receiver's own Python environment contains the
heavy retrieval stack.
"""

from __future__ import annotations

import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .lab_tool_primitives import ToolPayload, ToolResult, payload_optional_int, payload_str
from .server_hardening import run_subprocess_envelope, safe_json_loads

SemanticRegistrar = Callable[
    ..., Callable[[Callable[[ToolPayload], ToolResult]], Callable[[ToolPayload], ToolResult]]
]

_REQUIRED_MODULES = ("faiss", "numpy", "torch", "sentence_transformers", "transformers", "PIL", "peft", "torchvision")
_DEFAULT_MINILM_INDEX = Path(r"D:\PCMMAD_TQ2_GEOMETRIC_LAB\data\pcmmad_semantic_index_full")
_DEFAULT_JINA_INDEX = Path(r"D:\PCMMAD_TQ2_GEOMETRIC_LAB\data\pcmmad_semantic_index_jina_v4")
_DEFAULT_MINILM_MODEL = (
    Path.home()
    / ".cache"
    / "huggingface"
    / "hub"
    / "models--sentence-transformers--all-MiniLM-L6-v2"
    / "snapshots"
    / "c9745ed1d9f207416be6d2e6f8de32d1f16199bf"
)


@dataclass(frozen=True)
class ResolvedPath:
    path: Path
    source: str

    def to_dict(self) -> ToolResult:
        return {
            "path": str(self.path),
            "source": self.source,
            "exists": self.path.exists(),
        }


@dataclass(frozen=True)
class PythonProbe:
    path: Path
    source: str
    execution_ok: bool
    modules: dict[str, bool]
    probe: ToolResult

    @property
    def qualified(self) -> bool:
        return self.execution_ok and all(self.modules.get(name, False) for name in _REQUIRED_MODULES)

    def to_dict(self) -> ToolResult:
        return {
            "path": str(self.path),
            "source": self.source,
            "exists": self.path.exists(),
            "qualified": self.qualified,
            "modules": dict(self.modules),
            "probe_ok": self.execution_ok,
            "return_code": self.probe.get("return_code"),
            "stderr": self.probe.get("stderr"),
        }


def _first_nonempty(*values: str | None) -> str | None:
    for value in values:
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _projects_root() -> Path | None:
    explicit = _first_nonempty(os.environ.get("PCMMAD_PROJECTS_ROOT"))
    if explicit:
        return Path(explicit)
    pcmmad_root = _first_nonempty(os.environ.get("PCMMAD_ROOT"))
    if pcmmad_root:
        candidate = Path(pcmmad_root) / "projects"
        if candidate.exists():
            return candidate
    # Migration-aware fallback.  It is only selected when it actually exists and
    # is reported as a fallback source rather than silently treated as doctrine.
    fallback = Path(r"E:\new pc\AI_Pushes_Sandbox\projects")
    return fallback if fallback.exists() else None


def _resolve_script(payload: ToolPayload) -> ResolvedPath:
    explicit = payload_str(payload, "script_path", "").strip()
    if explicit:
        return ResolvedPath(Path(explicit), "payload.script_path")
    env_value = _first_nonempty(os.environ.get("MONSTER_DUAL_RETRIEVER_PATH"))
    if env_value:
        return ResolvedPath(Path(env_value), "env.MONSTER_DUAL_RETRIEVER_PATH")
    root = _projects_root()
    candidates: list[tuple[Path, str]] = []
    if root is not None:
        candidates.extend(
            [
                (
                    root / "cto-chat-thread-organizer" / "tools" / "db_helper" / "monster_dual_retriever.py",
                    "projects.cto_evolved_donor",
                ),
                (
                    root
                    / "monster-standard-inference-revival-2026-04-06"
                    / "tools"
                    / "db_helper"
                    / "monster_dual_retriever.py",
                    "projects.monster_ancestry",
                ),
            ]
        )
    for path, source in candidates:
        if path.is_file():
            return ResolvedPath(path, source)
    fallback = candidates[0][0] if candidates else Path("monster_dual_retriever.py")
    return ResolvedPath(fallback, "unresolved")


def _resolve_db_path(payload: ToolPayload) -> ResolvedPath:
    explicit = payload_str(payload, "db_path", "").strip()
    if explicit:
        return ResolvedPath(Path(explicit), "payload.db_path")
    env_value = _first_nonempty(os.environ.get("MONSTER_DB_HELPER_DB_PATH"))
    if env_value:
        return ResolvedPath(Path(env_value), "env.MONSTER_DB_HELPER_DB_PATH")
    root = _projects_root()
    if root is not None:
        return ResolvedPath(
            root / "pcmmad_ingress" / "pcmmad_corpus_analysis.sqlite",
            "projects.pcmmad_ingress",
        )
    return ResolvedPath(Path("pcmmad_corpus_analysis.sqlite"), "unresolved")


def _resolved_payload_or_env_path(
    payload: ToolPayload,
    payload_key: str,
    env_key: str,
    default: Path,
    default_source: str,
) -> ResolvedPath:
    explicit = payload_str(payload, payload_key, "").strip()
    if explicit:
        return ResolvedPath(Path(explicit), f"payload.{payload_key}")
    env_value = _first_nonempty(os.environ.get(env_key))
    if env_value:
        return ResolvedPath(Path(env_value), f"env.{env_key}")
    return ResolvedPath(default, default_source)


def _resolve_minilm_index(payload: ToolPayload) -> ResolvedPath:
    return _resolved_payload_or_env_path(
        payload,
        "minilm_index_dir",
        "MONSTER_DB_HELPER_MINILM_INDEX_DIR",
        _DEFAULT_MINILM_INDEX,
        "legacy_tq2_index_root",
    )


def _resolve_jina_index(payload: ToolPayload) -> ResolvedPath:
    return _resolved_payload_or_env_path(
        payload,
        "jina_index_dir",
        "MONSTER_DB_HELPER_JINA_INDEX_DIR",
        _DEFAULT_JINA_INDEX,
        "legacy_tq2_index_root",
    )


def _resolve_minilm_model(payload: ToolPayload) -> ResolvedPath:
    explicit = payload_str(payload, "minilm_model_path", "").strip()
    if explicit:
        return ResolvedPath(Path(explicit), "payload.minilm_model_path")
    env_value = _first_nonempty(os.environ.get("MONSTER_DB_HELPER_MINILM_MODEL_PATH"))
    if env_value:
        return ResolvedPath(Path(env_value), "env.MONSTER_DB_HELPER_MINILM_MODEL_PATH")
    root = _projects_root()
    if root is not None:
        deployment = (
            root
            / "PCMMAD_RECEIVER_LAB"
            / "runtimes"
            / "models"
            / "all-MiniLM-L6-v2"
        )
        if deployment.is_dir():
            return ResolvedPath(deployment, "pcmmad_lab_model_runtime")
    return ResolvedPath(_DEFAULT_MINILM_MODEL, "user_hf_cache")


def _dependency_probe(python_path: Path, cwd: Path) -> PythonProbe:
    # Keep this single-line so the command cannot be corrupted by nested newline
    # escaping when passed through Windows `python -c`.
    code = (
        "import importlib.util,json,sys; "
        f"mods={list(_REQUIRED_MODULES)!r}; "
        "sys.stdout.write(json.dumps({m: importlib.util.find_spec(m) is not None for m in mods}, sort_keys=True))"
    )
    result = run_subprocess_envelope(
        [str(python_path), "-c", code],
        cwd=cwd,
        timeout_seconds=15,
        stdout_max_bytes=8192,
        stderr_max_bytes=8192,
    )
    modules: dict[str, bool] = {}
    if result.get("ok"):
        try:
            parsed = safe_json_loads(str(result.get("stdout") or "{}"))
            if isinstance(parsed, dict):
                modules = {name: bool(parsed.get(name, False)) for name in _REQUIRED_MODULES}
        except (TypeError, ValueError):
            modules = {}
    return PythonProbe(
        path=python_path,
        source="probe",
        execution_ok=bool(result.get("ok")),
        modules=modules,
        probe=result,
    )


def _python_candidates(payload: ToolPayload, script: ResolvedPath) -> list[tuple[Path, str]]:
    explicit = payload_str(payload, "python_executable", "").strip()
    if explicit:
        return [(Path(explicit), "payload.python_executable")]
    env_value = _first_nonempty(
        os.environ.get("MONSTER_PYTHON_EXECUTABLE"),
        os.environ.get("MONSTER_PYTHON"),
    )
    if env_value:
        return [(Path(env_value), "env.MONSTER_PYTHON_EXECUTABLE")]

    candidates: list[tuple[Path, str]] = []
    # A donor-local environment is preferred if it exists, but is never assumed.
    donor_root = script.path.parent.parent.parent if len(script.path.parents) >= 3 else script.path.parent
    candidates.append((donor_root / ".venv" / "Scripts" / "python.exe", "script_project_venv"))
    root = _projects_root()
    if root is not None:
        candidates.extend(
            [
                (
                    root
                    / "PCMMAD_RECEIVER_LAB"
                    / "runtimes"
                    / "semantic_monster_py312"
                    / "Scripts"
                    / "python.exe",
                    "pcmmad_lab_semantic_runtime",
                ),
                (
                    root / "pcmmad_ingress" / ".venv" / "Scripts" / "python.exe",
                    "pcmmad_ingress_venv",
                ),
            ]
        )
    candidates.extend(
        [
            (Path(r"D:\PCMMAD_TQ2_GEOMETRIC_LAB\.venv_cuda\Scripts\python.exe"), "legacy_tq2_venv"),
            (Path(sys.executable), "receiver_python"),
        ]
    )
    seen: set[str] = set()
    unique: list[tuple[Path, str]] = []
    for path, source in candidates:
        key = str(path).casefold()
        if key not in seen:
            seen.add(key)
            unique.append((path, source))
    return unique


def _probe_python_candidates(payload: ToolPayload, script: ResolvedPath) -> tuple[PythonProbe | None, list[ToolResult]]:
    probes: list[ToolResult] = []
    selected: PythonProbe | None = None
    cwd = script.path.parent if script.path.parent.exists() else Path.cwd()
    for path, source in _python_candidates(payload, script):
        if not path.is_file():
            probes.append(
                {
                    "path": str(path),
                    "source": source,
                    "exists": False,
                    "qualified": False,
                    "modules": {},
                    "probe_ok": False,
                }
            )
            continue
        probe = _dependency_probe(path, cwd)
        probe = PythonProbe(
            path=probe.path,
            source=source,
            execution_ok=probe.execution_ok,
            modules=probe.modules,
            probe=probe.probe,
        )
        probes.append(probe.to_dict())
        if probe.qualified:
            selected = probe
            break
        # Explicit runtime selection is authoritative enough to stop fallback;
        # health should report why that explicit choice is not qualified.
        if source.startswith("payload.") or source.startswith("env."):
            break
    return selected, probes


def _nonempty_file(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def _minilm_model_qualification(path: Path) -> dict[str, object]:
    required_text = [
        "config.json",
        "modules.json",
        "1_Pooling/config.json",
        "tokenizer_config.json",
    ]
    text_ok = {name: _nonempty_file(path / name) for name in required_text}
    weight_candidates = ["model.safetensors", "pytorch_model.bin"]
    tokenizer_candidates = ["tokenizer.json", "vocab.txt"]
    weights_ok = any(_nonempty_file(path / name) for name in weight_candidates)
    tokenizer_ok = any(_nonempty_file(path / name) for name in tokenizer_candidates)
    return {
        "qualified": bool(path.is_dir() and all(text_ok.values()) and weights_ok and tokenizer_ok),
        "required_text_files": text_ok,
        "weights_ok": weights_ok,
        "tokenizer_ok": tokenizer_ok,
    }


def _sha256_if_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _semantic_resolution(payload: ToolPayload) -> ToolResult:
    script = _resolve_script(payload)
    db = _resolve_db_path(payload)
    minilm_index = _resolve_minilm_index(payload)
    jina_index = _resolve_jina_index(payload)
    minilm_model = _resolve_minilm_model(payload)
    selected_python, python_probes = _probe_python_candidates(payload, script)

    minilm_model_info = minilm_model.to_dict()
    minilm_model_info["qualification"] = _minilm_model_qualification(minilm_model.path)
    resources = {
        "script": {**script.to_dict(), "sha256": _sha256_if_file(script.path)},
        "db": db.to_dict(),
        "minilm_index": minilm_index.to_dict(),
        "jina_index": jina_index.to_dict(),
        "minilm_model": minilm_model_info,
    }
    blockers: list[str] = []
    for name, info in resources.items():
        if not bool(info.get("exists")):
            blockers.append(f"missing_{name}")
    if minilm_model.path.exists() and not bool(minilm_model_info["qualification"]["qualified"]):
        blockers.append("invalid_minilm_model")
    if selected_python is None:
        blockers.append("no_qualified_python_runtime")

    available = not blockers
    selected_view = selected_python.to_dict() if selected_python else None
    compatibility_probe = selected_view or (python_probes[-1] if python_probes else None)
    return {
        "status": "online" if available else "unavailable",
        "available": available,
        "blockers": blockers,
        # Backward-compatible projections.  These are derived from `resources` /
        # `python` and are not independent authority surfaces.
        "script_path": str(script.path),
        "script_exists": script.path.exists(),
        "script_size": script.path.stat().st_size if script.path.is_file() else None,
        "dependency_probe": {
            "probe": compatibility_probe,
            "dependencies": dict((compatibility_probe or {}).get("modules", {})),
        },
        "defaults": {
            "db_path_default": str(db.path),
            "minilm_index_default": str(minilm_index.path),
            "jina_index_default": str(jina_index.path),
        },
        "default_paths_exist": {
            "db": db.path.exists(),
            "minilm_index": minilm_index.path.exists(),
            "jina_index": jina_index.path.exists(),
        },
        "resources": resources,
        "python": {
            "selected": selected_view,
            "candidates": python_probes,
            "required_modules": list(_REQUIRED_MODULES),
        },
        "env_overrides": {
            "MONSTER_DUAL_RETRIEVER_PATH": os.environ.get("MONSTER_DUAL_RETRIEVER_PATH"),
            "MONSTER_PYTHON_EXECUTABLE": os.environ.get("MONSTER_PYTHON_EXECUTABLE"),
            "MONSTER_DB_HELPER_DB_PATH": os.environ.get("MONSTER_DB_HELPER_DB_PATH"),
            "MONSTER_DB_HELPER_MINILM_INDEX_DIR": os.environ.get("MONSTER_DB_HELPER_MINILM_INDEX_DIR"),
            "MONSTER_DB_HELPER_JINA_INDEX_DIR": os.environ.get("MONSTER_DB_HELPER_JINA_INDEX_DIR"),
            "MONSTER_DB_HELPER_MINILM_MODEL_PATH": os.environ.get("MONSTER_DB_HELPER_MINILM_MODEL_PATH"),
        },
    }


MONSTER_BASE_PROPERTIES={"script_path":{"type":"string"},"db_path":{"type":"string"},"minilm_index_dir":{"type":"string"},"jina_index_dir":{"type":"string"},"minilm_model_path":{"type":"string"},"python_executable":{"type":"string"}}
MONSTER_HEALTH_SCHEMA={"type":"object","additionalProperties":False,"properties":MONSTER_BASE_PROPERTIES}
MONSTER_SEARCH_SCHEMA={"type":"object","additionalProperties":False,"properties":{**MONSTER_BASE_PROPERTIES,"query":{"type":"string"},"search":{"type":"string"},"topk":{"type":"integer","minimum":1},"k":{"type":"integer","minimum":1}}}

def _register_monster_health(register_tool: SemanticRegistrar) -> None:
    @register_tool(
        "semantic.monster.health",
        (
            "Inspect Monster/Chimera retriever availability, resolved data/index paths, "
            "qualified Python runtime, and explicit blockers."
        ),
        "low",
        category="semantic",
        tags=["monster", "retrieval", "semantic", "database", "availability"],
        side_effect_class="read_probe",
        effect_traits=["reads_files", "hashes_content", "spawns_process", "probes_dependencies", "bounded_subprocess_output", "availability_probe"],
        input_schema=MONSTER_HEALTH_SCHEMA,
    )
    def tool_semantic_monster_health(payload: ToolPayload) -> ToolResult:
        return _semantic_resolution(payload)


def _monster_query_spec(
    payload: ToolPayload, error_cls: type[Exception]
) -> tuple[str, int, ToolResult]:
    query = payload_str(payload, "query", "").strip() or payload_str(payload, "search", "").strip()
    if not query:
        raise error_cls("BAD_REQUEST", "query is required", 400)
    topk = payload_optional_int(payload, "topk") or payload_optional_int(payload, "k") or 10
    topk = topk if topk > 0 else 10
    resolution = _semantic_resolution(payload)
    if not resolution.get("available"):
        raise error_cls(
            "SEMANTIC_UNAVAILABLE",
            "Monster/Chimera semantic retriever is not currently executable",
            503,
            blockers=resolution.get("blockers", []),
            resolution=resolution,
        )
    return query, topk, resolution


def _parse_monster_stdout(result: ToolResult) -> object | None:
    if not result.get("stdout"):
        return None
    try:
        return safe_json_loads(str(result["stdout"]))
    except (TypeError, ValueError):
        return None


def _monster_search_payload(payload: ToolPayload, error_cls: type[Exception]) -> ToolResult:
    query, topk, resolution = _monster_query_spec(payload, error_cls)
    resources = resolution["resources"]
    selected_python = resolution["python"]["selected"]
    script_path = Path(str(resources["script"]["path"]))
    python_path = Path(str(selected_python["path"]))
    child_env = os.environ.copy()
    child_env.update(
        {
            "MONSTER_DB_HELPER_DB_PATH": str(resources["db"]["path"]),
            "MONSTER_DB_HELPER_MINILM_INDEX_DIR": str(resources["minilm_index"]["path"]),
            "MONSTER_DB_HELPER_JINA_INDEX_DIR": str(resources["jina_index"]["path"]),
            "MONSTER_DB_HELPER_MINILM_MODEL_PATH": str(resources["minilm_model"]["path"]),
        }
    )
    result = run_subprocess_envelope(
        [str(python_path), str(script_path), "--search", query, "--topk", str(topk)],
        cwd=script_path.parent,
        timeout_seconds=None,
        stdout_max_bytes=None,
        stderr_max_bytes=None,
        env=child_env,
    )
    if not bool(result.get("ok")):
        raise error_cls(
            "SEMANTIC_EXECUTION_FAILED",
            "Monster/Chimera retriever process failed",
            502,
            runtime={
                "python": str(python_path),
                "script": str(script_path),
                "script_sha256": resources["script"].get("sha256"),
            },
            execution=result,
        )
    parsed = _parse_monster_stdout(result)
    if parsed is None:
        raise error_cls(
            "SEMANTIC_OUTPUT_INVALID",
            "Monster/Chimera retriever completed but did not emit valid JSON",
            502,
            runtime={
                "python": str(python_path),
                "script": str(script_path),
                "script_sha256": resources["script"].get("sha256"),
            },
            execution=result,
        )
    return {
        "query": query,
        "topk": topk,
        "runtime": {
            "python": str(python_path),
            "script": str(script_path),
            "script_sha256": resources["script"].get("sha256"),
        },
        "execution": result,
        "parsed": parsed,
        "parsed_ok": parsed is not None,
    }


def _semantic_default_search_availability() -> ToolResult:
    resolution = _semantic_resolution({})
    selected = (resolution.get("python") or {}).get("selected") if isinstance(resolution, dict) else None
    return {
        "status": "available" if bool(resolution.get("available")) else "unavailable",
        "available": bool(resolution.get("available")),
        "blockers": list(resolution.get("blockers") or [])[:16],
        "basis": "semantic_default_runtime_probe",
        "selected_python": (selected or {}).get("path") if isinstance(selected, dict) else None,
    }


def _register_monster_search(register_tool: SemanticRegistrar, error_cls: type[Exception]) -> None:
    @register_tool(
        "semantic.monster.search",
        "Run the qualified Monster/Chimera dual semantic retriever in its resolved execution environment.",
        "medium",
        category="semantic",
        tags=["monster", "retrieval", "semantic", "database"],
        side_effect_class="execution",
        effect_traits=["executes_code", "heavy_compute", "reads_state", "may_write_cache"],
        availability_mode="dynamic",
        availability_scope="default_runtime; per-call explicit path/runtime overrides may change outcome",
        availability_provider_id="semantic.monster.default_runtime",
        availability_provider=_semantic_default_search_availability,
        input_schema=MONSTER_SEARCH_SCHEMA,
    )
    def tool_semantic_monster_search(payload: ToolPayload) -> ToolResult:
        return _monster_search_payload(payload, error_cls)


def register_semantic_tools(
    register_tool: SemanticRegistrar, *, error_cls: type[Exception]
) -> None:
    _register_monster_health(register_tool)
    _register_monster_search(register_tool, error_cls)
