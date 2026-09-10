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


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: emit_ci_test_annotations.py <junit.xml>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"::error title=pytest diagnostics::JUnit file missing: {_escape(str(path))}")
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
            body = f"{classname}::{name} — {message} — {tail}"[:3500]
            print(
                "::error "
                f"title={_escape('pytest ' + kind + ': ' + name)}::"
                f"{_escape(body)}"
            )
    suite = next(root.iter("testsuite"), None)
    if suite is not None:
        print(
            "PYTEST_JUNIT_SUMMARY "
            f"tests={suite.attrib.get('tests')} "
            f"failures={suite.attrib.get('failures')} "
            f"errors={suite.attrib.get('errors')} "
            f"skipped={suite.attrib.get('skipped')}"
        )
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
