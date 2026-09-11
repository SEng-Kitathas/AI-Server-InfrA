"""Neutral structured error type for server-native lab capability projections."""
from __future__ import annotations
from typing import Any


class LabToolError(Exception):
    def __init__(self, error_code: str, message: str, status: int = 400, **extra: Any) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status = status
        self.extra = extra
