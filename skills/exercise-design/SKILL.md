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
