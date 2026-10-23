# Cyber Range Slice 1 — Design Phase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the `exercise-design` phase skill, reword `brainstorming` so it hands an exercise idea to that phase, and add trigger fixtures that fail when either skill stops firing.

**Architecture:** A new phase skill under `skills/exercise-design/` carries the design phase: it elicits the decisions only a human can make, maps them to observable assessment criteria, and writes one design spec. `brainstorming` keeps its job — finding out what the human partner actually wants — but its `description` and its pre-implementation handoff name the exercise domain, so it fires on "we need an exercise on X" and ends at `exercise-design` instead of at `writing-plans`. Trigger tests follow the existing `tests/explicit-skill-requests/` prompt-file pattern. `using-superpowers` stops calling `exercise-design` planned.

**Tech Stack:** Markdown skills (frontmatter `name`/`description`, body < 20,000 bytes); bash test suites run per directory; the existing `tests/explicit-skill-requests/run-test.sh` harness for LLM trigger checks.

**Spec:** `docs/superpowers/specs/2026-10-23-cyber-range-exercise-methodology-design.md` (§3.2 inventory, §3.3 routing, §4 UC-1 and UC-6, §8 build slices, §9 testing)

## Global Constraints

- Every `SKILL.md` stays under 20,000 bytes (`tests/skill-size/test-skill-size.sh`, limit is byte count, not characters).
- Skill frontmatter carries exactly `name:` and `description:`; the description is a single line and is the only routing signal — there is no registry (spec §3.3).
- Only `skills/exercise-design/` (new), `skills/brainstorming/SKILL.md`, `skills/using-superpowers/SKILL.md` and the named test files may change in this slice. No artefact skill, no phase skill beyond `exercise-design`.
- `brainstorming` keeps its structure — "Size the Work", "The Written Design", the `<HARD-GATE>`, the Red Flags table and the "human partner" vocabulary. The reword changes the domain language and the handoff, not the process.
- Bash tests must run under bash 3.2 (macOS): no associative arrays, no `mapfile`.
- `set -euo pipefail` plus `grep` is a trap: a `grep` that finds nothing exits 1 and aborts the script. Every "expect absent" check uses `if ... ; then fail; fi` or appends `|| true`.
- `tests/explicit-skill-requests/run-test.sh` shells out to `timeout`, which macOS does not ship. That suite fails with `timeout: command not found` unless a `timeout` shim (or `gtimeout`) is on `PATH`; `run-test.sh` swallows the error with `|| true`, so the failure shows up as "skill was NOT triggered".
- Tests live beside their suite (`tests/<area>/test-*.sh`) and are run directly; there is no `npm test`.

## Review Focus

The five input classes the spec implies but no test in this slice exercises mechanically. The live-session checks in Task 5 are where each is actually judged:

1. **Two skills, one trigger.** "We need an exercise on X" matches both `brainstorming` and `exercise-design`. A reasonable person gets one process skill first, then the phase skill — never both fired in parallel, never the phase skill skipping the elicitation.
2. **The human answers nothing.** Every question in UC-1 can go unanswered or be answered "you decide". A reasonable person gets a stop and a question, not a design spec with invented objectives.
3. **Non-observable objectives.** "Understand incident response better" is not testable. A reasonable person gets it rewritten into an observable criterion, or asked to restate — not silently accepted.
4. **Classification unstated.** A reasonable person is asked for the classification and data-handling rules before any scenario content that could encode sensitive detail is written.
5. **A design spec already exists.** Re-running the phase on an existing spec must not overwrite it silently. A reasonable person gets the existing spec read first and a question about whether to revise or start a new one.

---

### Task 1: The `exercise-design` skill

**Files:**
- Create: `skills/exercise-design/SKILL.md`
- Test: `tests/exercise-design/test-skill-structure.sh`

