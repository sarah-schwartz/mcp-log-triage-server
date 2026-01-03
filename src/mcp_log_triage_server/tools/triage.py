"""MCP tool implementations.

This module contains the *implementation* behind the exposed MCP tools.
Keep this layer thin: validate inputs, translate them into core calls, and
return JSON-serializable data structures.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from mcp_log_triage_server.core.ai_review import triage_with_ai_review
from mcp_log_triage_server.core.log_service import default_parser, get_logs
from mcp_log_triage_server.core.models import LogEntry, LogLevel
from mcp_log_triage_server.core.time_window import resolve_time_window

DEFAULT_LEVELS = ["WARNING", "ERROR"]
DEFAULT_AI_IDENTIFIED_LEVELS = ["WARNING", "ERROR", "CRITICAL"]
ALL_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def _parse_levels(levels: Sequence[str] | None) -> list[LogLevel] | None:
    """Parse user-supplied severity names into LogLevel enums."""
    if not levels:
        return None
    out: list[LogLevel] = []
    for s in levels:
        name = s.strip().upper()
        if not name:
            continue
        try:
            out.append(LogLevel[name])
        except KeyError as e:
            valid = ", ".join(ALL_LEVELS)
            raise ValueError(
                f"Unknown log level '{s}'. Valid values: {valid}. "
                "Tip: levels is case-insensitive (e.g., 'error', 'WARNING')."
            ) from e
    return out or None


def _entry_to_dict(entry: LogEntry, *, include_raw: bool) -> dict[str, Any]:
    """Convert a LogEntry into a JSON-serializable dict."""
    d: dict[str, Any] = {
        "timestamp": entry.timestamp.isoformat() if entry.timestamp is not None else None,
        "level": entry.level.name.lower(),
        "message": entry.message,
        "line_no": entry.line_no,
    }
    if entry.meta:
        d["meta"] = entry.meta

    if include_raw and entry.raw is not None:
        d["raw"] = entry.raw
    return d


def triage_logs_impl(
    *,
    log_path: str,
    since: str | None = None,
    until: str | None = None,
    date: str | None = None,
    hour: str | None = None,
    week: str | None = None,
    month: str | None = None,
    levels: list[str] | None = None,
    contains: str | None = None,
    limit: int | None = None,
    include_raw: bool = False,
    include_all_levels: bool = False,
    include_ai_review: bool = False,
) -> dict[str, Any]:
    """Return structured log entries and optional AI findings.

    Parameters
    ----------
    log_path : str
        Path to a local log file. Plain text and .gz files are supported.
    since, until : str | None
        ISO-8601 datetimes. If timezone is omitted, UTC is assumed.
    date, hour, week, month : str | None
        Convenience selectors for common time windows.
    levels : list[str] | None
        Severity filter, case-insensitive. Defaults are applied when omitted.
    contains : str | None
        Substring filter applied to the raw line.
    limit : int | None
        Accepted for compatibility but ignored.
    include_raw : bool
        Whether to include the original raw line in each entry.
    include_all_levels : bool
        When true, ignore levels and include all severities.
    include_ai_review : bool
        When true, split logs into identified entries and AI findings.

    Returns
    -------
    dict[str, Any]
        Payload with `count`, `entries`, and optional `ai_findings`.

    Notes
    -----
    - Time window precedence: date/hour/week/month > since/until > last 24 hours
    - include_ai_review cannot be combined with include_all_levels
    """
    if include_all_levels and include_ai_review:
        raise ValueError("include_all_levels cannot be used with include_ai_review.")

    if include_ai_review:
        levels_eff = DEFAULT_AI_IDENTIFIED_LEVELS if not levels else levels
    elif include_all_levels:
        levels_eff = ALL_LEVELS
    elif not levels:
        levels_eff = DEFAULT_LEVELS
    else:
        levels_eff = levels
    window_since, window_until = resolve_time_window(
        since=since,
        until=until,
        date_=date,
        hour=hour,
        week=week,
        month=month,
    )
    # If resolve_time_window produced any bound, treat it as an explicit window
    has_window = (window_since is not None) or (window_until is not None)

    sev = _parse_levels(levels_eff)

    if include_ai_review:
        result = triage_with_ai_review(
            log_path=log_path,
            exclude_line_nos=set(),
            hours_lookback=None if has_window else 24,
            since=window_since,
            until=window_until,
            contains=contains,
            identified_levels=sev or [],
        )
        entries = result.identified_entries
        return {
            "count": len(entries),
            "entries": [_entry_to_dict(e, include_raw=include_raw) for e in entries],
            "ai_findings": [f.model_dump() for f in result.ai_review.findings],
        }

    entries = get_logs(
        log_path=log_path,
        parser=default_parser(),
        hours_lookback=None if has_window else 24,
        since=window_since,
        until=window_until,
        severities=sev,
        contains=contains,
        include_raw=include_raw,
    )

    return {
        "count": len(entries),
        "entries": [_entry_to_dict(e, include_raw=include_raw) for e in entries],
    }
