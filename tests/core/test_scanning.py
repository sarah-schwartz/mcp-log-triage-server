from __future__ import annotations

from pathlib import Path

import pytest

from mcp_log_triage_server.core.formats import default_scan_config
from mcp_log_triage_server.core.models import LogLevel

from mcp_log_triage_server.core.scanning import DetectedFormat, iter_hits, sniff_format


@pytest.mark.asyncio
async def test_sniff_format_access(tmp_path: Path, write_bytes) -> None:
    path = tmp_path / "access.log"
    lines = [
        b'127.0.0.1 - - [10/Oct/2000:13:55:36 -0700] "GET / HTTP/1.0" 404 2326',
        b'127.0.0.1 - - [10/Oct/2000:13:55:37 -0700] "GET /" 404 10',
        b'127.0.0.1 - - [10/Oct/2000:13:55:38 -0700] "GET /" 404 10',
    ]
    write_bytes(path, lines)
    assert await sniff_format(path, sample_lines=10) == DetectedFormat.ACCESS


@pytest.mark.asyncio
async def test_sniff_format_syslog(tmp_path: Path, write_bytes) -> None:
    path = tmp_path / "sys.log"
    lines = [
        b"<34>1 2025-12-30T08:12:04Z host app 1 - - msg",
        b"<34>1 2025-12-30T08:12:05Z host app 1 - - msg",
        b"<34>1 2025-12-30T08:12:06Z host app 1 - - msg",
    ]
    write_bytes(path, lines)
    assert await sniff_format(path, sample_lines=10) == DetectedFormat.SYSLOG


@pytest.mark.asyncio
async def test_sniff_format_jsonl(tmp_path: Path, write_bytes) -> None:
    path = tmp_path / "json.log"
    lines = [
        b'{"level":"error","message":"boom"}',
        b'{"level":"error","message":"boom"}',
        b'{"level":"error","message":"boom"}',
    ]
    write_bytes(path, lines)
    assert await sniff_format(path, sample_lines=10) == DetectedFormat.JSONL


@pytest.mark.asyncio
async def test_sniff_format_bracket(tmp_path: Path, write_bytes) -> None:
    path = tmp_path / "bracket.log"
    lines = [
        b"2025-12-30 08:12:04 [ERROR] boom",
        b"2025-12-30 08:12:05 [ERROR] boom",
        b"2025-12-30 08:12:06 [ERROR] boom",
    ]
    write_bytes(path, lines)
    assert await sniff_format(path, sample_lines=10) == DetectedFormat.BRACKET


@pytest.mark.asyncio
async def test_sniff_format_unknown(tmp_path: Path, write_bytes) -> None:
    path = tmp_path / "unknown.log"
    write_bytes(path, [b"just text", b"more text", b"still nothing"])
    assert await sniff_format(path, sample_lines=10) == DetectedFormat.UNKNOWN


@pytest.mark.asyncio
async def test_iter_hits_access(tmp_path: Path, write_bytes) -> None:
    path = tmp_path / "access.log"
    lines = [
        b'127.0.0.1 - - [10/Oct/2000:13:55:36 -0700] "GET /" 200 10',
        b'127.0.0.1 - - [10/Oct/2000:13:55:37 -0700] "GET /" 404 10',
    ]
    write_bytes(path, lines)
    hits = [hit async for hit in iter_hits(path, detected=DetectedFormat.ACCESS)]
    assert len(hits) == 1
    assert hits[0].line_no == 2
    assert hits[0].level == LogLevel.WARNING


@pytest.mark.asyncio
async def test_iter_hits_syslog(tmp_path: Path, write_bytes) -> None:
    path = tmp_path / "sys.log"
    lines = [
        b"<11>1 2025-12-30T08:12:04Z host app 1 - - error",
        b"<14>1 2025-12-30T08:12:05Z host app 1 - - info",
    ]
    write_bytes(path, lines)
    hits = [hit async for hit in iter_hits(path, detected=DetectedFormat.SYSLOG)]
    assert len(hits) == 1
    assert hits[0].line_no == 1
    assert hits[0].level == LogLevel.ERROR


@pytest.mark.asyncio
async def test_iter_hits_token_scan(tmp_path: Path, write_bytes) -> None:
    path = tmp_path / "tokens.log"
    write_bytes(path, [b"INFO ok", b"foo ERROR failure"])
    hits = [
        hit
        async for hit in iter_hits(
            path,
            detected=DetectedFormat.UNKNOWN,
            scan=default_scan_config(),
        )
    ]
    assert len(hits) == 1
    assert hits[0].line_no == 2
