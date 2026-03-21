#!/bin/bash
# Evaluation script for epiphan-autoresearch
# Runs pytest + mypy + ruff and outputs a single score.
# Exit 0 = no regressions (keep commit), Exit 1 = regression (revert commit)

set -euo pipefail

cd "$(dirname "$0")/.."

# Activate venv
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
fi

echo "=== Evaluating ==="

# Run tests
TEST_OUTPUT=$(pytest tests/ -x -q 2>&1 || true)
PASSED=$(echo "$TEST_OUTPUT" | grep -o '[0-9]* passed' | grep -o '[0-9]*' || echo "0")
FAILED=$(echo "$TEST_OUTPUT" | grep -o '[0-9]* failed' | grep -o '[0-9]*' || echo "0")
SKIPPED=$(echo "$TEST_OUTPUT" | grep -o '[0-9]* skipped' | grep -o '[0-9]*' || echo "0")

# Run mypy
MYPY_OUTPUT=$(mypy src/ 2>&1 || true)
if echo "$MYPY_OUTPUT" | grep -q "Success"; then
    MYPY_ERRORS=0
else
    MYPY_ERRORS=$(echo "$MYPY_OUTPUT" | grep -c "error:" || echo "0")
fi

# Run ruff
RUFF_OUTPUT=$(ruff check src/ 2>&1 || true)
if echo "$RUFF_OUTPUT" | grep -q "All checks passed"; then
    RUFF_ERRORS=0
else
    RUFF_ERRORS=$(echo "$RUFF_OUTPUT" | grep -c "Found" || echo "0")
fi

# Calculate score
SCORE=$(( PASSED * 10 - FAILED * 100 - MYPY_ERRORS * 50 - RUFF_ERRORS * 25 ))

# Log result
mkdir -p autoresearch
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
COMMIT=$(git log --oneline -1 --format="%h %s")
echo "$TIMESTAMP	$COMMIT	tests=$PASSED/$((PASSED + FAILED))	skipped=$SKIPPED	mypy=$MYPY_ERRORS	ruff=$RUFF_ERRORS	score=$SCORE" >> autoresearch/results.tsv

echo "Tests:  $PASSED passed, $FAILED failed, $SKIPPED skipped"
echo "Mypy:   $MYPY_ERRORS errors"
echo "Ruff:   $RUFF_ERRORS errors"
echo "Score:  $SCORE"
echo ""

# Pass/fail decision
if [ "$FAILED" -gt 0 ]; then
    echo "VERDICT: FAIL (test failures)"
    exit 1
fi

if [ "$MYPY_ERRORS" -gt 0 ]; then
    echo "VERDICT: FAIL (mypy errors)"
    exit 1
fi

if [ "$RUFF_ERRORS" -gt 0 ]; then
    echo "VERDICT: FAIL (ruff errors)"
    exit 1
fi

echo "VERDICT: PASS"
exit 0
