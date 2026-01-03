"""LLM-facing review logic.

Turns a set of log entries into a structured AI review response.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .log_service import iter_entries
from .models import LogEntry, LogLevel

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_JWT_RE = re.compile(r"\beyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b")
_LONG_TOKEN_RE = re.compile(r"\b[a-zA-Z0-9_\-]{32,}\b")


class AIFinding(BaseModel):
    line_numbers: list[int] = Field(description="Relevant log line numbers.")
    severity_guess: Literal["low", "medium", "high"] = Field(
        description="Estimated incident severity."
    )
    confidence: float = Field(ge=0.0, le=1.0, description="0..1 confidence for this finding.")
    title: str = Field(description="Short title of the suspected issue.")
    rationale: str = Field(description="Why these lines may indicate an error/incident.")
    recommendation: str = Field(description="Next debugging step to confirm or mitigate.")


class AIReviewResponse(BaseModel):
    findings: list[AIFinding] = Field(default_factory=list)


@dataclass(frozen=True, slots=True)
class AIReviewConfig:
    model: str = "gemini-2.5-flash-lite"
    segment_max_lines: int = 40

    # Local-identified (not sent to AI)
    identified_levels: tuple[LogLevel, ...] = (
        LogLevel.ERROR,
        LogLevel.WARNING,
        LogLevel.CRITICAL,
    )

    # Levels that are sent to the AI review stage.
    ai_levels: tuple[LogLevel, ...] = (
        LogLevel.INFO,
        LogLevel.DEBUG,
        LogLevel.UNKNOWN,
    )

    min_confidence: float = 0.55
    temperature: float = 0.0
    redact: bool = True
    max_retries: int = 3


@dataclass(frozen=True, slots=True)
class AITriageResult:
    """Split output for local triage + AI findings."""

    identified_entries: list[LogEntry]
    ai_review: AIReviewResponse


def _redact(text: str) -> str:
    """Redact sensitive tokens from log text."""
    text = _JWT_RE.sub("<REDACTED_JWT>", text)
    text = _EMAIL_RE.sub("<REDACTED_EMAIL>", text)
    text = _IPV4_RE.sub("<REDACTED_IP>", text)
    text = _LONG_TOKEN_RE.sub("<REDACTED_TOKEN>", text)
    return text


def _fmt_line(e: LogEntry) -> str:
    """Format a log entry for the AI review prompt."""
    ts = e.timestamp.isoformat() if e.timestamp else "-"
    return f"{e.line_no} {ts} [{e.level.value}] {e.message}"


def _split_entries_for_ai(
    entries: Iterable[LogEntry],
    *,
    exclude_line_nos: set[int],
    identified_levels: set[LogLevel],
    segment_max_lines: int,
) -> tuple[list[LogEntry], list[list[LogEntry]]]:
    """Split entries into identified entries and AI review segments."""
    identified: list[LogEntry] = []
    segments: list[list[LogEntry]] = []
    current: list[LogEntry] = []

    for e in entries:
        if e.line_no in exclude_line_nos:
            continue

        if e.level in identified_levels:
            identified.append(e)
            continue

        current.append(e)

        if len(current) >= segment_max_lines:
            segments.append(current)
            current = []

    if current:
        segments.append(current)

    return identified, segments


def _call_gemini_json(prompt: str, *, cfg: AIReviewConfig) -> AIReviewResponse:
    """Call Gemini and validate the response against the schema."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY (or GOOGLE_API_KEY).")

    try:
        from google import genai
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "google-genai is required for AI review. Install with: pip install '.[ai]'"
        ) from e

    client = genai.Client(api_key=api_key)

    last_err: Exception | None = None
    for attempt in range(1, cfg.max_retries + 1):
        try:
            resp = client.models.generate_content(
                model=cfg.model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": AIReviewResponse.model_json_schema(),
                    "temperature": cfg.temperature,
                },
            )
            return AIReviewResponse.model_validate_json(resp.text)
        except Exception as e:
            last_err = e
            if attempt >= cfg.max_retries:
                break
            sleep_s = min(8, 2 ** (attempt - 1))
            logger.warning("Gemini call failed (attempt %s/%s): %s", attempt, cfg.max_retries, e)
            time.sleep(sleep_s)

    raise RuntimeError(
        f"Gemini call failed after {cfg.max_retries} attempts: {last_err}"
    ) from last_err


