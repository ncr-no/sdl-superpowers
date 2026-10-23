# Cyber Range Slice 2 — SDL and Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `sdl-authoring` and `datalog-verification`: a skill that authors `.sdl` by hand and validates it through `sdl_parser`, and a self-contained stratified-Datalog engine with four rule packs that turns facts into PASS / VIOLATION / UNKNOWN verdicts with derivation traces.

**Architecture:** The parser is a Rust library with a thin Python wrapper; it validates syntax and referential closure and returns a plain dict. The verifier owns everything above that: it synthesises the `node`/`edge` facts the parser does not emit, loads `.dl` rules stratified by negation, evaluates them semi-naively, and renders a traceability table. Facts are JSON; the engine is pure Python with no third-party imports. Both skills detect their absent tools and take the `UNKNOWN` path with an install command rather than failing opaquely (spec §2.4).

**Tech Stack:** Python 3.9+ standard library only; pytest for tests (already used by `tests/hermes`); bash for the two structural skill tests; the existing `tests/explicit-skill-requests/` trigger harness.

**Spec:** `docs/superpowers/specs/2026-10-23-cyber-range-exercise-methodology-design.md` (§2.4 tooling gaps, §3.2 inventory, §7 verification model, §8 slice 2, §9 testing)

**Status of the code in this plan:** Tasks 1–5 were executed in a scratch
tree while the plan was written, not merely written down. The engine passed
11 tests, every rule-pack assertion in Tasks 3–4 held, and the CLI produced
the exact verdict table the golden file in Task 5 predicts (`0` / `1` / `2` /
`3` exit paths all observed). Three defects that run exposed are already
fixed in the text: a predicate-name token that swallowed the rule terminator,
`derivation()` returning the rule instead of the body facts, and body-less
facts having no stratum. Task 6–8's code has not been executed.

## Global Constraints

- Engine, extractor and CLI are standard-library Python only — no `pytest` import outside tests, no third-party packages (spec §7.3).
- Every `SKILL.md` stays under 20,000 bytes (`tests/skill-size/test-skill-size.sh`).
- `import sdl_parser` fails at import time when `libsdl_parser` is absent, because the wrapper loads the shared library with `ctypes` at module import. Detection must therefore wrap the import in `try/except`, never test for the module by name only.
- The parser raises exactly one exception, `SDLLibraryParsingError`, with a single `.message` attribute and **no** line number. Error handling keys off `.message` only.
- The parser emits **no** edge vocabulary. Facts named `edge/3` are synthesised by this slice; the mapping from SDL fields to relation labels is defined in Task 2 and is the contract later slices read.
- Slice 2 does not author or read `package.toml`, and does not call `deputy`; the artefact-integrity pack consumes facts that slice 3 will extract. Its tests supply those facts by hand.
- Bash tests must run under bash 3.2; `set -euo pipefail` plus `grep` aborts on no-match, so every "expect absent" check is guarded.
- Skills import their scripts by path (`sys.path.insert(0, .../scripts)`), the pattern `tests/hermes` already uses.

## Review Focus

Five inputs the spec does not describe, most likely to bite a person using this:

1. **A rule that never fires is indistinguishable from a rule that passes.** If extraction silently yields no `objective` facts, "every objective has a criterion" is vacuously true. A reasonable person sees `UNKNOWN (documents missing)`, not `PASS`.
2. **Recursion through negation.** A rule set where `not p` and `p :- ... not q` sit in one cycle has no stratification. A reasonable person gets a named error and the two predicates, not a hang or a wrong verdict.
3. **A cycle is a violation, not a fixpoint failure.** `a depends_on b, b depends_on a` must produce `VIOLATION` on both nodes — the engine must not silently converge on a partial answer.
4. **The SDL parse error has no line number.** A reasonable person gets `.message` verbatim plus the file path and the failing construct when the message names one, not a fabricated line.
5. **Facts from a hand-edited file.** Duplicate atoms, the same predicate at two arities, and a predicate the rules never mention must each be handled: dedupe, name the arity clash with both counts, and ignore the unused predicate.

---

### Task 1: The Datalog engine

**Files:**
- Create: `skills/datalog-verification/scripts/datalog.py`
- Test: `tests/datalog-verification/test_datalog.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `class DatalogError(Exception)` — unstratifiable rules, arity clash, unsafe negation.
  - `parse_program(text: str, source: str = "<string>") -> list[Rule]`
  - `parse_facts(data: dict) -> dict[str, set[tuple]]` — `{"pred": [["a", "b"], ...]}`
  - `evaluate(rules: list[Rule], facts: dict[str, set[tuple]]) -> Evaluation` with
    `.facts: dict[str, set[tuple]]`, `.derivation(pred, args) -> tuple | None` (body fact tuples that produced it), `.rule_for(pred, args) -> Rule | None`.
  - `Atom(pred, args)` and `Rule(head, body, negated, source)` dataclasses; a variable arg is `Var(name)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/datalog-verification/test_datalog.py
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../skills/datalog-verification/scripts")
))

from datalog import DatalogError, evaluate, parse_facts, parse_program  # noqa: E402


def run(program, facts):
    return evaluate(parse_program(program), parse_facts(facts))


def test_derives_a_simple_rule():
    result = run(
        'hosted(F) :- edge(N, "has_feature", F), node(N, "VM").',
        {"edge": [["a", "has_feature", "svc"]], "node": [["a", "VM"]]},
    )
    assert result.facts["hosted"] == {("svc",)}


def test_transitive_closure_reaches_fixpoint():
    result = run(
        'reach(X, Y) :- edge(X, "d", Y).\nreach(X, Y) :- reach(X, Z), edge(Z, "d", Y).',
        {"edge": [["a", "d", "b"], ["b", "d", "c"]]},
    )
    assert result.facts["reach"] == {("a", "b"), ("b", "c"), ("a", "c")}


def test_cycle_still_converges_and_is_visible():
    result = run(
        'reach(X, Y) :- edge(X, "d", Y).\nreach(X, Y) :- reach(X, Z), edge(Z, "d", Y).',
        {"edge": [["a", "d", "b"], ["b", "d", "a"]]},
    )
    assert ("a", "a") in result.facts["reach"]


def test_negation_in_a_higher_stratum():
    result = run(
        'orphan(N) :- node(N), not connected(N).\nconnected(N) :- edge(N, _, _).',
        {"node": [["a"], ["b"]], "edge": [["a", "x", "c"]]},
    )
    assert result.facts["orphan"] == {("b",)}


def test_unstratified_negation_is_an_error_naming_both_predicates():
    with pytest.raises(DatalogError) as excinfo:
        run('p(X) :- q(X), not p(X).', {"q": [["v"]]})
    message = str(excinfo.value)
    assert "unstratified" in message
    assert "p" in message


def test_inequality_filter_excludes_equal_values():
    result = run(
        'diff(A, B) :- pair(A, B), A != B.',
        {"pair": [["a", "b"], ["a", "a"]]},
    )
    assert result.facts["diff"] == {("a", "b")}


def test_underscore_is_an_anonymous_variable():
    result = run('has_type(F) :- feature(F, _).',
                 {"feature": [["a", "service"], ["b", "config"]]})
    assert result.facts["has_type"] == {("a",), ("b",)}


def test_a_bare_atom_is_a_base_fact():
    result = run('check("structural/no_orphan_nodes").', {})
    assert result.facts["check"] == {("structural/no_orphan_nodes",)}


def test_arity_clash_names_the_predicate_and_both_arities():
    with pytest.raises(DatalogError) as excinfo:
        run('x(A) :- a(A).', {"a": [["one", "two"]]})
    assert "arity" in str(excinfo.value)


def test_derivation_records_the_body_facts():
    result = run(
        'hosted(F) :- edge(N, "has_feature", F), node(N, "VM").',
        {"edge": [["a", "has_feature", "svc"]], "node": [["a", "VM"]]},
    )
    assert result.derivation("hosted", ("svc",)) == (
        ("edge", ("a", "has_feature", "svc")),
        ("node", ("a", "VM")),
    )


def test_duplicate_facts_are_deduplicated():
    result = run('x(A) :- a(A).', {"a": [["v"], ["v"]]})
    assert result.facts["x"] == {("v",)}
