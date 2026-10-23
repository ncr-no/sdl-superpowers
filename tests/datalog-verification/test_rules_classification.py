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
    assert ("classification/cross_zone_edge_allowed", "web01") not in result.facts.get("violation", set())


def test_edge_with_one_unclassified_end_is_undecidable():
    facts = dict(TWO_ZONES, classification=[["web01", "public"]])
    result = verdict(facts)
    assert any(row[0] == "classification/cross_zone_edge_allowed" and row[1] == "db01"
               for row in result.facts["undecidable"])
