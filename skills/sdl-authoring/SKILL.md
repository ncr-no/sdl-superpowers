---
name: sdl-authoring
description: Use when writing or editing a Scenario Definition Language (.sdl) document for a cyber range — nodes, services, features, infrastructure links and dependencies — or when a range's topology has to be expressed and validated
---

# SDL Authoring

You are authoring the scenario definition: the machine-readable topology of
the range. One document per scenario, YAML, validated by the parser before
you hand it on.

## What this produces

`sdl/<scenario>.sdl` — the scenario's nodes, features and infrastructure.
Find where the project keeps scenario files first; if there is no such
directory, ask before creating one.

## The document

`name` is the only required key. Everything else is optional and may be
absent. Read `references/sdl-grammar.md` for the section shapes before you
write a field you have not used.

Start from the smallest thing that describes the range and grow it:

```yaml
name: hospital-ransomware
description: Hospital network under ransomware pressure

nodes:
  ehr01:
    type: VM
    source: ubuntu22
    features:
      ehr_svc: default
  fwsrv:
    type: Switch

features:
  ehr_svc:
    type: service
    dependencies: [auth_svc]
  auth_svc:
    type: configuration

infrastructure:
  ehr01:
    count: 1
    links: [fwsrv]
```

## Rules of authorship

1. **Names are stable.** Inject targets, assessment maps and evaluation
   scripts refer to node and feature names. Renaming one after an exercise
   is written breaks them silently; rename first, then search the exercise
   for the old name.
2. **Every service gets a host.** A feature with no node that lists it is a
   service that exists nowhere.
3. **Link what talks.** `links` is how you say two hosts reach each other;
   leaving it out makes every node look stranded.
4. **Dependencies point down the stack.** `ehr_svc` depends on `auth_svc`,
   not the other way round, and never in a cycle.
5. **No secrets, no real hostnames, no customer data.** The SDL is an
   exercise artefact and may be shared at the exercise's classification.
6. **Do not invent a field.** If the schema you have does not express what
   you need, say so; an unknown section is either rejected or ignored, and
   an ignored one is worse.

## Validate before you hand off

```bash
python3 scripts/validate.py sdl/<scenario>.sdl
```

- `PASS` — the parser accepted it. That means the YAML is well formed and
  every reference resolves. It does not mean the scenario is sensible.
- `FAIL` — the parser's message, verbatim. It has no line number; read the
  field it names and look there. Fix one error at a time — the parser
  reports the first failure and stops.
- `UNKNOWN` — the parser is not installed. Give your human partner the
  install command the message carries (`sudo apt install libsdl-parser`,
  then `pip install <sdl-parser repo>/python-package`); do not hand-write
  YAML and claim it is validated.

## Red flags

| Thought | Reality |
|---|---|
| "The parser accepted it, so the scenario is sound" | Syntax and referential closure only. Run `datalog-verification` for the rest. |
| "I'll add the nodes later, the shape is what matters" | A scenario with no nodes validates and describes nothing. |
| "This field probably exists" | Unknown keys are ignored or rejected. Check the grammar reference. |
| "I'll rename the node, it's clearer" | Inject targets and assessment maps refer to it by name. Rename everywhere or not at all. |
| "I'll put the real hostname in, it's internal" | The SDL outlives the exercise and gets shared. Use invented names. |

## Handoff

A validated SDL goes to `datalog-verification` with the exercise documents,
then to the development phase. An SDL that validates but fails the
structural rules is not ready: fix the graph, not the rules.
