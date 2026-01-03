---
title: Quickstart
description: Run the server and make your first tool call.
---

## 1) Run the Server (stdio)

```bash
python -m mcp_log_triage_server
```

Or via the console script:

```bash
log-triage-mcp
```

## 2) Call the Tool

The server exposes a single tool named `triage_logs`. Example payload:

```json
{
  "log_path": "samples/access.log",
  "date": "2025-12-31",
  "levels": ["error", "critical"],
  "include_raw": true
}
```

The response includes a `count` and an `entries` array with structured fields.

## 3) Optional AI Review

If the AI review extra is installed and an API key is set, you can add:

```json
{
  "log_path": "samples/bracket.log",
  "hours_lookback": 6,
  "include_ai_review": true
}
```

The response adds an `ai_findings` array with structured recommendations.

## Next Steps

- Learn the full tool API in `docs/guides/tools.md`
- Review resources and prompts in `docs/guides/resources.md` and
  `docs/guides/prompts.md`
- Configure base paths and log levels in `docs/reference/configuration.md`
