---
name: datalog-verification
description: Use when verifying a cyber range exercise for integrity against Datalog rules — that every service is hosted, the scenario graph is sound, classifications are respected, and the exercise documents agree with the SDL — before development builds against it
---

# Datalog Verification

You are verifying an exercise, not writing one. Facts go in, rules judge them,
and every verdict carries the derivation that produced it.

## What this produces

A traceability table with one row per check:

| Check | Verdict | Evidence |
|---|---|---|
| `structural/no_orphan_nodes` | VIOLATION | `("structural/no_orphan_nodes", "lonely")` |
| `artefact/declared_dependency_present` | UNKNOWN | `("…", "nginx_svc")` |

Written into the exercise's plan and, in summary, into its design spec's
traceability section.

## Facts

Facts are JSON: `{"predicate": [[arg, …], …]}`. Two sources, merged:

- **From the SDL** — `scripts/facts.py` turns a parsed SDL document into
  `node/2`, `feature/2`, `edge/3` and `source/2`. The parser emits no graph,
  so the relation labels are ours: `has_feature`, `has_inject`,
  `has_condition`, `links`, `depends_on`.
- **From the exercise documents** — objectives, criteria, injects and their
  mapping, plus classification levels and allowances. Extract them from what
  the exercise actually contains; never infer an objective.

If a fact set is missing, the affected checks come back UNKNOWN. That is the
correct answer, not a failure — do not invent facts to turn it green.

## Running it

```bash
python3 scripts/verify.py facts.json --rules references/rules
```

Exit `0` all pass, `1` at least one violation, `2` at least one unknown and
no violation, `3` the run itself failed. Several fact files merge.

## Reading the verdicts

- **PASS** — the rule ran and found nothing. A pass over an empty fact set
  is the one to distrust; check that the facts you expected are present.
- **VIOLATION** — the evidence names the subject. Fix the exercise, not the
  rule. If the rule is genuinely wrong, change it in a separate commit and
  say why.
- **UNKNOWN** — a fact or a tool is missing. Say which, and what would make
  it decidable. An UNKNOWN is never quietly upgraded to PASS.

## Writing a rule

Rules live in `references/rules/*.dl`. A pack declares its invariants with
`check("id")` and derives `violation("id", subject)` or
`undecidable("id", reason)`. See `references/rules.md` for the syntax, the
stratification constraint, and the fact names available.

## Red flags

| Thought | Reality |
|---|---|
| "Every check passes" | Check the fact count first. Vacuous passes are the common failure. |
| "This violation is a rule bug" | Prove it with the derivation, then fix the rule separately. |
| "I'll mark it PASS, it's obviously fine" | UNKNOWN exists precisely so you do not have to guess. |
| "I'll add the missing facts from the design doc's intent" | Intent is not a fact. Extract what the documents say. |
| "The cycle is fine in practice" | A dependency cycle is a violation even when the range boots. |

## Handoff

A table with no VIOLATION and no UNKNOWN goes to the development phase as
the scenario's integrity record. Anything else goes back to whoever owns the
SDL or the exercise documents, with the evidence column quoted.
