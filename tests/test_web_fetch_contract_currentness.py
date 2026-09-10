from __future__ import annotations

import socket
import sys
import unittest
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

import lab_tools
import lab_tools_ops as ops


def dep():
    return SimpleNamespace(error_cls=lab_tools.LabToolError, beautiful_soup=None)


def public_addr(ip: str = "93.184.216.34", port: int = 443):
    return (socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))


class FakeResponse:
    def __init__(self, data: bytes, *, url: str = "https://example.com/final", status: int = 200, content_type: str = "text/plain; charset=utf-8") -> None:
        self.data = data
        self.url = url
        self.status = status
        self.headers = {"Content-Type": content_type}
        self.requested = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, size=-1):
        self.requested = size
        return self.data[:size] if size >= 0 else self.data

    def geturl(self):
        return self.url


class FakeOpener:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response

    def open(self, request, timeout=None):
        return self.response


class WebFetchContractCurrentnessTests(unittest.TestCase):
    def test_embedded_url_credentials_are_rejected_before_dns(self) -> None:
        with patch.object(socket, "getaddrinfo") as resolver:
            with self.assertRaises(lab_tools.LabToolError) as caught:
                ops._resolve_public_web_target("https://alice:secret@example.com/x", dep())
        self.assertEqual(caught.exception.error_code, "WEB_CREDENTIALS_FORBIDDEN")
        resolver.assert_not_called()

    def test_redirect_with_embedded_credentials_is_rejected_before_follow(self) -> None:
        handler = ops._PublicOnlyRedirectHandler(dep())
        with self.assertRaises(lab_tools.LabToolError) as caught:
            handler.redirect_request(
                urllib.request.Request("https://example.com"),
                None,
                302,
                "Found",
                {},
                "https://user:pass@other.example/private",
            )
        self.assertEqual(caught.exception.error_code, "WEB_CREDENTIALS_FORBIDDEN")
        self.assertEqual(handler.redirect_targets, [])

    def test_url_length_and_control_characters_are_rejected(self) -> None:
        too_long = "https://example.com/" + ("x" * ops.WEB_MAX_URL_CHARS)
        with self.assertRaises(lab_tools.LabToolError) as caught:
            ops._resolve_public_web_target(too_long, dep())
        self.assertEqual(caught.exception.error_code, "WEB_URL_TOO_LONG")

        with self.assertRaises(lab_tools.LabToolError) as caught2:
            ops._resolve_public_web_target("https://example.com/a\r\nInjected: x", dep())
        self.assertEqual(caught2.exception.error_code, "WEB_TARGET_INVALID")

    def test_user_agent_is_bounded_and_rejects_header_controls(self) -> None:
        target = {
            "scheme": "https",
            "hostname": "example.com",
            "port": 443,
            "resolved_addresses": ["93.184.216.34"],
            "scope": "public_network",
            "validated_at_unix_ms": 1,
        }
        with patch.object(ops, "_resolve_public_web_target", return_value=target):
            with self.assertRaises(lab_tools.LabToolError) as caught:
                ops._web_request(
                    {"url": "https://example.com", "user_agent": "good\r\nX-Evil: yes"}, dep()
                )
            self.assertEqual(caught.exception.error_code, "WEB_USER_AGENT_INVALID")

            with self.assertRaises(lab_tools.LabToolError) as caught2:
                ops._web_request(
                    {
                        "url": "https://example.com",
                        "user_agent": "x" * (ops.WEB_MAX_USER_AGENT_CHARS + 1),
                    },
                    dep(),
                )
            self.assertEqual(caught2.exception.error_code, "WEB_USER_AGENT_INVALID")

    def test_redirect_limit_is_explicit_and_bounded(self) -> None:
        self.assertEqual(ops._PublicOnlyRedirectHandler.max_redirections, ops.WEB_MAX_REDIRECTS)
        self.assertLessEqual(ops.WEB_MAX_REDIRECTS, 5)

    def test_complete_raw_body_can_have_separately_truncated_distilled_text(self) -> None:
        body = b"a" * (ops.WEB_TEXT_MAX_CHARS + 5000)
        response = FakeResponse(body, status=206)
        opener = FakeOpener(response)
        request = urllib.request.Request("https://example.com")
        target = {
            "scheme": "https",
            "hostname": "example.com",
            "port": 443,
            "resolved_addresses": ["93.184.216.34"],
            "scope": "public_network",
            "validated_at_unix_ms": 123456,
        }
        with patch.object(
            ops,
            "_web_request",
            return_value=("https://example.com", request, 10, len(body) + 1024, target),
        ), patch.object(urllib.request, "build_opener", return_value=opener), patch.object(
            ops, "_resolve_public_web_target", return_value=target
        ):
            result = ops._web_fetch_payload({}, dep())
        self.assertFalse(result["truncated"])
        self.assertTrue(result["text_truncated"])
        self.assertEqual(len(result["text"]), ops.WEB_TEXT_MAX_CHARS)
        self.assertEqual(result["http_status"], 206)
        self.assertEqual(result["redirect_count"], 0)
        self.assertEqual(result["redirect_limit"], ops.WEB_MAX_REDIRECTS)
        self.assertIn("validated_at_unix_ms", result["initial_target"])
        self.assertIn("stdlib urllib", result["dns_rebinding_residual"])

    def test_public_target_evidence_has_validation_timestamp(self) -> None:
        with patch.object(socket, "getaddrinfo", return_value=[public_addr()]):
            result = ops._resolve_public_web_target("https://example.com/x", dep())
        self.assertIsInstance(result["validated_at_unix_ms"], int)
        self.assertGreater(result["validated_at_unix_ms"], 0)

    def test_machine_contract_exposes_current_bounds_and_residuals(self) -> None:
        card = {row["name"]: row for row in lab_tools.list_tools()}["web.fetch"]
        props = card["input_schema"]["properties"]
        self.assertEqual(props["url"]["maxLength"], ops.WEB_MAX_URL_CHARS)
        self.assertEqual(props["user_agent"]["maxLength"], ops.WEB_MAX_USER_AGENT_CHARS)
        self.assertEqual(props["timeout_seconds"]["maximum"], ops.WEB_TIMEOUT_MAX_SECONDS)
        self.assertEqual(props["max_bytes"]["maximum"], ops.WEB_BODY_MAX_BYTES)
        self.assertFalse(card["approval_required"])
        traits = set(card["effect_traits"])
        self.assertTrue(
            {
                "public_network_only",
                "redirects_revalidated",
                "bounded_redirects",
                "url_credentials_rejected",
                "header_controls_rejected",
                "dns_validation_evidence",
                "dns_rebinding_residual_disclosed",
            }.issubset(traits)
        )
        out = card["output_schema"]["properties"]
        self.assertIn("text_truncated", out)
        self.assertIn("redirect_limit", out)
        self.assertIn("dns_rebinding_residual", out)


if __name__ == "__main__":
    unittest.main()
