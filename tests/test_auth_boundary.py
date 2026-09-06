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
