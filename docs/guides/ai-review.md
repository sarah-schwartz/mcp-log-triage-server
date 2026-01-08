---
title: AI Review
description: Optional Gemini-based review of non-error log signals.
---

The AI review pipeline sends non-identified log lines to Gemini and returns
structured findings. It is optional and only triggered when
`include_ai_review=true` on `triage_logs`.

By default, identified levels are WARNING/ERROR/CRITICAL and are returned in
`entries`. Remaining lines are chunked, redacted, and sent to the AI review
pipeline.

The AI review helpers are async to avoid blocking the event loop during file
reads and model calls.

## Requirements

- Install the extra: `uv pip install -e ".[ai]"`
- Set `GEMINI_API_KEY` (or `GOOGLE_API_KEY`)

## How It Works

1. The log is scanned and parsed as usual.
2. Identified severities are separated from non-identified lines.
3. Non-identified lines are chunked into segments.
4. Each segment is redacted and sent to Gemini with a structured schema.
5. Findings below the confidence threshold are discarded.

Redaction removes common PII or secret-like tokens (emails, IPv4, JWTs, and
long tokens) before sending content to the model.

## Example Usage

```python
import asyncio
from datetime import UTC, datetime, timedelta

from mcp_log_triage_server.core.ai_review import review_non_error_logs

async def main() -> None:
    now = datetime.now(UTC)
    response = await review_non_error_logs(
        "samples/bracket.log",
        exclude_line_nos=set(),
        hours_lookback=None,
        since=now - timedelta(hours=2),
        until=now,
    )

    for finding in response.findings:
        print(finding.title, finding.confidence)

asyncio.run(main())
```

## Operational Notes

- Expect higher latency when AI review is enabled.
- API keys are read from environment variables at runtime.
- AI review is best used for noisy logs where errors are not explicit.
