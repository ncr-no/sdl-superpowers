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


def test_no_documents_leaves_every_scenario_check_undecidable():
    result = verdict({})
    ids = {row[0] for row in result.facts["undecidable"]}
    assert ids == {
        "scenario/documents_present",
        "scenario/objective_has_criterion",
        "scenario/objective_has_inject",
        "scenario/inject_target_exists",
    }


def test_injects_without_target_facts_are_undecidable_not_a_vacuous_pass():
    result = verdict({"inject": [["inj-1"]]})
    assert any(row[0] == "scenario/inject_target_exists"
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
