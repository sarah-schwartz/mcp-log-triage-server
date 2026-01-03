from __future__ import annotations

from datetime import UTC, datetime

from mcp_log_triage_server.core.formats import (
    AccessLogParser,
    BracketTimestampParser,
    CompositeParser,
    JsonLinesParser,
    LooseLevelParser,
    SyslogParser,
)
from mcp_log_triage_server.core.models import LogLevel


def test_bracket_timestamp_parser() -> None:
    parser = BracketTimestampParser()
    entry = parser.parse(1, "2025-12-30 08:12:04 [ERROR] boom")
    assert entry is not None
    assert entry.line_no == 1
    assert entry.timestamp == datetime(2025, 12, 30, 8, 12, 4, tzinfo=UTC)
    assert entry.level == LogLevel.ERROR
    assert entry.message == "boom"
    assert "[ERROR]" not in entry.message


def test_json_lines_parser() -> None:
    parser = JsonLinesParser()
    line = '{"timestamp":"2025-12-30T08:12:04Z","level":"error","message":"boom"}'
    entry = parser.parse(1, line)
    assert entry is not None
    assert entry.line_no == 1
    assert entry.timestamp == datetime(2025, 12, 30, 8, 12, 4, tzinfo=UTC)
    assert entry.level == LogLevel.ERROR
    assert entry.message == "boom"


def test_syslog_parser_rfc5424() -> None:
    parser = SyslogParser()
    line = "<34>1 2025-12-30T08:12:04Z host app 123 - - hello world"
    entry = parser.parse(1, line)
    assert entry is not None
    assert entry.line_no == 1
    assert entry.timestamp == datetime(2025, 12, 30, 8, 12, 4, tzinfo=UTC)
    assert entry.level == LogLevel.CRITICAL
    assert entry.message == "host app: hello world"


def test_access_log_parser() -> None:
    parser = AccessLogParser()
    line = '127.0.0.1 - - [10/Oct/2000:13:55:36 -0700] "GET / HTTP/1.0" 404 2326'
    entry = parser.parse(1, line)
    assert entry is not None
    assert entry.line_no == 1
    if entry.timestamp is not None:
        assert entry.timestamp == datetime(2000, 10, 10, 20, 55, 36, tzinfo=UTC)
    assert entry.level == LogLevel.WARNING
    assert "404" in entry.message


def test_loose_level_parser() -> None:
    parser = LooseLevelParser()
    entry = parser.parse(1, "WARN something happened")
    assert entry is not None
    assert entry.line_no == 1
    assert entry.timestamp is None
    assert entry.level == LogLevel.WARNING
    assert "something happened" in entry.message


def test_composite_parser_first_match_wins() -> None:
    parser = CompositeParser(parsers=[JsonLinesParser(), LooseLevelParser()])
    entry = parser.parse(1, '{"level":"error","message":"boom","timestamp":"2025-12-30T08:12:04Z"}')
    assert entry is not None
    assert entry.line_no == 1
    assert entry.timestamp == datetime(2025, 12, 30, 8, 12, 4, tzinfo=UTC)
    assert entry.level == LogLevel.ERROR
    assert entry.message == "boom"
