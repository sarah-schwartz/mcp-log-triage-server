# Log Triage MCP Server

Local MCP server that exposes tools, resources, and prompts to triage log files.

## What It Does

- Parses common log formats (syslog, access logs, JSON lines, bracketed timestamps)
- Filters by time window, severity, and substring
- Exposes resources for sample data and scoped file/log access
- Optionally reviews non-error signals with a Gemini-based pipeline

## Requirements

- Python 3.11+
- Local access to the log files you want to analyze

## Run Locally (stdio)

```bash
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e .
python -m mcp_log_triage_server
```

## Example Tool Call

```json
{
  "log_path": "samples/access.log",
  "date": "2025-12-31",
  "levels": ["error", "critical"],
  "include_raw": true
}
```

## Documentation

- `docs/index.md`
- `docs/getting-started/installation.md`
- `docs/getting-started/quickstart.md`
- `docs/guides/tools.md`
- `docs/guides/resources.md`
- `docs/guides/prompts.md`
- `docs/guides/ai-review.md`
- `docs/reference/configuration.md`
- `docs/reference/log-formats.md`
- `docs/reference/cli.md`
- `docs/development/architecture.md`
- `docs/development/testing.md`

## Project Layout

- `src/mcp_log_triage_server/core`: parsing, filtering, scanning, time windows
- `src/mcp_log_triage_server/tools`: MCP tool implementations
- `src/mcp_log_triage_server/resources`: MCP resource registry
- `src/mcp_log_triage_server/prompts`: MCP prompt registry
- `src/mcp_log_triage_server/server`: MCP wiring and stdio entrypoints
- `tests`: mirrors `src` structure
- `docs`: structured documentation
- `samples`: example log files
