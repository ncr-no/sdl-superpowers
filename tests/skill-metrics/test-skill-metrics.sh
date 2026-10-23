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

# --- fixture skills: zero keyword hits, zero references, rounding boundary ---
# Slice 6 strips software vocabulary and slice 1 adds skills nothing references
# yet, so both zero cases must render a row instead of aborting the table.
fixture_root="$(mktemp -d)"
trap 'rm -rf "$fixture_root"' EXIT

quiet_name="fixture-quiet-$$"
mkdir -p "$fixture_root/$quiet_name"
printf '# Quiet\n\nAn exercise with objectives and nothing else.\n' \
    > "$fixture_root/$quiet_name/SKILL.md"

round_name="fixture-round-$$"
mkdir -p "$fixture_root/$round_name"
{
    printf '# Round\n'
    printf 'code\n'
    i=0
    while [ "$i" -lt 198 ]; do
        printf 'word\n'
        i=$((i + 1))
    done
} > "$fixture_root/$round_name/SKILL.md"

fixture_output="$(SKILLS_DIR="$fixture_root" bash "$REPO_ROOT/scripts/skill-metrics.sh")"

if printf '%s\n' "$fixture_output" | grep -Fq "| $quiet_name | 3 | 1 | 0% | 0 |"; then
    echo "  [PASS] a skill with no software keywords and no references renders a row"
else
    echo "  [FAIL] a skill with no software keywords and no references should render"
    printf '%s\n' "$fixture_output" | sed 's/^/      /'
    failures=$((failures + 1))
fi

if printf '%s\n' "$fixture_output" | grep -Fq "| $round_name | 200 | 1 | 1% | 0 |"; then
    echo "  [PASS] density rounds to the nearest percent (1 hit per 200 lines is 1%)"
else
    echo "  [FAIL] density should round to the nearest percent, not floor"
    printf '%s\n' "$fixture_output" | sed 's/^/      /'
    failures=$((failures + 1))
fi

if [ "$failures" -gt 0 ]; then
    echo "STATUS: FAILED ($failures failure(s))"
    exit 1
fi

echo "STATUS: PASSED"
