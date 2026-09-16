"""Authentication boundary regression tests."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "baseline" / "pcmmad_receiver"))

from shared_core import require_valid_api_key


class AuthBoundaryTests(unittest.TestCase):
    def test_research_routes_fail_closed_without_receiver_key(self) -> None:
        from app_factory import create_app

        with patch.dict(os.environ, {"GITHOME_API_KEY": "expected-key"}, clear=False):
            app = create_app()
            client = app.test_client()
            cases = [
                ("get", "/research/health", None),
                ("post", "/research/arxiv/search", {"query": "test"}),
                ("post", "/research/arxiv/paper", {"paper_id": "1234.5678"}),
                ("post", "/research/hunt", {"topic": "test", "mode": "direct_hunt"}),
            ]
            for method, url, body in cases:
                with self.subTest(url=url):
                    response = (
                        getattr(client, method)(url, json=body)
                        if body is not None
                        else getattr(client, method)(url)
                    )
                    self.assertEqual(response.status_code, 401)
                    self.assertEqual(response.get_json()["error_code"], "UNAUTHORIZED")

    def test_research_health_accepts_exact_receiver_key(self) -> None:
        from app_factory import create_app

        with patch.dict(os.environ, {"GITHOME_API_KEY": "expected-key"}, clear=False):
            app = create_app()
            client = app.test_client()
            response = client.get(
                "/research/health",
                headers={"X-GitHome-Key": "expected-key"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.get_json()["ok"])

    def test_missing_configuration_never_falls_open(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(PermissionError):
                require_valid_api_key({"X-GitHome-Key": "anything"})

    def test_exact_key_is_required(self) -> None:
        with patch.dict(os.environ, {"GITHOME_API_KEY": "expected-key"}, clear=False):
            require_valid_api_key({"X-GitHome-Key": "expected-key"})
            for candidate in ("", "expected", "expected-key ", object()):
                with self.subTest(candidate=candidate), self.assertRaises(PermissionError):
                    require_valid_api_key({"X-GitHome-Key": candidate})


if __name__ == "__main__":
    unittest.main()
