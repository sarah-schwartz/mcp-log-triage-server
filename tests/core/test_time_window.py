from __future__ import annotations

from datetime import UTC, datetime

import pytest

from mcp_log_triage_server.core.time_window import (
    parse_iso_dt,
    range_for_hour,
    range_for_month,
    range_for_week,
    resolve_time_window,
)


def test_parse_iso_dt_assumes_utc() -> None:
    dt = parse_iso_dt("2025-12-31T10:00:00")
    assert dt == datetime(2025, 12, 31, 10, 0, 0, tzinfo=UTC)


def test_range_for_hour_rounds_to_hour() -> None:
    start, end = range_for_hour("2025-12-31T10")
    assert start == datetime(2025, 12, 31, 10, 0, 0, tzinfo=UTC)
    assert end == datetime(2025, 12, 31, 11, 0, 0, tzinfo=UTC)


def test_range_for_week_invalid_format() -> None:
    with pytest.raises(ValueError):
        range_for_week("2025-52")


def test_range_for_month_invalid_format() -> None:
    with pytest.raises(ValueError):
        range_for_month("2025-W52")


def test_resolve_date_overrides_since_until() -> None:
    since, until = resolve_time_window(
        since="2025-12-31T10:00:00Z",
        until="2025-12-31T11:00:00Z",
        date_="2025-12-30",
    )
    assert since == datetime(2025, 12, 30, 0, 0, 0, tzinfo=UTC)
    assert until == datetime(2025, 12, 31, 0, 0, 0, tzinfo=UTC)


def test_resolve_since_until() -> None:
    since, until = resolve_time_window(
        since="2025-12-31T10:00:00Z",
        until="2025-12-31T11:00:00Z",
    )
    assert since == datetime(2025, 12, 31, 10, 0, 0, tzinfo=UTC)
    assert until == datetime(2025, 12, 31, 11, 0, 0, tzinfo=UTC)
