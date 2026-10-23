#!/usr/bin/env bash
# Run all explicit skill request tests
# Usage: ./run-all.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPTS_DIR="$SCRIPT_DIR/prompts"

echo "=== Running All Explicit Skill Request Tests ==="
echo ""

PASSED=0
FAILED=0
RESULTS=""

# Test: subagent-driven-development, please
echo ">>> Test 1: subagent-driven-development-please"
if "$SCRIPT_DIR/run-test.sh" "subagent-driven-development" "$PROMPTS_DIR/subagent-driven-development-please.txt"; then
    PASSED=$((PASSED + 1))
    RESULTS="$RESULTS\nPASS: subagent-driven-development-please"
else
    FAILED=$((FAILED + 1))
    RESULTS="$RESULTS\nFAIL: subagent-driven-development-please"
fi
echo ""

# Test: use systematic-debugging
echo ">>> Test 2: use-systematic-debugging"
if "$SCRIPT_DIR/run-test.sh" "systematic-debugging" "$PROMPTS_DIR/use-systematic-debugging.txt"; then
    PASSED=$((PASSED + 1))
    RESULTS="$RESULTS\nPASS: use-systematic-debugging"
else
    FAILED=$((FAILED + 1))
    RESULTS="$RESULTS\nFAIL: use-systematic-debugging"
fi
echo ""

# Test: please use brainstorming
echo ">>> Test 3: please-use-brainstorming"
if "$SCRIPT_DIR/run-test.sh" "brainstorming" "$PROMPTS_DIR/please-use-brainstorming.txt"; then
    PASSED=$((PASSED + 1))
    RESULTS="$RESULTS\nPASS: please-use-brainstorming"
else
    FAILED=$((FAILED + 1))
    RESULTS="$RESULTS\nFAIL: please-use-brainstorming"
fi
echo ""

# Test: mid-conversation execute plan
echo ">>> Test 4: mid-conversation-execute-plan"
if "$SCRIPT_DIR/run-test.sh" "subagent-driven-development" "$PROMPTS_DIR/mid-conversation-execute-plan.txt"; then
    PASSED=$((PASSED + 1))
    RESULTS="$RESULTS\nPASS: mid-conversation-execute-plan"
else
    FAILED=$((FAILED + 1))
    RESULTS="$RESULTS\nFAIL: mid-conversation-execute-plan"
fi
echo ""

# Test: please use exercise-design
echo ">>> Test 5: exercise-design-please"
if "$SCRIPT_DIR/run-test.sh" "exercise-design" "$PROMPTS_DIR/please-use-exercise-design.txt" 5; then
    PASSED=$((PASSED + 1))
    RESULTS="$RESULTS\nPASS: exercise-design-please"
else
    FAILED=$((FAILED + 1))
    RESULTS="$RESULTS\nFAIL: exercise-design-please"
fi
echo ""

# Test: we need an exercise (no skill named; must route to brainstorming)
echo ">>> Test 6: we-need-an-exercise"
if "$SCRIPT_DIR/run-test.sh" "brainstorming" "$PROMPTS_DIR/we-need-an-exercise.txt"; then
    PASSED=$((PASSED + 1))
    RESULTS="$RESULTS\nPASS: we-need-an-exercise"
else
    FAILED=$((FAILED + 1))
    RESULTS="$RESULTS\nFAIL: we-need-an-exercise"
fi
echo ""

# Test 7: sdl-authoring is invoked when named
echo ">>> Test 7: sdl-authoring-please"
if "$SCRIPT_DIR/run-test.sh" "sdl-authoring" "$PROMPTS_DIR/please-use-sdl-authoring.txt" 5; then
    PASSED=$((PASSED + 1))
    RESULTS="$RESULTS\nPASS: sdl-authoring-please"
else
    FAILED=$((FAILED + 1))
    RESULTS="$RESULTS\nFAIL: sdl-authoring-please"
fi
echo ""

# Test 8: datalog-verification is invoked when named
echo ">>> Test 8: datalog-verification-please"
if "$SCRIPT_DIR/run-test.sh" "datalog-verification" "$PROMPTS_DIR/please-use-datalog-verification.txt" 5; then
    PASSED=$((PASSED + 1))
    RESULTS="$RESULTS\nPASS: datalog-verification-please"
else
    FAILED=$((FAILED + 1))
    RESULTS="$RESULTS\nFAIL: datalog-verification-please"
fi
echo ""

echo "=== Summary ==="
echo -e "$RESULTS"
echo ""
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo "Total: $((PASSED + FAILED))"

if [ "$FAILED" -gt 0 ]; then
    exit 1
fi
