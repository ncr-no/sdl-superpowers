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


def _tok(tokens, i, source, what):
    if i >= len(tokens):
        raise DatalogError("%s: unexpected end of program while reading %s" % (source, what))
    return tokens[i]


def _atom(tokens, i, source, anon):
    kind, pred = _tok(tokens, i, source, "a predicate")
    if kind != "ident":
        raise DatalogError("%s: expected a predicate, found %r" % (source, pred))
    if _tok(tokens, i + 1, source, "the arguments of %r" % pred)[0] != "(":
        raise DatalogError("%s: predicate %r is missing '('" % (source, pred))
    i += 2
    args = []
    while _tok(tokens, i, source, "the arguments of %r" % pred)[0] != ")":
        args.append(_term(tokens[i], anon))
        i += 1
        if _tok(tokens, i, source, "the arguments of %r" % pred)[0] == ",":
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
        if _tok(tokens, i, source, "'.' after %r" % head.pred)[0] == ".":
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
            kind = _tok(tokens, i, source, "a body item for %r" % head.pred)[0]
            if kind == "not":
                atom, i = _atom(tokens, i + 1, source, anon)
                negated.append(atom)
            elif kind == "ident" and i + 1 < len(tokens) and tokens[i + 1][0] == "!=":
                filters.append((_term(tokens[i], anon), _term(tokens[i + 2], anon)))
                i += 3
            else:
                atom, i = _atom(tokens, i, source, anon)
                body.append(atom)
            if _tok(tokens, i, source, "',' or '.' after a body item")[0] == ",":
                i += 1
                continue
            if tokens[i][0] == ".":
                i += 1
                break
            raise DatalogError("%s: expected ',' or '.' after a body item" % source)
        for left, right in filters:
            for operand in (left, right):
                if not isinstance(operand, Var):
                    raise DatalogError(
                        '%s: "!=" compares two variables; %r is a constant' % (source, operand))
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


def validate_facts(data):
    """Reject shapes that would otherwise fail as an unreadable traceback.

    A fact set is `{predicate: [[arg, …], …]}`. Anything else is a malformed
    input file, which the caller reports as a failed run.
    """
    if not isinstance(data, dict):
        raise ValueError("facts must be an object mapping predicate to rows")
    for pred, rows in data.items():
        if not isinstance(rows, (list, tuple)) or isinstance(rows, (str, bytes)):
            raise ValueError("facts for %r must be a list of rows" % (pred,))
        for row in rows:
            if not isinstance(row, (list, tuple)) or isinstance(row, (str, bytes)):
                raise ValueError("every row for %r must be a list of arguments" % (pred,))
    return data


def parse_facts(data):
    facts = {}
    for pred, rows in validate_facts(data).items():
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
            edges[rule.head.pred].add(atom.pred)
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
