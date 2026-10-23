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
import traceback

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
    declared = {row[0] for row in result.facts.get("check", ())}
    if not declared:
        raise DatalogError("the rules declare no check(\"…\") — there is nothing to verify")
    for predicate in ("violation", "undecidable"):
        for row in result.facts.get(predicate, ()):
            if row[0] not in declared:
                raise DatalogError(
                    "%s %r has no matching check(%r)" % (predicate, row[0], row[0]))
    rows = []
    for rule_id in sorted(declared):
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
    except Exception as error:  # a crash is a failed run, never a verdict
        traceback.print_exc()
        print("verify: internal error: %s" % error, file=sys.stderr)
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
