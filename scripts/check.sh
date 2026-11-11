#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHONPATH="$ROOT/src" python3 -m figma_mcp_guard doctor
PYTHONPATH="$ROOT/src" python3 -m figma_mcp_guard check \
  --tokens "$ROOT/examples/tokens.json" \
  --css "$ROOT/examples/theme.css"
PYTHONPATH="$ROOT/src" python3 -m unittest discover -s "$ROOT/tests" -t "$ROOT" -q
echo "All self-checks passed."