```

- [ ] **Step 2: Run it and watch it fail**

```bash
cd /Users/mmpeal/Developer/ncr/sdl-superpowers && python3 -m pytest tests/datalog-verification/test_datalog.py -q
```

Expected: collection error, `ModuleNotFoundError: No module named 'datalog'`.

- [ ] **Step 3: Write the engine**

```python
# skills/datalog-verification/scripts/datalog.py
"""Stratified Datalog with semi-naive evaluation and derivation traces.

Pure standard library. Rules are loaded from `.dl` files, facts from JSON.
The graph sizes this runs on are tens to hundreds of nodes, so the design
favours obviousness: one stratum at a time, delta-driven joins, first
derivation wins in the trace.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass


class DatalogError(Exception):
    """A program that cannot be evaluated: bad syntax, unstratified
    negation, an arity clash between rules and facts, or unsafe negation."""


@dataclass(frozen=True)
class Var:
    name: str


@dataclass(frozen=True)
class Atom:
    pred: str
    args: tuple


@dataclass(frozen=True)
class Rule:
    head: Atom
    body: tuple          # positive atoms, in source order
    negated: tuple       # negated atoms
    filters: tuple       # (Var, Var) pairs meaning "these two values differ"
    source: str


_TOKEN = re.compile(
    r'\s*(?:(:-)|([(),.])|(not)\b|("(?:[^"\\]|\\.)*")|([A-Za-z_][A-Za-z0-9_]*)|(!=))'
)


def _tokens(text):
    pos, out = 0, []
    while pos < len(text):
        if text[pos] in " \t\r\n":
            pos += 1
            continue
        if text[pos] == "#":
            nl = text.find("\n", pos)
            pos = len(text) if nl < 0 else nl + 1
            continue
        m = _TOKEN.match(text, pos)
        if not m:
            raise DatalogError("cannot tokenise near: %r" % text[pos:pos + 30])
        pos = m.end()
        if m.group(1):
            out.append((":-", None))
        elif m.group(2):
            out.append((m.group(2), None))
        elif m.group(3):
            out.append(("not", None))
        elif m.group(4):
            out.append(("const", json.loads(m.group(4))))
        elif m.group(5):
            out.append(("ident", m.group(5)))
        else:
            out.append(("!=", None))
    return out


def _term(tok, anon):
    kind, value = tok
    if kind == "const":
        return value
    if kind == "ident":
        if value == "_":
            anon[0] += 1
            return Var("__anon%d" % anon[0])
        return Var(value) if value[0].isupper() else value
    raise DatalogError("expected a term, found %r" % (tok,))


def _atom(tokens, i, source, anon):
    kind, pred = tokens[i]
    if kind != "ident":
        raise DatalogError("%s: expected a predicate, found %r" % (source, pred))
    if tokens[i + 1][0] != "(":
        raise DatalogError("%s: predicate %r is missing '('" % (source, pred))
    i += 2
    args = []
    while tokens[i][0] != ")":
        args.append(_term(tokens[i], anon))
        i += 1
        if tokens[i][0] == ",":
            i += 1
        elif tokens[i][0] != ")":
            raise DatalogError("%s: expected ',' or ')' in %r" % (source, pred))
    return Atom(pred, tuple(args)), i + 1


def parse_program(text, source="<string>"):
    tokens = _tokens(text)
    rules, i = [], 0
    while i < len(tokens):
        anon = [0]
        head, i = _atom(tokens, i, source, anon)
        if tokens[i][0] == ".":
            # A bare atom is a base fact, which is how packs declare
            # `check("structural/no_orphan_nodes").`
            rules.append(Rule(head, (), (), (), source))
            i += 1
            continue
        if tokens[i][0] != ":-":
            raise DatalogError("%s: rule for %r has no ':-'" % (source, head.pred))
        i += 1
        body, negated, filters = [], [], []
        while True:
            kind = tokens[i][0]
            if kind == "not":
                atom, i = _atom(tokens, i + 1, source, anon)
                negated.append(atom)
            elif kind == "ident" and i + 1 < len(tokens) and tokens[i + 1][0] == "!=":
                filters.append((_term(tokens[i], anon), _term(tokens[i + 2], anon)))
                i += 3
            else:
                atom, i = _atom(tokens, i, source, anon)
                body.append(atom)
            if tokens[i][0] == ",":
                i += 1
                continue
            if tokens[i][0] == ".":
                i += 1
                break
            raise DatalogError("%s: expected ',' or '.' after a body item" % source)
        _check_negation_safety(head, body, negated, source)
        rules.append(Rule(head, tuple(body), tuple(negated), tuple(filters), source))
    return rules


def _check_negation_safety(head, body, negated, source):
    bound = {a.name for atom in body for a in atom.args if isinstance(a, Var)}
    for atom in negated:
        free = {v.name for v in atom.args if isinstance(v, Var)} - bound
        if free:
            raise DatalogError(
                "%s: negated %r has unbound variable(s) %s"
                % (source, atom.pred, ", ".join(sorted(free)))
            )


def parse_facts(data):
    facts = {}
    for pred, rows in data.items():
        for row in rows:
            facts.setdefault(pred, set()).add(tuple(row))
    return facts


@dataclass(frozen=True)
class Evaluation:
    facts: dict
    _prov: dict

    def derivation(self, pred, args):
        found = self._prov.get((pred, tuple(args)))
        return None if found is None else found[1]

    def rule_for(self, pred, args):
        found = self._prov.get((pred, tuple(args)))
        return None if found is None else found[0]


def evaluate(rules, facts):
    arities = {}
    for pred, rows in facts.items():
        for row in rows:
            arities.setdefault(pred, len(row))
            if arities[pred] != len(row):
                raise DatalogError(
                    "arity clash: %r appears with %d and %d arguments"
                    % (pred, arities[pred], len(row))
                )

    strata = _stratify(rules)
    world = {pred: set(rows) for pred, rows in facts.items()}
    prov = {}
    for stratum in strata:
        world, prov = _run_stratum(stratum, world, prov, arities)
    return Evaluation(world, prov)


def _preds_of(rule):
    return [a.pred for a in rule.body + rule.negated] + [rule.head.pred]


def _stratify(rules):
    """Tarjan SCC over the predicate graph; a negative edge inside one SCC is
    an unstratifiable program. Strata come out in dependency order."""
    edges = {}
    negative = set()
    for rule in rules:
        # A body-less rule (a base fact) still owns a node in this graph;
        # without this, its predicate never gets a stratum and never runs.
        edges.setdefault(rule.head.pred, set())
        for atom in rule.body:
            edges[rule.head.pred].add(atom.pred)
        for atom in rule.negated:
            edges.setdefault(rule.head.pred, set()).add(atom.pred)
            negative.add((rule.head.pred, atom.pred))

    index, low, on_stack, stack, sccs = {}, {}, set(), [], []
    counter = [0]

    def strongconnect(v):
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on_stack.add(v)
        for w in edges.get(v, ()):
            if w not in index:
                strongconnect(w)
                low[v] = min(low[v], low[w])
            elif w in on_stack:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            component = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                component.append(w)
                if w == v:
                    break
            sccs.append(set(component))

    for v in list(edges):
        if v not in index:
            strongconnect(v)

    component_of = {}
    for i, component in enumerate(sccs):
        for pred in component:
            component_of[pred] = i
    for head, body in negative:
        if component_of.get(head) == component_of.get(body):
            raise DatalogError(
                "unstratified rules: %r and %r depend on each other through "
                "negation inside one cycle" % (head, body)
            )

    # Tarjan emits a component only after every component reachable from it,
    # and edges run head -> body, so `sccs` is already in dependency order.
    strata = []
    for component in sccs:
        stratum = [r for r in rules if r.head.pred in component]
        if stratum:
            strata.append(stratum)
    return strata


def _ground(atom, env):
    args = []
    for arg in atom.args:
        args.append(env[arg.name] if isinstance(arg, Var) else arg)
    return tuple(args)


def _matches(rule, world, delta_position=None, delta_rows=None):
    """Every binding of the rule's positive body. Position `delta_position`,
    when given, reads from `delta_rows` instead of the whole relation — that
    is what makes the fixpoint semi-naive instead of naive."""
    out = []

    def walk(index, env):
        if index == len(rule.body):
            out.append(env)
            return
        atom = rule.body[index]
        rows = delta_rows if index == delta_position else world.get(atom.pred, ())
        for row in rows:
            if len(row) != len(atom.args):
                raise DatalogError(
                    "arity clash: %r used with %d arguments but the facts have %d"
                    % (atom.pred, len(atom.args), len(row))
                )
            trial = dict(env)
            for value, term in zip(row, atom.args):
                if isinstance(term, Var):
                    if term.name in trial and trial[term.name] != value:
                        trial = None
                        break
                    trial[term.name] = value
                elif term != value:
                    trial = None
                    break
            if trial is not None:
                walk(index + 1, trial)

    walk(0, {})
    return out


def _accept(rule, env, world):
    for left, right in rule.filters:
        if env[left.name] == env[right.name]:
            return False
    return not any(_ground(n, env) in world.get(n.pred, ()) for n in rule.negated)


def _check_head_bound(rule):
    bound = {v.name for atom in rule.body for v in atom.args if isinstance(v, Var)}
    for arg in rule.head.args:
        if isinstance(arg, Var) and arg.name not in bound:
            raise DatalogError(
                "%s: head variable %r is unbound" % (rule.source, arg.name)
            )
    for left, right in rule.filters:
        for var in (left, right):
            if var.name not in bound:
                raise DatalogError(
                    "%s: comparison variable %r is unbound" % (rule.source, var.name)
                )


def _run_stratum(stratum, world, prov, arities):
    delta = {pred: set(rows) for pred, rows in world.items()}
    first = True
    while first or any(delta.values()):
        first = False
        produced = {}
        for rule in stratum:
            _check_head_bound(rule)
            # A rule whose positive body is empty (only negations) has no
            # position to drive the join, so it is evaluated once as a whole.
            for position in list(range(len(rule.body))) or [None]:
                if position is None:
                    delta_rows = None
                else:
                    delta_rows = delta.get(rule.body[position].pred)
                    if not delta_rows:
                        continue
                for env in _matches(rule, world, position, delta_rows):
                    if not _accept(rule, env, world):
                        continue
                    ground = _ground(rule.head, env)
                    target = world.setdefault(rule.head.pred, set())
                    if arities.setdefault(rule.head.pred, len(ground)) != len(ground):
                        raise DatalogError(
                            "arity clash: %r derived with %d arguments, facts have %d"
                            % (rule.head.pred, len(ground), arities[rule.head.pred])
                        )
                    if ground in target:
                        continue
                    target.add(ground)
                    produced.setdefault(rule.head.pred, set()).add(ground)
                    prov.setdefault(
                        (rule.head.pred, ground),
                        (rule, tuple((a.pred, _ground(a, env)) for a in rule.body)),
                    )
        delta = produced
    return world, prov
```

- [ ] **Step 4: Run the tests**

```bash
python3 -m pytest tests/datalog-verification/test_datalog.py -q
```

Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/datalog-verification/scripts/datalog.py tests/datalog-verification/test_datalog.py
git commit -m "Add a stratified Datalog engine with derivation traces

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 2: Facts — from the parsed SDL and from exercise documents

**Files:**
- Create: `skills/datalog-verification/scripts/facts.py`
- Test: `tests/datalog-verification/test_facts.py`
- Fixture: `tests/datalog-verification/fixtures/hospital.sdl.json` (a parsed-SDL dict, hand-written from the parser's schema)

**Interfaces:**
- Consumes: the parsed-SDL dict shape documented below; JSON fact files.
- Produces:
  - `from_sdl(parsed: dict) -> dict[str, list[list[str]]]` — facts in the JSON shape.
  - `load(path) -> dict` for a facts JSON file, and `merge(*fact_dicts) -> dict`.
  - Relation labels, which later slices read: `links`, `depends_on`, `has_feature`, `has_inject`, `has_condition`.
  - Predicates: `node/2`, `feature/2`, `edge/3`, `source/2`, plus whatever document facts the file supplies (`objective/1`, `criterion/2`, `inject/1`, `inject_target/2`, `assessment_maps/2`, `classification/2`, `allowed/2`, `registry_package/2`, `manifest_declares/2`, `pattern_hit/2`).

- [ ] **Step 1: Write the failing test**

```python
# tests/datalog-verification/test_facts.py
import json
import os
import sys

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../skills/datalog-verification/scripts")
))

from facts import from_sdl, merge  # noqa: E402

HERE = os.path.dirname(__file__)


def test_nodes_and_vm_sources():
    parsed = {
        "nodes": {
            "web01": {"type": "VM", "source": "ubuntu22"},
            "sw01": {"type": "Switch"},
            "db01": {"type": "VM", "source": {"name": "postgres16", "version": "*"}},
        },
        "infrastructure": {"web01": 1},
    }
    facts = from_sdl(parsed)
    assert sorted(facts["node"]) == [["db01", "VM"], ["sw01", "Switch"], ["web01", "VM"]]
    assert ["web01", "ubuntu22"] in facts["source"]
    assert ["db01", "postgres16"] in facts["source"]


def test_features_links_and_dependencies_become_edges():
    parsed = {
        "nodes": {"web01": {"type": "VM", "features": {"nginx_svc": "default"}}},
        "features": {
            "nginx_svc": {"type": "service", "source": "nginx", "dependencies": ["cert_svc"]},
            "cert_svc": {"type": "configuration", "source": "certs"},
        },
        "infrastructure": {
            "web01": {"count": 1, "links": ["dmz"], "dependencies": ["git01"]},
        },
    }
    facts = from_sdl(parsed)
    edges = {tuple(e) for e in facts["edge"]}
    assert ("web01", "has_feature", "nginx_svc") in edges
    assert ("nginx_svc", "depends_on", "cert_svc") in edges
    assert ("web01", "links", "dmz") in edges
    assert ("web01", "depends_on", "git01") in edges
    assert ["nginx_svc", "service"] in facts["feature"]


def test_absent_sections_yield_no_facts_and_no_error():
    assert from_sdl({"name": "empty"}) == {}


def test_duplicate_rows_survive_merge_deduplicated():
    merged = merge({"node": [["a", "VM"]]}, {"node": [["a", "VM"], ["b", "VM"]]})
    assert sorted(merged["node"]) == [["a", "VM"], ["b", "VM"]]


def test_fixture_is_valid_json_with_the_documented_shape():
    with open(os.path.join(HERE, "fixtures/hospital.sdl.json")) as handle:
        parsed = json.load(handle)
    facts = from_sdl(parsed)
    assert facts["node"], "fixture must produce nodes"
    assert facts["edge"], "fixture must produce edges"
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python3 -m pytest tests/datalog-verification/test_facts.py -q`
Expected: `ModuleNotFoundError: No module named 'facts'`.

- [ ] **Step 3: Write the extractor**

```python
# skills/datalog-verification/scripts/facts.py
"""Turn a parsed SDL document (and any extra JSON) into Datalog facts.