**Interfaces:**
- Consumes: nothing at runtime — a skill is Markdown read by the agent.
- Produces: the skill named `exercise-design`, whose `description` is what later slices' cross-references and the `using-superpowers` lifecycle table point at; the output path `exercises/<slug>/design.md`, which `exercise-develop` (slice 4) and `exercise-evaluate` (slice 5) read.

- [ ] **Step 1: Write the failing test**

```bash
mkdir -p tests/exercise-design
cat > tests/exercise-design/test-skill-structure.sh <<'TEST'
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
TEST
chmod +x tests/exercise-design/test-skill-structure.sh
bash tests/exercise-design/test-skill-structure.sh
```

Expected: `[FAIL] skills/exercise-design/SKILL.md does not exist` and `STATUS: FAILED (1 failure(s))`.

- [ ] **Step 2: Write the skill**

```bash
mkdir -p skills/exercise-design
cat > skills/exercise-design/SKILL.md <<'SKILL'
---
name: exercise-design
description: Use when designing a cyber range exercise, drill, tabletop or training event — turning a scenario idea into learning objectives, audience, scope, classification and assessment criteria
---

# Exercise Design

You are in the design phase. Nothing gets built here. The work is deciding,
with your human partner, what the exercise is for and how anyone will know it
worked — and writing that down so the next phase can build against it.

## What this phase produces

One design spec at `exercises/<slug>/design.md` (ask if the project keeps
exercises somewhere else). It carries:

- terminal and enabling learning objectives, each observable
- audience: roles, current competence, prerequisites, team size
- scope: what is in the exercise, and explicitly what is out
- classification level and the handling rules that follow from it
- the scenario premise, in two or three sentences
- assessment criteria mapped to objectives
- constraints: time, environment, legal, safety

## Ask before you design

Six decisions belong to your human partner. Ask for them one at a time, in this
order, and wait for each answer. Use the harness question tool when one exists
(AskUserQuestion, ask_user, or equivalent), preferring multiple choice; with no
question tool, ask in plain text and stop.

1. **What is this for?** The triggering requirement — a compliance obligation,
   a real incident, a capability gap, an upcoming deployment.
2. **What should participants do afterwards that they cannot do today?** Ask
   for behaviour, not knowledge. "Recognise a phishing lure" is behaviour;
   "understand phishing" is not.
3. **Who are they?** Roles, seniority, team size, and what they already do.
4. **What is in and out of scope?** Systems, networks, business units, and the
   topics the exercise must not touch.
5. **What classification and handling rules apply?** Never guess this one, and
   never write scenario content before you have it.
6. **What are the constraints?** Duration, environment, licences, anything that
   forbids a scenario premise you would otherwise recommend.

Never invent an answer to any of the six. If an answer is partial, say which
part you still need. If the answer is "you decide", say which decision you
would make and why, and get agreement before writing it into the spec.

## Learning objectives

Write a terminal objective (what the team can do at the end) and enabling
objectives (the parts that make it up). Each one states an actor, an observable
action, and the condition it happens under:

- **Terminal:** "The SOC analyst triages a suspected phishing report to a
  containment decision within fifteen minutes of delivery."
- **Not an objective:** "Improve phishing awareness."

If your human partner gives you a non-observable objective, rewrite it into one
that can be observed and read the rewrite back to them before proceeding.
Objectives drive everything after this: scope, scenario, criteria, evaluation.

## Audience

Record roles, not names. For each role note what they do today, what they are
expected to do in the exercise, and what prerequisite skill the exercise assumes.
An exercise that assumes a prerequisite the audience lacks measures nothing.

## Scope and classification

Write the exclusions down as carefully as the inclusions — they are what stops
the scenario growing. Record the classification level, who may see the resulting
artefacts, and any handling rule (data residency, marking, storage) the level
implies. If classification is unstated, stop and ask; do not proceed on a guess.

## Scenario premise

Propose two or three premises that fit the objectives, recommend one with the
reason, and let your human partner choose. Keep each to a few sentences: the
situation, the pressure, and the decision point. A premise that needs a
paragraph of backstory is usually the wrong premise.

## Assessment criteria

For each objective, write the evidence a white cell could record:

| Objective | Evidence | Met | Not met |
|---|---|---|---|
| Triage to containment decision within 15 minutes | Time-stamped triage log, containment ticket | Decision logged and justified in the window | Decision late, absent, or unexplained |

Criteria are criterion-level: one row per objective, each row observable from
what the white cell or the environment records. If you cannot name the evidence,
the objective is not yet observable — go back to it.

## The design spec

Write `exercises/<slug>/design.md` with these sections, in this order:
Purpose, Objectives, Audience, Scope, Classification, Scenario premise,
Assessment criteria, Constraints, Open questions, Traceability stub.

The traceability stub is a heading and an empty table; later phases fill it.
Record every answer your human partner gave and every decision you proposed and
they accepted. Leave open questions as open — an unanswered question in the spec
is honest, an invented answer is not.

If a design spec already exists for this exercise, read it first and ask whether
to revise it or start a new one. Never overwrite one silently.

## Red flags

| Thought | Reality |
|---|---|
| "The objectives are obvious from the topic" | The topic is not an objective. Ask. |
| "Classification is probably internal" | Guess classification and you have written an unauthorised document. |
| "I'll fill in the audience later" | Objectives without an audience are unfalsifiable. |
| "This objective is close enough to observable" | Close enough cannot be assessed. Rewrite it. |
| "The human is busy, I'll draft the answers" | A drafted answer becomes a real exercise that teaches the wrong thing. |
| "I know what a good exercise looks like" | You know what a good exercise looks like for someone else's range. Ask for theirs. |

## Handoff

A design spec with no open questions is ready for `exercise-develop`
(planned; in the meantime, treat the blueprint work as a build plan under
`superpowers:writing-plans`). A spec with open questions goes back to your
human partner with the questions listed — not forward to the next phase.

## What this phase does not do

It does not author SDL, packages, content or injects, and it does not schedule
delivery. Those belong to `exercise-develop` and its artefact skills.
SKILL

bash tests/exercise-design/test-skill-structure.sh
```

