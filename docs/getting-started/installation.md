---
title: Installation
description: Install the server and optional development tools.
---

## Local Development Install

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

## Development Extras

Install test and lint tooling:

```bash
pip install -e ".[dev]"
```

## Optional AI Review

The AI review pipeline uses Gemini and is optional. Install the extra and set
the API key:

```bash
pip install -e ".[ai]"
```

Then set one of:

- `GEMINI_API_KEY`
- `GOOGLE_API_KEY`