`sdl_parser.parse_sdl` returns the Scenario as a plain dict and emits no
graph: links, dependencies and node-to-feature references live in list and
map fields. This module is the single place that mapping is defined.

Relation labels (stable — later slices depend on them):
  has_feature   node  -> feature named in nodes.<n>.features
  has_inject    node  -> inject named in nodes.<n>.injects
  has_condition node  -> condition named in nodes.<n>.conditions
  links         node  -> node named in infrastructure.<n>.links
  depends_on    node or feature -> its dependency
"""
from __future__ import annotations

import json


def _rows(facts, pred, rows):
    facts.setdefault(pred, []).extend([list(row) for row in rows])


def _named(value):
    """A package reference is either a name or {name, version}."""
    if isinstance(value, dict):
        return value.get("name")
    return value


def from_sdl(parsed):
    facts = {}

    def section(name):
        value = parsed.get(name)
        return value if isinstance(value, dict) else {}

    for name, node in section("nodes").items():
        if not isinstance(node, dict):
            continue
        _rows(facts, "node", [(name, node.get("type") or "VM")])
        package = _named(node.get("source"))
        if package:
            _rows(facts, "source", [(name, package)])
        for field, relation in (
            ("features", "has_feature"),
            ("injects", "has_inject"),
            ("conditions", "has_condition"),
        ):
            targets = node.get(field)
            if isinstance(targets, dict):
                _rows(facts, "edge", [(name, relation, t) for t in targets])
            elif isinstance(targets, list):
                _rows(facts, "edge", [(name, relation, t) for t in targets])

    for name, feature in section("features").items():
        if not isinstance(feature, dict):
            continue
        _rows(facts, "feature", [(name, feature.get("type") or "service")])
        for dependency in feature.get("dependencies") or ():
            _rows(facts, "edge", [(name, "depends_on", dependency)])

    for name, infrastructure in section("infrastructure").items():
        if not isinstance(infrastructure, dict):
            continue
        for field, relation in (("links", "links"), ("dependencies", "depends_on")):
            for other in infrastructure.get(field) or ():
                _rows(facts, "edge", [(name, relation, other)])

    return facts


def merge(*fact_dicts):
    seen, merged = {}, {}
    for facts in fact_dicts:
        for pred, rows in facts.items():
            bucket = seen.setdefault(pred, set())
            out = merged.setdefault(pred, [])
            for row in rows:
                key = tuple(row)
                if key not in bucket:
                    bucket.add(key)
                    out.append(list(row))
    return merged


def load(path):
    with open(path) as handle:
        return json.load(handle)
```

- [ ] **Step 4: Write the fixture**

```json
{
  "name": "hospital-ransomware",
  "description": "Hospital network under ransomware pressure",
  "nodes": {
    "ehr01": {"type": "VM", "source": "ubuntu22", "features": {"ehr_svc": "default"}},
    "fileserver01": {"type": "VM", "source": "windows2022"},
    "backup01": {"type": "VM", "source": "truenas", "features": {"backup_svc": "default"}},
    "fwsrv": {"type": "Switch"}
  },
  "features": {
    "ehr_svc": {"type": "service", "source": "ehr", "dependencies": ["auth_svc"]},
    "auth_svc": {"type": "configuration", "source": "sso"},
    "backup_svc": {"type": "service", "source": "restic"}
  },
  "infrastructure": {
    "ehr01": {"count": 1, "links": ["fwsrv"]},
    "fileserver01": {"count": 1, "links": ["fwsrv"], "dependencies": ["backup01"]},
    "backup01": {"count": 1, "links": ["fwsrv"]}
  }
}
```

Write it with the Write tool at `tests/datalog-verification/fixtures/hospital.sdl.json`.

- [ ] **Step 5: Run the tests**

```bash
python3 -m pytest tests/datalog-verification/test_facts.py -q
```

Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add skills/datalog-verification/scripts/facts.py tests/datalog-verification/test_facts.py tests/datalog-verification/fixtures/hospital.sdl.json
git commit -m "Extract Datalog facts from a parsed SDL document

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 3: Structural and scenario-integrity rule packs

**Files:**
- Create: `skills/datalog-verification/references/rules/structural.dl`
- Create: `skills/datalog-verification/references/rules/scenario_integrity.dl`
- Test: `tests/datalog-verification/test_rules_structural.py`
- Test: `tests/datalog-verification/test_rules_scenario.py`

**Interfaces:**
- Consumes: `parse_program`, `parse_facts`, `evaluate` from Task 1; the predicate and relation names from Task 2.
- Produces: the rule-author contract every later pack uses — a pack declares `check("id")` for each invariant, and derives either `violation("id", subject…)` or `undecidable("id", reason…)`. A check with neither is `PASS`. Pack files are `references/rules/*.dl`.

- [ ] **Step 1: Write the failing structural tests**

```python
# tests/datalog-verification/test_rules_structural.py
import os
import sys

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../skills/datalog-verification/scripts")
))

from datalog import evaluate, parse_facts, parse_program  # noqa: E402

RULES = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "../../skills/datalog-verification/references/rules"
))


def verdict(pack, facts):
    with open(os.path.join(RULES, pack)) as handle:
        return evaluate(parse_program(handle.read(), source=pack), parse_facts(facts))


def test_clean_graph_has_no_violations_or_unknowns():
    result = verdict("structural.dl", {
        "node": [["web01", "VM"], ["dmz", "Switch"]],
        "feature": [["nginx_svc", "service"]],
        "edge": [["web01", "has_feature", "nginx_svc"],
                 ["web01", "links", "dmz"]],
        "source": [["web01", "ubuntu22"]],
        "registry_package": [["ubuntu22", "public"]],
    })
    assert result.facts.get("violation", set()) == set()
    assert result.facts.get("undecidable", set()) == set()


def test_orphan_node_is_a_violation():
    result = verdict("structural.dl", {"node": [["lonely", "VM"]]})
    assert ("structural/no_orphan_nodes", "lonely") in result.facts["violation"]


def test_service_with_no_host_is_a_violation():
    result = verdict("structural.dl", {
        "node": [["a", "VM"], ["b", "Switch"]],
        "feature": [["ghost_svc", "service"]],
        "edge": [["a", "links", "b"]],
    })
    assert ("structural/service_has_host", "ghost_svc") in result.facts["violation"]


def test_dependency_cycle_violates_on_every_node_in_the_cycle():
    result = verdict("structural.dl", {
        "node": [["a", "VM"], ["b", "VM"]],
        "edge": [["a", "depends_on", "b"], ["b", "depends_on", "a"]],
    })
    assert ("structural/dependencies_acyclic", "a") in result.facts["violation"]
    assert ("structural/dependencies_acyclic", "b") in result.facts["violation"]


def test_source_without_registry_facts_is_undecidable():
    result = verdict("structural.dl", {
        "node": [["a", "VM"]],
        "source": [["a", "ubuntu22"]],
    })
    assert any(row[0] == "structural/source_resolves"
               for row in result.facts["undecidable"])
```

- [ ] **Step 2: Run them and watch them fail**

Run: `python3 -m pytest tests/datalog-verification/test_rules_structural.py -q`
Expected: 5 failed, each with `FileNotFoundError: .../references/rules/structural.dl`.

- [ ] **Step 3: Write `structural.dl`**

```
# Structural invariants. The parser guarantees references resolve; it does
# not guarantee the graph is sensible. These rules cover the four the spec
# names: every service is hosted, no node is stranded, dependencies are
# acyclic, and every referenced package resolves.

check("structural/service_has_host").
violation("structural/service_has_host", F) :- feature(F, T), not hosted(F).
hosted(F) :- node(N, T), edge(N, "has_feature", F).

check("structural/no_orphan_nodes").
violation("structural/no_orphan_nodes", N) :- node(N, T), not connected(N).
connected(N) :- edge(N, R, O).
connected(N) :- edge(O, R, N).

check("structural/dependencies_acyclic").
violation("structural/dependencies_acyclic", A) :- edge(A, "depends_on", B), reaches(B, A).
reaches(X, Y) :- edge(X, "depends_on", Y).
reaches(X, Y) :- reaches(X, Z), edge(Z, "depends_on", Y).

check("structural/source_resolves").
# Absent registry facts mean slice 3 has not run yet: UNDECIDABLE, not PASS.
undecidable("structural/source_resolves", P) :- source(N, P), not registry_known(P).
registry_known(P) :- registry_package(P, V).
```

- [ ] **Step 4: Run the structural tests**

Run: `python3 -m pytest tests/datalog-verification/test_rules_structural.py -q`
Expected: 5 passed.

- [ ] **Step 5: Write the failing scenario tests**

```python
# tests/datalog-verification/test_rules_scenario.py
import os
import sys

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../skills/datalog-verification/scripts")
))

from datalog import evaluate, parse_facts, parse_program  # noqa: E402

RULES = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "../../skills/datalog-verification/references/rules"
))


def verdict(facts):
    with open(os.path.join(RULES, "scenario_integrity.dl")) as handle:
        rules = parse_program(handle.read(), source="scenario_integrity.dl")
    return evaluate(rules, parse_facts(facts))


DOCUMENTED = {
    "objective": [["obj-1"]],
    "criterion": [["crit-1", "obj-1"]],
    "inject": [["inj-1"]],
    "inject_target": [["inj-1", "web01"]],
    "assessment_maps": [["crit-1", "inj-1"]],
    "node": [["web01", "VM"]],
}


def test_no_documents_is_undecidable_not_vacuous_pass():
    result = verdict({})
    assert any(row[0] == "scenario/documents_present"
               for row in result.facts["undecidable"])


def test_complete_documents_pass_every_scenario_check():
    result = verdict(DOCUMENTED)
    assert result.facts.get("violation", set()) == set()
    assert result.facts.get("undecidable", set()) == set()


def test_objective_without_a_criterion_is_a_violation():
    result = verdict({"objective": [["obj-1"]]})
    assert ("scenario/objective_has_criterion", "obj-1") in result.facts["violation"]


def test_objective_with_no_mapped_inject_is_a_violation():
    facts = dict(DOCUMENTED, assessment_maps=[])
    result = verdict(facts)
    assert ("scenario/objective_has_inject", "obj-1") in result.facts["violation"]


def test_inject_target_missing_from_the_sdl_is_a_violation():
    facts = dict(DOCUMENTED, inject_target=[["inj-1", "ghost-host"]])
    result = verdict(facts)
    assert ("scenario/inject_target_exists", "inj-1") in result.facts["violation"]
```

- [ ] **Step 6: Run them and watch them fail**

Run: `python3 -m pytest tests/datalog-verification/test_rules_scenario.py -q`
Expected: 5 failed, each with `FileNotFoundError: .../scenario_integrity.dl`.

- [ ] **Step 7: Write `scenario_integrity.dl`**

```
# Scenario integrity: the exercise documents must hang together, and must
# exist at all. An empty objective set means the documents were not supplied
# — UNDECIDABLE. Treating that as PASS would certify an exercise with no
# objectives.

check("scenario/documents_present").
undecidable("scenario/documents_present", "no exercise documents were provided") :-
    not has_objective().
has_objective() :- objective(O).

check("scenario/objective_has_criterion").
violation("scenario/objective_has_criterion", O) :- objective(O), not has_criterion(O).
has_criterion(O) :- criterion(C, O).

check("scenario/objective_has_inject").
violation("scenario/objective_has_inject", O) :- objective(O), not has_inject(O).
has_inject(O) :- inject_for(O, I).
inject_for(O, I) :- criterion(C, O), assessment_maps(C, I), inject(I).

check("scenario/inject_target_exists").
violation("scenario/inject_target_exists", I) :-
    inject(I), inject_target(I, T), not known_entity(T).
known_entity(X) :- node(X, T).
known_entity(X) :- feature(X, T).
```

Note the `undecidable` head spans two lines. The tokenizer treats newlines as whitespace, so a rule may wrap — that is worth an assertion of its own, and the test above already relies on it.

- [ ] **Step 8: Run the scenario tests**

Run: `python3 -m pytest tests/datalog-verification/test_rules_scenario.py -q`
Expected: 5 passed.

- [ ] **Step 9: Commit**

```bash
git add skills/datalog-verification/references/rules tests/datalog-verification/test_rules_structural.py tests/datalog-verification/test_rules_scenario.py
git commit -m "Add structural and scenario-integrity rule packs

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 4: Classification and artefact-integrity rule packs

**Files:**
- Create: `skills/datalog-verification/references/rules/classification.dl`
- Create: `skills/datalog-verification/references/rules/artefact_integrity.dl`
- Test: `tests/datalog-verification/test_rules_classification.py`
- Test: `tests/datalog-verification/test_rules_artefact.py`

**Interfaces:**
- Consumes: engine and fact names as in Task 3; `!=` filters from Task 1.
- Produces: `classification/2` and `allowed/2` are the fact names slice 5 reads; `manifest_declares/2` and `pattern_hit/2` are the names slice 3's extractor must supply.

- [ ] **Step 1: Write the failing classification tests**

```python
# tests/datalog-verification/test_rules_classification.py
import os
import sys

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../skills/datalog-verification/scripts")
))

from datalog import evaluate, parse_facts, parse_program  # noqa: E402

RULES = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "../../skills/datalog-verification/references/rules"
))


def verdict(facts):
    with open(os.path.join(RULES, "classification.dl")) as handle:
        rules = parse_program(handle.read(), source="classification.dl")
    return evaluate(rules, parse_facts(facts))


TWO_ZONES = {
    "node": [["web01", "VM"], ["db01", "VM"]],
    "edge": [["web01", "links", "db01"]],
    "classification": [["web01", "public"], ["db01", "restricted"]],
    "allowed": [["public", "restricted"]],
}


def test_classified_nodes_with_an_allowed_crossing_pass():
    result = verdict(TWO_ZONES)
    assert result.facts.get("violation", set()) == set()


def test_unclassified_node_is_a_violation():
    facts = dict(TWO_ZONES, classification=[["web01", "public"]])
    result = verdict(facts)
    assert ("classification/host_has_classification", "db01") in result.facts["violation"]


def test_crossing_between_levels_without_an_allowance_is_a_violation():
    facts = dict(TWO_ZONES, allowed=[])
    result = verdict(facts)
    assert ("classification/cross_zone_edge_allowed", "web01") in result.facts["violation"]


def test_explicit_allowance_clears_the_crossing():
    facts = dict(TWO_ZONES, allowed=[["public", "restricted"]])
    result = verdict(facts)
    assert ("classification/cross_zone_edge_allowed", "web01") not in result.facts["violation"]


def test_edge_with_one_unclassified_end_is_undecidable():
    facts = dict(TWO_ZONES, classification=[["web01", "public"]])
    result = verdict(facts)
    assert any(row[0] == "classification/cross_zone_edge_allowed" and row[1] == "db01"
               for row in result.facts["undecidable"])
```

- [ ] **Step 2: Run them and watch them fail**

Run: `python3 -m pytest tests/datalog-verification/test_rules_classification.py -q`
Expected: 5 failed on the missing `classification.dl`.

- [ ] **Step 3: Write `classification.dl`**

```
# Classification: a node with no level cannot be assessed, and a link that
# crosses levels is only acceptable when the exercise says so.

check("classification/host_has_classification").
# `not classification(N, L)` would leave L bound nowhere; the engine rejects
# that as unsafe negation. `classified/1` is the existential form.
violation("classification/host_has_classification", N) :-
    node(N, T), not classified(N).
classified(N) :- classification(N, L).

check("classification/cross_zone_edge_allowed").
# Only node-to-node edges are crossings; a service has no level of its own.
undecidable("classification/cross_zone_edge_allowed", B) :-
    edge(A, R, B), node(A, NA), node(B, NB), classified(A), not classified(B).
undecidable("classification/cross_zone_edge_allowed", A) :-
    edge(A, R, B), node(A, NA), node(B, NB), classified(B), not classified(A).
violation("classification/cross_zone_edge_allowed", A) :-
    edge(A, R, B), node(A, NA), node(B, NB), classification(A, CA),
    classification(B, CB), CA != CB, not allowed(CA, CB).
```

- [ ] **Step 4: Run the classification tests**

Run: `python3 -m pytest tests/datalog-verification/test_rules_classification.py -q`
Expected: 5 passed.

- [ ] **Step 5: Write the failing artefact tests**

```python
# tests/datalog-verification/test_rules_artefact.py
import os
import sys

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../skills/datalog-verification/scripts")
))

from datalog import evaluate, parse_facts, parse_program  # noqa: E402

RULES = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "../../skills/datalog-verification/references/rules"
))


def verdict(facts):
    with open(os.path.join(RULES, "artefact_integrity.dl")) as handle:
        rules = parse_program(handle.read(), source="artefact_integrity.dl")
    return evaluate(rules, parse_facts(facts))


def test_declared_dependency_without_manifest_facts_is_undecidable():
    result = verdict({"edge": [["nginx_svc", "depends_on", "cert_svc"]]})
    assert ("artefact/declared_dependency_present", "nginx_svc") in result.facts["undecidable"]


def test_dependency_missing_from_the_manifest_is_a_violation():
    result = verdict({
        "edge": [["nginx_svc", "depends_on", "cert_svc"]],
        "manifest_declares": [["nginx_svc", "openssl"]],
    })
    assert ("artefact/declared_dependency_present", "nginx_svc") in result.facts["violation"]


def test_dependency_declared_in_the_manifest_passes():
    result = verdict({
        "edge": [["nginx_svc", "depends_on", "cert_svc"]],
        "manifest_declares": [["nginx_svc", "cert_svc"]],
    })
    assert result.facts.get("violation", set()) == set()
    assert result.facts.get("undecidable", set()) == set()


def test_private_key_material_is_a_violation():
    result = verdict({"pattern_hit": [["content/site.yaml", "private_key"]]})
    assert ("artefact/no_secret_material", "content/site.yaml") in result.facts["violation"]


def test_cloud_credential_material_is_a_violation():
    result = verdict({"pattern_hit": [["content/provision.sh", "cloud_credential"]]})
    assert ("artefact/no_secret_material", "content/provision.sh") in result.facts["violation"]
```

- [ ] **Step 6: Run them and watch them fail**

Run: `python3 -m pytest tests/datalog-verification/test_rules_artefact.py -q`
Expected: 5 failed on the missing `artefact_integrity.dl`.

- [ ] **Step 7: Write `artefact_integrity.dl`**

```
# Artefact integrity. The manifest facts come from slice 3's Deputy extractor;
# until it runs, a dependency check is UNDECIDABLE rather than PASS.

check("artefact/declared_dependency_present").
undecidable("artefact/declared_dependency_present", P) :-
    edge(P, "depends_on", D), not manifest_known(P).
manifest_known(P) :- manifest_declares(P, D).
violation("artefact/declared_dependency_present", P) :-
    edge(P, "depends_on", D), manifest_known(P), not manifest_declares(P, D).

check("artefact/no_secret_material").
violation("artefact/no_secret_material", F) :- pattern_hit(F, "private_key").
violation("artefact/no_secret_material", F) :- pattern_hit(F, "cloud_credential").
```

- [ ] **Step 8: Run the artefact tests**

Run: `python3 -m pytest tests/datalog-verification/test_rules_artefact.py -q`
Expected: 5 passed.

- [ ] **Step 9: Commit**

```bash
git add skills/datalog-verification/references/rules tests/datalog-verification/test_rules_classification.py tests/datalog-verification/test_rules_artefact.py
git commit -m "Add classification and artefact-integrity rule packs

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 5: The verification CLI and its traceability table

**Files:**
- Create: `skills/datalog-verification/scripts/verify.py`
- Test: `tests/datalog-verification/test_verify_cli.py`
- Fixture: `tests/datalog-verification/fixtures/violation-facts.json`
- Fixture: `tests/datalog-verification/fixtures/golden-verdicts.json`

**Interfaces:**
- Consumes: `evaluate`, `parse_program`, `parse_facts` (Task 1); `merge` (Task 2); all four packs (Tasks 3–4).
- Produces: `python3 verify.py FACTS… [--rules DIR] [--json]`, exit `0` all PASS, `1` any VIOLATION, `2` any UNKNOWN; and `load_rules(path)`, `run(facts, rules) -> list[(id, status, evidence)]`, `render(rows) -> str` for later slices to call instead of shelling out.

- [ ] **Step 1: Write the failing CLI tests**

```python
# tests/datalog-verification/test_verify_cli.py
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "../.."))
CLI = os.path.join(REPO, "skills/datalog-verification/scripts/verify.py")
RULES = os.path.join(REPO, "skills/datalog-verification/references/rules")
FIXTURES = os.path.join(HERE, "fixtures")


def run(*facts, rules=RULES):
    return subprocess.run(
        [sys.executable, CLI, *facts, "--rules", rules],
        cwd=REPO, capture_output=True, text=True,
    )


def write(tmp_path, name, payload):
    path = tmp_path / name
    path.write_text(json.dumps(payload))
    return str(path)


def test_all_pass_exits_zero(tmp_path):
    facts = write(tmp_path, "clean.json", {
        "node": [["web01", "VM"], ["dmz", "Switch"]],
        "feature": [["nginx_svc", "service"]],
        "edge": [["web01", "has_feature", "nginx_svc"],
                 ["web01", "links", "dmz"]],
        "source": [["web01", "ubuntu22"]],
        "registry_package": [["ubuntu22", "public"]],
        "objective": [["obj-1"]],
        "criterion": [["crit-1", "obj-1"]],
        "inject": [["inj-1"]],
        "inject_target": [["inj-1", "web01"]],
        "assessment_maps": [["crit-1", "inj-1"]],
        "classification": [["web01", "public"], ["dmz", "public"]],
        "manifest_declares": [["nginx_svc", "cert_svc"]],
    })
    result = run(facts)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "**Verdict: PASS**" in result.stdout


def test_a_violation_exits_one(tmp_path):
    facts = write(tmp_path, "orphan.json", {"node": [["lonely", "VM"]]})
    result = run(facts)
    assert result.returncode == 1
    assert "VIOLATION" in result.stdout


def test_missing_manifest_facts_exit_two(tmp_path):
    facts = write(tmp_path, "unknown.json", {
        "node": [["web01", "VM"], ["db01", "VM"]],
        "edge": [["web01", "links", "db01"], ["web01", "depends_on", "db01"]],
        "source": [["web01", "ubuntu22"]],
        "registry_package": [["ubuntu22", "public"]],
        "objective": [["obj-1"]],
        "criterion": [["crit-1", "obj-1"]],
        "inject": [["inj-1"]],
        "inject_target": [["inj-1", "web01"]],
        "assessment_maps": [["crit-1", "inj-1"]],
        "classification": [["web01", "public"], ["db01", "public"]],
    })
    result = run(facts)
    assert result.returncode == 2, result.stdout
    assert "UNKNOWN" in result.stdout


def test_several_fact_files_are_merged(tmp_path):
    first = write(tmp_path, "a.json", {"node": [["web01", "VM"], ["dmz", "Switch"]]})
    second = write(tmp_path, "b.json", {"edge": [["web01", "links", "dmz"]]})
    result = run(first, second)
    line = next(row for row in result.stdout.splitlines() if "no_orphan_nodes" in row)
    assert "PASS" in line


def test_statuses_match_the_golden_file():
    with open(os.path.join(FIXTURES, "golden-verdicts.json")) as handle:
        golden = json.load(handle)
    result = run(os.path.join(FIXTURES, "violation-facts.json"))
    statuses = {}
    for line in result.stdout.splitlines():
        if line.startswith("| `"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            statuses[cells[0].strip("`")] = cells[1]
    assert statuses == golden


def test_rule_directory_without_packs_fails_loudly(tmp_path):
    empty = tmp_path / "rules"
    empty.mkdir()
    result = run(os.path.join(FIXTURES, "violation-facts.json"), rules=str(empty))
    assert result.returncode == 3
    assert "no .dl files" in result.stderr
```

- [ ] **Step 2: Run them and watch them fail**

Run: `python3 -m pytest tests/datalog-verification/test_verify_cli.py -q`
Expected: errors on `can't open file .../verify.py`.

- [ ] **Step 3: Write `verify.py`**

```python
#!/usr/bin/env python3
"""Evaluate facts against the rule packs and print a traceability table.

