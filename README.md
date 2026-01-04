# Log Triage MCP Server

Local MCP server for structured triage of log files.

This project exposes a single primary MCP tool (`triage_logs`) along with supporting resources and prompts. The goal is to quickly extract relevant log entries (typically warnings and errors) while optionally providing additional context and AI-assisted analysis.

---

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
  - JSON lines
  - CEF, logfmt, LTSV
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

- **Optional AI review**
  - Reviews non-error signals
  - Redacts PII and tokens before sending
  - Returns structured findings

---

## Requirements

- Python 3.13+
- Local access to log files
- Optional: Gemini API key for AI review

---

## Quickstart (stdio)

```bash
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e .
python -m mcp_log_triage_server
```

Or via the console script:

```bash
log-triage-mcp
```

---

## Example MCP Tool Call

Request:

```json
{
  "log_path": "samples/access.log",
  "date": "2025-12-31",
  "levels": ["error", "critical"],
  "include_raw": true
}
```

Response (shape):

```json
{
  "count": 1,
  "entries": [
    {
      "line_no": 42,
      "timestamp": "2025-12-31T08:12:04Z",
      "level": "error",
      "message": "upstream timeout",
      "raw": "2025-12-31T08:12:04Z [ERROR] upstream timeout"
    }
  ]
}
```

---

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

Environment variables:

- `GEMINI_API_KEY` or `GOOGLE_API_KEY`

When `include_ai_review=true`:

- Warning/error entries are excluded
- Remaining lines are redacted and analyzed
- Findings are returned under `ai_findings`

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

- `src/mcp_log_triage_server/core` — parsing, filtering, time windows
- `src/mcp_log_triage_server/tools` — MCP tool implementations
- `src/mcp_log_triage_server/resources` — MCP resources
- `src/mcp_log_triage_server/prompts` — MCP prompts
- `src/mcp_log_triage_server/server` — MCP wiring and entrypoints
- `tests` — mirrors `src`
- `docs` — extended documentation
- `samples` — example log files
