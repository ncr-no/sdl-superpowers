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

Four phases, each owned by a skill. `exercise-design` is installed; the other three are planned and ship in later slices. Until they do, walk the phase yourself and ask your human partner for its inputs; never substitute a software skill for a missing one, and never fill the gap by inventing what the phase was meant to produce.

| Phase | Skill | Produces |
|---|---|---|
| Design | `exercise-design` | objectives, audience, scope, classification, assessment criteria |
| Develop | `exercise-develop` (planned) | SDL blueprint, Deputy packages, exercise content, inject timeline |
| Conduct | `exercise-conduct` (planned) | white-cell plan, runbook, inject schedule, stop conditions |
| Evaluate | `exercise-evaluate` (planned) | criterion-level evidence, AAR, improvement actions |

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
- "Build the blueprint" → `sdl-authoring` (planned), validated before anything else proceeds.
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