Exit codes: 0 every check PASS, 1 at least one VIOLATION, 2 at least one
UNKNOWN and no VIOLATION, 3 the run itself failed (bad rules, bad JSON).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datalog import DatalogError, evaluate, parse_facts, parse_program
from facts import merge

PASS, VIOLATION, UNKNOWN = "PASS", "VIOLATION", "UNKNOWN"

DEFAULT_RULES = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "references", "rules"
))


def load_rules(path):
    if os.path.isdir(path):
        paths = sorted(glob.glob(os.path.join(path, "*.dl")))
        if not paths:
            raise DatalogError("no .dl files in %s" % path)
    else:
        paths = [path]
    rules = []
    for filename in paths:
        with open(filename) as handle:
            rules.extend(parse_program(handle.read(), source=os.path.basename(filename)))
    return rules


def load_facts(paths):
    merged = {}
    for path in paths:
        with open(path) as handle:
            merged = merge(merged, json.load(handle))
    return merged


def _atom(row):
    return "%s(%s)" % (row[0], ", ".join('"%s"' % value for value in row[1:]))


def run(facts, rules):
    result = evaluate(rules, parse_facts(facts))
    rows = []
    for (rule_id,) in sorted(result.facts.get("check", ())):
        violations = sorted(
            row for row in result.facts.get("violation", ()) if row[0] == rule_id
        )
        unknown = sorted(
            row for row in result.facts.get("undecidable", ()) if row[0] == rule_id
        )
        if violations:
            rows.append((rule_id, VIOLATION, [_atom(row) for row in violations]))
        elif unknown:
            rows.append((rule_id, UNKNOWN, [_atom(row) for row in unknown]))
        else:
            rows.append((rule_id, PASS, []))
    return rows


