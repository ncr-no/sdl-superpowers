#!/usr/bin/env bash
# Every bootstrap injection point must name the exercise methodology identically.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PHRASE="cyber range exercise development methodology"

failures=0
for relative_path in \
    "hooks/session-start" \
    ".opencode/plugins/superpowers.js" \
    ".pi/extensions/superpowers.ts"; do
    if grep -Fq "$PHRASE" "$REPO_ROOT/$relative_path"; then
        echo "  [PASS] $relative_path names the methodology"
    else
        echo "  [FAIL] $relative_path is missing: $PHRASE"
        failures=$((failures + 1))
    fi
done

if [ "$failures" -gt 0 ]; then
    echo "STATUS: FAILED ($failures failure(s))"
    exit 1
fi

echo "STATUS: PASSED"
