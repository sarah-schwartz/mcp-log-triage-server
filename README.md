# Log Triage MCP Server

Local MCP server for structured triage of log files.

This project exposes a single primary MCP tool (`triage_logs`) along with supporting resources and prompts. The goal is to quickly extract relevant log entries (typically warnings and errors) while optionally providing additional context and AI-assisted analysis.

---

## Quickstart

```bash
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e .
python -m mcp_log_triage_server
```

## What This Server Provides

- An MCP (Model Context Protocol) server over stdio
- One main tool for querying log files in a structured way
- Support for multiple common log formats
- Optional AI review for non-error signals with redaction

---

## Core Capabilities

- **Log parsing**
  - Syslog (RFC5424 / RFC3164)
  - Access logs (Common / Combined)
  - Bracketed timestamps
  - JSON lines (one JSON object per line)
  - CEF (Common Event Format)
  - logfmt
  - LTSV
  - Loose keyword-based logs

- **Filtering**
  - Time windows: `since` / `until`, `date`, `hour`, `week`, `month`, `year`
  - Relative lookbacks (hours / days)
  - Severity filtering (default focuses on warning/error)
  - Substring matching
  - Optional inclusion of raw log lines

- **MCP integration**
  - Tool: `triage_logs`
  - Resources for sample data and file access
  - Prompts for guided triage and reporting

- **Async log IO**
  - Non-blocking scans to allow concurrent triage requests
- **Parallel parsing (non-.gz)**
  - Reader -> queue -> worker pool -> ordered aggregator (keeps line_no order)
  - Tune with `LOG_TRIAGE_MAX_WORKERS`

- **Optional AI review**
  - Reviews non-error signals
  - Redacts PII and tokens before sending
  - Returns structured findings

---

## How It Works (High Level)

- Sniff format from the first N lines, then fast-scan for candidate lines when possible
- Parse lines into normalized entries (parallel parsing for non-.gz)
- Filter by time window, severity, and substring
- Optional AI review runs on non-error levels and returns structured findings

---

## Requirements

- Python 3.13+
- Local access to log files
- Optional: Gemini API key for AI review

---

## Running (stdio)

```bash
log-triage-mcp
```

---

## Configuration

Environment variables:

- `GEMINI_API_KEY` or `GOOGLE_API_KEY`
- `LOG_TRIAGE_MAX_WORKERS` (optional, overrides default parser worker count)
- `LOG_TRIAGE_AI_MAX_CONCURRENCY` (optional, overrides AI review concurrency)
- `LOG_TRIAGE_BASE_DIR` (optional, base directory for file:// and log://)

---

## Examples

### Basic triage

Request:

```json
{
  "log_path": "samples/access.log",
  "date": "2025-12-29",
  "levels": ["error"],
  "include_raw": true
}
```

Response (shape):

```json
{
  "count": 1,
  "entries": [
    {
      "timestamp": "2025-12-29T10:05:02+00:00",
      "level": "error",
      "message": "127.0.0.1 \"POST /api/v1/login HTTP/1.1\" -> 500 (42 bytes)",
      "line_no": 3,
      "raw": "127.0.0.1 - - [29/Dec/2025:10:05:02 +0000] \"POST /api/v1/login HTTP/1.1\" 500 42 \"-\" \"curl/8.0\""
    }
  ]
}
```

## Documentation

- `docs/index.md` - documentation index
- `docs/getting-started/quickstart.md` - setup and quickstart
- `docs/reference/log-formats.md` - log format details
- `docs/reference/configuration.md` - configuration options
- `docs/guides/tools.md` - tool usage
- `docs/guides/ai-review.md` - AI review behavior
- `docs/guides/prompts.md` - prompt templates

## Time Window Resolution

Time filters are resolved in the following order:

1. Convenience selectors (`date`, `hour`, `week`, `month`, `year`)
2. Relative lookbacks
3. Explicit `since` / `until`

If none are provided, the default window is the last 24 hours.

---

## AI Review (Optional)

Install with extras:

```bash
uv pip install -e ".[ai]"
```

When `include_ai_review=true`:

- Warning/error entries are excluded
- Remaining lines are redacted and analyzed
- Findings are returned under `ai_findings`
- AI review requests run concurrently (see `AIReviewConfig.max_concurrent_requests`)

---

## Testing

```bash
pytest
```

---

## Limitations and Notes

- `.gz` files are processed serially to preserve ordering and because gzip is not easily splittable
- AI review depends on external API limits and may require retries

---

## Resources and Prompts

### Resources

- `app://log-triage/...`
- `file://{path}` (restricted to `LOG_TRIAGE_BASE_DIR`)
- `log://{path}`

### Prompts

- `summarize_resource`
- `triage_log_file`
- `create_bug_report`

---

## Project Structure

- `src/mcp_log_triage_server/core` - parsing, filtering, time windows
- `src/mcp_log_triage_server/tools` - MCP tool implementations
- `src/mcp_log_triage_server/resources` - MCP resources
- `src/mcp_log_triage_server/prompts` - MCP prompts
- `src/mcp_log_triage_server/server` - MCP wiring and entrypoints
- `tests` - mirrors `src`
- `docs` - extended documentation
- `samples` - example log files
