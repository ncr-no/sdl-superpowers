#!/usr/bin/env bash
# brainstorming is the process skill that fires first on "we need an exercise on
# X". It keeps its generic creative-work reach; what changes in slice 1 is that
# it names the exercise domain and hands the approved design to exercise-design
# instead of to writing-plans.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SKILL="$REPO_ROOT/skills/brainstorming/SKILL.md"

failures=0
pass() { echo "  [PASS] $1"; }
fail() { echo "  [FAIL] $1"; failures=$((failures + 1)); }

description="$(grep -m1 '^description:' "$SKILL" || true)"

if printf '%s' "$description" | grep -qi 'exercise'; then
    pass "description names the exercise domain"
else
    fail "description must name the exercise domain so the router fires on exercise requests"
fi

if printf '%s' "$description" | grep -qiE 'in software or out of it|talk, a business'; then
    pass "description keeps its generic creative-work reach"
else
    fail "description must keep covering non-exercise creative work"
fi

if grep -q 'exercise-design' "$SKILL"; then
    pass "body hands the approved design to exercise-design"
else
    fail "body must name exercise-design as the next step for an exercise"
fi

if [ "$failures" -gt 0 ]; then
    echo "STATUS: FAILED ($failures failure(s))"
    exit 1
fi

echo "STATUS: PASSED"
