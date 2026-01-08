"""MCP resource registry.

Resources are addressable by URI and can be fetched by the MCP client on demand.
"""

from __future__ import annotations

import asyncio
import gzip
import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_log_triage_server.core.ai_review import AIReviewResponse
from mcp_log_triage_server.core.formats import default_scan_config

ALLOWED_FILE_SUFFIXES = {".log", ".txt", ".md"}
BASE_DIR_ENV = "LOG_TRIAGE_BASE_DIR"
TEXT_ENCODING = "utf-8"
TEXT_ERRORS = "replace"


def _base_dir() -> Path:
    """Return the resolved base directory for file resources."""
    raw = os.getenv(BASE_DIR_ENV, os.getcwd())
    return Path(raw).resolve()


def _safe_resolve(path: str) -> Path:
    """Resolve a path under the configured base directory."""
    base = _base_dir()
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = base / p
    p = p.resolve()
    if base not in p.parents and p != base:
        raise ValueError("Path escapes base dir")
    return p


def _allowed_suffix(path: Path) -> str:
    """Return the effective suffix for allowlist checks."""
    suffix = path.suffix.lower()
    if suffix == ".gz":
        suffix = path.with_suffix("").suffix.lower()
    return suffix


def _ensure_allowed_suffix(path: Path) -> None:
    """Validate the file suffix against the allowlist."""
    suffix = _allowed_suffix(path)
    if suffix not in ALLOWED_FILE_SUFFIXES:
        allowed = ", ".join(sorted(ALLOWED_FILE_SUFFIXES))
        raise ValueError(f"File type not allowed. Allowed: {allowed}.")


def _resolve_resource_path(path: str) -> Path:
    """Resolve and validate a resource file path."""
    resolved = _safe_resolve(path)
    if not resolved.is_file():
        raise FileNotFoundError(f"File not found: {resolved}")
    _ensure_allowed_suffix(resolved)
    return resolved


def _open_text(path: Path) -> str:
    """Read text from a file, supporting optional gzip compression."""
    if path.suffix.lower() == ".gz":
        with gzip.open(path, mode="rt", encoding=TEXT_ENCODING, errors=TEXT_ERRORS) as f:
            return f.read()
    return path.read_text(encoding=TEXT_ENCODING, errors=TEXT_ERRORS)


def register_resources(mcp: FastMCP) -> None:
    """Register resource handlers on the MCP server."""

    @mcp.resource("app://log-triage/help")
    def help_resource() -> str:
        """Return a short list of available resource URIs."""
        allowed = ", ".join(sorted(ALLOWED_FILE_SUFFIXES))
        base = _base_dir()
        return (
            "Resources:\n"
            "- app://log-triage/help\n"
            "- app://log-triage/config/scan-tokens\n"
            "- app://log-triage/schemas/ai-review-response\n"
            "- app://log-triage/examples/sample-log\n"
            f"- file://{{path}} (restricted to {BASE_DIR_ENV}; allowed: {allowed}, .gz)\n"
            "- log://{path} (same rules as file://; intended for logs)\n"
            f"\nBase directory: {base}\n"
        )

    @mcp.resource("app://log-triage/examples/sample-log")
    def sample_log() -> str:
        """Return a tiny sample log for demos and tests."""
        return (
            "2025-12-30T08:12:01Z [INFO] service started\n"
            "2025-12-30T08:12:03Z [WARNING] retrying request id=abc123\n"
            "2025-12-30T08:12:04Z [ERROR] upstream timeout route=/api/v1/items\n"
            "2025-12-30T08:12:05Z [CRITICAL] database unavailable\n"
        )

    @mcp.resource("app://log-triage/config/scan-tokens")
    def scan_tokens() -> dict[str, list[str]]:
        """Return the configured scan tokens as strings."""
        cfg = default_scan_config()
        out: dict[str, list[str]] = {}
        for level, toks in cfg.tokens.items():
            out[level.value] = [t.decode("utf-8", errors="replace") for t in toks]
        return out

    @mcp.resource("app://log-triage/schemas/ai-review-response")
    def ai_review_schema() -> dict[str, Any]:
        """Return the JSON schema for AI review responses."""
        return AIReviewResponse.model_json_schema()

    @mcp.resource("file://{path}")
    async def read_file(path: str) -> str:
        """Read a text file from within LOG_TRIAGE_BASE_DIR."""
        p = _resolve_resource_path(path)
        return await asyncio.to_thread(_open_text, p)

    @mcp.resource("log://{path}")
    async def tail_log(path: str) -> str:
        """Return the full log contents."""
        p = _resolve_resource_path(path)
        return await asyncio.to_thread(_open_text, p)
