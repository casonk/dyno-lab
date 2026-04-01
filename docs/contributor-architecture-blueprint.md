# dyno-lab Contributor Architecture Blueprint

## Overview

`dyno-lab` is a Python utility library with no runtime dependencies beyond the
standard library.  Its architecture centers on a set of narrowly focused modules,
each addressing one reusable test bench concern extracted from portfolio-wide patterns.

## Architecture Paths

### Programmatic path

`dyno-lab` exposes importable helpers; it has no CLI entry point.  Consumers
install it as an editable dependency and import from `dyno_lab.*`.

This path is deterministic.

### Agentic authoring path

Agents may extend `dyno-lab` by adding new modules for test patterns discovered
in portfolio repos.  Follow the single-responsibility principle: one concern per module.

This path is intentionally non-deterministic.

## Module Responsibilities

| Module | Concern |
|---|---|
| `base.py` | Extended `unittest.TestCase` assertions |
| `proc.py` | `subprocess.run` mock recording |
| `env.py` | `os.environ` patch context managers |
| `fs.py` | Temporary directory and file tree fixtures |
| `cli.py` | `sys.stdout` / `sys.stderr` capture for CLI tests |
| `http.py` | `requests.Session`-compatible mock objects |
| `schema.py` | Row-width, key presence, type, and parity validation |
| `module.py` | `importlib`-based module loading by filesystem path |
| `markers.py` | Shared pytest marker registry |
| `fixtures.py` | pytest fixture wrappers (requires pytest at runtime) |
| `smoke.py` | Abstract smoke test base class and runner |

## Diagram Sources

Architecture diagrams live in `docs/diagrams/`.  Render with:

```bash
cd ../util-repos/archility
python3 -m archility render ../../util-repos/dyno-lab
```

## Supplemental Diagrams

After `archility render`, generate Python import and class diagrams:

```bash
# Import dependency graph
pydeps src/dyno_lab --noshow -o docs/diagrams/python-import-deps-src-dyno_lab.svg

# Class and package diagrams
pyreverse -o puml -d docs/diagrams src/dyno_lab
# Outputs: docs/diagrams/python-classes.puml, docs/diagrams/python-packages.puml
```
