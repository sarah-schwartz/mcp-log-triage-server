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
    """Configure a reasonable default logging setup.

    The MCP client typically captures stderr; keeping logs concise makes them easier to consume.
    """
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
    log_path:
        Path to a local log file. Supports plain text and .gz.
    since/until:
        ISO-8601 datetimes (e.g., 2025-12-31T20:00:00Z). If timezone is omitted, UTC is assumed.
    date/hour/week/month:
        Convenience selectors that set a time window without exact timestamps.
        Only one selector should be used at a time (or since/until).
        Examples:
          - date: 2025-12-31
          - hour: 2025-12-31T20
          - week: 2025-W52
          - month: 2025-12
    levels:
        Filter by severity names (e.g., ["error", "warning"]). Case-insensitive.
    include_all_levels:
        When true, ignore levels and include all severities.
    include_ai_review:
        When true, split logs into identified entries and AI findings.
    contains:
        Substring filter applied to the raw line.
    limit:
        Maximum number of entries returned (hard-capped in the implementation).
    include_raw:
        Whether to include the original raw log line in each entry.

    Returns
    -------
    dict:
        {"count": int, "entries": list[dict]}
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
