"""MCP server entrypoint (stdio transport).

This module wires together:
- Tools: callable actions (e.g., triage a log file)
- Resources: addressable data blobs (e.g., log tail via URI)
- Prompts: reusable conversation templates that clients can invoke

Run locally (stdio):
    python -m mcp_log_triage_server.server.log_server
"""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Sequence
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_log_triage_server.prompts.registry import register_prompts
from mcp_log_triage_server.resources.registry import register_resources
from mcp_log_triage_server.tools.triage import triage_logs_impl

LOGGER = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Configure the default logging setup."""
    level_name = os.getenv("LOG_TRIAGE_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


mcp = FastMCP("log-triage", json_response=True)

register_resources(mcp)
register_prompts(mcp)


@mcp.tool()
def triage_logs(
    log_path: str,
    since: str | None = None,
    until: str | None = None,
    date: str | None = None,
    hour: str | None = None,
    week: str | None = None,
    month: str | None = None,
    levels: Sequence[str] | None = None,
    include_all_levels: bool = False,
    include_ai_review: bool = False,
    contains: str | None = None,
    limit: int | None = None,
    include_raw: bool = False,
) -> dict[str, Any]:
    """Return structured log entries for a file and time window.

    Parameters
    ----------
    log_path : str
        Path to a local log file. Supports plain text and .gz.
    since, until : str | None
        ISO-8601 datetimes (e.g., 2025-12-31T20:00:00Z). If timezone is omitted, UTC is assumed.
    date, hour, week, month : str | None
        Convenience selectors that set a time window without exact timestamps.
    levels : Sequence[str] | None
        Filter by severity names (e.g., ["error", "warning"]). Case-insensitive.
    include_all_levels : bool
        When true, ignore levels and include all severities.
    include_ai_review : bool
        When true, split logs into identified entries and AI findings.
    contains : str | None
        Substring filter applied to the raw line.
    limit : int | None
        Ignored; all matching entries are returned.
    include_raw : bool
        Whether to include the original raw log line in each entry.

    Returns
    -------
    dict[str, Any]
        Payload with `count`, `entries`, and optional `ai_findings`.

    Notes
    -----
    - Time window precedence: date/hour/week/month > since/until > last 24 hours
    - include_ai_review cannot be combined with include_all_levels
    """
    return triage_logs_impl(
        log_path=log_path,
        since=since,
        until=until,
        date=date,
        hour=hour,
        week=week,
        month=month,
        levels=levels,
        include_all_levels=include_all_levels,
        include_ai_review=include_ai_review,
        contains=contains,
        limit=limit,
        include_raw=include_raw,
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Start the MCP server over stdio."""
    _configure_logging()
    LOGGER.debug("Starting MCP server (transport=stdio)")
    _ = argv or sys.argv[1:]
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
