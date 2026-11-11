"""Module entrypoint for `python -m figma_mcp_guard`."""

import sys
from .cli import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
