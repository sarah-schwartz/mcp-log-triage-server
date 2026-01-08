---
title: Tools
description: Tool reference for log triage.
---

# `triage_logs`

Return structured log entries from a file, optionally constrained by time
windows and filters. This is the primary tool exposed by the server.

## Purpose

Use this tool to scan local logs for relevant incidents without loading the
entire file into memory. The server can prefilter large logs and then parse
recognized formats for structured output.

The tool runs asynchronously in the server so multiple triage requests can
execute concurrently without blocking the event loop.

## Inputs

`log_path` (str)
Path to a local log file. Plain text and `.gz` files are supported.

`since` / `until` (str, optional)
ISO-8601 datetimes. If timezone is omitted, UTC is assumed.

`date` (str, optional)
`YYYY-MM-DD` selector for a full UTC day window.

`hour` (str, optional)
`YYYY-MM-DDTHH` selector for a single UTC hour.

`week` (str, optional)
`YYYY-Www` ISO week selector.

`month` (str, optional)
`YYYY-MM` calendar month selector.

`year` (str, optional)
`YYYY` calendar year selector.

`days_lookback` (int, optional)
Relative lookback window in days.

`hours_lookback` (int, optional)
Relative lookback window in hours.

Only one lookback value should be set at a time.

`levels` (list[str], optional)
Severity filter, case-insensitive. Defaults to `["WARNING", "ERROR"]` unless
`include_ai_review=true`, which defaults to `["WARNING", "ERROR", "CRITICAL"]`.

`include_all_levels` (bool, optional)
When true, ignore `levels` and return all severities.

`include_ai_review` (bool, optional)
When true, split logs into identified entries and AI findings.

`contains` (str, optional)
Substring filter applied to the raw line.

`include_raw` (bool, optional)
Whether to include the original raw log line in each entry.

## Time Window Behavior

Selector precedence:

1. `date` / `hour` / `week` / `month` / `year`
2. `days_lookback` / `hours_lookback`
3. `since` / `until`
4. fallback to last 24 hours

Only one selector should be used at a time. If both a selector and `since`/`until`
are provided, the selector takes precedence. Lookback values also override
`since`/`until` when both are provided.

## AI Review Notes

- `include_ai_review` cannot be combined with `include_all_levels`
- Requires `GEMINI_API_KEY` or `GOOGLE_API_KEY`
- AI review only evaluates non-identified levels; identified entries are still
  returned in `entries`

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

## Errors You May See

- `FileNotFoundError`: `log_path` does not exist
- `ValueError`: invalid time windows or unknown level names
- `RuntimeError`: missing API key or AI client dependency (AI review only)

## Example

```json
{
  "log_path": "samples/bracket.log",
  "date": "2025-12-30",
  "levels": ["warning", "error", "critical"],
  "contains": "timeout"
}
```