def overall(rows):
    if any(status == VIOLATION for _, status, _ in rows):
        return VIOLATION
    if any(status == UNKNOWN for _, status, _ in rows):
        return UNKNOWN
    return PASS


def render(rows):
    lines = ["| Check | Verdict | Evidence |", "|---|---|---|"]
    for rule_id, status, evidence in rows:
        lines.append("| `%s` | %s | %s |" % (rule_id, status, "<br>".join(evidence) or "—"))
    counts = {status: 0 for status in (PASS, VIOLATION, UNKNOWN)}
    for _, status, _ in rows:
        counts[status] += 1
    lines.append("")
    lines.append("**Verdict: %s** — %d pass, %d violation, %d unknown" % (
        overall(rows), counts[PASS], counts[VIOLATION], counts[UNKNOWN]))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("facts", nargs="+", help="facts JSON files")
    parser.add_argument("--rules", default=DEFAULT_RULES, help="a .dl file or a directory")
    parser.add_argument("--json", action="store_true", help="emit rows as JSON")
    args = parser.parse_args(argv)

    try:
        rows = run(load_facts(args.facts), load_rules(args.rules))
    except (DatalogError, OSError, ValueError) as error:
        print("verify: %s" % error, file=sys.stderr)
        return 3

    if args.json:
        print(json.dumps([
            {"check": rule_id, "verdict": status, "evidence": evidence}
            for rule_id, status, evidence in rows
        ], indent=2))
    else:
        print(render(rows))

    verdict = overall(rows)
    return {PASS: 0, VIOLATION: 1, UNKNOWN: 2}[verdict]


