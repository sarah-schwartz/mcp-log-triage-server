from __future__ import annotations

from mcp_log_triage_server.core import ai_review as ai_module
from mcp_log_triage_server.core.ai_review import (
    AIFinding,
    AIReviewResponse,
    _redact,
    _split_entries_for_ai,
)
from mcp_log_triage_server.core.models import LogEntry, LogLevel


def test_redact_replaces_sensitive_tokens() -> None:
    text = (
        "user@example.com 1.2.3.4 "
        "eyJaaaaaaaaaa.bbbbbbbbbb.cccccccccc "
        "token=abcdefghijklmnopqrstuvwxyz1234567890"
    )
    redacted = _redact(text)
    assert "<REDACTED_EMAIL>" in redacted
    assert "<REDACTED_IP>" in redacted
    assert "<REDACTED_JWT>" in redacted
    assert "<REDACTED_TOKEN>" in redacted


def test_split_entries_for_ai_separates_identified() -> None:
    entries = [
        LogEntry(line_no=1, timestamp=None, level=LogLevel.INFO, message="start"),
        LogEntry(
            line_no=2,
            timestamp=None,
            level=LogLevel.WARNING,
            message="timeout while calling upstream",
        ),
        LogEntry(line_no=3, timestamp=None, level=LogLevel.INFO, message="after"),
        LogEntry(line_no=4, timestamp=None, level=LogLevel.INFO, message="other"),
    ]

    identified, segments = _split_entries_for_ai(
        entries,
        exclude_line_nos=set(),
        identified_levels={LogLevel.WARNING, LogLevel.ERROR},
        segment_max_lines=10,
    )

    assert len(segments) == 1
    assert [e.line_no for e in segments[0]] == [1, 3, 4]
    assert [e.line_no for e in identified] == [2]


def test_split_entries_for_ai_excludes_line_numbers() -> None:
    entries = [
        LogEntry(line_no=1, timestamp=None, level=LogLevel.INFO, message="start"),
        LogEntry(
            line_no=2,
            timestamp=None,
            level=LogLevel.WARNING,
            message="timeout while calling upstream",
        ),
    ]

    _, segments = _split_entries_for_ai(
        entries,
        exclude_line_nos={1},
        identified_levels={LogLevel.WARNING},
        segment_max_lines=10,
    )

    assert segments == []


def test_review_non_error_logs_excludes_identified_levels(tmp_path, monkeypatch) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text(
        "\n".join(
            [
                "2025-12-30 08:00:00 [INFO] ok",
                "2025-12-30 09:00:00 [WARNING] warn",
                "2025-12-30 10:00:00 [INFO] still ok",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    captured: dict[str, str] = {}

    def fake_call(prompt: str, *, cfg) -> AIReviewResponse:
        captured["prompt"] = prompt
        return AIReviewResponse(
            findings=[
                AIFinding(
                    line_numbers=[1],
                    severity_guess="low",
                    confidence=0.6,
                    title="Test",
                    rationale="Test",
                    recommendation="Test",
                )
            ]
        )

    monkeypatch.setattr(ai_module, "_call_gemini_json", fake_call)

    ai_module.review_non_error_logs(
        log_path=str(log_path),
        exclude_line_nos=set(),
        hours_lookback=None,
        since=None,
        until=None,
    )

    assert "[WARNING]" not in captured["prompt"]
