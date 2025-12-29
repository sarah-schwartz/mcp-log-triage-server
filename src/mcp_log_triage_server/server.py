from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mcp_log_triage_server.log_service import default_parser, get_logs
from mcp_log_triage_server.models import LogLevel


def _parse_levels(s: str) -> list[LogLevel]:
    """Parse comma-separated levels into LogLevel values."""
    out: list[LogLevel] = []
    for part in s.split(","):
        name = part.strip().upper()
        if not name:
            continue
        try:
            out.append(LogLevel(name))
        except ValueError as e:
            raise argparse.ArgumentTypeError(
                "Invalid level. Allowed: CRITICAL, ERROR, WARNING, INFO, DEBUG, UNKNOWN"
            ) from e
    if not out:
        raise argparse.ArgumentTypeError("At least one level must be provided")
    return out


def main() -> None:
    """CLI entrypoint for local testing (not MCP yet)."""
    p = argparse.ArgumentParser(description="Generic log triage (sniff + adaptive fast scan).")
    p.add_argument("log_path")
    p.add_argument("--hours", type=int, default=24)
    p.add_argument(
        "--levels",
        type=_parse_levels,
        default=[LogLevel.ERROR, LogLevel.WARNING, LogLevel.CRITICAL],
    )
    p.add_argument("--max", type=int, default=None)
    p.add_argument("--no-fast", action="store_true")
    p.add_argument("--sniff-lines", type=int, default=120)
    p.add_argument("--timestamp-policy", choices=["include", "exclude"], default="include")
    p.add_argument("--no-raw", action="store_true", help="Do not keep the raw line in results")

    args = p.parse_args()
    path = Path(args.log_path)

    try:
        entries = get_logs(
            path,
            hours_lookback=args.hours,
            severities=args.levels,
            max_results=args.max,
            fast_prefilter=not args.no_fast,
            parser=default_parser(),
            timestamp_policy=args.timestamp_policy,
            sniff_lines=args.sniff_lines,
            include_raw=not args.no_raw,
        )
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        raise SystemExit(2)

    for e in entries:
        ts = e.timestamp.isoformat() if e.timestamp else "-"
        print(f"{e.line_no} {ts} [{e.level.value}] {e.message}")

    print(f"\nFound {len(entries)} matching entries.")


if __name__ == "__main__":
    main()
