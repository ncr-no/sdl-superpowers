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


def test_a_truncated_program_is_a_datalog_error_not_an_index_error():
    with pytest.raises(DatalogError) as excinfo:
        parse_program('x(A) :- a(A', source="broken.dl")
    assert "broken.dl" in str(excinfo.value)


def test_comparing_a_variable_to_a_constant_is_rejected():
    with pytest.raises(DatalogError) as excinfo:
        run('x(A) :- a(A), A != "b".', {"a": [["v"]]})
    assert "!=" in str(excinfo.value)


def test_facts_that_are_not_a_row_list_raise_value_error():
    with pytest.raises(ValueError):
        parse_facts({"node": [1]})
    with pytest.raises(ValueError):
        parse_facts(["node"])