if __name__ == "__main__":
    sys.exit(main())
```

One trap in the test above: `run()` shadows pytest's own helper name, and `test_all_pass_exits_zero` expects `manifest_declares` present for `nginx_svc` because `nginx_svc` has no `depends_on` edge — so the artefact check has no subject and passes. Add the edge only where the test wants it; the clean fixture deliberately has none.

- [ ] **Step 4: Write `violation-facts.json`**

```json
{
  "node": [["web01", "VM"], ["dmz", "Switch"], ["db01", "VM"]],
  "feature": [["nginx_svc", "service"], ["cert_svc", "configuration"]],
  "edge": [
    ["web01", "has_feature", "nginx_svc"],
    ["web01", "has_feature", "cert_svc"],
    ["web01", "links", "dmz"],
    ["db01", "links", "web01"],
    ["nginx_svc", "depends_on", "cert_svc"]
  ],
  "source": [["web01", "ubuntu22"]],
  "registry_package": [["ubuntu22", "public"]],
  "objective": [["obj-1"], ["obj-2"]],
  "criterion": [["crit-1", "obj-1"], ["crit-2", "obj-2"]],
  "inject": [["inj-1"]],
  "inject_target": [["inj-1", "ghost-host"]],
  "assessment_maps": [["crit-1", "inj-1"]],
  "classification": [["web01", "public"], ["db01", "restricted"]],
  "pattern_hit": [["content/site.yaml", "private_key"]]
}
```

- [ ] **Step 5: Write `golden-verdicts.json`**

The expected status of every check for that fixture, worked through by hand — `obj-2` has no mapped inject, `inj-1` targets a host the SDL does not define, `db01` and `web01` sit on different levels with no allowance, `nginx_svc` declares a dependency with no manifest facts, and one file carries key material:

```json
{
  "artefact/declared_dependency_present": "UNKNOWN",
  "artefact/no_secret_material": "VIOLATION",
  "classification/cross_zone_edge_allowed": "VIOLATION",
  "classification/host_has_classification": "VIOLATION",
  "scenario/documents_present": "PASS",
  "scenario/inject_target_exists": "VIOLATION",
  "scenario/objective_has_criterion": "PASS",
  "scenario/objective_has_inject": "VIOLATION",
  "structural/dependencies_acyclic": "PASS",
  "structural/no_orphan_nodes": "PASS",
  "structural/service_has_host": "PASS",
  "structural/source_resolves": "PASS"
}
```

- [ ] **Step 6: Run the CLI tests**

Run: `python3 -m pytest tests/datalog-verification/test_verify_cli.py -q`
Expected: 7 passed.

If a status differs from the golden file, the fixture and the golden disagree about the scenario, not about the engine — decide which is wrong, fix it, and ledger the correction rather than editing the assertion to match.

- [ ] **Step 7: Commit**

```bash
git add skills/datalog-verification/scripts/verify.py tests/datalog-verification/test_verify_cli.py tests/datalog-verification/fixtures/violation-facts.json tests/datalog-verification/fixtures/golden-verdicts.json
git commit -m "Add the verification CLI and its traceability table

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 6: Provisioning detection

**Files:**
- Create: `skills/datalog-verification/scripts/provisioning.py`
- Test: `tests/datalog-verification/test_provisioning.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `check_sdl_parser() -> (status, detail)` and `check_deputy() -> (status, detail)`, status in `{"PASS", "UNKNOWN"}`, detail carrying the install command on `UNKNOWN`; `report() -> list[(name, status, detail)]`; `python3 provisioning.py` prints the table.

- [ ] **Step 1: Write the failing tests**

```python
# tests/datalog-verification/test_provisioning.py
import os
import sys
import types

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../skills/datalog-verification/scripts")
))

import provisioning  # noqa: E402


def test_missing_parser_is_unknown_with_an_install_command(monkeypatch):
    def missing(name):
        raise ImportError("No module named 'sdl_parser'")
    monkeypatch.setattr(provisioning.importlib, "import_module", missing)
    status, detail = provisioning.check_sdl_parser()
    assert status == "UNKNOWN"
    assert "apt install libsdl-parser" in detail


def test_shared_library_load_failure_is_unknown_not_a_crash(monkeypatch):
    def missing(name):
        raise OSError("libsdl_parser.so: cannot open shared object file")
    monkeypatch.setattr(provisioning.importlib, "import_module", missing)
    status, detail = provisioning.check_sdl_parser()
    assert status == "UNKNOWN"
    assert "libsdl_parser.so" in detail


def test_importable_parser_passes(monkeypatch):
    module = types.SimpleNamespace(__version__="0.3.0")
    monkeypatch.setattr(provisioning.importlib, "import_module", lambda name: module)
    status, detail = provisioning.check_sdl_parser()
    assert status == "PASS"
    assert "0.3.0" in detail


def test_missing_deputy_is_unknown(monkeypatch):
    monkeypatch.setattr(provisioning.shutil, "which", lambda name: None)
    status, detail = provisioning.check_deputy()
    assert status == "UNKNOWN"
    assert "deputy" in detail


def test_present_deputy_passes(monkeypatch):
    monkeypatch.setattr(provisioning.shutil, "which",
                        lambda name: "/usr/local/bin/deputy")
    assert provisioning.check_deputy()[0] == "PASS"


def test_report_names_both_tools(monkeypatch):
    monkeypatch.setattr(provisioning.shutil, "which", lambda name: None)
    monkeypatch.setattr(provisioning.importlib, "import_module",
                        lambda name: (_ for _ in ()).throw(ImportError("absent")))
    names = [row[0] for row in provisioning.report()]
    assert names == ["sdl_parser", "deputy"]
```

- [ ] **Step 2: Run them and watch them fail**

Run: `python3 -m pytest tests/datalog-verification/test_provisioning.py -q`
Expected: `ModuleNotFoundError: No module named 'provisioning'`.

- [ ] **Step 3: Write `provisioning.py`**

```python
#!/usr/bin/env python3
"""Report which verification tools are present.

`sdl_parser` is a ctypes wrapper around a Rust shared library, so importing
it raises when the library is missing — detection has to catch the import,
not look for a filename. A missing tool is UNKNOWN with an install command;
it is never a traceback (spec §2.4).
"""
from __future__ import annotations

import importlib
import shutil

PASS, UNKNOWN = "PASS", "UNKNOWN"

SDL_INSTALL = (
    "sudo apt install libsdl-parser, then pip install <sdl-parser repo>/python-package"
)


def check_sdl_parser():
    try:
        module = importlib.import_module("sdl_parser")
    except Exception as error:  # ImportError, or OSError from ctypes on load
        return UNKNOWN, "sdl_parser is not importable (%s). Install: %s" % (error, SDL_INSTALL)
    return PASS, "sdl_parser %s" % getattr(module, "__version__", "loaded")


