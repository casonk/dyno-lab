# AGENTS.md — dyno-lab

## Purpose

`dyno-lab` is the portfolio-wide test bench utility library. It provides reusable
fixtures, mock builders, assertions, and smoke-test scaffolding drawn from patterns
across every tested repository in the portfolio.

Any repository that needs shared test infrastructure should depend on `dyno-lab`
rather than reinventing subprocess mocking, environment patching, filesystem fixtures,
CLI capture, HTTP session mocking, schema validation, or smoke scaffolding locally.

## Repository Layout

```
src/dyno_lab/
  __init__.py      — public API re-exports
  base.py          — DynoTestCase (unittest.TestCase subclass with extra assertions)
  proc.py          — ProcessRecorder, SubprocessPatch (subprocess mock builders)
  env.py           — EnvPatch, patched_env (os.environ patching utilities)
  fs.py            — TempWorkdir, make_tree (filesystem fixture utilities)
  cli.py           — capture_cli, CLITestMixin, CliResult (CLI capture helpers)
  http.py          — SequenceSession, StaticSession, RaisingSession (HTTP mock sessions)
  schema.py        — assert_parity, assert_row_width, assert_schema_keys (contract helpers)
  module.py        — load_module_by_path (dynamic module loading)
  markers.py       — MARKERS dict + register_markers() (shared pytest marker definitions)
  fixtures.py      — dyno_tmp, dyno_env, dyno_proc, dyno_cli (pytest fixtures)
  smoke.py         — SmokeTest, SmokeRunner, SmokeResult, SmokeSummary

tests/
  test_base.py
  test_proc.py
  test_env.py
  test_fs.py
  test_cli.py
  test_http.py
  test_schema.py
  test_module.py
  test_smoke.py

docs/
  contributor-architecture-blueprint.md
  diagrams/
    repo-architecture.puml
    repo-architecture.drawio
```

## Setup And Commands

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest -q

# Pre-commit
pre-commit run --all-files
```

## Architecture Notes

`dyno-lab` is framework-agnostic:

- `DynoTestCase`, `CLITestMixin`, and all context managers work with plain `unittest`.
- `dyno_lab.fixtures` exposes pytest fixtures that can be activated via `pytest_plugins`.
- `dyno_lab.markers` provides shared marker definitions callable from any `conftest.py`.

### Subprocess mocking

`ProcessRecorder` records every `subprocess.run` call and returns scripted
`CompletedProcess` objects in order, falling back to configurable defaults.
`SubprocessPatch` wraps `unittest.mock.patch` to activate the recorder for a block.

### Environment patching

`EnvPatch` wraps `unittest.mock.patch.dict(os.environ, ...)` and is usable as
a context manager or a decorator.  `patched_env()` is an inline contextmanager.

### Filesystem fixtures

`TempWorkdir` is a context-manager-based temporary directory with `write`, `read`,
`populate`, and inline assertion helpers.  `make_tree` populates a `Path` from a
`{relative_path: content}` dict.

### CLI capture

`capture_cli(func, args)` replaces `sys.stdout` and `sys.stderr` with `io.StringIO`
buffers, calls `func(args)`, and returns `(exit_code, stdout_text, stderr_text)`.
`CLITestMixin` wraps this for unittest.

### HTTP session mocking

`SequenceSession` returns scripted responses in order.  `StaticSession` always
returns the same body.  `RaisingSession` always raises.  All three record calls.

### Schema / parity helpers

`assert_parity` validates that N independent implementations produce identical
shapes.  `assert_row_width` checks column counts.  `assert_schema_keys` and
`assert_schema_shape` validate dict structure.

### Smoke scaffolding

`SmokeTest` is an abstract base class.  Subclass it, implement `run()`, and
return `SmokeResult.ok()` or `SmokeResult.failed()`.  `SmokeRunner` collects
tests, calls `run_safe()` on each, and returns a `SmokeSummary`.

## Change Guidance

- Keep each module narrowly focused on its declared responsibility.
- Do not introduce runtime dependencies beyond the standard library.  `pytest` is
  an optional dev dependency and must not be imported at import time in core modules.
- When adding a new utility pattern discovered in a portfolio repo, add tests first.
- Update `__init__.py` exports and this `AGENTS.md` layout when adding modules.
- Prefer explicit context managers and factories over magic or auto-fixtures.

## Portfolio Standards Reference

For portfolio-wide repository standards, consult the control-plane repo at
`./util-repos/traction-control` from the portfolio root.

Start with:
- `./util-repos/traction-control/AGENTS.md`
- `./util-repos/traction-control/LESSONSLEARNED.md`

Shared implementation repos available portfolio-wide:
- `./util-repos/archility` — architecture toolchain bootstrap/render, diagram support, scaffolding
- `./util-repos/auto-pass` — KeePassXC-backed password management and secret retrieval
- `./util-repos/nordility` — NordVPN-based VPN switching and connection orchestration
- `./util-repos/shock-relay` — external messaging (Signal, Telegram, Twilio, WhatsApp, Gmail)
- `./util-repos/snowbridge` — SMB-based private file sharing and phone-accessible fileshare
- `./util-repos/short-circuit` — WireGuard VPN setup and private tunnel configuration
- `./util-repos/dyno-lab` — unified test bench utilities (this repo)

## Agent Memory

Use `./LESSONSLEARNED.md` as the tracked durable lessons file for this repo.
Use `./CHATHISTORY.md` as the standard local handoff file for this repo (gitignored).
