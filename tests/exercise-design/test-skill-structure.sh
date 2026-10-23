#!/usr/bin/env bash
# The design phase is the first skill a user meets, and every later phase reads
# its output. Pin the parts of it that other skills and tests depend on: the
# frontmatter the router matches, the output path, and the sections a reader
# needs to find without scanning.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SKILL="$REPO_ROOT/skills/exercise-design/SKILL.md"

failures=0
check() {
    if grep -Fq -- "$1" "$SKILL" 2>/dev/null; then
        echo "  [PASS] $2"
    else
        echo "  [FAIL] $2"
        failures=$((failures + 1))
    fi
}

if [ ! -f "$SKILL" ]; then
    echo "  [FAIL] skills/exercise-design/SKILL.md does not exist"
    echo "STATUS: FAILED (1 failure(s))"
    exit 1
fi

first_line="$(sed -n '1p' "$SKILL")"
if [ "$first_line" = "---" ]; then
    echo "  [PASS] frontmatter opens on line 1"
else
    echo "  [FAIL] frontmatter must open on line 1, found: $first_line"
    failures=$((failures + 1))
fi

check "name: exercise-design" "frontmatter names the skill"
check "exercises/<slug>/design.md" "names the design spec output path"

for section in \
    "## What this phase produces" \
    "## Ask before you design" \
    "## Learning objectives" \
    "## Assessment criteria" \
    "## The design spec" \
    "## Red flags" \
    "## Handoff"; do
    check "$section" "has section: $section"
done

description="$(grep -m1 '^description:' "$SKILL" || true)"
if printf '%s' "$description" | grep -qi 'exercise'; then
    echo "  [PASS] description carries the exercise trigger word"
else
    echo "  [FAIL] description must name the exercise domain (routing depends on it)"
    failures=$((failures + 1))
fi

if [ "$failures" -gt 0 ]; then
    echo "STATUS: FAILED ($failures failure(s))"
    exit 1
fi

echo "STATUS: PASSED"
