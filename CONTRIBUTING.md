# Contributing

Thanks for taking the time to contribute. This project aims to stay small,
predictable, and easy to maintain.

## Before You Start

- For non-trivial changes, open an issue first to confirm scope and direction.
- Small fixes (typos, docs, tests) can go straight to a pull request.

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Code Quality

```bash
ruff check .
ruff format .
pytest -q
```

## Documentation

- Keep docs concise and task-focused.
- Prefer runnable examples and concrete outputs.
- Update `docs/index.md` when adding new pages.

## Pull Request Checklist

- Tests updated or added for behavior changes
- Docs updated for user-facing changes
- `ruff` and `pytest` pass locally
- PR description explains the "why" and any trade-offs
