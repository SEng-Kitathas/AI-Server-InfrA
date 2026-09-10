from __future__ import annotations

import math
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from hypothesis import given, settings, strategies as st

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "baseline" / "pcmmad_receiver"))

import server_hardening
import shared_core
import ucm_v1_runtime as ucm
import user_continuity_store as memory


class IdentifierPropertyTests(unittest.TestCase):
    @settings(max_examples=150, deadline=None)
    @given(st.sampled_from([".", "..", "CON", "con.txt", "NUL", "PRN", "AUX", "COM1", "COM9", "LPT1", "LPT9"]))
    def test_reserved_project_identifiers_never_validate(self, value: str):
        with self.assertRaises(ValueError):
            shared_core.validate_project_id(value)

    @settings(max_examples=150, deadline=None)
    @given(st.sampled_from([".", "..", "CON", "con.txt", "NUL", "PRN", "AUX", "COM1", "COM9", "LPT1", "LPT9"]))
    def test_reserved_profile_identifiers_never_validate(self, value: str):
        with self.assertRaises(memory.UserContinuityError):
            memory._profile_id(value)

    @settings(max_examples=200, deadline=None)
    @given(st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-", min_size=1, max_size=32))
    def test_regex_valid_identifier_is_either_namespace_safe_or_explicitly_rejected(self, value: str):
        try:
            project = shared_core.validate_project_id(value)
        except ValueError as exc:
            self.assertTrue(
                any(token in str(exc).lower() for token in ("reserved windows device", "aliases a parent", "trailing dot/space")),
                str(exc),
            )
            with self.assertRaises(memory.UserContinuityError):
                memory._profile_id(value)
            return
        self.assertNotIn(project, {".", ".."})
        profile = memory._profile_id(value)
        self.assertEqual(profile, value.lower())
        self.assertNotIn(profile, {".", ".."})


class ZipNamespacePropertyTests(unittest.TestCase):
    def inspect_name(self, name: str):
        with tempfile.TemporaryDirectory(prefix="pcmmad-warfort-fuzzzip-") as td:
            path = Path(td) / "x.zip"
            with zipfile.ZipFile(path, "w") as zf:
                zf.writestr(name, b"x")
            return server_hardening.inspect_zip_safety(path)

    @settings(max_examples=120, deadline=None)
    @given(
        base=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-", min_size=1, max_size=20),
        suffix=st.sampled_from([".", " ", ":stream"]),
    )
    def test_windows_alias_suffixes_never_pass(self, base: str, suffix: str):
        result = self.inspect_name(f"safe/{base}{suffix}")
        self.assertFalse(result["ok"], result)

    @settings(max_examples=120, deadline=None)
    @given(device=st.sampled_from(["CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1,10)], *[f"LPT{i}" for i in range(1,10)]]), ext=st.sampled_from(["", ".txt", ".json", ".log"]))
    def test_windows_reserved_device_components_never_pass(self, device: str, ext: str):
        result = self.inspect_name(f"safe/{device}{ext}")
        self.assertFalse(result["ok"], result)


class CanonicalJsonPropertyTests(unittest.TestCase):
    @settings(max_examples=250, deadline=None)
    @given(st.floats(allow_nan=False, allow_infinity=False, width=64))
    def test_finite_floats_are_canonical_json_eligible(self, value: float):
        ucm._ensure_canonical_json_value({"v": value})

    def test_all_nonfinite_ieee_values_are_rejected(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaises(ucm.UcmError) as ctx:
                    ucm._ensure_canonical_json_value({"v": value})
                self.assertEqual(ctx.exception.error_code, "UCM_CONTRACT_INVALID")

    @settings(max_examples=100, deadline=None)
    @given(st.integers(min_value=65, max_value=90))
    def test_depth_boundary_64_accepts_but_65_rejects(self, marker: int):
        value = chr(marker)
        for _ in range(64):
            value = [value]
        ucm._ensure_canonical_json_value(value, max_depth=64)
        value = [value]
        with self.assertRaises(ucm.UcmError) as ctx:
            ucm._ensure_canonical_json_value(value, max_depth=64)
        self.assertEqual(ctx.exception.error_code, "UCM_CONTRACT_INVALID")


if __name__ == "__main__":
    unittest.main()
