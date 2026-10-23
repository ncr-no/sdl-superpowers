#!/usr/bin/env bash
# Verifies that scripts/skill-metrics.sh emits a well-formed, self-consistent
# impact table. Totals are recomputed from the corpus, so the test tracks the
# skills rather than pinning today's numbers.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

OUTPUT="$(bash "$REPO_ROOT/scripts/skill-metrics.sh")"

failures=0
check() {
    if printf '%s\n' "$OUTPUT" | grep -Fq -- "$1"; then
        echo "  [PASS] $2"
    else
        echo "  [FAIL] $2"
        failures=$((failures + 1))
    fi
}

check "| Skill | SKILL.md lines | Files | Software-keyword density | External files referencing it |" \
    "header row is present"
check "| **Total** |" "total row is present"

skill_count="$(find "$REPO_ROOT/skills" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')"
row_count="$(printf '%s\n' "$OUTPUT" | grep -c '^| [a-z]' || true)"
if [ "$row_count" -eq "$skill_count" ]; then
    echo "  [PASS] one row per skill ($skill_count)"
else
    echo "  [FAIL] expected $skill_count skill rows, found $row_count"
    failures=$((failures + 1))
fi

expected_lines="$(cat "$REPO_ROOT"/skills/*/SKILL.md | wc -l | tr -d ' ')"
if printf '%s\n' "$OUTPUT" | grep -Fq "| **Total** | **${expected_lines}** |"; then
    echo "  [PASS] total line count matches SKILL.md corpus ($expected_lines)"
else
    echo "  [FAIL] total line count does not match $expected_lines"
    failures=$((failures + 1))
fi

if [ "$failures" -gt 0 ]; then
    echo "STATUS: FAILED ($failures failure(s))"
    exit 1
fi

echo "STATUS: PASSED"
