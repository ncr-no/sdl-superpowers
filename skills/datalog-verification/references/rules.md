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

A check with neither is PASS. A check that never appears is a bug in the
pack, and `verify.py` fails the run rather than skipping it.

A PASS must mean the rule looked and found nothing — not that nothing was
there to look at. When a check's input facts may be absent, guard it:

```
undecidable("group/name", "no scanning facts were provided") :-
    not has_pattern_hit(), not scan_complete("secrets").
```

Absence of the fact is UNDECIDABLE. Only a marker that the work was done —
such as `scan_complete("secrets")` for an empty hit set — earns a PASS.

## Available facts

| Predicate | From |
|---|---|
| `node/2`, `feature/2`, `edge/3`, `source/2` | SDL |
| `objective/1`, `criterion/2`, `inject/1`, `inject_target/2`, `assessment_maps/2` | Exercise documents |
| `classification/2`, `allowed/2` | Exercise classification |
| `registry_package/2`, `manifest_declares/2`, `pattern_hit/2` | Deputy / scanning (slice 3) |
| `scan_complete/1` | The scanner covered the artefacts — one row per scan kind |

The scanner emits `scan_complete("secrets")` once it has checked every
artefact. Without it, an empty `pattern_hit` set proves nothing.

## Adding a pack

Write the failing test first: facts in, expected `violation`/`undecidable`
facts out. Then the pack. A rule whose test only covers PASS is untested —
include the violating and the undecidable case.
