from __future__ import annotations

from pathlib import Path

from mcp_log_triage_server.core.formats import default_scan_config
from mcp_log_triage_server.core.models import LogLevel
from mcp_log_triage_server.core.scanning import DetectedFormat, iter_hits, sniff_format


def _write_bytes(path: Path, lines: list[bytes]) -> None:
    path.write_bytes(b"".join(line + b"\n" for line in lines))


def test_sniff_format_access(tmp_path: Path) -> None:
    path = tmp_path / "access.log"
    lines = [
        b'127.0.0.1 - - [10/Oct/2000:13:55:36 -0700] "GET / HTTP/1.0" 404 2326',
        b'127.0.0.1 - - [10/Oct/2000:13:55:37 -0700] "GET /" 404 10',
        b'127.0.0.1 - - [10/Oct/2000:13:55:38 -0700] "GET /" 404 10',
    ]
    _write_bytes(path, lines)
    assert sniff_format(path, sample_lines=10) == DetectedFormat.ACCESS


def test_sniff_format_syslog(tmp_path: Path) -> None:
    path = tmp_path / "sys.log"
    lines = [
        b"<34>1 2025-12-30T08:12:04Z host app 1 - - msg",
        b"<34>1 2025-12-30T08:12:05Z host app 1 - - msg",
        b"<34>1 2025-12-30T08:12:06Z host app 1 - - msg",
    ]
    _write_bytes(path, lines)
    assert sniff_format(path, sample_lines=10) == DetectedFormat.SYSLOG


def test_sniff_format_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "json.log"
    lines = [
        b'{"level":"error","message":"boom"}',
        b'{"level":"error","message":"boom"}',
        b'{"level":"error","message":"boom"}',
    ]
    _write_bytes(path, lines)
    assert sniff_format(path, sample_lines=10) == DetectedFormat.JSONL


def test_sniff_format_bracket(tmp_path: Path) -> None:
    path = tmp_path / "bracket.log"
    lines = [
        b"2025-12-30 08:12:04 [ERROR] boom",
        b"2025-12-30 08:12:05 [ERROR] boom",
        b"2025-12-30 08:12:06 [ERROR] boom",
    ]
    _write_bytes(path, lines)
    assert sniff_format(path, sample_lines=10) == DetectedFormat.BRACKET


def test_sniff_format_unknown(tmp_path: Path) -> None:
    path = tmp_path / "unknown.log"
    _write_bytes(path, [b"just text", b"more text", b"still nothing"])
    assert sniff_format(path, sample_lines=10) == DetectedFormat.UNKNOWN


def test_iter_hits_access(tmp_path: Path) -> None:
    path = tmp_path / "access.log"
    lines = [
        b'127.0.0.1 - - [10/Oct/2000:13:55:36 -0700] "GET /" 200 10',
        b'127.0.0.1 - - [10/Oct/2000:13:55:37 -0700] "GET /" 404 10',
    ]
    _write_bytes(path, lines)
    hits = list(iter_hits(path, detected=DetectedFormat.ACCESS))
    assert len(hits) == 1
    assert hits[0].line_no == 2
    assert hits[0].level == LogLevel.WARNING


def test_iter_hits_syslog(tmp_path: Path) -> None:
    path = tmp_path / "sys.log"
    lines = [
        b"<11>1 2025-12-30T08:12:04Z host app 1 - - error",
        b"<14>1 2025-12-30T08:12:05Z host app 1 - - info",
    ]
    _write_bytes(path, lines)
    hits = list(iter_hits(path, detected=DetectedFormat.SYSLOG))
    assert len(hits) == 1
    assert hits[0].line_no == 1
    assert hits[0].level == LogLevel.ERROR


def test_iter_hits_token_scan(tmp_path: Path) -> None:
    path = tmp_path / "tokens.log"
    _write_bytes(path, [b"INFO ok", b"foo ERROR failure"])
    hits = list(
        iter_hits(
            path,
            detected=DetectedFormat.UNKNOWN,
            scan=default_scan_config(),
        )
    )
    assert len(hits) == 1
    assert hits[0].line_no == 2
