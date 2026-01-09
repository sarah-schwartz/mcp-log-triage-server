from __future__ import annotations

import threading
from datetime import UTC, datetime
from pathlib import Path

import pytest

from mcp_log_triage_server.core.log_service import iter_entries
from mcp_log_triage_server.core.models import LogEntry, LogLevel


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


@pytest.mark.asyncio
async def test_iter_entries_parallel_preserves_order(tmp_path: Path) -> None:
    path = tmp_path / "app.log"
    lines = [f"line {i}" for i in range(1, 7)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    release_first = threading.Event()

    class SlowParser:
        def parse(self, line_no: int, line: str) -> LogEntry | None:
            if line_no == len(lines):
                release_first.set()
            if line_no == 1:
                release_first.wait()
            return LogEntry(
                line_no=line_no,
                timestamp=None,
                level=LogLevel.INFO,
                message=line,
                raw=line,
            )

    entries = [
        e
        async for e in iter_entries(
            path,
            parser=SlowParser(),
            fast_prefilter=False,
            max_workers=4,
            hours_lookback=None,
        )
    ]

    assert [e.line_no for e in entries] == list(range(1, 7))


@pytest.mark.asyncio
async def test_iter_entries_invalid_env_max_workers_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "app.log"
    path.write_text("line 1\n", encoding="utf-8")

    class BasicParser:
        def parse(self, line_no: int, line: str) -> LogEntry | None:
            return LogEntry(
                line_no=line_no,
                timestamp=None,
                level=LogLevel.INFO,
                message=line,
                raw=line,
            )

    monkeypatch.setenv("LOG_TRIAGE_MAX_WORKERS", "0")

    with pytest.raises(ValueError, match="LOG_TRIAGE_MAX_WORKERS"):
        _ = [
            e
            async for e in iter_entries(
                path,
                parser=BasicParser(),
                fast_prefilter=False,
                hours_lookback=None,
            )
        ]
