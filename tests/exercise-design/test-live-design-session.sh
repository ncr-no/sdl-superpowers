#!/usr/bin/env bash
# Opt-in live check for UC-1. Drives a real Claude Code session with only this
# plugin loaded and asserts that the design phase asks instead of inventing.
#
# The skill call is read from the stream-json tool events, not from the prose:
# the announcement is paraphrased freely ("I'll start with the design phase"),
# and the default output format shows no tool calls at all.
#
# Usage: tests/exercise-design/test-live-design-session.sh
# Requires: claude on PATH with a working model, and jq; ~2 minutes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if ! command -v claude >/dev/null 2>&1; then
    echo "SKIP: claude not on PATH"
    exit 0
fi
if ! command -v jq >/dev/null 2>&1; then
    echo "SKIP: jq not on PATH"
    exit 0
fi

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

project="$work/project"
mkdir -p "$project"
log="$work/stream.jsonl"

echo "=== Live design session ==="
( cd "$project" && CLAUDE_CONFIG_DIR="$work/config" \
    claude -p "please use the exercise-design skill to design a ransomware exercise for a hospital network" \
        --plugin-dir "$REPO_ROOT" --output-format stream-json --verbose \
        --max-turns 6 > "$log" 2> "$work/stream.err" ) || true

text="$(jq -r 'select(.type=="assistant") | .message.content[]? | select(.type=="text") | .text' "$log" 2>/dev/null || true)"

if grep -qE '"name":"Skill".*"skill":"([^"]*:)?exercise-design"' "$log"; then
    echo "  [PASS] the Skill tool loaded exercise-design"
else
    echo "  [FAIL] exercise-design was never invoked"
    echo "    skills seen: $(grep -o '"skill":"[^"]*"' "$log" | sort -u | tr '\n' ' ')"
    exit 1
fi

# The skill's own vocabulary is paraphrased freely, so the question is judged by
# its shape, not its words: a reply that asks something and hands the decision
# back is doing the phase's work.
if printf '%s' "$text" | grep -q '?'; then
    echo "  [PASS] it asked a question rather than delivering a design"
else
    echo "  [FAIL] it delivered without asking"
    printf '%s\n' "$text" | sed 's/^/    /'
    exit 1
fi

if printf '%s' "$text" | grep -qiE '^#+ .*(objective|criteria)|terminal objective'; then
    echo "  [FAIL] it wrote objectives or criteria it was not given"
    printf '%s\n' "$text" | sed 's/^/    /'
    exit 1
fi
echo "  [PASS] it invented no objectives or criteria"

# The failure mode this phase exists to prevent: a design written from guesses.
if find "$project" -name design.md -print -quit | grep -q .; then
    echo "  [FAIL] it wrote a design spec without asking for the inputs"
    exit 1
fi
echo "  [PASS] it wrote no design spec before getting answers"

echo "STATUS: PASSED"
