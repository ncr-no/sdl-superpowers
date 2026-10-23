#!/usr/bin/env bash
# Every bootstrap injection point must carry the exercise-methodology framing
# paragraph byte-for-byte, after the marker that suppresses duplicate injection.
#
# A substring check is not enough: the paragraph is deliberately duplicated in
# three sources, so identity is the property that matters. The marker check
# pins the prefix `tests/opencode` and `tests/pi` detect an existing bootstrap by.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

PHRASE_PARAGRAPH='This plugin provides a cyber range exercise development methodology (design, develop, conduct, evaluate), not a software development methodology. Walk the exercise through those phases, and ask your human partner whenever a skill tells you to — using the harness question tool when one is available.'

failures=0
for relative_path in \
    "hooks/session-start" \
    ".opencode/plugins/superpowers.js" \
    ".pi/extensions/superpowers.ts"; do
    if grep -Fq -- "$PHRASE_PARAGRAPH" "$REPO_ROOT/$relative_path"; then
        echo "  [PASS] $relative_path carries the full framing paragraph"
    else
        echo "  [FAIL] $relative_path does not carry the framing paragraph verbatim"
        failures=$((failures + 1))
    fi

    if grep -Fq "You have superpowers." "$REPO_ROOT/$relative_path" &&
        grep -Fq "EXTREMELY_IMPORTANT" "$REPO_ROOT/$relative_path"; then
        echo "  [PASS] $relative_path keeps the duplicate-suppression marker"
    else
        echo "  [FAIL] $relative_path lost the '<EXTREMELY_IMPORTANT> / You have superpowers.' marker"
        failures=$((failures + 1))
    fi
done

if [ "$failures" -gt 0 ]; then
    echo "STATUS: FAILED ($failures failure(s))"
    exit 1
fi

echo "STATUS: PASSED"
