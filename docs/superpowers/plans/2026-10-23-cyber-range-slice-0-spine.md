# Cyber Range Methodology — Slice 0 (Spine) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-frame the plugin's bootstrap and documentation as a cyber range exercise development methodology, and add the metrics script that keeps the spec's impact figures honest.

**Architecture:** The bootstrap is injected in three places — `hooks/session-start` (Claude Code, Cursor, Copilot, Muse), `.opencode/plugins/superpowers.js`, and `.pi/extensions/superpowers.ts` — each embedding the body of `skills/using-superpowers/SKILL.md`. Slice 0 rewrites that skill, adds a short framing paragraph at each injection site, and pins the shared phrasing with a parity test. No skill from later slices is touched.

**Tech Stack:** Bash 3.2-compatible hooks, Node 22 for tests, Markdown skills.

**Spec:** `docs/superpowers/specs/2026-10-23-cyber-range-exercise-methodology-design.md`

## Global Constraints

- The literal prefix `<EXTREMELY_IMPORTANT>\nYou have superpowers.` MUST survive in all three bootstrap sources — `tests/opencode/test-session-bootstrap.mjs` and `tests/pi/test-pi-extension.mjs` key off it. Add text after it; never reword it.
- `hooks/session-start` may use only bash builtins and redirection. It runs with an empty or broken `PATH` on some Claude Code startups; adding any external command breaks existing tests.
- `skills/using-superpowers/SKILL.md` MUST stay under 20,000 bytes (`tests/skill-size/test-skill-size.sh`).
- Hook output shapes (`additional_context` for Cursor, nested `hookSpecificOutput` for Claude Code/Muse, top-level `additionalContext` for SDK/Copilot) MUST NOT change.
- Scripts must be bash 3.2 compatible (macOS) — no associative arrays, no `mapfile`.
- Do not modify any skill other than `using-superpowers` in this slice.

## Review Focus

- **Empty PATH at session start** — the hook must still emit JSON context; a new external command would break this silently on Windows Git Bash.
- **Missing `using-superpowers/SKILL.md`** — the hook must emit `Error reading using-superpowers skill`, not crash.
- **Bootstrap duplicate suppression** — OpenCode and Pi detect an already-injected bootstrap by the `<EXTREMELY_IMPORTANT>\nYou have superpowers.` marker; any byte change there causes double injection.
- **20 KB compaction cut** — a rewritten skill that crosses it is silently truncated after context compaction.
- **Harness JSON shapes** — text edits must not disturb per-harness output shape.

---

### Task 1: Skill metrics script

**Files:**
- Create: `scripts/skill-metrics.sh`
- Test: `tests/skill-metrics/test-skill-metrics.sh`

**Interfaces:**
- Consumes: nothing.
- Produces: `scripts/skill-metrics.sh` — prints a Markdown table to stdout, exit 0. Header row: `| Skill | SKILL.md lines | Files | Software-keyword density | External files referencing it |`. Final row: `| **Total** | **<lines>** | **<files>** | | |`.

- [ ] **Step 1: Write the failing test**

Create `tests/skill-metrics/test-skill-metrics.sh`:

```bash
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `bash tests/skill-metrics/test-skill-metrics.sh`
Expected: FAIL — `bash: scripts/skill-metrics.sh: No such file or directory`.

- [ ] **Step 3: Write the script**

Create `scripts/skill-metrics.sh`:

```bash
#!/usr/bin/env bash
#
# skill-metrics.sh — print the per-skill impact table used by
# docs/superpowers/specs/2026-10-23-cyber-range-exercise-methodology-design.md
#
# Density is software-keyword hits per 100 SKILL.md lines — the figure the
# spec table quotes. Reference counts include every file outside the skill's
# own directory, so they drift as documentation changes; treat them as a
# signal, not a fixed number.
#
# Usage:
#   scripts/skill-metrics.sh
#
set -euo pipefail

