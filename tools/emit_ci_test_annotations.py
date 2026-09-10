from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def _escape(value: str) -> str:
    return (
        value.replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
        .replace(":", "%3A")
        .replace(",", "%2C")
    )


def _emit(title: str, body: str) -> None:
    print(f"::error title={_escape(title)}::{_escape(body[:3500])}")


def main() -> int:
    if len(sys.argv) not in {2, 3}:
        print("usage: emit_ci_test_annotations.py <junit.xml> [pytest-output.txt]", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) == 3 else None
    output_tail = ""
    if output_path is not None and output_path.is_file():
        lines = [line for line in output_path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
        output_tail = " | ".join(lines[-25:])
    if not path.is_file():
        _emit("pytest diagnostics", f"JUnit file missing: {path} — {output_tail}")
        return 1
    root = ET.parse(path).getroot()
    failures = 0
    for case in root.iter("testcase"):
        for kind in ("failure", "error"):
            node = case.find(kind)
            if node is None:
                continue
            failures += 1
            classname = str(case.attrib.get("classname") or "")
            name = str(case.attrib.get("name") or "unknown")
            message = str(node.attrib.get("message") or "")
            detail_lines = [line for line in (node.text or "").splitlines() if line.strip()]
            tail = " | ".join(detail_lines[-8:])
            _emit(f"pytest {kind}: {name}", f"{classname}::{name} — {message} — {tail}")
    suite = next(root.iter("testsuite"), None)
    suite_errors = int(suite.attrib.get("errors", "0")) if suite is not None else 0
    suite_failures = int(suite.attrib.get("failures", "0")) if suite is not None else 0
    if suite is not None:
        print(
            "PYTEST_JUNIT_SUMMARY "
            f"tests={suite.attrib.get('tests')} "
            f"failures={suite.attrib.get('failures')} "
            f"errors={suite.attrib.get('errors')} "
            f"skipped={suite.attrib.get('skipped')}"
        )
    if (suite_errors or suite_failures) and failures == 0:
        _emit(
            "pytest suite failure without testcase node",
            output_tail or f"suite failures={suite_failures} errors={suite_errors}",
        )
    return 0 if not (suite_errors or suite_failures) else 1


if __name__ == "__main__":
    raise SystemExit(main())