Expected: every check `[PASS]`, `STATUS: PASSED`.

- [ ] **Step 3: Run the structural gates**

```bash
bash tests/skill-size/test-skill-size.sh && bash tests/using-superpowers/test-skill-references.sh
```

Expected: `PASS: every SKILL.md is under 20000 bytes`; then the skill-references
test still `STATUS: PASSED` (its rule only fires for skills named in the
introduction — `exercise-design` is still marked planned there, which Task 4
removes).

- [ ] **Step 4: Commit**

```bash
git add skills/exercise-design/SKILL.md tests/exercise-design/test-skill-structure.sh
git commit -m "Add the exercise-design phase skill"
```

---

### Task 2: Reword `brainstorming` for the exercise domain

**Files:**
- Modify: `skills/brainstorming/SKILL.md:3` (description), `:7-10` (opening), `:32` (last item of the pre-implementation list), `:258-260` (closing paragraph of the `<HARD-GATE>`)
- Test: `tests/brainstorming/test-exercise-framing.sh`

**Interfaces:**
- Consumes: the `exercise-design` name and output path from Task 1.
- Produces: a `brainstorming` whose `description` fires on exercise requests and whose pre-implementation handoff ends at `exercise-design`; Task 3's trigger fixtures depend on that wording.

- [ ] **Step 1: Write the failing test**