case "$0" in
  */*|*\\*) SCRIPT_DIR="$(cd "${0%[/\\]*}" && pwd)" ;;
  *) SCRIPT_DIR="$(pwd)" ;;
esac
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SKILLS_DIR="${REPO_ROOT}/skills"

# Software vocabulary used to estimate how much of a skill is code-specific.
SW_PATTERN='\b(code|git|commit|branch|merge|pull request|PR|refactor|compile|lint|bug|debug|unit test|repository|repo)\b'

printf '| Skill | SKILL.md lines | Files | Software-keyword density | External files referencing it |\n'
printf '|---|---:|---:|---:|---:|\n'

total_lines=0
total_files=0

for dir in "${SKILLS_DIR}"/*/; do
  [ -d "$dir" ] || continue
  name="$(basename "$dir")"
  skill_md="${dir}SKILL.md"
  [ -f "$skill_md" ] || continue

  lines="$(wc -l < "$skill_md" | tr -d ' ')"
  files="$(find "$dir" -type f | wc -l | tr -d ' ')"
  sw_hits="$(grep -oiE "$SW_PATTERN" "$skill_md" | wc -l | tr -d ' ')"
  if [ "$lines" -gt 0 ]; then
    density=$(( sw_hits * 100 / lines ))
  else
    density=0
  fi
  refs="$(grep -rIl -F --exclude-dir=.git --exclude-dir=node_modules \
      --exclude-dir="$name" --exclude=RELEASE-NOTES.md \
      "$name" "$REPO_ROOT" 2>/dev/null | wc -l | tr -d ' ')"

  printf '| %s | %s | %s | %s%% | %s |\n' "$name" "$lines" "$files" "$density" "$refs"
  total_lines=$(( total_lines + lines ))
  total_files=$(( total_files + files ))
done

printf '| **Total** | **%s** | **%s** | | |\n' "$total_lines" "$total_files"
```

- [ ] **Step 4: Make it executable and run the test**

Run:

```bash
chmod +x scripts/skill-metrics.sh
bash tests/skill-metrics/test-skill-metrics.sh
```

Expected: `STATUS: PASSED` with four `[PASS]` lines.

- [ ] **Step 5: Sanity-check the output against the spec**

Run: `bash scripts/skill-metrics.sh`
Expected: 15 skill rows, total line count `3331`, total file count `84` — the figures the spec's §2.1 table quotes. The reference column counts files outside each skill's own directory, so it will read higher than the spec's older measurement (the spec and plan documents themselves mention many skill names). Do not "fix" the script to match those older numbers; report the difference instead.

- [ ] **Step 6: Commit**

```bash
git add scripts/skill-metrics.sh tests/skill-metrics/test-skill-metrics.sh
git commit -m "Add skill metrics script for impact analysis"
```

---

### Task 2: Rewrite the using-superpowers skill as an exercise methodology

**Files:**
- Modify: `skills/using-superpowers/SKILL.md` (full replacement)
- Test: `tests/hooks/test-session-start.sh` (assertion added to existing call)

**Interfaces:**
- Consumes: nothing.
- Produces: `skills/using-superpowers/SKILL.md` whose body is injected verbatim by all three bootstraps and contains the phrase `cyber range exercise development methodology`.

- [ ] **Step 1: Write the failing test**

In `tests/hooks/test-session-start.sh`, the Claude Code assertion currently reads:

```bash
claude_home="$(make_home claude-code)"
assert_command_output \
    "Claude Code emits nested SessionStart additionalContext" \
    "nested" \
    "" \
    "" \
    "$claude_home" \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    bash "$HOOK_UNDER_TEST"
```

Replace the first empty string (the `contains` argument) with the methodology phrase:

```bash
claude_home="$(make_home claude-code)"
assert_command_output \
    "Claude Code emits nested SessionStart additionalContext with the exercise methodology" \
    "nested" \
    "cyber range exercise development methodology" \
    "" \
    "$claude_home" \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    bash "$HOOK_UNDER_TEST"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `bash tests/hooks/test-session-start.sh`