def _review_segments(segments: list[list[LogEntry]], *, cfg: AIReviewConfig) -> AIReviewResponse:
    """Review segments with the AI model and filter findings."""
    if not segments:
        return AIReviewResponse(findings=[])

    findings: list[AIFinding] = []
    seen_hashes: set[str] = set()

    for seg in segments:
        text = "\n".join(_fmt_line(e) for e in seg)
        if cfg.redact:
            text = _redact(text)

        h = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
        if h in seen_hashes:
            continue
        seen_hashes.add(h)

        prompt = (
            "You are a log triage assistant.\n"
            "You will be given application log lines that are NOT classified as "
            "WARNING/ERROR/CRITICAL.\n"
            "Identify whether these lines likely indicate a hidden error or incident signal.\n"
            "Return ONLY valid JSON that matches the provided schema.\n"
            "Rules:\n"
            "- Only use evidence from the given lines.\n"
            "- Prefer fewer, higher-quality findings.\n"
            "- If nothing looks like an incident, return an empty findings array.\n\n"
            f"LOG LINES:\n{text}\n"
        )

        resp = _call_gemini_json(prompt, cfg=cfg)
        for f in resp.findings:
            if f.confidence >= cfg.min_confidence:
                findings.append(f)

    return AIReviewResponse(findings=findings)


def review_non_error_logs(
    log_path: str,
    *,
    exclude_line_nos: set[int],
    hours_lookback: int | None,
    since: datetime | None,
    until: datetime | None,
    sniff_lines: int = 120,
    timestamp_policy: str = "include",
    cfg: AIReviewConfig | None = None,
) -> AIReviewResponse:
    """Review non-identified logs by chunking and sending to AI."""
    if cfg is None:
        cfg = AIReviewConfig()

    # Limit iteration to identified and AI-review levels.
    wanted_levels = set(cfg.identified_levels) | set(cfg.ai_levels)

    it = iter_entries(
        log_path,
        severities=wanted_levels,
        hours_lookback=hours_lookback,
        since=since,
        until=until,
        fast_prefilter=False,
        sniff_lines=sniff_lines,
        timestamp_policy=timestamp_policy,
        include_raw=True,
    )

    _, segments = _split_entries_for_ai(
        it,
        exclude_line_nos=exclude_line_nos,
        identified_levels=set(cfg.identified_levels),
        segment_max_lines=cfg.segment_max_lines,
    )

    return _review_segments(segments, cfg=cfg)


def triage_with_ai_review(
    log_path: str,
    *,
    exclude_line_nos: set[int],
    hours_lookback: int | None,
    since: datetime | None,
    until: datetime | None,
    contains: str | None = None,
    sniff_lines: int = 120,
    timestamp_policy: str = "include",
    identified_levels: Iterable[LogLevel] | None = None,
    identified_limit: int | None = None,
    cfg: AIReviewConfig | None = None,
) -> AITriageResult:
    """Split logs into identified entries and AI findings."""
    if cfg is None:
        cfg = AIReviewConfig()
    _ = identified_limit

    identified_set = (
        set(identified_levels) if identified_levels is not None else set(cfg.identified_levels)
    )
    ai_set = set(cfg.ai_levels)

    # Limit iteration to identified and AI-review levels.
    wanted_levels = identified_set | ai_set

    it = iter_entries(
        log_path,
        severities=wanted_levels,
        hours_lookback=hours_lookback,
        since=since,
        until=until,
        contains=contains,
        fast_prefilter=False,
        sniff_lines=sniff_lines,
        timestamp_policy=timestamp_policy,
        include_raw=True,
    )

    identified, segments = _split_entries_for_ai(
        it,
        exclude_line_nos=exclude_line_nos,
        identified_levels=identified_set,
        segment_max_lines=cfg.segment_max_lines,
    )

    return AITriageResult(
        identified_entries=identified,
        ai_review=_review_segments(segments, cfg=cfg),
    )
