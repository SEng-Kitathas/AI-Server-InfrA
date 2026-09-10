from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask, jsonify, request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "baseline"))

from pcmmad_receiver import access_logging as al


class AccessLoggingUnitTests(unittest.TestCase):
    def test_known_and_explicit_project_aliases_are_bounded(self) -> None:
        self.assertEqual(al.project_log_tag("PCMMAD_RECEIVER_LAB"), "PCMMAD")
        self.assertEqual(al.project_log_tag("rahl-engineering-canonical-sop"), "RAHL")
        self.assertEqual(
            al.project_log_tag("a-very-long-project-identifier", {"a-very-long-project-identifier": "forge-main"}),
            "FORGE-MAIN",
        )
        derived = al.project_log_tag("some-very-long-project-name-that-needs-a-suffix")
        self.assertLessEqual(len(derived), al.PROJECT_TAG_MAX_CHARS)
        self.assertIn("~", derived)

    def test_project_id_collection_handles_nested_and_multi_project_payloads(self) -> None:
        found = al._collect_project_ids(
            {
                "project_id": "p1",
                "steps": [
                    {"payload": {"project_id": "p1"}},
                    {"arguments": {"project_id": "p2"}},
                ],
            }
        )
        self.assertEqual(found, {"p1", "p2"})

    def test_job_shortening_is_compact(self) -> None:
        self.assertEqual(al._short_job_tag({"job-fb9d410c4834"}), "FB9D410C48")
        self.assertEqual(al._short_job_tag({"job-a", "job-b"}), "MULTI")
        self.assertIsNone(al._short_job_tag(set()))


class AccessLoggingMiddlewareTests(unittest.TestCase):
    def _app(self) -> Flask:
        app = Flask(__name__)

        @app.post("/echo")
        def echo():
            payload = request.get_json(force=True)
            return jsonify({"project_id": payload.get("project_id"), "job_id": "job-deadbeef1234"})

        @app.post("/multi")
        def multi():
            return jsonify({"ok": True})

        @app.get("/health")
        def health():
            return jsonify({"ok": True})

        return app

    def test_middleware_tags_project_job_and_preserves_body_for_route(self) -> None:
        app = self._app()
        with patch.dict("os.environ", {"PCMMAD_ACCESS_LOG": "1"}, clear=False), patch.object(
            al._access_logger(), "info"
        ) as info:
            al.install_access_logging(app)
            response = app.test_client().post("/echo", json={"project_id": "PCMMAD_RECEIVER_LAB", "value": 7})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["project_id"], "PCMMAD_RECEIVER_LAB")
        args = info.call_args.args
        self.assertEqual(args[0], "[%s]%s %s %s %s %.1fms")
        self.assertEqual(args[1], "PCMMAD")
        self.assertEqual(args[2], " [job:DEADBEEF12]")
        self.assertEqual(args[3:6], ("POST", "/echo", 200))
        self.assertGreaterEqual(args[6], 0.0)

    def test_alias_map_applies_without_exposing_full_project_id(self) -> None:
        app = self._app()
        aliases = json.dumps({"extremely-long-secret-ish-project-name": "LABX"})
        with patch.dict(
            "os.environ",
            {"PCMMAD_ACCESS_LOG": "1", "PCMMAD_PROJECT_LOG_ALIASES_JSON": aliases},
            clear=False,
        ), patch.object(al._access_logger(), "info") as info:
            al.install_access_logging(app)
            response = app.test_client().post(
                "/echo", json={"project_id": "extremely-long-secret-ish-project-name"}
            )
        self.assertEqual(response.status_code, 200)
        args = info.call_args.args
        self.assertEqual(args[1], "LABX")
        self.assertNotIn("extremely-long-secret-ish-project-name", " ".join(map(str, args)))

    def test_multi_project_payload_is_tagged_multi(self) -> None:
        app = self._app()
        with patch.dict("os.environ", {"PCMMAD_ACCESS_LOG": "1"}, clear=False), patch.object(
            al._access_logger(), "info"
        ) as info:
            al.install_access_logging(app)
            response = app.test_client().post(
                "/multi",
                json={
                    "steps": [
                        {"payload": {"project_id": "p1"}},
                        {"payload": {"project_id": "p2"}},
                    ]
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(info.call_args.args[1], "MULTI")

    def test_global_request_has_global_tag(self) -> None:
        app = self._app()
        with patch.dict("os.environ", {"PCMMAD_ACCESS_LOG": "1"}, clear=False), patch.object(
            al._access_logger(), "info"
        ) as info:
            al.install_access_logging(app)
            response = app.test_client().get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(info.call_args.args[1], "GLOBAL")

    def test_oversized_body_is_not_parsed_for_tagging(self) -> None:
        app = Flask(__name__)

        @app.post("/raw")
        def raw():
            return jsonify({"bytes": len(request.get_data(cache=True))})

        body = b"x" * (al.ACCESS_BODY_INSPECT_MAX_BYTES + 1)
        with patch.dict("os.environ", {"PCMMAD_ACCESS_LOG": "1"}, clear=False), patch.object(
            al._access_logger(), "info"
        ) as info:
            al.install_access_logging(app)
            response = app.test_client().post("/raw", data=body, content_type="application/octet-stream")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["bytes"], len(body))
        self.assertEqual(info.call_args.args[1], "GLOBAL")

    def test_explicit_disable_installs_no_hooks(self) -> None:
        app = self._app()
        with patch.dict("os.environ", {"PCMMAD_ACCESS_LOG": "0"}, clear=False):
            al.install_access_logging(app)
        self.assertEqual(len(app.before_request_funcs.get(None, [])), 0)
        self.assertEqual(len(app.after_request_funcs.get(None, [])), 0)


if __name__ == "__main__":
    unittest.main()