Expected: FAIL on `Claude Code emits nested SessionStart additionalContext with the exercise methodology` — `context did not contain expected text: cyber range exercise development methodology`.

- [ ] **Step 3: Replace the skill body**

Replace the entire contents of `skills/using-superpowers/SKILL.md` with:

```markdown
---
name: using-superpowers
description: Use when starting any conversation - establishes the cyber range exercise development methodology and how to find and use skills, requiring skill invocation before ANY response including clarifying questions
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, ignore this skill.
</SUBAGENT-STOP>

<EXTREMELY-IMPORTANT>
If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill.

IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.

This is not negotiable. You cannot rationalize your way out of this.
</EXTREMELY-IMPORTANT>

## What this library is for

Superpowers is a **cyber range exercise development methodology**. It takes an exercise from learning objectives through design, artefact development, conduct, and evaluation. It is not a software development methodology — but exercise artefacts are software (scenario services, Deputy packages, validation scripts), so software practices apply to building them.

## The lifecycle

| Phase | Skill | Produces |
|---|---|---|
| Design | `exercise-design` | objectives, audience, scope, classification, assessment criteria |
| Develop | `exercise-develop` | SDL blueprint, Deputy packages, exercise content, inject timeline |
| Conduct | `exercise-conduct` | white-cell plan, runbook, inject schedule, stop conditions |
| Evaluate | `exercise-evaluate` | criterion-level evidence, AAR, improvement actions |

## The Rule

**Invoke relevant or requested skills BEFORE any response or action** — including clarifying questions, exploring the repository, or checking files. If it turns out wrong for the situation, you don't have to use it.

**Before entering plan mode:** if you haven't already brainstormed, invoke the brainstorming skill first.

Then announce "Using [skill] to [purpose]" and follow the skill exactly. If it has a checklist, create a todo per item.

## Asking instead of guessing

Exercise work turns on decisions only your human partner can make. Ask.

- **Use the harness question tool whenever one exists** (AskUserQuestion, ask_user, or equivalent). Ask one question at a time and prefer multiple choice.
- **If no question tool exists**, ask in plain text and wait. Do not continue with an assumed answer.
- **Never invent** learning objectives, target audience, scope, classification level, safety limits, or stop conditions.
- **Stop and ask** when a validation rule returns `UNKNOWN`, a required package cannot be found, a tool the workflow needs is not installed, or a repair attempt has failed three times.

## Skill Priority

When multiple skills apply, process skills come first — they set the approach, then artefact skills carry it out.

- "We need an exercise on X" → `brainstorming`, then `exercise-design`.
- "Build the blueprint" → `sdl-authoring`, validated before anything else proceeds.
- "Something is broken in the range" → `systematic-debugging`, then the relevant artefact skill.

## Red Flags

These thoughts mean STOP—you're rationalizing:

| Thought | Reality |
|---------|---------|
| "This is just a simple question" | Questions are tasks. Check for skills. |
| "I need more context first" | Skill check comes BEFORE clarifying questions. |
| "Let me explore the repository first" | Skills tell you HOW to explore. Check first. |
| "I know what the exercise should teach" | Objectives come from the customer or designer, not from you. Ask. |
| "The format is obvious" | Validate against the parser; do not assume. |
| "This doesn't need a formal skill" | If a skill exists, use it. |
| "I remember this skill" | Skills evolve. Read current version. |
| "This doesn't count as a task" | Action = task. Check for skills. |
| "The skill is overkill" | Simple things become complex. Use it. |
| "I'll just do this one thing first" | Check BEFORE doing anything. |
| "This feels productive" | Undisciplined action wastes time. Skills prevent this. |
| "I know what that means" | Knowing the concept ≠ using the skill. Invoke it. |

## Platform Adaptation

If your harness appears here, read its reference file for special instructions:

- Claude Code: `references/claude-code-tools.md`
- Codex: `references/codex-tools.md`
- Pi: `references/pi-tools.md`
- Antigravity: `references/antigravity-tools.md`
- Hermes Agent: `references/hermes-tools.md`
- Muse: `references/muse-tools.md`

## User Instructions

User instructions (CLAUDE.md, AGENTS.md, GEMINI.md, etc, direct requests) take precedence over skills, which in turn override default behavior. Only skip skill workflows or instructions when your human partner has explicitly told you to.
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
bash tests/hooks/test-session-start.sh
bash tests/skill-size/test-skill-size.sh
```