def check_deputy():
    path = shutil.which("deputy")
    if path is None:
        return UNKNOWN, "deputy is not on PATH. Install it from the Deputy release page"
    return PASS, path


def report():
    return [
        ("sdl_parser",) + check_sdl_parser(),
        ("deputy",) + check_deputy(),
    ]


def main():
    for name, status, detail in report():
        print("%-10s %-8s %s" % (name, status, detail))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests**

Run: `python3 -m pytest tests/datalog-verification/test_provisioning.py -q`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/datalog-verification/scripts/provisioning.py tests/datalog-verification/test_provisioning.py
git commit -m "Detect the parser and Deputy without crashing when absent

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 7: The `sdl-authoring` skill

**Files:**
- Create: `skills/sdl-authoring/SKILL.md`
- Create: `skills/sdl-authoring/references/sdl-grammar.md`
- Create: `skills/sdl-authoring/scripts/validate.py`
- Test: `tests/sdl-authoring/test-skill-structure.sh`
- Test: `tests/sdl-authoring/test_validate.py`

**Interfaces:**
- Consumes: `sdl_parser.parse_sdl(str) -> dict`, `sdl_parser.SDLLibraryParsingError` with `.message`.
- Produces: `validate(path, parser=None) -> (code, message)` with code `0` valid, `1` parse failure, `2` parser unavailable; `python3 validate.py FILE`.

- [ ] **Step 1: Write the failing validator tests**

```python
# tests/sdl-authoring/test_validate.py
import os
import sys

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../skills/sdl-authoring/scripts")
))

from validate import validate  # noqa: E402


class FakeParser:
    class SDLLibraryParsingError(Exception):
        def __init__(self, message):
            super().__init__(message)
            self.message = message

    def __init__(self, result=None, error=None):
        self.result = result or {"name": "hospital-ransomware"}
        self.error = error

    def parse_sdl(self, text):
        if self.error:
            raise self.SDLLibraryParsingError(self.error)
        return self.result


def write(tmp_path, text):
    path = tmp_path / "scenario.sdl"
    path.write_text(text)
    return str(path)


def test_valid_file_reports_its_name(tmp_path):
    code, message = validate(write(tmp_path, "name: hospital-ransomware\n"), FakeParser())
    assert code == 0
    assert "hospital-ransomware" in message


def test_parse_failure_reports_the_parser_message_verbatim(tmp_path):
    code, message = validate(
        write(tmp_path, "name: x\n"),
        FakeParser(error="error parsing field `nodes`: invalid type: found sequence"),
    )
    assert code == 1
    assert "error parsing field `nodes`: invalid type: found sequence" in message


def test_parse_failure_message_carries_the_file_path(tmp_path):
    path = write(tmp_path, "name: x\n")
    _, message = validate(path, FakeParser(error="missing field `name`"))
    assert path in message


def test_missing_parser_is_unknown_with_install_steps(tmp_path, monkeypatch):
    import validate as module

    def missing(name):
        raise ImportError("No module named 'sdl_parser'")

    monkeypatch.setattr(module.importlib, "import_module", missing)
    code, message = validate(write(tmp_path, "name: x\n"))
    assert code == 2
    assert "UNKNOWN" in message
    assert "apt install libsdl-parser" in message
```

- [ ] **Step 2: Run them and watch them fail**

Run: `python3 -m pytest tests/sdl-authoring/test_validate.py -q`
Expected: `ModuleNotFoundError: No module named 'validate'`.

- [ ] **Step 3: Write `validate.py`**

```python
#!/usr/bin/env python3
"""Validate an SDL file, or say why it cannot be validated.

The parser reports one exception, SDLLibraryParsingError, whose `.message`
is the only field — there is no line number. Quote it verbatim and let the
author find the construct; never invent a position.
"""
from __future__ import annotations

import argparse
import importlib
import sys


def _parser():
    return importlib.import_module("sdl_parser")


def validate(path, parser=None):
    if parser is None:
        try:
            parser = _parser()
        except Exception as error:  # ImportError, or OSError from ctypes on load
            return 2, (
                "UNKNOWN %s: sdl_parser is not importable (%s). Install: "
                "sudo apt install libsdl-parser, then pip install "
                "<sdl-parser repo>/python-package" % (path, error)
            )
    with open(path) as handle:
        text = handle.read()
    try:
        scenario = parser.parse_sdl(text)
    except parser.SDLLibraryParsingError as error:
        return 1, "FAIL %s: %s" % (path, error.message)
    name = (scenario or {}).get("name") or "<unnamed>"
    return 0, "PASS %s: %s" % (path, name)


def main(argv=None):
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("path")
    parsed = args.parse_args(argv)
    code, message = validate(parsed.path)
    print(message)
    return code


if __name__ == "__main__":
    sys.exit(main())
```

`test_missing_parser_is_unknown_with_install_steps` monkeypatches `validate.importlib.import_module`; `_parser()` must call it through the module attribute, which it does.

- [ ] **Step 4: Run the validator tests**

Run: `python3 -m pytest tests/sdl-authoring/test_validate.py -q`
Expected: 4 passed.

- [ ] **Step 5: Write `references/sdl-grammar.md`**

```markdown
# The SDL schema

SDL is a YAML document. `sdl_parser.parse_sdl(text)` returns it as a plain
dictionary; sections that are absent come back as `None`.

## Top level

`name` is the only required key. The parser accepts, in addition:
`description`, `nodes`, `features`, `infrastructure`, `conditions`,
`vulnerabilities`, `metrics`, `evaluations`, `tlos`, `entities`, `goals`,
`injects`, `events`, `scripts`, `stories`.

The smallest valid document is one line:

```yaml
name: test-scenario
```

## The sections this plugin's rules read

| Section | Shape | Becomes |
|---|---|---|
| `nodes.<name>` | `type`, `source`, `features`, `injects`, `conditions` | `node/2`, `source/2`, `edge/3` |
| `features.<name>` | `type`, `source`, `dependencies` | `feature/2`, `edge/3` |
| `infrastructure.<name>` | `links`, `dependencies` | `edge/3` |

`nodes.<n>.features`, `.injects` and `.conditions` are maps of
`target: role-name`. `features.<f>.dependencies` and
`infrastructure.<n>.links` are lists of names. A package reference is either
a name or a `{name, version}` map.

## What the parser guarantees

- YAML validity, and that every name referenced by `links`, `dependencies`,
  `features`, `injects` and `conditions` is defined. A dangling reference is
  a parse error, not a warning.
- Nothing else. It does not check that a service has a host, that a node is
  connected, or that dependencies are acyclic — that is what
  `datalog-verification` is for.

## Errors

One exception: `SDLLibraryParsingError`, with a `.message` and nothing else.
No line, no column, no path. The message names the failing field when it can.

## Installing the parser

`import sdl_parser` loads `libsdl_parser` with `ctypes` at import time, so it
fails at import when the shared library is absent:

```bash
sudo apt install libsdl-parser
pip install <sdl-parser repo>/python-package
```
```

- [ ] **Step 6: Write `skills/sdl-authoring/SKILL.md`**

````markdown
---
name: sdl-authoring
description: Use when writing or editing a Scenario Definition Language (.sdl) document for a cyber range — nodes, services, features, infrastructure links and dependencies — or when a range's topology has to be expressed and validated
---

# SDL Authoring

You are authoring the scenario definition: the machine-readable topology of
the range. One document per scenario, YAML, validated by the parser before
you hand it on.

## What this produces

`sdl/<scenario>.sdl` — the scenario's nodes, features and infrastructure.
Find where the project keeps scenario files first; if there is no such
directory, ask before creating one.

## The document

`name` is the only required key. Everything else is optional and may be
absent. Read `references/sdl-grammar.md` for the section shapes before you
write a field you have not used.

Start from the smallest thing that describes the range and grow it:

```yaml
name: hospital-ransomware
description: Hospital network under ransomware pressure

nodes:
  ehr01:
    type: VM
    source: ubuntu22
    features:
      ehr_svc: default
  fwsrv:
    type: Switch

features:
  ehr_svc:
    type: service
    dependencies: [auth_svc]
  auth_svc:
    type: configuration

infrastructure:
  ehr01:
    count: 1
    links: [fwsrv]
```

## Rules of authorship

1. **Names are stable.** Inject targets, assessment maps and evaluation
   scripts refer to node and feature names. Renaming one after an exercise
   is written breaks them silently; rename first, then search the exercise
   for the old name.
2. **Every service gets a host.** A feature with no node that lists it is a
   service that exists nowhere.
3. **Link what talks.** `links` is how you say two hosts reach each other;
   leaving it out makes every node look stranded.
4. **Dependencies point down the stack.** `ehr_svc` depends on `auth_svc`,
   not the other way round, and never in a cycle.
5. **No secrets, no real hostnames, no customer data.** The SDL is an
   exercise artefact and may be shared at the exercise's classification.
6. **Do not invent a field.** If the schema you have does not express what
   you need, say so; an unknown section is either rejected or ignored, and
   an ignored one is worse.

## Validate before you hand off

```bash
python3 scripts/validate.py sdl/<scenario>.sdl
```

- `PASS` — the parser accepted it. That means the YAML is well formed and
  every reference resolves. It does not mean the scenario is sensible.
- `FAIL` — the parser's message, verbatim. It has no line number; read the
  field it names and look there. Fix one error at a time — the parser
  reports the first failure and stops.
- `UNKNOWN` — the parser is not installed. Give your human partner the
  install command the message carries; do not hand-write YAML and claim it
  is validated.

