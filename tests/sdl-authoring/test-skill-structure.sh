#!/usr/bin/env bash
# The router matches on the description, and the validator path in the skill
# is what a reader runs. Pin both, plus the sections a reader needs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SKILL="$REPO_ROOT/skills/sdl-authoring/SKILL.md"

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
    echo "  [FAIL] skills/sdl-authoring/SKILL.md does not exist"
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

check "name: sdl-authoring" "frontmatter names the skill"
check "references/sdl-grammar.md" "points at the grammar reference"
check "scripts/validate.py" "names the validator to run"
check "apt install libsdl-parser" "carries the install command for the UNKNOWN path"

for section in "## What this produces" "## Rules of authorship" \
               "## Validate before you hand off" "## Red flags" "## Handoff"; do
    check "$section" "has section: $section"
done

description="$(grep -m1 '^description:' "$SKILL" || true)"
if printf '%s' "$description" | grep -qiE 'sdl|scenario definition'; then
    echo "  [PASS] description carries the SDL trigger"
else
    echo "  [FAIL] description must name SDL (routing depends on it)"
    failures=$((failures + 1))
fi

if [ "$failures" -gt 0 ]; then
    echo "STATUS: FAILED ($failures failure(s))"
    exit 1
fi

echo "STATUS: PASSED"
