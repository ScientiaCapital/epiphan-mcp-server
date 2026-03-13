#!/bin/bash
set -e
echo "Setting up epiphan-mcp-server..."

# Check for required env
if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    echo "Warning: No .env file found. Copy from .env.example:"
    echo "  cp .env.example .env"
  else
    echo "Warning: No .env file found. Required vars: PEARL_DEVICES, PEARL_USERNAME, PEARL_PASSWORD"
  fi
fi

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install package with dev dependencies
pip install -e ".[dev]"

echo "Ready!"
echo "  Run MCP server: python -m epiphan_mcp"
echo "  Run tests: pytest"
echo "  Type check: mypy src/"
echo "  Lint: ruff check src/"