## Red flags

| Thought | Reality |
|---|---|
| "The parser accepted it, so the scenario is sound" | Syntax and referential closure only. Run `datalog-verification` for the rest. |
| "I'll add the nodes later, the shape is what matters" | A scenario with no nodes validates and describes nothing. |
| "This field probably exists" | Unknown keys are ignored or rejected. Check the grammar reference. |
| "I'll rename the node, it's clearer" | Inject targets and assessment maps refer to it by name. Rename everywhere or not at all. |
| "I'll put the real hostname in, it's internal" | The SDL outlives the exercise and gets shared. Use invented names. |

## Handoff

A validated SDL goes to `datalog-verification` with the exercise documents,
then to the development phase. An SDL that validates but fails the
structural rules is not ready: fix the graph, not the rules.
````

- [ ] **Step 7: Write the failing structural test**

```bash
#!/usr/bin/env bash
# The router matches on the description, and the validator path in the skill
# is what a reader runs. Pin both, plus the sections a reader needs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SKILL="$REPO_ROOT/skills/sdl-authoring/SKILL.md"

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
    echo "  [FAIL] skills/sdl-authoring/SKILL.md does not exist"
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

check "name: sdl-authoring" "frontmatter names the skill"
check "references/sdl-grammar.md" "points at the grammar reference"
check "scripts/validate.py" "names the validator to run"
check "apt install libsdl-parser" "carries the install command for the UNKNOWN path"

for section in "## What this produces" "## Rules of authorship" \
               "## Validate before you hand off" "## Red flags" "## Handoff"; do
    check "$section" "has section: $section"
done

description="$(grep -m1 '^description:' "$SKILL" || true)"
if printf '%s' "$description" | grep -qiE 'sdl|scenario definition'; then
    echo "  [PASS] description carries the SDL trigger"
else
    echo "  [FAIL] description must name SDL (routing depends on it)"
    failures=$((failures + 1))
fi

if [ "$failures" -gt 0 ]; then
    echo "STATUS: FAILED ($failures failure(s))"
    exit 1
fi

echo "STATUS: PASSED"
```

Save as `tests/sdl-authoring/test-skill-structure.sh`, then `chmod +x` it.

- [ ] **Step 8: Run it**

Run: `bash tests/sdl-authoring/test-skill-structure.sh`
Expected: `STATUS: PASSED`. This gate is written after the prose it checks — the RED for this task came from the validator tests in Steps 1–4. If it fails, the skill is missing a section the test names; fix the skill, not the test.

- [ ] **Step 9: Commit**

```bash
git add skills/sdl-authoring tests/sdl-authoring
git commit -m "Add the sdl-authoring skill and its validator

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 8: The `datalog-verification` skill, trigger fixtures, and inventory

**Files:**
- Create: `skills/datalog-verification/SKILL.md`
- Create: `skills/datalog-verification/references/rules.md`
- Test: `tests/datalog-verification/test-skill-structure.sh`
- Create: `tests/explicit-skill-requests/prompts/please-use-sdl-authoring.txt`
- Create: `tests/explicit-skill-requests/prompts/please-use-datalog-verification.txt`
- Modify: `tests/explicit-skill-requests/run-all.sh`

**Interfaces:**
- Consumes: everything from Tasks 1–7.
- Produces: the two skills the router can reach by name; a rule-author guide at `references/rules.md`.

- [ ] **Step 1: Write the failing structural test**

```bash
#!/usr/bin/env bash
# Pin the parts of the skill other skills and fixtures depend on: the name the
# router matches, the CLI it tells the reader to run, and the verdict words.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SKILL="$REPO_ROOT/skills/datalog-verification/SKILL.md"

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
    echo "  [FAIL] skills/datalog-verification/SKILL.md does not exist"
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

check "name: datalog-verification" "frontmatter names the skill"
check "scripts/verify.py" "names the CLI to run"
check "references/rules" "points at the rule packs"
check "PASS" "names the passing verdict"
check "VIOLATION" "names the failing verdict"
check "UNKNOWN" "names the undecidable verdict"

for section in "## What this produces" "## Facts" "## Running it" \
               "## Reading the verdicts" "## Red flags" "## Handoff"; do
    check "$section" "has section: $section"
done

description="$(grep -m1 '^description:' "$SKILL" || true)"
if printf '%s' "$description" | grep -qiE 'verif|datalog|rule'; then
    echo "  [PASS] description carries the verification trigger"
else
    echo "  [FAIL] description must name verification (routing depends on it)"
    failures=$((failures + 1))
fi

if [ "$failures" -gt 0 ]; then
    echo "STATUS: FAILED ($failures failure(s))"
    exit 1
fi

echo "STATUS: PASSED"
```

Save as `tests/datalog-verification/test-skill-structure.sh`, `chmod +x`, run it once to watch it fail before writing the skill.

- [ ] **Step 2: Write `skills/datalog-verification/SKILL.md`**

````markdown
---
name: datalog-verification
description: Use when checking a cyber range exercise for integrity — that every service is hosted, the scenario graph is sound, classifications are respected, and the exercise documents agree with the SDL — before development builds against it
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
````

- [ ] **Step 3: Write `references/rules.md`**

````markdown
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
````

- [ ] **Step 4: Run the structural test**

Run: `bash tests/datalog-verification/test-skill-structure.sh`
Expected: `STATUS: PASSED`.

- [ ] **Step 5: Add the trigger fixtures**

```bash
cat > tests/explicit-skill-requests/prompts/please-use-sdl-authoring.txt <<'EOF'
please use the sdl-authoring skill to write an SDL for a two-host ransomware range
EOF
cat > tests/explicit-skill-requests/prompts/please-use-datalog-verification.txt <<'EOF'
please use the datalog-verification skill to check this exercise's SDL against the rules
EOF
```

- [ ] **Step 6: Register them in `run-all.sh`**

Append after Test 6, matching the file's existing shape:

```bash
# Test 7: sdl-authoring is invoked when named
run-test.sh "sdl-authoring" "$PROMPTS_DIR/please-use-sdl-authoring.txt" 5

# Test 8: datalog-verification is invoked when named
run-test.sh "datalog-verification" "$PROMPTS_DIR/please-use-datalog-verification.txt" 5
```

- [ ] **Step 7: Run the registry and the new cases**

```bash
bash tests/explicit-skill-requests/test-fixture-registry.sh
```

Expected: PASSED — it fails in both directions if a prompt file has no case or
a case names a missing file.

Then, with `timeout` on `PATH` (macOS: `brew install coreutils`, or a shim):

```bash
PATH="/tmp/shim-bin:$PATH" bash tests/explicit-skill-requests/run-all.sh
```

Expected: 8 passed, 0 failed.

- [ ] **Step 8: Inventory and docs**

Run:

```bash
bash tests/using-superpowers/test-skill-references.sh
bash tests/docs/run-all.sh 2>/dev/null || ls tests/docs
bash tests/skill-size/test-skill-size.sh
```

If the inventory or docs tests name a missing skill entry, add
`sdl-authoring` and `datalog-verification` to `README.md`'s skill list and to
the `using-superpowers` inventory table, then re-run. Both new `SKILL.md`
files must stay under 20,000 bytes.

- [ ] **Step 9: Commit**

```bash
git add skills/datalog-verification/SKILL.md skills/datalog-verification/references/rules.md tests/datalog-verification/test-skill-structure.sh tests/explicit-skill-requests
git commit -m "Add the datalog-verification skill and trigger fixtures

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage.** §7 facts table → Tasks 2–4 name every predicate and who
extracts it. §7 rule groups (structural, scenario integrity, classification,
artefact integrity) → one pack each, Tasks 3–4. §7 verdicts → Task 5, including
the exit codes and the UNKNOWN precedence over PASS. §7 traceability table →
Task 5's `render` and Task 8's skill. §2.4 provisioning detection → Task 6,
with the ctypes-at-import failure mode pinned by test. §3.2 inventory: both
skills authored, frontmattered, and reachable through trigger fixtures. §9
verification tests: facts JSON → rules → verdicts, golden file, deliberate
violations and an UNKNOWN, per-skill trigger fixture, per-skill structural
test. Slice 3's Deputy extraction is deliberately out of scope; the fact names
it must produce are fixed here.

**Placeholder scan.** No "TBD", no "similar to Task N", every code step carries
the code, every run step carries a command and an expected result. The one
conditional step (Task 8, inventory) is conditional on a test's output rather
than on a guess, and names the files it would touch.

**Type consistency.** `Violation`/`undecidable` are three-argument facts in
every pack and `render`/`run` index `row[0]` only. `check/1`. `load_rules`
returns `list[Rule]` and is used by `run(facts, rules)`. `merge` is defined in
`facts.py` and imported by `verify.py`. `from_sdl` returns the same JSON shape
`parse_facts` consumes. `validate()` and `provisioning.check_sdl_parser()`
return `(code, message)` / `(status, detail)` respectively — deliberately
different shapes, because one is a CLI exit code and the other is a status row.

**Review Focus coverage.** Vacuous pass → `scenario/documents_present`,
`structural/source_resolves`, `artefact/declared_dependency_present`. Recursion
through negation → `test_unstratified_negation_is_an_error_naming_both_predicates`.
Cycle → `test_dependency_cycle_violates_on_every_node_in_the_cycle`. Parse error
without a line number → `test_parse_failure_reports_the_parser_message_verbatim`
and `test_parse_failure_message_carries_the_file_path`. Hand-edited facts →
`test_duplicate_facts_are_deduplicated`, `test_arity_clash_names_the_predicate_and_both_arities`.

