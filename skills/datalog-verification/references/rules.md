# Writing rule packs

One file per concern in `references/rules/`. All packs load together.

## Syntax

```
check("group/name").
violation("group/name", Subject) :- atom(Subject), not other(Subject).
undecidable("group/name", Subject) :- atom(Subject), not known(Subject).
```

- Identifiers starting uppercase are variables; `_` is a fresh anonymous
  variable. Everything else is a constant — quote strings.
- A bare atom is a base fact: `check("structural/no_orphan_nodes").`
- `not` is stratified negation. A predicate cannot depend on itself through
  negation; the engine raises `unstratified rules: 'a' and 'b' …` and stops.
- A variable may not appear **only** inside `not` — `not classification(N, L)`
  is rejected as unsafe. Write a helper predicate instead:
  `classified(N) :- classification(N, L).` then `not classified(N)`.
- `!=` compares two bound variables.
- Comments start with `#`. Rules may wrap across lines.

## The contract

| Fact | Meaning |
|---|---|
| `check("id")` | This invariant exists |
| `violation("id", subject…)` | It fails for that subject |
| `undecidable("id", reason…)` | It cannot be judged — say why |

A check with neither is PASS. A check that never appears is a bug in the pack.

## Available facts

| Predicate | From |
|---|---|
| `node/2`, `feature/2`, `edge/3`, `source/2` | SDL |
| `objective/1`, `criterion/2`, `inject/1`, `inject_target/2`, `assessment_maps/2` | Exercise documents |
| `classification/2`, `allowed/2` | Exercise classification |
| `registry_package/2`, `manifest_declares/2`, `pattern_hit/2` | Deputy / scanning (slice 3) |

## Adding a pack

Write the failing test first: facts in, expected `violation`/`undecidable`
facts out. Then the pack. A rule whose test only covers PASS is untested —
include the violating and the undecidable case.
