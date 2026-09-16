"""Lab plugin discovery and registration boundary for optional server-side tool extensions."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path
from typing import Callable

from control_plane_models import PluginLoadRecord


class PluginLoadError(Exception):
    """Plugin load failure with structured propagation through lab tool registry."""


def discover_plugin_modules(base_dir: Path) -> list[Path]:
    plugins_dir = base_dir / "lab_plugins"
    if not plugins_dir.exists():
        return []
    return sorted([p for p in plugins_dir.glob("*.py") if p.name != "__init__.py"])


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_plugins(base_dir: Path, register_func: Callable) -> list[PluginLoadRecord]:
    loaded: list[PluginLoadRecord] = []
    touched_modules: list[tuple[str, object | None]] = []
    try:
        for path in discover_plugin_modules(base_dir):
            module_name = f"pcmmad_lab_plugin_{path.stem}"
            spec = importlib.util.spec_from_file_location(module_name, path)
            if not spec or not spec.loader:
                raise PluginLoadError(f"unable to load plugin spec: {path}")
            previous = sys.modules.get(module_name)
            touched_modules.append((module_name, previous))
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            try:
                spec.loader.exec_module(module)
                if hasattr(module, "register"):
                    module.register(register_func)
            except Exception as exc:
                raise PluginLoadError(f"plugin load failed: {path}: {exc}") from exc
            loaded.append(
                PluginLoadRecord(
                    module=module_name,
                    path=str(path),
                    sha256=_file_sha256(path),
                )
            )
        return loaded
    except Exception:
        for module_name, previous in reversed(touched_modules):
            if previous is None:
                sys.modules.pop(module_name, None)
            else:
                sys.modules[module_name] = previous
        raise

