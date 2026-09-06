"""Generate or verify the immutable PCMMAD V29 release-body manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_JSON = PROJECT_ROOT / "PACKAGE_MANIFEST_V29.json"
MANIFEST_SHA256 = PROJECT_ROOT / "MANIFEST.sha256"

EXCLUDED_TOP_LEVEL = {
    ".git",
    ".pytest_cache",
    "reports",
    "data",
    "browser_screenshots",
    "browser_bridge_logs",
}
EXCLUDED_NAMES = {
    "MANIFEST.sha256",
    "PACKAGE_MANIFEST_V29.json",
    "pcmmad_lab_action_schema_ACTIVE.json",
    "PCMMAD_LOCAL_ENV.cmd",
}


def _excluded(relative: Path) -> bool:
    if not relative.parts:
        return True
    if relative.parts[0] in EXCLUDED_TOP_LEVEL:
        return True
    if relative.name in EXCLUDED_NAMES:
        return True
    if any(
        part in {".venv", "__pycache__"} or part.startswith(".pcmmad_gate_runtime")
        for part in relative.parts
    ):
        return True
    return relative.suffix in {".pyc", ".pyo"}


def _body_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if _excluded(relative) or relative.suffix in {".pyc", ".pyo"}:
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(root).as_posix())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(root: Path) -> dict[str, object]:
    entries = [
        {
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in _body_files(root)
    ]
    return {
        "format": "pcmmad.release-body-manifest.v1",
        "release": "PCMMAD Receiver V29 Native Protocol Release Candidate",
        "root": ".",
        "exclusions": {
            "mutable_top_level": sorted(EXCLUDED_TOP_LEVEL),
            "machine_local_names": sorted(EXCLUDED_NAMES),
            "generated_or_interpreter_state": [".venv", "__pycache__", "*.pyc", "*.pyo"],
        },
        "file_count": len(entries),
        "total_bytes": sum(int(item["bytes"]) for item in entries),
        "files": entries,
    }


def write_manifest(root: Path) -> None:
    manifest = build_manifest(root)
    MANIFEST_JSON.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    lines = [f"{item['sha256']}  {item['path']}" for item in manifest["files"]]
    MANIFEST_SHA256.write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_manifest(root: Path) -> tuple[bool, list[str]]:
    manifest_path = root / MANIFEST_JSON.name
    if not manifest_path.exists():
        return False, ["manifest missing"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {str(item["path"]): item for item in manifest.get("files", [])}
    actual = {
        path.relative_to(root).as_posix(): {
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in _body_files(root)
    }
    failures: list[str] = []
    for name in sorted(expected.keys() - actual.keys()):
        failures.append(f"missing: {name}")
    for name in sorted(actual.keys() - expected.keys()):
        failures.append(f"unmanifested: {name}")
    for name in sorted(expected.keys() & actual.keys()):
        if int(expected[name]["bytes"]) != int(actual[name]["bytes"]):
            failures.append(f"size mismatch: {name}")
        if str(expected[name]["sha256"]) != str(actual[name]["sha256"]):
            failures.append(f"hash mismatch: {name}")
    return not failures, failures


def verify_zip(zip_path: Path) -> tuple[bool, list[str]]:
    failures: list[str] = []
    try:
        with zipfile.ZipFile(zip_path) as archive:
            bad = archive.testzip()
            if bad:
                failures.append(f"corrupt zip member: {bad}")
            names = archive.namelist()
            for info in archive.infolist():
                name = info.filename
                normalized = name.replace("\\", "/")
                posix = PurePosixPath(normalized)
                windows = PureWindowsPath(name)
                unix_mode = (info.external_attr >> 16) & 0xFFFF
                file_type = stat.S_IFMT(unix_mode) if unix_mode else 0
                if (
                    posix.is_absolute()
                    or windows.is_absolute()
                    or windows.drive
                    or any(part == ".." for part in posix.parts)
                ):
                    failures.append(f"unsafe zip member: {name}")
                if file_type and file_type not in {stat.S_IFREG, stat.S_IFDIR}:
                    failures.append(f"special zip member: {name}")
            roots = {PurePosixPath(name.replace("\\", "/")).parts[0] for name in names if name}
            if len(roots) != 1:
                failures.append(f"expected one top-level directory, got {sorted(roots)}")
            if not failures:
                with tempfile.TemporaryDirectory() as temp:
                    archive.extractall(temp)
                    clean, manifest_failures = verify_manifest(Path(temp) / next(iter(roots)))
                    if not clean:
                        failures.extend(manifest_failures)
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        failures.append(f"{type(exc).__name__}: {exc}")
    return not failures, failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--zip", type=Path)
    args = parser.parse_args()
    if args.write:
        write_manifest(PROJECT_ROOT)
    clean, failures = verify_zip(args.zip) if args.zip else verify_manifest(PROJECT_ROOT)
    print(json.dumps({"clean": clean, "failures": failures}, indent=2))
    raise SystemExit(0 if clean else 1)


if __name__ == "__main__":
    main()