```bash
mkdir -p tests/brainstorming
cat > tests/brainstorming/test-exercise-framing.sh <<'TEST'
#!/usr/bin/env bash
# brainstorming is the process skill that fires first on "we need an exercise on
# X". It keeps its generic creative-work reach; what changes in slice 1 is that
# it names the exercise domain and hands off to exercise-design instead of
# invoking an implementation skill.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SKILL="$REPO_ROOT/skills/brainstorming/SKILL.md"

failures=0
pass() { echo "  [PASS] $1"; }
fail() { echo "  [FAIL] $1"; failures=$((failures + 1)); }

description="$(grep -m1 '^description:' "$SKILL" || true)"

if printf '%s' "$description" | grep -qi 'exercise'; then
    pass "description names the exercise domain"
else
    fail "description must name the exercise domain so the router fires on exercise requests"
fi

if printf '%s' "$description" | grep -qiE 'in software or out of it|talk, a business'; then
    pass "description keeps its generic creative-work reach"
else
    fail "description must keep covering non-exercise creative work"
fi

# The architectural path ends in exercise-design; the old text sent it to
# writing-plans, which in an exercise reads as software work.
if grep -q 'exercise-design' "$SKILL"; then
    pass "body hands off to exercise-design"
else
    fail "body must name exercise-design as the architectural path's next step"
fi

if [ "$failures" -gt 0 ]; then
    echo "STATUS: FAILED ($failures failure(s))"
    exit 1
fi

echo "STATUS: PASSED"
TEST
chmod +x tests/brainstorming/test-exercise-framing.sh
bash tests/brainstorming/test-exercise-framing.sh
```

Expected: FAIL on the first two checks (the current description says
"creating features, building components… in software or out of it (a talk, a
business, a renovation)") and on `exercise-design`; `STATUS: FAILED (3 failure(s))`.

- [ ] **Step 2: Reword the description and the opening**

Line 3 becomes:

```markdown
description: "You MUST use this before any creative work - designing a cyber range exercise or drill, creating features, building components, adding functionality, modifying behavior, or planning anything new, in software or out of it (a talk, a business, a renovation)."
```

The first paragraph (lines 7–10) ends `... and why, before anything gets built.`
Rewrite only that final sentence:

```markdown
You are very good at building. You build what you believe your human
partner wants, and that belief is usually thinner than it feels. This
skill is for finding out what they actually want, and why, before
anything gets built — a range exercise, a scenario service, a talk.
```

- [ ] **Step 3: Point the handoff at the design phase**

Item 4 of the numbered list that begins `Before you start implementing, you
must, in order:` (line 32, currently `4. Invoke the superpowers:writing-plans
skill.`) becomes:

```markdown
4. Hand the approved design to the next phase. For a cyber range
   exercise that is `exercise-design`, which turns the design into the
   exercise design spec; for software work, invoke
   superpowers:writing-plans.
```

The closing paragraph of the `<HARD-GATE>` (lines 258–260, currently
`After the design doc is approved, the next step is the plan: invoke
superpowers:writing-plans and no other skill.`) becomes:

```markdown
After the design doc is approved, the next step is the plan: invoke
superpowers:writing-plans and no other skill. The exception is a cyber
range exercise, where the approved design goes to `exercise-design`
first — that exercise's plan is written once its design spec exists.
```

Keep every other line of the file as is — including "Size the Work", "The
Written Design", the rest of the `<HARD-GATE>`, the Red Flags table, and the
"human partner" vocabulary.

- [ ] **Step 4: Run the test**

```bash
bash tests/brainstorming/test-exercise-framing.sh && bash tests/skill-size/test-skill-size.sh
```

Expected: `STATUS: PASSED` for both.

- [ ] **Step 5: Commit**

```bash
git add skills/brainstorming/SKILL.md tests/brainstorming/test-exercise-framing.sh
git commit -m "Point brainstorming at the exercise design phase"
```

---

### Task 3: Trigger fixtures for both skills

**Files:**
- Create: `tests/explicit-skill-requests/prompts/please-use-exercise-design.txt`
- Create: `tests/explicit-skill-requests/prompts/we-need-an-exercise.txt`
- Modify: `tests/explicit-skill-requests/run-all.sh` (append two cases before the summary)
- Test: `tests/explicit-skill-requests/test-fixture-registry.sh`

