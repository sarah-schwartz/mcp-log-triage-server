---
title: Installation
description: Install the server and optional development tools.
---

## Prerequisites

- Python 3.11+
- `pip` available on your PATH
- Read access to the log files you want to triage

## Local Install

```bash
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e .
```

## Optional Extras

Install development tools:

```bash
uv pip install -e ".[dev]"
```

Install the AI review dependency (Gemini client):

```bash
uv pip install -e ".[ai]"
```

Then set one of the required API keys:

- `GEMINI_API_KEY`
- `GOOGLE_API_KEY`

## Verify the Install

Run the server over stdio:

```bash
python -m mcp_log_triage_server
```

If the command exits immediately, check for missing dependencies or an
incorrect Python version.
