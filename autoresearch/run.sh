#!/bin/bash
# Launch an autoresearch session
# Usage: ./autoresearch/run.sh [target_file] [goal]
#
# Examples:
#   ./autoresearch/run.sh src/epiphan_mcp/tools/recording.py "Add missing Pearl recording endpoints"
#   ./autoresearch/run.sh src/epiphan_mcp/tools/streaming.py "Improve streaming tool test coverage"

set -euo pipefail

TARGET=${1:-"src/epiphan_mcp/tools/recording.py"}
GOAL=${2:-"Improve test coverage and add missing Pearl API endpoints"}
BRANCH="autoresearch/$(date +%b%d | tr '[:upper:]' '[:lower:]')-$(echo "$TARGET" | sed 's|.*/||;s|\.py||')"

cd "$(dirname "$0")/.."

# Ensure clean state
if [ -n "$(git status --porcelain)" ]; then
    echo "ERROR: Working tree not clean. Commit or stash changes first."
    exit 1
fi

# Create experiment branch
git checkout -b "$BRANCH"

# Capture baseline
echo "=== Autoresearch Session ==="
echo "Target:  $TARGET"
echo "Goal:    $GOAL"
echo "Branch:  $BRANCH"
echo "Metric:  pytest + mypy + ruff"
echo "Started: $(date)"
echo ""
echo "Running baseline evaluation..."
./autoresearch/evaluate.sh
echo ""
echo "Launching autonomous agent..."
echo "==========================================="
echo ""

# Build the prompt from program.md + runtime context
PROMPT="$(cat autoresearch/program.md)

---

## Session Context

TARGET_FILE: $TARGET
GOAL: $GOAL
BRANCH: $BRANCH
BASELINE_TESTS: $(grep -c 'passed' autoresearch/results.tsv 2>/dev/null || echo 'see baseline above')

Begin the autonomous research loop now. Do not stop. Do not ask for permission."

# Launch Claude autonomously
claude --dangerously-skip-permissions -p "$PROMPT"
