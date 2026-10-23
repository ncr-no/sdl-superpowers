#!/usr/bin/env bash
# The introduction is injected into every session, so every skill it names is a
# promise the agent will try to keep. A skill that does not exist yet must be
# marked as planned: an agent that discovers the name is missing otherwise has
# to choose between the intro's framing and its own skill list, and a live
# Claude Code probe showed it choosing the skill list.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SKILL_FILE="$REPO_ROOT/skills/using-superpowers/SKILL.md"

failures=0

# Backticked kebab-case tokens are how this file names skills. Paths (they
# contain "/" or ".") and constants (upper case, e.g. `UNKNOWN`) are not
# skills and are excluded here.
tokens="$(grep -oE '`[a-z][a-z0-9-]+`' "$SKILL_FILE" | tr -d '`' | sort -u)"

if [ -z "$tokens" ]; then
    echo "  [FAIL] found no backticked skill names to check — the parse is broken"
    exit 1
fi

while IFS= read -r token; do
    [ -n "$token" ] || continue

    if [ -f "$REPO_ROOT/skills/$token/SKILL.md" ]; then
        echo "  [PASS] $token is installed"
        continue
    fi

    # Every line mentioning the token must say the skill is not available yet.
    unmarked="$(
        grep -n "\`$token\`" "$SKILL_FILE" |
            grep -viE 'planned|not yet installed|not installed' || true
    )"

    if [ -z "$unmarked" ]; then
        echo "  [PASS] $token is not installed but is marked as planned"
    else
        echo "  [FAIL] $token is not installed and is named as if it were available:"
        printf '%s\n' "$unmarked" | sed 's/^/      /'
        failures=$((failures + 1))
    fi
done <<< "$tokens"

if [ "$failures" -gt 0 ]; then
    echo "STATUS: FAILED ($failures failure(s))"
    exit 1
fi

echo "STATUS: PASSED"