**Interfaces:**
- Consumes: the skill names from Tasks 1 and 2.
- Produces: named prompt files and `run-all.sh` cases, so `run-all.sh` exercises both skills; `run-test.sh <skill> <prompt-file>` is unchanged.

- [ ] **Step 1: Write the failing test**

```bash
cat > tests/explicit-skill-requests/test-fixture-registry.sh <<'TEST'
#!/usr/bin/env bash
# run-all.sh only runs what it lists, and its cases are hand-written. A prompt
# file with no case is dead weight; a case with no prompt file fails at runtime.
# Check both directions so a new fixture cannot land half-wired.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROMPTS="$SCRIPT_DIR/prompts"
RUN_ALL="$SCRIPT_DIR/run-all.sh"

failures=0
pass() { echo "  [PASS] $1"; }
fail() { echo "  [FAIL] $1"; failures=$((failures + 1)); }

for pair in \
    "exercise-design:please-use-exercise-design.txt" \
    "brainstorming:we-need-an-exercise.txt"; do
    skill="${pair%%:*}"
    file="${pair##*:}"

    if [ -s "$PROMPTS/$file" ]; then
        pass "prompt fixture exists and is not empty: $file"
    else
        fail "missing or empty prompt fixture: prompts/$file"
    fi

    if grep -Fq "\"$skill\" \"\$PROMPTS_DIR/$file\"" "$RUN_ALL"; then
        pass "run-all.sh runs $file against $skill"
    else
        fail "run-all.sh has no case for $file against $skill"
    fi
done

if [ "$failures" -gt 0 ]; then
    echo "STATUS: FAILED ($failures failure(s))"
    exit 1
fi

echo "STATUS: PASSED"
TEST
chmod +x tests/explicit-skill-requests/test-fixture-registry.sh
bash tests/explicit-skill-requests/test-fixture-registry.sh
```

Expected: four `[FAIL]` lines and `STATUS: FAILED (4 failure(s))`.

- [ ] **Step 2: Write the prompt fixtures**

```bash
cat > tests/explicit-skill-requests/prompts/please-use-exercise-design.txt <<'PROMPT'
please use the exercise-design skill to design a ransomware exercise for a hospital network
PROMPT

cat > tests/explicit-skill-requests/prompts/we-need-an-exercise.txt <<'PROMPT'
we need an exercise on phishing response for our SOC analysts
PROMPT
```

The first prompt is the spec §9 acceptance drill, named explicitly, so the test
measures routing and not whether the topic is interesting. The second
deliberately does not name a skill: it is the phrasing the `using-superpowers`
Skill Priority row promises will route to `brainstorming`.

- [ ] **Step 3: Register the cases**

Append to `tests/explicit-skill-requests/run-all.sh`, immediately before the
`echo "=== Summary ==="` line:

```bash
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
```

`run-test.sh` defaults to `--max-turns 3`. The design case gets 5: the
introduction tells the agent to run `brainstorming` first, so a run that obeys
both rules needs the extra turns to reach `exercise-design`. The pass condition
is the Skill tool call (`"skill":"exercise-design"` anywhere in the stream), not
the order skills were invoked in.

- [ ] **Step 4: Run the registry test**

```bash
bash tests/explicit-skill-requests/test-fixture-registry.sh
```

Expected: four `[PASS]` lines, `STATUS: PASSED`.

Do not run the full `run-all.sh` here: it drives `claude -p` per case and takes
minutes. It runs in Task 5.

- [ ] **Step 5: Commit**

```bash
git add tests/explicit-skill-requests/prompts/please-use-exercise-design.txt \
        tests/explicit-skill-requests/prompts/we-need-an-exercise.txt \
        tests/explicit-skill-requests/run-all.sh \
        tests/explicit-skill-requests/test-fixture-registry.sh
git commit -m "Add trigger fixtures for the design phase"
```

