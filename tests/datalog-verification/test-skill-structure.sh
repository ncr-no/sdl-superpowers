#!/usr/bin/env bash
# Pin the parts of the skill other skills and fixtures depend on: the name the
# router matches, the CLI it tells the reader to run, and the verdict words.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SKILL="$REPO_ROOT/skills/datalog-verification/SKILL.md"

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
    echo "  [FAIL] skills/datalog-verification/SKILL.md does not exist"
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

check "name: datalog-verification" "frontmatter names the skill"
check "scripts/verify.py" "names the CLI to run"
check "references/rules" "points at the rule packs"
check "PASS" "names the passing verdict"
check "VIOLATION" "names the failing verdict"
check "UNKNOWN" "names the undecidable verdict"

for section in "## What this produces" "## Facts" "## Running it" \
               "## Reading the verdicts" "## Red flags" "## Handoff"; do
    check "$section" "has section: $section"
done

description="$(grep -m1 '^description:' "$SKILL" || true)"
if printf '%s' "$description" | grep -qiE 'verif|datalog|rule'; then
    echo "  [PASS] description carries the verification trigger"
else
    echo "  [FAIL] description must name verification (routing depends on it)"
    failures=$((failures + 1))
fi

if [ "$failures" -gt 0 ]; then
    echo "STATUS: FAILED ($failures failure(s))"
    exit 1
fi

echo "STATUS: PASSED"
