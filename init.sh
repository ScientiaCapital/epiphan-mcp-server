#!/usr/bin/env bash
set -euo pipefail

echo "Initializing epiphan-mcp-server (Python 3.11+)..."

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -e ".[dev]"

echo ""
echo "Done. Virtual environment is at .venv/"
echo "Activate with: source .venv/bin/activate"
echo ""
echo "Run MCP server: python -m epiphan_mcp"
echo "Run tests:      pytest"
echo "Type check:     mypy src/"
echo "Lint:           ruff check src/"
