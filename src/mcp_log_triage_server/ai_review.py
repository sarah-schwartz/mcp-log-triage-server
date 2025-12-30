from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Literal, Optional

from google import genai
from pydantic import BaseModel, Field

from mcp_log_triage_server.log_service import iter_entries
from mcp_log_triage_server.models import LogEntry, LogLevel

logger = logging.getLogger(__name__)

_SUSPICIOUS_RE = re.compile(
    r"(?i)\b("
    r"fail|failed|failure|fatal|panic|segfault|exception|traceback|stack\s*trace|"
    r"timeout|timed\s*out|deadline|circuit\s*open|unavailable|refused|denied|"
    r"rate\s*limit|429|503|disconnect|reset\s*by\s*peer|broken\s*pipe|oom|out\s*of\s*memory|"
    r"corrupt|invalid|checksum|permission|unauthorized|forbidden|"
    r"rollback|retrying|retri(?:ed|es)|backoff|throttl"
    r")\b"
)

_EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_JWT_RE = re.compile(r"\beyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b")
_LONG_TOKEN_RE = re.compile(r"\b[a-zA-Z0-9_\-]{32,}\b")


class AIFinding(BaseModel):
    line_numbers: List[int] = Field(description="Relevant log line numbers.")
    severity_guess: Literal["low", "medium", "high"] = Field(description="Estimated incident severity.")
    confidence: float = Field(ge=0.0, le=1.0, description="0..1 confidence for this finding.")
    title: str = Field(description="Short title of the suspected issue.")
    rationale: str = Field(description="Why these lines may indicate an error/incident.")
    recommendation: str = Field(description="Next debugging step to confirm or mitigate.")


class AIReviewResponse(BaseModel):
    findings: List[AIFinding] = Field(default_factory=list)


@dataclass(frozen=True, slots=True)
class AIReviewConfig:
    model: str = "gemini-2.5-flash-lite"
    max_segments: int = 25
    max_lines_total: int = 800
    segment_max_lines: int = 40
    context_before: int = 2
    context_after: int = 2
    min_confidence: float = 0.55
    temperature: float = 0.0
    redact: bool = True
    max_retries: int = 3


def _redact(text: str) -> str:
    text = _JWT_RE.sub("<REDACTED_JWT>", text)
    text = _EMAIL_RE.sub("<REDACTED_EMAIL>", text)
    text = _IPV4_RE.sub("<REDACTED_IP>", text)
    text = _LONG_TOKEN_RE.sub("<REDACTED_TOKEN>", text)
    return text


def _fmt_line(e: LogEntry) -> str:
    ts = e.timestamp.isoformat() if e.timestamp else "-"
    return f"{e.line_no} {ts} [{e.level.value}] {e.message}"


def _is_candidate(e: LogEntry, exclude_line_nos: set[int]) -> bool:
    if e.line_no in exclude_line_nos:
        return False
    if e.level in (LogLevel.ERROR, LogLevel.CRITICAL):
        return False
    return bool(_SUSPICIOUS_RE.search(e.message) or (e.raw and _SUSPICIOUS_RE.search(e.raw)))


def _build_segments(
    entries: Iterable[LogEntry],
    *,
    exclude_line_nos: set[int],
    context_before: int,
    context_after: int,
    max_segments: int,
    max_lines_total: int,
    segment_max_lines: int,
) -> List[List[LogEntry]]:
    prev: deque[LogEntry] = deque(maxlen=context_before)
    segments: List[List[LogEntry]] = []
    active: Optional[List[LogEntry]] = None
    after_remaining = 0
    total_lines = 0

    for e in entries:
        if active is not None:
            active.append(e)
            after_remaining -= 1
            if len(active) >= segment_max_lines:
                after_remaining = 0
            if after_remaining <= 0:
                segments.append(active)
                total_lines += len(active)
                active = None
                if len(segments) >= max_segments or total_lines >= max_lines_total:
                    break
        else:
            if _is_candidate(e, exclude_line_nos):
                active = list(prev) + [e]
                after_remaining = context_after

        prev.append(e)

    if active is not None and len(segments) < max_segments and total_lines < max_lines_total:
        segments.append(active)

    return segments


def _call_gemini_json(prompt: str, *, cfg: AIReviewConfig) -> AIReviewResponse:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY (or GOOGLE_API_KEY).")

    client = genai.Client(api_key=api_key)

    last_err: Optional[Exception] = None
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

    raise RuntimeError(f"Gemini call failed after {cfg.max_retries} attempts: {last_err}") from last_err


def review_non_error_logs(
    log_path: str,
    *,
    exclude_line_nos: set[int],
    hours_lookback: Optional[int],
    since: Optional[datetime],
    until: Optional[datetime],
    sniff_lines: int = 120,
    timestamp_policy: str = "include",
    cfg: AIReviewConfig = AIReviewConfig(),
) -> AIReviewResponse:
    it = iter_entries(
        log_path,
        severities=None,
        hours_lookback=hours_lookback,
        since=since,
        until=until,
        fast_prefilter=False,
        sniff_lines=sniff_lines,
        timestamp_policy=timestamp_policy,
        include_raw=True,
    )

    segments = _build_segments(
        it,
        exclude_line_nos=exclude_line_nos,
        context_before=cfg.context_before,
        context_after=cfg.context_after,
        max_segments=cfg.max_segments,
        max_lines_total=cfg.max_lines_total,
        segment_max_lines=cfg.segment_max_lines,
    )

    if not segments:
        return AIReviewResponse(findings=[])

    findings: List[AIFinding] = []
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
            "You will be given application log lines that were NOT classified as ERROR/CRITICAL.\n"
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
