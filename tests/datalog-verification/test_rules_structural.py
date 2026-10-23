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
