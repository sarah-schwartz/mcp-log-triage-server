"""Time-window parsing helpers.

Converts user-friendly time window selectors into UTC datetime ranges.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta

_WEEK_RE = re.compile(r"^(?P<y>\d{4})-W(?P<w>\d{2})$")
_MONTH_RE = re.compile(r"^(?P<y>\d{4})-(?P<m>\d{2})$")


def parse_iso_dt(s: str) -> datetime:
    """Parse ISO8601 datetime. If tz is missing, assume UTC."""
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def range_for_date(s: str) -> tuple[datetime, datetime]:
    """Return the UTC day window for an ISO date string."""
    d = date.fromisoformat(s)
    start = datetime(d.year, d.month, d.day, tzinfo=UTC)
    end = start + timedelta(days=1)
    return start, end


def range_for_hour(s: str) -> tuple[datetime, datetime]:
    """Return the UTC hour window for a YYYY-MM-DDTHH selector."""
    base = datetime.fromisoformat(s)
    if base.tzinfo is None:
        base = base.replace(tzinfo=UTC)
    start = base.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=1)
    return start, end


def range_for_week(s: str) -> tuple[datetime, datetime]:
    """Return the UTC week window for a YYYY-Www selector."""
    m = _WEEK_RE.match(s)
    if not m:
        raise ValueError("week must look like YYYY-Www (e.g., 2025-W52)")
    y = int(m.group("y"))
    w = int(m.group("w"))
    start_date = date.fromisocalendar(y, w, 1)  # Monday
    start = datetime(start_date.year, start_date.month, start_date.day, tzinfo=UTC)
    end = start + timedelta(days=7)
    return start, end


def range_for_month(s: str) -> tuple[datetime, datetime]:
    """Return the UTC month window for a YYYY-MM selector."""
    m = _MONTH_RE.match(s)
    if not m:
        raise ValueError("month must look like YYYY-MM (e.g., 2025-12)")
    y = int(m.group("y"))
    mo = int(m.group("m"))
    start = datetime(y, mo, 1, tzinfo=UTC)
    if mo == 12:
        end = datetime(y + 1, 1, 1, tzinfo=UTC)
    else:
        end = datetime(y, mo + 1, 1, tzinfo=UTC)
    return start, end


def resolve_time_window(
    *,
    since: str | None = None,
    until: str | None = None,
    date_: str | None = None,
    hour: str | None = None,
    week: str | None = None,
    month: str | None = None,
) -> tuple[datetime | None, datetime | None]:
    """Resolve a UTC time window using selectors over explicit bounds."""
    if date_:
        return range_for_date(date_)
    if hour:
        return range_for_hour(hour)
    if week:
        return range_for_week(week)
    if month:
        return range_for_month(month)

    s = parse_iso_dt(since) if since else None
    u = parse_iso_dt(until) if until else None
    return s, u