Expected: `STATUS: PASSED` from the hooks test; the skill-size test exits 0 with no output.

- [ ] **Step 5: Commit**

```bash
git add skills/using-superpowers/SKILL.md tests/hooks/test-session-start.sh
git commit -m "Reframe using-superpowers as an exercise development methodology"
```

---

### Task 3: Frame the injected session context

**Files:**
- Modify: `hooks/session-start:41`
- Test: `tests/hooks/test-session-start.sh`

**Interfaces:**
- Consumes: the rewritten `SKILL.md` from Task 2.
- Produces: hook context that names the methodology in the framing paragraph, before the skill body.

- [ ] **Step 1: Add the failing assertion**

In `tests/hooks/test-session-start.sh`, add a new assertion immediately after the Claude Code block from Task 2:

```bash
frame_home="$(make_home methodology-frame)"
assert_command_output \
    "SessionStart framing names the exercise methodology" \
    "nested" \
    "This plugin provides a cyber range exercise development methodology" \
    "" \
    "$frame_home" \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    bash "$HOOK_UNDER_TEST"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `bash tests/hooks/test-session-start.sh`
Expected: FAIL on `SessionStart framing names the exercise methodology`.

- [ ] **Step 3: Rewrite the session context string**

In `hooks/session-start`, replace line 41 with:

```bash
session_context="<EXTREMELY_IMPORTANT>\nYou have superpowers.\n\nThis plugin provides a cyber range exercise development methodology (design, develop, conduct, evaluate), not a software development methodology. Walk the exercise through those phases, and ask your human partner whenever a skill tells you to — using the harness question tool when one is available.\n\n**Below is the full content of your 'superpowers:using-superpowers' skill - your introduction to using skills. For all other skills, use the 'Skill' tool:**\n\n${using_superpowers_escaped}\n</EXTREMELY_IMPORTANT>"
```

The prefix `<EXTREMELY_IMPORTANT>\nYou have superpowers.\n\n` is unchanged — only the paragraph after it is new.

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
bash tests/hooks/test-session-start.sh
bash -n hooks/session-start
```

Expected: `STATUS: PASSED`; `bash -n` prints nothing. If `shellcheck` is on `PATH`, also run `scripts/lint-shell.sh --strict hooks/session-start`.

- [ ] **Step 5: Commit**

```bash
git add hooks/session-start tests/hooks/test-session-start.sh
git commit -m "Name the exercise methodology in session-start context"
```

---

### Task 4: Bootstrap parity for OpenCode and Pi

**Files:**
- Modify: `.opencode/plugins/superpowers.js:130-138`
- Modify: `.pi/extensions/superpowers.ts:64-72`
- Test: `tests/bootstrap-parity/test-bootstrap-parity.sh` (create)

**Interfaces:**
- Consumes: the framing phrase introduced in Task 3.
- Produces: the same phrase in all three bootstrap sources, asserted by a parity test.

- [ ] **Step 1: Write the failing parity test**

Create `tests/bootstrap-parity/test-bootstrap-parity.sh`:

```bash
#!/usr/bin/env bash
# Every bootstrap injection point must name the exercise methodology identically.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PHRASE="cyber range exercise development methodology"

failures=0
for relative_path in \
    "hooks/session-start" \
    ".opencode/plugins/superpowers.js" \
    ".pi/extensions/superpowers.ts"; do
    if grep -Fq "$PHRASE" "$REPO_ROOT/$relative_path"; then
        echo "  [PASS] $relative_path names the methodology"
    else
        echo "  [FAIL] $relative_path is missing: $PHRASE"
        failures=$((failures + 1))
    fi
done

if [ "$failures" -gt 0 ]; then
    echo "STATUS: FAILED ($failures failure(s))"
    exit 1
fi

echo "STATUS: PASSED"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `bash tests/bootstrap-parity/test-bootstrap-parity.sh`
Expected: hook passes (Task 3); OpenCode and Pi fail.

- [ ] **Step 3: Update the OpenCode bootstrap**

In `.opencode/plugins/superpowers.js`, inside `getBootstrapContent`, the template literal currently begins:

```js
  _bootstrapCache.set(toolMapping, `<EXTREMELY_IMPORTANT>
You have superpowers.

**IMPORTANT: The using-superpowers skill content is included below. It is ALREADY LOADED - you are currently following it. Do NOT use the skill tool to load "using-superpowers" again - that would be redundant.**
```

Insert the framing paragraph between the marker and the IMPORTANT line:

```js
  _bootstrapCache.set(toolMapping, `<EXTREMELY_IMPORTANT>
You have superpowers.

This plugin provides a cyber range exercise development methodology (design, develop, conduct, evaluate), not a software development methodology. Walk the exercise through those phases, and ask your human partner whenever a skill tells you to — using the harness question tool when one is available.

**IMPORTANT: The using-superpowers skill content is included below. It is ALREADY LOADED - you are currently following it. Do NOT use the skill tool to load "using-superpowers" again - that would be redundant.**
```

- [ ] **Step 4: Update the Pi bootstrap**

In `.pi/extensions/superpowers.ts`, inside the `cachedBootstrap` template literal, the text currently reads:

```ts
You have superpowers.

The using-superpowers skill content is included below and is already loaded for this Pi session. Follow it now. Do not try to load using-superpowers again.
```

Insert the framing paragraph between them:

```ts
You have superpowers.

This plugin provides a cyber range exercise development methodology (design, develop, conduct, evaluate), not a software development methodology. Walk the exercise through those phases, and ask your human partner whenever a skill tells you to — using the harness question tool when one is available.

The using-superpowers skill content is included below and is already loaded for this Pi session. Follow it now. Do not try to load using-superpowers again.
```

- [ ] **Step 5: Run the tests to verify they pass**

Run:

```bash
bash tests/bootstrap-parity/test-bootstrap-parity.sh
node tests/opencode/test-session-bootstrap.mjs .opencode/plugins/superpowers.js
node --experimental-strip-types --test tests/pi/test-pi-extension.mjs
```

Expected: `STATUS: PASSED`; `Session classification, recovery and cache lifetime passed`; Pi reports `# fail 0`. (Node 22 needs `--experimental-strip-types` to import the `.ts` extension; without it the Pi suite fails on module loading before exercising any assertion.)

- [ ] **Step 6: Commit**

```bash
git add .opencode/plugins/superpowers.js .pi/extensions/superpowers.ts tests/bootstrap-parity/test-bootstrap-parity.sh
git commit -m "Name the exercise methodology in OpenCode and Pi bootstraps"
```

---

### Task 5: README methodology wording

**Files:**
- Modify: `README.md:3` (intro) and `README.md:35-45` (How it works)
- Test: `tests/docs/test-methodology-wording.sh` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: README that describes the exercise lifecycle.

- [ ] **Step 1: Write the failing test**

Create `tests/docs/test-methodology-wording.sh`:

```bash
#!/usr/bin/env bash
# README must describe the exercise methodology, not a software methodology.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
README="$REPO_ROOT/README.md"

failures=0

if grep -Fq "cyber range exercise development methodology" "$README"; then
    echo "  [PASS] README names the exercise methodology"
else
    echo "  [FAIL] README is missing the exercise methodology phrase"
    failures=$((failures + 1))
fi

if grep -Fq "complete software development methodology" "$README"; then
    echo "  [FAIL] README still claims a software development methodology"
    failures=$((failures + 1))
else
    echo "  [PASS] README no longer claims a software development methodology"
fi

if [ "$failures" -gt 0 ]; then
    echo "STATUS: FAILED ($failures failure(s))"
    exit 1
fi

echo "STATUS: PASSED"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `bash tests/docs/test-methodology-wording.sh`
Expected: FAIL on both assertions.

- [ ] **Step 3: Rewrite the README intro**

Replace line 3:

```markdown
Superpowers is a complete software development methodology for your coding agents, built on top of a set of composable skills and some initial instructions that make sure your agent uses them.
```

with:

```markdown
Superpowers is a complete cyber range exercise development methodology for your coding agents, built on top of a set of composable skills and some initial instructions that make sure your agent uses them.
```

- [ ] **Step 4: Rewrite the "How it works" paragraphs**

Replace lines 35–45 (from `## How it works` through the closing `Your coding agent just has Superpowers.`) with:

```markdown
## How it works

It starts from the moment you fire up your coding agent. As soon as it sees that you're building an exercise, it *doesn't* just jump into writing artefacts. Instead, it steps back and asks what the exercise is meant to teach and who it is for.

Once it has teased objectives, audience, scope, classification, and constraints out of the conversation, it writes a design spec and shows it to you in chunks short enough to actually read and digest.

After you've signed off on the design, your agent turns it into exercise artefacts — a scenario blueprint in SDL, Deputy packages, exercise content, and an inject timeline — validating each one before moving on. The blueprint must parse, package dependencies must resolve, and every learning objective must have at least one inject and one assessment criterion.

Next it writes the conduct plan — roles, inject schedule, escalation paths, and stop conditions — and after the exercise, the evaluation and after-action report. It's not uncommon for your agent to work autonomously through the artefact set without deviating from the plan you put together.

There's a bunch more to it, but that's the core of the system. And because the skills trigger automatically, you don't need to do anything special. Your coding agent just has Superpowers.
```

Leave the `Skills Library` listing under "What's Inside" unchanged in this slice — slice 6 rewrites it.

- [ ] **Step 5: Run the test to verify it passes**

Run:

```bash
bash tests/docs/test-methodology-wording.sh
bash tests/skill-size/test-skill-size.sh
```

Expected: `STATUS: PASSED`; skill-size exits 0.

- [ ] **Step 6: Commit**

```bash
git add README.md tests/docs/test-methodology-wording.sh
git commit -m "Describe the exercise lifecycle in the README"
```

---

### Task 6: Slice gate

**Files:**
- No source changes. Verification only.

**Interfaces:**
- Consumes: all prior tasks.
- Produces: a recorded pass/fail for each slice-0 gate.

- [ ] **Step 1: Run the slice-0 test set**

```bash
bash tests/hooks/test-session-start.sh
bash tests/bootstrap-parity/test-bootstrap-parity.sh
bash tests/skill-metrics/test-skill-metrics.sh
bash tests/docs/test-methodology-wording.sh
bash tests/skill-size/test-skill-size.sh
node tests/opencode/test-session-bootstrap.mjs .opencode/plugins/superpowers.js
node --experimental-strip-types --test tests/pi/test-pi-extension.mjs
bash -n hooks/session-start scripts/skill-metrics.sh
```

Expected:

| Command | Expected |
|---|---|
| hooks | `STATUS: PASSED` |
| bootstrap parity | `STATUS: PASSED` |
| skill metrics | `STATUS: PASSED` |
| docs wording | `STATUS: PASSED` |
| skill size | exit 0, no output |
| opencode | `Session classification, recovery and cache lifetime passed` |
| pi | `# fail 0` |
| `bash -n` | no output |

- [ ] **Step 2: Confirm the marker prefix survived**

Run:

```bash
grep -c "You have superpowers\." hooks/session-start .opencode/plugins/superpowers.js .pi/extensions/superpowers.ts
```

Expected: exactly `1` for each file.

- [ ] **Step 3: Report**

Report the gate results to your human partner. Do not open a pull request; slice 0 ends here and slice 1 begins from a clean tree.