---

### Task 4: Stop calling `exercise-design` planned

**Files:**
- Modify: `skills/using-superpowers/SKILL.md` (lifecycle table and Skill Priority)
- Modify: `tests/using-superpowers/test-skill-references.sh`

**Interfaces:**
- Consumes: `skills/exercise-design/SKILL.md` from Task 1.
- Produces: an introduction whose statement about which skills exist is true, and a test that catches the stale marker from now on.

- [ ] **Step 1: Extend the test so the stale marker fails**

In `tests/using-superpowers/test-skill-references.sh`, replace the
`if [ -f "$REPO_ROOT/skills/$token/SKILL.md" ]` block with:

```bash
    if [ -f "$REPO_ROOT/skills/$token/SKILL.md" ]; then
        # A skill that now exists must not still be advertised as planned — the
        # marker was true when it was written and turns into a lie the moment
        # the skill lands.
        stale="$(
            grep -n "\`$token\`" "$SKILL_FILE" |
                grep -iE 'planned|not yet installed|not installed' || true
        )"
        if [ -z "$stale" ]; then
            echo "  [PASS] $token is installed and not marked planned"
        else
            echo "  [FAIL] $token is installed but still marked as planned:"
            printf '%s\n' "$stale" | sed 's/^/      /'
            failures=$((failures + 1))
        fi
        continue
    fi
```

- [ ] **Step 2: Run it and watch it fail**

```bash
bash tests/using-superpowers/test-skill-references.sh
```

Expected: `[FAIL] exercise-design is installed but still marked as planned:` with
the lifecycle row and the Skill Priority line, plus the five `(planned)` skills
that still do not exist passing. `STATUS: FAILED (1 failure(s))`.

- [ ] **Step 3: Drop the marker for `exercise-design`**

In `skills/using-superpowers/SKILL.md`:

- Lifecycle table row becomes
  `| Design | `exercise-design` | objectives, audience, scope, classification, assessment criteria |`
- Skill Priority first bullet becomes
  ``- "We need an exercise on X" → `brainstorming`, then `exercise-design`. ``
- The paragraph under the heading becomes:

```markdown
Four phases, each owned by a skill. `exercise-design` is installed; the other
three are planned and ship in later slices. Until they do, walk the phase
yourself and ask your human partner for its inputs; never substitute a software
skill for a missing one, and never fill the gap by inventing what the phase was
meant to produce.
```

Leave the `(planned)` markers on `exercise-develop`, `exercise-conduct`,
`exercise-evaluate` and `sdl-authoring`.

- [ ] **Step 4: Run the test and the neighbours**

```bash
bash tests/using-superpowers/test-skill-references.sh \
  && bash tests/hooks/test-session-start.sh \
  && bash tests/skill-size/test-skill-size.sh \
  && bash tests/bootstrap-parity/test-bootstrap-parity.sh
```

Expected: all four `STATUS: PASSED`. The hooks test asserts a phrase from the
skill body ("Asking instead of guessing") and the framing paragraph, neither of
which this task touches.

- [ ] **Step 5: Commit**

```bash
git add skills/using-superpowers/SKILL.md tests/using-superpowers/test-skill-references.sh
git commit -m "Stop advertising exercise-design as planned"
```

---

### Task 5: Verify the phase in a live session

**Files:**
- Test: `tests/exercise-design/test-live-design-session.sh` (new, opt-in — it drives `claude -p` and is not part of the default suite)

**Interfaces:**
- Consumes: every file from Tasks 1–4.
- Produces: a scripted acceptance check for UC-1 that a human can run after any later edit to either skill.

- [ ] **Step 1: Write the script**

