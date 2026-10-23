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
        "scan_complete": [["secrets"]],
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


def test_rules_that_declare_no_check_fail_instead_of_reporting_pass(tmp_path):
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "empty.dl").write_text("# a pack with no invariants\n")
    result = run(os.path.join(FIXTURES, "violation-facts.json"), rules=str(rules))
    assert result.returncode == 3
    assert "check" in result.stderr


def test_a_violation_for_an_undeclared_check_id_fails_the_run(tmp_path):
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "ghost.dl").write_text(
        'check("ghost/known").\n'
        'violation("ghost/unknown", X) :- node(X, T).\n'
    )
    result = run(os.path.join(FIXTURES, "violation-facts.json"), rules=str(rules))
    assert result.returncode == 3
    assert "ghost/unknown" in result.stderr


def test_a_truncated_rule_file_fails_the_run(tmp_path):
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "broken.dl").write_text('check("broken/one").\nviolation("broken/one", X) :- node(X, T')
    result = run(os.path.join(FIXTURES, "violation-facts.json"), rules=str(rules))
    assert result.returncode == 3
    assert "broken.dl" in result.stderr


def test_malformed_facts_fail_the_run(tmp_path):
    facts = write(tmp_path, "malformed.json", {"node": [1]})
    result = run(facts)
    assert result.returncode == 3
    assert "node" in result.stderr
