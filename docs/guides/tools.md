---
title: Tools
description: Tool reference for log triage.
---

# `triage_logs`

Return structured log entries from a file, optionally constrained by a time
window and filters.

## Inputs

- `log_path` (str): path to a local log file (plain text or `.gz`)
- `since` / `until` (str, optional): ISO-8601 datetimes
- `date` (str, optional): `YYYY-MM-DD`
- `hour` (str, optional): `YYYY-MM-DDTHH`
- `week` (str, optional): `YYYY-Www`
- `month` (str, optional): `YYYY-MM`
- `levels` (list[str], optional): severity filter, case-insensitive (defaults to
  `["WARNING", "ERROR"]`)
- `include_all_levels` (bool, optional): return all severities and ignore `levels`
- `include_ai_review` (bool, optional): split logs into identified entries and AI
  findings; defaults `levels` to `["WARNING", "ERROR", "CRITICAL"]`
- `contains` (str, optional): substring filter applied to the raw line
- `limit` (int, optional): accepted for compatibility but ignored
- `include_raw` (bool, optional): include the original raw log line

Time window precedence:

1. `date` / `hour` / `week` / `month`
2. `since` / `until`
3. fallback to last 24 hours

Note: `include_ai_review` cannot be combined with `include_all_levels`.
AI review requires `GEMINI_API_KEY` or `GOOGLE_API_KEY`.

## Output

```json
{
  "count": 3,
  "entries": [
    {
      "timestamp": "2025-12-30T08:12:04+00:00",
      "level": "error",
      "message": "upstream timeout route=/api/v1/items",
      "line_no": 42,
      "raw": "2025-12-30T08:12:04Z [ERROR] upstream timeout route=/api/v1/items"
    }
  ]
}
```

When `include_ai_review=true`, the response adds `ai_findings`:

```json
{
  "count": 3,
  "entries": [],
  "ai_findings": [
    {
      "line_numbers": [12, 13],
      "severity_guess": "medium",
      "confidence": 0.62,
      "title": "Retry loop detected",
      "rationale": "Repeated retries with backoff may indicate upstream outage.",
      "recommendation": "Check upstream availability and retry policy."
    }
  ]
}
```

## Example

```json
{
  "log_path": "samples/bracket.log",
  "date": "2025-12-30",
  "levels": ["warning", "error", "critical"],
  "contains": "timeout"
}
```
