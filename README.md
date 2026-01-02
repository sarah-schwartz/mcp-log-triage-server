# mcp-log-triage-server

An MCP server that exposes tools, resources, and prompts to triage local log files.

## Features

- `triage_logs` tool with time-window selectors, severity filters, and fast prefiltering
- Built-in parsers for syslog, access logs, JSON lines, and bracketed timestamps
- Resources and prompts for MCP clients that support them
- Optional AI review pipeline for non-error signals (Gemini-based)

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

Run the server over stdio:

```bash
python -m mcp_log_triage_server
```

Example tool payload:

```json
{
  "log_path": "samples/access.log",
  "date": "2025-12-31",
  "levels": ["error", "critical"],
  "limit": 200
}
```

## Documentation

- `docs/index.md`
- `docs/getting-started/quickstart.md`
- `docs/guides/tools.md`
- `docs/guides/resources.md`
- `docs/guides/prompts.md`
- `docs/reference/configuration.md`
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

## Development

Lint and format:

```bash
ruff check .
ruff format .
```

Run tests:

```bash
pytest -q
```

## Contributing

See `CONTRIBUTING.md`.

## License

MIT
