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


def addr(ip: str, port: int = 80):
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    sockaddr = (ip, port, 0, 0) if family == socket.AF_INET6 else (ip, port)
    return (family, socket.SOCK_STREAM, 6, "", sockaddr)


class FakeResponse:
    def __init__(self, data: bytes, url: str = "https://example.com/final") -> None:
        self.data = data
        self.url = url
        self.headers = {"Content-Type": "text/plain; charset=utf-8"}
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


class WebFetchNetworkScopeTests(unittest.TestCase):
    def test_public_target_is_accepted_with_resolved_evidence(self) -> None:
        with patch.object(socket, "getaddrinfo", return_value=[addr("93.184.216.34", 443)]):
            result = ops._resolve_public_web_target("https://example.com/x", dep())
        self.assertEqual(result["scope"], "public_network")
        self.assertEqual(result["resolved_addresses"], ["93.184.216.34"])
        self.assertEqual(result["hostname"], "example.com")

    def test_loopback_private_linklocal_and_unspecified_are_rejected(self) -> None:
        for ip in ("127.0.0.1", "10.0.0.7", "192.168.1.4", "169.254.169.254", "0.0.0.0", "::1", "fe80::1"):
            with self.subTest(ip=ip), patch.object(socket, "getaddrinfo", return_value=[addr(ip)]):
                with self.assertRaises(lab_tools.LabToolError) as caught:
                    ops._resolve_public_web_target("http://internal.invalid/", dep())
                self.assertEqual(caught.exception.error_code, "WEB_TARGET_FORBIDDEN")
                self.assertIn(ip, caught.exception.extra["blocked_addresses"])

    def test_mixed_public_private_dns_answer_is_rejected(self) -> None:
        answers = [addr("93.184.216.34"), addr("10.10.10.10")]
        with patch.object(socket, "getaddrinfo", return_value=answers):
            with self.assertRaises(lab_tools.LabToolError) as caught:
                ops._resolve_public_web_target("http://mixed.invalid/", dep())
        self.assertEqual(caught.exception.error_code, "WEB_TARGET_FORBIDDEN")
        self.assertEqual(set(caught.exception.extra["resolved_addresses"]), {"93.184.216.34", "10.10.10.10"})

    def test_redirect_to_private_target_is_rejected_before_superclass_follow(self) -> None:
        handler = ops._PublicOnlyRedirectHandler(dep())
        with patch.object(socket, "getaddrinfo", return_value=[addr("127.0.0.1")]):
            with self.assertRaises(lab_tools.LabToolError) as caught:
                handler.redirect_request(
                    urllib.request.Request("https://example.com"),
                    None,
                    302,
                    "Found",
                    {},
                    "http://localhost/admin",
                )
        self.assertEqual(caught.exception.error_code, "WEB_TARGET_FORBIDDEN")
        self.assertEqual(handler.redirect_targets, [])

    def test_fetch_physically_reads_only_budget_plus_one_and_reports_truncation(self) -> None:
        response = FakeResponse(b"x" * 5000)
        opener = FakeOpener(response)
        request = urllib.request.Request("https://example.com")
        target = {
            "scheme": "https",
            "hostname": "example.com",
            "port": 443,
            "resolved_addresses": ["93.184.216.34"],
            "scope": "public_network",
        }
        with patch.object(
            ops,
            "_web_request",
            return_value=("https://example.com", request, 10, 1024, target),
        ), patch.object(urllib.request, "build_opener", return_value=opener), patch.object(
            ops, "_resolve_public_web_target", return_value=target
        ):
            result = ops._web_fetch_payload({}, dep())
        self.assertEqual(response.requested, 1025)
        self.assertEqual(result["bytes"], 1024)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["network_scope"], "public_network")
        self.assertLessEqual(len(result["text"].encode("utf-8")), 1024)

    def test_web_fetch_contract_exposes_public_network_effects(self) -> None:
        tools = {row["name"]: row for row in lab_tools.list_tools()}
        card = tools["web.fetch"]
        self.assertEqual(card["side_effect_class"], "external_read")
        self.assertTrue({"network_io", "public_network_only", "redirects_revalidated", "bounded_output"}.issubset(set(card["effect_traits"])))


if __name__ == "__main__":
    unittest.main()
