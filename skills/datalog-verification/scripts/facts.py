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

from datalog import validate_facts


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
        for pred, rows in validate_facts(facts).items():
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
