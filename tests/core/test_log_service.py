from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from mcp_log_triage_server.core.log_service import iter_entries
from mcp_log_triage_server.core.models import LogLevel


@pytest.mark.asyncio
async def test_iter_entries_time_window(tmp_path: Path, write_bracket_log) -> None:
    path = tmp_path / "app.log"
    write_bracket_log(path)

    since = datetime(2025, 12, 30, 8, 30, 0, tzinfo=UTC)
    until = datetime(2025, 12, 30, 10, 0, 0, tzinfo=UTC)

    entries = [
        e
        async for e in iter_entries(
            path,
            since=since,
            until=until,
            hours_lookback=None,
        )
    ]

    assert [e.level for e in entries] == [LogLevel.WARNING]


@pytest.mark.asyncio
async def test_iter_entries_severity_and_contains(tmp_path: Path, write_bracket_log) -> None:
    path = tmp_path / "app.log"
    write_bracket_log(path)

    entries = [
        e
        async for e in iter_entries(
            path,
            since=datetime(2025, 12, 30, 0, 0, 0, tzinfo=UTC),
            until=datetime(2025, 12, 31, 0, 0, 0, tzinfo=UTC),
            hours_lookback=None,
            severities=[LogLevel.ERROR],
            contains="err",
        )
    ]

    assert len(entries) == 1
    assert entries[0].level == LogLevel.ERROR


@pytest.mark.asyncio
async def test_iter_entries_timestamp_policy_exclude(tmp_path: Path, write_bracket_log) -> None:
    path = tmp_path / "app.log"
    write_bracket_log(path)
    path.write_text(path.read_text(encoding="utf-8") + "ERROR without timestamp\n")

    entries = [
        e
        async for e in iter_entries(
            path,
            since=datetime(2025, 12, 30, 0, 0, 0, tzinfo=UTC),
            until=datetime(2025, 12, 31, 0, 0, 0, tzinfo=UTC),
            hours_lookback=None,
            timestamp_policy="exclude",
        )
    ]

    assert all(e.timestamp is not None for e in entries)


@pytest.mark.asyncio
async def test_iter_entries_missing_file_raises(tmp_path: Path) -> None:
    path = tmp_path / "missing.log"
    with pytest.raises(FileNotFoundError):
        _ = [e async for e in iter_entries(path)]