```bash
cat > tests/exercise-design/test-live-design-session.sh <<'TEST'
#!/usr/bin/env bash
# Opt-in live check for UC-1. Drives a real Claude Code session with only this
# plugin loaded and asserts the design phase asks instead of inventing.
#
# Usage: tests/exercise-design/test-live-design-session.sh
# Requires: claude on PATH with a working model; ~2 minutes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if ! command -v claude >/dev/null 2>&1; then
    echo "SKIP: claude not on PATH"
    exit 0
fi

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

ask() {
    local prompt="$1"
    local dir="$work/$(date +%s%N)"
    mkdir -p "$dir"
    ( cd "$dir" && CLAUDE_CONFIG_DIR="$work/cfg-$RANDOM" \
        claude -p "$prompt" --plugin-dir "$REPO_ROOT" 2>/dev/null ) | tail -40
}

echo "=== Live design session ==="
output="$(ask "We need an exercise on phishing response for our SOC analysts.")"

if printf '%s' "$output" | grep -qi 'exercise-design\|design phase'; then
    echo "  [PASS] the design phase is named"
else
    echo "  [FAIL] the design phase is not named in the response"
    printf '%s\n' "$output" | sed 's/^/    /'
    exit 1
fi

if printf '%s' "$output" | grep -qiE 'objective|audience|scope|classification'; then
    echo "  [PASS] it asks for a design input rather than proposing the exercise"
else
    echo "  [FAIL] it did not ask for any design input"
    printf '%s\n' "$output" | sed 's/^/    /'
    exit 1
fi

if printf '%s' "$output" | grep -qiE '^.{0,80}(the exercise will|objectives are|I have designed)'; then
    echo "  [FAIL] it invented a design instead of asking"
    exit 1
fi

echo "STATUS: PASSED"
TEST
chmod +x tests/exercise-design/test-live-design-session.sh
```

- [ ] **Step 2: Run it**

```bash
bash tests/exercise-design/test-live-design-session.sh
```

Expected: `[PASS]` twice, `STATUS: PASSED`. If the model answers "Happy to help"
and asks about objectives, that is a pass. If it writes a design spec with
invented objectives, that is the finding this script exists for — fix the skill,
not the script.

- [ ] **Step 3: Run the trigger suite**

```bash
cd tests/explicit-skill-requests && ./run-all.sh
```

On macOS this fails every case with `timeout: command not found`; `run-test.sh`
needs a `timeout` on `PATH`. With coreutils installed,
`PATH="$(brew --prefix coreutils)/libexec/gnubin:$PATH" ./run-all.sh` works;
otherwise put a shim named `timeout` on `PATH` that forwards to
`perl -e 'alarm shift; exec @ARGV'`.

Expected: the two new cases pass alongside the existing ones. A failure here
means the `description` wording does not route; adjust the description, re-run
only the failing case with `./run-test.sh <skill> <prompt-file> 5`.

- [ ] **Step 4: Commit**

```bash
git add tests/exercise-design/test-live-design-session.sh
git commit -m "Add a live acceptance check for the design phase"
```

---

## Self-Review

**Spec coverage:** UC-1 (design an exercise) → Tasks 1 and 5. UC-6 (ask rather
than guess) → Task 1's "Ask before you design" and the live check. §3.2's
`exercise-design` row → Task 1. §3.2's `brainstorming` reword → Task 2. §3.3's
routing control surfaces (bootstrap paragraph, description, cross-references) →
Tasks 2 and 4. §9's "one trigger fixture per new skill" → Task 3. Slice 1's
"trigger fixtures" → Tasks 3 and 5.

**Not covered by this slice, by design:** `exercise-develop` and the artefact
skills are slices 2–4; the introduction keeps calling them planned.

**Placeholder scan:** no "TBD", no "handle edge cases", no "similar to Task N".
Every test is written out; every command has an `Expected:` line.

**Type consistency:** the skill name `exercise-design`, the path
`exercises/<slug>/design.md`, and the section headings asserted in Task 1 are the
same strings used in Task 2's handoff and Task 5's assertions.
