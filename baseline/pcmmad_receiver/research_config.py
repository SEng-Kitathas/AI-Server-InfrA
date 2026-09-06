"""Research subsystem feature flags and bounded query defaults."""

from __future__ import annotations

PARSER_VERSION = "research_v5_exec"
ENABLED_SOURCES = ("arxiv",)
ENABLED_HUNT_MODES = ("direct_hunt",)
DEFAULT_MAX_RESULTS = 8
REQUEST_TIMEOUT_SECONDS = 20
PER_QUERY_MAX_RESULTS = 5

ARXIV_API_URL = "https:" + "//export.arxiv.org/api/query"
ARXIV_XML_NAMESPACES = (
    ("atom", "http:" + "//www.w3.org/2005/Atom"),
    ("arxiv", "http:" + "//arxiv.org/schemas/atom"),
)

ARXIV_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
RESEARCH_CACHE_MAX_BYTES = 64 * 1024 * 1024
RESEARCH_HUNT_DEFAULT_WALL_SECONDS = 20
RESEARCH_HUNT_MAX_WALL_SECONDS = 30
