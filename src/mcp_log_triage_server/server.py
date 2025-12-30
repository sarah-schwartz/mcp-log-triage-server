from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple

from mcp_log_triage_server.log_service import default_parser, get_logs
from mcp_log_triage_server.models import LogLevel


_WEEK_RE = re.compile(r"^(?P<y>\d{4})-W(?P<w>\d{2})$")
_MONTH_RE = re.compile(r"^(?P<y>\d{4})-(?P<m>\d{2})$")


def _parse_levels(s: str) -> list[LogLevel]:
    """Parse comma-separated levels into LogLevel values."""
    out: list[LogLevel] = []
    for part in s.split(","):
        name = part.strip().upper()
        if not name:
            continue
        try:
            out.append(LogLevel(name))
        except ValueError as e:
            raise argparse.ArgumentTypeError(
                "Invalid level. Allowed: CRITICAL, ERROR, WARNING, INFO, DEBUG, UNKNOWN"
            ) from e
    if not out:
        raise argparse.ArgumentTypeError("At least one level must be provided")
    return out


def _parse_iso_dt(s: str) -> datetime:
    """Parse ISO8601 datetime. If tz is missing, assume UTC."""
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _range_for_date(s: str) -> tuple[datetime, datetime]:
    d = date.fromisoformat(s)
    start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start, end


def _range_for_hour(s: str) -> tuple[datetime, datetime]:
    # Format: YYYY-MM-DDTHH  (e.g., 2025-12-29T10)
    base = datetime.fromisoformat(s)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    start = base.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=1)
    return start, end


def _range_for_week(s: str) -> tuple[datetime, datetime]:
    m = _WEEK_RE.match(s)
    if not m:
        raise argparse.ArgumentTypeError("week must look like YYYY-Www (e.g., 2025-W52)")
    y = int(m.group("y"))
    w = int(m.group("w"))
    start_date = date.fromisocalendar(y, w, 1)  # Monday
    start = datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc)
    end = start + timedelta(days=7)
    return start, end


def _range_for_month(s: str) -> tuple[datetime, datetime]:
    m = _MONTH_RE.match(s)
    if not m:
        raise argparse.ArgumentTypeError("month must look like YYYY-MM (e.g., 2025-12)")
    y = int(m.group("y"))
    mo = int(m.group("m"))
    start = datetime(y, mo, 1, tzinfo=timezone.utc)
    if mo == 12:
        end = datetime(y + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(y, mo + 1, 1, tzinfo=timezone.utc)
    return start, end


def _resolve_time_window(args: argparse.Namespace) -> tuple[Optional[datetime], Optional[datetime]]:
    """
    Resolve a time window [since, until) in UTC.
    Priority: date/hour/week/month > since/until > none.
    """
    if args.date:
        return _range_for_date(args.date)
    if args.hour:
        return _range_for_hour(args.hour)
    if args.week:
        return _range_for_week(args.week)
    if args.month:
        return _range_for_month(args.month)

    since = _parse_iso_dt(args.since) if args.since else None
    until = _parse_iso_dt(args.until) if args.until else None
    return since, until


def main() -> None:
    """CLI entrypoint for local testing (not MCP yet)."""
    p = argparse.ArgumentParser(description="Generic log triage (sniff + adaptive fast scan).")
    p.add_argument("log_path")
    p.add_argument("--levels", type=_parse_levels, default=[LogLevel.ERROR, LogLevel.WARNING, LogLevel.CRITICAL])
    p.add_argument("--max", type=int, default=None)
    p.add_argument("--no-fast", action="store_true")
    p.add_argument("--sniff-lines", type=int, default=120)
    p.add_argument("--timestamp-policy", choices=["include", "exclude"], default="include")
    p.add_argument("--no-raw", action="store_true", help="Do not keep the raw line in results")

    # Lookback (simple mode)
    p.add_argument("--hours", type=int, default=24, help="Look back N hours (ignored when a time window is set)")

    # Time window (advanced mode)
    p.add_argument("--since", default=None, help="ISO8601 start time (assumes UTC if tz missing)")
    p.add_argument("--until", default=None, help="ISO8601 end time (assumes UTC if tz missing)")
    p.add_argument("--date", default=None, help="YYYY-MM-DD (UTC day)")
    p.add_argument("--hour", default=None, help="YYYY-MM-DDTHH (UTC hour)")
    p.add_argument("--week", default=None, help="YYYY-Www (ISO week, UTC)")
    p.add_argument("--month", default=None, help="YYYY-MM (UTC month)")

    args = p.parse_args()
    path = Path(args.log_path)

    try:
        since, until = _resolve_time_window(args)

        # If a window is defined, disable lookback in log_service by passing hours_lookback=None
        hours_lookback = None if (since is not None or until is not None) else args.hours

        entries = get_logs(
            path,
            hours_lookback=hours_lookback,
            since=since,
            until=until,
            severities=args.levels,
            max_results=args.max,
            fast_prefilter=not args.no_fast,
            parser=default_parser(),
            timestamp_policy=args.timestamp_policy,
            sniff_lines=args.sniff_lines,
            include_raw=not args.no_raw,
        )
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        raise SystemExit(2)
    except (ValueError, argparse.ArgumentTypeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(2)

    for e in entries:
        ts = e.timestamp.isoformat() if e.timestamp else "-"
        print(f"{e.line_no} {ts} [{e.level.value}] {e.message}")

    print(f"\nFound {len(entries)} matching entries.")


if __name__ == "__main__":
    main()
