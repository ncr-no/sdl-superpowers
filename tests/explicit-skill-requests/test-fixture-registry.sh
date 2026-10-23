#!/usr/bin/env bash
# run-all.sh only runs what it lists, and its cases are hand-written. A prompt
# file with no case is dead weight; a case with no prompt file fails at runtime.
# Check both directions so a new fixture cannot land half-wired.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROMPTS="$SCRIPT_DIR/prompts"
RUN_ALL="$SCRIPT_DIR/run-all.sh"

failures=0
pass() { echo "  [PASS] $1"; }
fail() { echo "  [FAIL] $1"; failures=$((failures + 1)); }

for pair in \
    "exercise-design:please-use-exercise-design.txt" \
    "brainstorming:we-need-an-exercise.txt"; do
    skill="${pair%%:*}"
    file="${pair##*:}"

    if [ -s "$PROMPTS/$file" ]; then
        pass "prompt fixture exists and is not empty: $file"
    else
        fail "missing or empty prompt fixture: prompts/$file"
    fi

    if grep -Fq "\"$skill\" \"\$PROMPTS_DIR/$file\"" "$RUN_ALL"; then
        pass "run-all.sh runs $file against $skill"
    else
        fail "run-all.sh has no case for $file against $skill"
    fi
done

if [ "$failures" -gt 0 ]; then
    echo "STATUS: FAILED ($failures failure(s))"
    exit 1
fi

echo "STATUS: PASSED"
