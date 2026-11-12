#!/bin/bash
# Install, run the offline checks, replay the healthcare answer keys.
set -euo pipefail
cd "$(dirname "$0")/.."

uv sync
uv run pytest -q
uv run callm oracle --industry healthcare --all || true
if command -v npm >/dev/null; then (cd ui && npm install --no-audit --no-fund && npm run build); else echo "npm not found: skipping the console UI build"; fi

echo
echo "Ready. Next: 'uv run callm ui' for the console, or README.md 'Run it' for the command line."
