"""Backward-compatible entrypoint for stdio transport.

Prefer importing from :mod:`server.log_server`.
"""

from mcp_log_triage_server.server.log_server import main

if __name__ == "__main__":
    main()
