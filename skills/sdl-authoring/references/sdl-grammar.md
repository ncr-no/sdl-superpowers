# The SDL schema

SDL is a YAML document. `sdl_parser.parse_sdl(text)` returns it as a plain
dictionary; sections that are absent come back as `None`.

## Top level

`name` is the only required key. The parser accepts, in addition:
`description`, `nodes`, `features`, `infrastructure`, `conditions`,
`vulnerabilities`, `metrics`, `evaluations`, `tlos`, `entities`, `goals`,
`injects`, `events`, `scripts`, `stories`.

The smallest valid document is one line:

```yaml
name: test-scenario
```

## The sections this plugin's rules read

| Section | Shape | Becomes |
|---|---|---|
| `nodes.<name>` | `type`, `source`, `features`, `injects`, `conditions` | `node/2`, `source/2`, `edge/3` |
| `features.<name>` | `type`, `source`, `dependencies` | `feature/2`, `edge/3` |
| `infrastructure.<name>` | `links`, `dependencies` | `edge/3` |

`nodes.<n>.features`, `.injects` and `.conditions` are maps of
`target: role-name`. `features.<f>.dependencies` and
`infrastructure.<n>.links` are lists of names. A package reference is either
a name or a `{name, version}` map.

## What the parser guarantees

- YAML validity, and that every name referenced by `links`, `dependencies`,
  `features`, `injects` and `conditions` is defined. A dangling reference is
  a parse error, not a warning.
- Nothing else. It does not check that a service has a host, that a node is
  connected, or that dependencies are acyclic — that is what
  `datalog-verification` is for.

## Errors

One exception: `SDLLibraryParsingError`, with a `.message` and nothing else.
No line, no column, no path. The message names the failing field when it can.

## Installing the parser

`import sdl_parser` loads `libsdl_parser` with `ctypes` at import time, so it
fails at import when the shared library is absent:

```bash
sudo apt install libsdl-parser
pip install <sdl-parser repo>/python-package
```
