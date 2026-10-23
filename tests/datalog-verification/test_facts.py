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
