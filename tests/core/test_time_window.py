from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from mcp_log_triage_server.core.time_window import (
    parse_iso_dt,
    range_for_hour,
    range_for_month,
    range_for_week,
    range_for_year,
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


def test_range_for_year() -> None:
    start, end = range_for_year("2025")
    assert start == datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
    assert end == datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)


def test_range_for_year_invalid_format() -> None:
    with pytest.raises(ValueError):
        range_for_year("25")


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


def test_resolve_year_overrides_since_until() -> None:
    since, until = resolve_time_window(
        since="2024-12-31T10:00:00Z",
        until="2024-12-31T11:00:00Z",
        year="2025",
    )
    assert since == datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
    assert until == datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)


def test_resolve_lookback_overrides_since_until() -> None:
    now = datetime(2025, 12, 31, 12, 0, 0, tzinfo=UTC)
    since, until = resolve_time_window(
        since="2025-12-01T00:00:00Z",
        until="2025-12-02T00:00:00Z",
        days_lookback=3,
        now=now,
    )
    assert since == now - timedelta(days=3)
    assert until == now


def test_resolve_hours_lookback() -> None:
    now = datetime(2025, 12, 31, 12, 0, 0, tzinfo=UTC)
    since, until = resolve_time_window(hours_lookback=6, now=now)
    assert since == now - timedelta(hours=6)
    assert until == now


def test_resolve_lookback_conflict() -> None:
    with pytest.raises(ValueError):
        resolve_time_window(days_lookback=1, hours_lookback=2)
