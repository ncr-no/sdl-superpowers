#!/usr/bin/env bash
# README must describe the exercise methodology, not a software methodology.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
README="$REPO_ROOT/README.md"

failures=0

if grep -Fq "cyber range exercise development methodology" "$README"; then
    echo "  [PASS] README names the exercise methodology"
else
    echo "  [FAIL] README is missing the exercise methodology phrase"
    failures=$((failures + 1))
fi

if grep -Fq "complete software development methodology" "$README"; then
    echo "  [FAIL] README still claims a software development methodology"
    failures=$((failures + 1))
else
    echo "  [PASS] README no longer claims a software development methodology"
fi

if [ "$failures" -gt 0 ]; then
    echo "STATUS: FAILED ($failures failure(s))"
    exit 1
fi

echo "STATUS: PASSED"
