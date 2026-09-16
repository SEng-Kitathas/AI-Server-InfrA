"""Typed runtime configuration derived from explicit environment boundaries."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit


class RuntimeConfigurationError(ValueError):
    """Raised when a load-bearing runtime setting is malformed."""


def parse_optional_unbounded_int(
    raw: str | int | None, default: int | None, *, minimum: int = 1
) -> int | None:
    """Parse positive integers while preserving the receiver's unbounded sentinels."""

    if raw is None or raw == "":
        return default
    text = str(raw).strip().lower()
    if text in {"0", "-1", "none", "unbounded", "unlimited", "inf", "infinite"}:
        return None
    try:
        value = int(text)
    except ValueError as exc:
        raise RuntimeConfigurationError(f"expected integer or unbounded sentinel, got {raw!r}") from exc
    return max(value, minimum)


def parse_float(
    raw: str | float | None, default: float, *, minimum: float | None = None
) -> float:
    """Parse a floating-point setting and clamp it to an explicit lower bound."""

    try:
        value = default if raw is None or raw == "" else float(raw)
    except ValueError as exc:
        raise RuntimeConfigurationError(f"expected floating-point value, got {raw!r}") from exc
    return max(value, minimum) if minimum is not None else value


def parse_port(raw: str | int | None, default: int) -> int:
    """Parse a TCP port and reject values that cannot be bound."""

    candidate = default if raw is None or str(raw).strip() == "" else raw
    try:
        port = int(candidate)
    except (TypeError, ValueError) as exc:
        raise RuntimeConfigurationError(f"invalid TCP port: {candidate!r}") from exc
    if not 1 <= port <= 65535:
        raise RuntimeConfigurationError(f"TCP port must be between 1 and 65535, got {port}")
    return port


def parse_http_base_url(raw: str | None, default: str) -> str:
    """Normalize an HTTP(S) service base URL without accepting opaque schemes."""

    value = (raw or default).strip().rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeConfigurationError(f"invalid HTTP(S) base URL: {value!r}")
    if parsed.query or parsed.fragment:
        raise RuntimeConfigurationError("service base URL must not contain query or fragment data")
    return value


def _execution_timeout_env_values() -> dict[str, int | None]:
    return {
        "default_timeout_seconds": parse_optional_unbounded_int(
            os.environ.get("PCMMAD_EXECUTION_DEFAULT_TIMEOUT_SECONDS"), None
        ),
        "max_timeout_seconds": parse_optional_unbounded_int(
            os.environ.get("PCMMAD_EXECUTION_MAX_TIMEOUT_SECONDS"), None
        ),
    }


def _execution_output_env_values() -> dict[str, int | None]:
    return {
        "default_stdout_max_bytes": parse_optional_unbounded_int(
            os.environ.get("PCMMAD_EXECUTION_DEFAULT_STDOUT_MAX_BYTES"), None
        ),
        "default_stderr_max_bytes": parse_optional_unbounded_int(
            os.environ.get("PCMMAD_EXECUTION_DEFAULT_STDERR_MAX_BYTES"), None
        ),
        "max_output_bytes": parse_optional_unbounded_int(
            os.environ.get("PCMMAD_EXECUTION_MAX_OUTPUT_BYTES"), None
        ),
    }


def _execution_queue_env_values() -> dict[str, int | None]:
    return {
        "global_concurrency": parse_optional_unbounded_int(
            os.environ.get("PCMMAD_EXECUTION_GLOBAL_CONCURRENCY"), 8
        ),
        "project_concurrency": parse_optional_unbounded_int(
            os.environ.get("PCMMAD_EXECUTION_PROJECT_CONCURRENCY"), None
        ),
        "global_queue_limit": parse_optional_unbounded_int(
            os.environ.get("PCMMAD_EXECUTION_GLOBAL_QUEUE_LIMIT"), None
        ),
        "project_queue_limit": parse_optional_unbounded_int(
            os.environ.get("PCMMAD_EXECUTION_PROJECT_QUEUE_LIMIT"), None
        ),
        "drain_batch": parse_optional_unbounded_int(
            os.environ.get("PCMMAD_EXECUTION_DRAIN_BATCH"), None
        ),
    }


def _execution_runtime_env_values() -> dict[str, int | float | None]:
    values: dict[str, int | float | None] = {}
    values.update(_execution_timeout_env_values())
    values.update(_execution_output_env_values())
    values.update(_execution_queue_env_values())
    values["scheduler_interval_seconds"] = parse_float(
        os.environ.get("PCMMAD_EXECUTION_SCHEDULER_INTERVAL_SECONDS"),
        0.25,
        minimum=0.05,
    )
    values["scheduler_active_resync_seconds"] = parse_float(
        os.environ.get("PCMMAD_EXECUTION_SCHEDULER_ACTIVE_RESYNC_SECONDS"),
        2.0,
        minimum=0.25,
    )
    values["scheduler_idle_resync_seconds"] = parse_float(
        os.environ.get("PCMMAD_EXECUTION_SCHEDULER_IDLE_RESYNC_SECONDS"),
        60.0,
        minimum=1.0,
    )
    return values


@dataclass(frozen=True)
class ServerRuntimeConfig:
    """Network binding invariant for the Flask authority plane."""

    host: str = "127.0.0.1"
    port: int = 5000

    @classmethod
    def from_env(cls) -> "ServerRuntimeConfig":
        host = os.environ.get("PCMMAD_BIND_HOST", "127.0.0.1").strip() or "127.0.0.1"
        return cls(host=host, port=parse_port(os.environ.get("PCMMAD_BIND_PORT"), 5000))


@dataclass(frozen=True)
class BrowserBridgeRuntimeConfig:
    """Optional browser sidecar location; absence never disables the receiver itself."""

    base_url: str = "http://127.0.0.1:4471"

    @classmethod
    def from_env(cls) -> "BrowserBridgeRuntimeConfig":
        return cls(
            base_url=parse_http_base_url(
                os.environ.get("PCMMAD_BROWSER_BRIDGE_URL"),
                "http://127.0.0.1:4471",
            )
        )


@dataclass(frozen=True)
class ExecutionRuntimeConfig:
    default_timeout_seconds: int | None = None
    max_timeout_seconds: int | None = None
    default_stdout_max_bytes: int | None = None
    default_stderr_max_bytes: int | None = None
    max_output_bytes: int | None = None
    global_concurrency: int | None = 8
    project_concurrency: int | None = None
    global_queue_limit: int | None = None
    project_queue_limit: int | None = None
    drain_batch: int | None = None
    scheduler_interval_seconds: float = 0.25
    scheduler_active_resync_seconds: float = 2.0
    scheduler_idle_resync_seconds: float = 60.0

    @classmethod
    def from_env(cls) -> "ExecutionRuntimeConfig":
        return cls(**_execution_runtime_env_values())


@dataclass(frozen=True)
class LabBatchRuntimeConfig:
    background_workers: int | None = 64

    @classmethod
    def from_env(cls) -> "LabBatchRuntimeConfig":
        return cls(
            background_workers=parse_optional_unbounded_int(
                os.environ.get("PCMMAD_LAB_BATCH_BACKGROUND_WORKERS"), 64
            ),
        )


SERVER_CONFIG = ServerRuntimeConfig.from_env()
EXECUTION_CONFIG = ExecutionRuntimeConfig.from_env()
LAB_BATCH_CONFIG = LabBatchRuntimeConfig.from_env()
