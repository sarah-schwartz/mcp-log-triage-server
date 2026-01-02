"""MCP resource registry.

Resources are addressable by URI and can be fetched by the MCP client on demand.
"""

from __future__ import annotations

import gzip
import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_log_triage_server.core.ai_review import AIReviewResponse
from mcp_log_triage_server.core.formats import default_scan_config

ALLOWED_FILE_SUFFIXES = {".log", ".txt", ".md"}


def _base_dir() -> Path:
    raw = os.getenv("LOG_TRIAGE_BASE_DIR", os.getcwd())
    return Path(raw).resolve()


def _safe_resolve(path: str) -> Path:
    base = _base_dir()
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = base / p
    p = p.resolve()
    if base not in p.parents and p != base:
        raise ValueError("Path escapes base dir")
    return p


def _open_text(path: Path) -> str:
    """Read text from a file, supporting optional gzip compression."""
    if path.suffix.lower() == ".gz":
        with gzip.open(path, mode="rt", encoding="utf-8", errors="replace") as f:
            return f.read()
    return path.read_text(encoding="utf-8", errors="replace")


def register_resources(mcp: FastMCP) -> None:
    @mcp.resource("app://log-triage/help")
    def help_resource() -> str:
        return (
            "Resources:\n"
            "- app://log-triage/help\n"
            "- app://log-triage/config/scan-tokens\n"
            "- app://log-triage/schemas/ai-review-response\n"
            "- app://log-triage/examples/sample-log\n"
            "- file://{path} (restricted + allowlist)\n"
            "- log://{path}\n"
        )

    @mcp.resource("app://log-triage/examples/sample-log")
    def sample_log() -> str:
        """A tiny sample log for demos and tests."""
        return (
            "2025-12-30T08:12:01Z [INFO] service started\n"
            "2025-12-30T08:12:03Z [WARNING] retrying request id=abc123\n"
            "2025-12-30T08:12:04Z [ERROR] upstream timeout route=/api/v1/items\n"
            "2025-12-30T08:12:05Z [CRITICAL] database unavailable\n"
        )

    @mcp.resource("app://log-triage/config/scan-tokens")
    def scan_tokens() -> dict[str, list[str]]:
        cfg = default_scan_config()
        out: dict[str, list[str]] = {}
        for level, toks in cfg.tokens.items():
            out[level.value] = [t.decode("utf-8", errors="replace") for t in toks]
        return out

    @mcp.resource("app://log-triage/schemas/ai-review-response")
    def ai_review_schema() -> dict[str, Any]:
        return AIReviewResponse.model_json_schema()

    @mcp.resource("file://{path}")
    def read_file(path: str) -> str:
        """Read a text file from within LOG_TRIAGE_BASE_DIR.

        Hardening:
        - Only allows .log/.txt/.md (and gzip variants: *.log.gz, *.txt.gz, *.md.gz)
        """
        p = _safe_resolve(path)

        suffix = p.suffix.lower()
        if suffix == ".gz":
            second = p.with_suffix("").suffix.lower()
            if second not in ALLOWED_FILE_SUFFIXES:
                raise ValueError("File type not allowed")
        else:
            if suffix not in ALLOWED_FILE_SUFFIXES:
                raise ValueError("File type not allowed")

        return _open_text(p)

    @mcp.resource("log://{path}")
    def tail_log(path: str) -> str:
        """Return the full log contents."""

        p = _safe_resolve(path)
        return _open_text(p)
