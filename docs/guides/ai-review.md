---
title: AI Review
description: Optional Gemini-based review of non-error log signals.
---

The AI review pipeline sends all non-identified log lines (by default: anything
that is not WARNING/ERROR/CRITICAL) to Gemini and returns structured findings.
It is optional and not exposed as an MCP tool unless enabled via
`include_ai_review`. You can override the identified levels by passing `levels`
to the tool.

## Requirements

- Install the extra: `pip install -e ".[ai]"`
- Set `GEMINI_API_KEY` (or `GOOGLE_API_KEY`)

## Example Usage

```python
from datetime import UTC, datetime, timedelta

from mcp_log_triage_server.core.ai_review import review_non_error_logs

now = datetime.now(UTC)
response = review_non_error_logs(
    "samples/bracket.log",
    exclude_line_nos=set(),
    hours_lookback=None,
    since=now - timedelta(hours=2),
    until=now,
)

for finding in response.findings:
    print(finding.title, finding.confidence)
```
