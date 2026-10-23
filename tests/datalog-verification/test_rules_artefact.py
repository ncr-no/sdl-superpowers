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
    assert not any(row[0] == "artefact/declared_dependency_present"
                   for row in result.facts.get("undecidable", set()))


def test_no_scanning_facts_is_undecidable_not_a_pass():
    result = verdict({})
    assert ("artefact/no_secret_material", "no scanning facts were provided") in result.facts["undecidable"]


def test_a_completed_scan_with_no_hits_passes():
    result = verdict({"scan_complete": [["secrets"]]})
    assert result.facts.get("violation", set()) == set()
    assert result.facts.get("undecidable", set()) == set()


def test_private_key_material_is_a_violation():
    result = verdict({"pattern_hit": [["content/site.yaml", "private_key"]]})
    assert ("artefact/no_secret_material", "content/site.yaml") in result.facts["violation"]


def test_cloud_credential_material_is_a_violation():
    result = verdict({"pattern_hit": [["content/provision.sh", "cloud_credential"]]})
    assert ("artefact/no_secret_material", "content/provision.sh") in result.facts["violation"]
