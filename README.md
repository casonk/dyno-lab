# dyno-lab

Portfolio-wide test bench utilities for unified test building, expansion, and refactoring.

`dyno-lab` provides reusable fixtures, mocks, assertions, and smoke-test scaffolding
drawn from patterns across every tested repository in the portfolio.

## Overview

| Module | Purpose |
|---|---|
| `dyno_lab.base` | `DynoTestCase` — `unittest.TestCase` with extra assertions |
| `dyno_lab.proc` | Subprocess mocking (`ProcessRecorder`, `SubprocessPatch`) |
| `dyno_lab.env` | Environment patching (`EnvPatch`, `patched_env`) |
| `dyno_lab.fs` | Filesystem fixtures (`TempWorkdir`, `make_tree`) |
| `dyno_lab.cli` | CLI capture (`capture_cli`, `CLITestMixin`, `CliResult`) |
| `dyno_lab.http` | HTTP session mocking (`SequenceSession`, `StaticSession`, `RaisingSession`) |
| `dyno_lab.schema` | Schema/contract helpers (`assert_parity`, `assert_row_width`) |
| `dyno_lab.module` | Dynamic module loading (`load_module_by_path`) |
| `dyno_lab.markers` | Shared pytest markers (`unit`, `integration`, `smoke`, `parity`, `slow`, `external`) |
| `dyno_lab.fixtures` | Pytest fixtures (`dyno_tmp`, `dyno_env`, `dyno_proc`, `dyno_cli`) |
| `dyno_lab.smoke` | Smoke test scaffolding (`SmokeTest`, `SmokeRunner`, `SmokeResult`) |

## Prerequisites

- Python 3.10 or later
- `pytest` (for the fixture and marker integrations)

## Installation

```bash
# From the portfolio root — install in editable mode into your target repo's venv
pip install -e ./util-repos/dyno-lab
```

Or as a local path dependency in `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = ["dyno-lab @ file:///path/to/util-repos/dyno-lab"]
```

## Quick Start

### Subprocess mocking

```python
from dyno_lab.proc import ProcessRecorder, SubprocessPatch, build_completed_process

recorder = ProcessRecorder(responses=[
    build_completed_process(stdout="VPN Connected"),
])
with SubprocessPatch(recorder, target="mymodule.subprocess.run"):
    result = client.connect()

assert recorder.commands()[0] == ("nordvpn", "connect", "United States")
```

### Environment patching

```python
from dyno_lab.env import EnvPatch, env_defaults

DEFAULTS = env_defaults(
    MY_APP_DB_PATH="/tmp/test.db",
    MY_APP_PASSWORD="test-pass",
)

with EnvPatch(DEFAULTS):
    result = my_function()
```

### Filesystem fixtures

```python
from dyno_lab.fs import TempWorkdir

with TempWorkdir() as wd:
    wd.populate({
        "config.toml": "[project]\nname = 'demo'\n",
        "src/pkg/__init__.py": "",
    })
    wd.assert_exists("config.toml")
    wd.assert_contains("config.toml", "demo")
```

### CLI capture

```python
from dyno_lab.cli import capture_cli

code, out, err = capture_cli(main, ["connect"])
assert code == 0
assert "Connected" in out
```

### HTTP session mocking

```python
from dyno_lab.http import SequenceSession
from unittest.mock import patch

session = SequenceSession(['{"results": []}', '<html>fallback</html>'])
with patch("myapp.get_session", return_value=session):
    items = fetch_items()

assert session.call_count == 2
```

### Schema / provider parity

```python
from dyno_lab.schema import assert_parity

assert_parity(
    [bank_module, cred_module, invest_module],
    factory=lambda m: m.StatementRecord(**base_kwargs()),
    extractor=lambda r: len(r.as_row()),
    attribute="row width",
)
```

### Smoke tests

```python
from dyno_lab.smoke import SmokeTest, SmokeResult, SmokeRunner

class MyServiceSmoke(SmokeTest):
    name = "my-service-ping"

    def run(self) -> SmokeResult:
        try:
            response = ping_service()
            return SmokeResult.ok(self.name, f"latency={response.latency_ms}ms")
        except Exception as exc:
            return SmokeResult.failed(self.name, str(exc))

runner = SmokeRunner([MyServiceSmoke()])
summary = runner.run_all()
summary.raise_if_failed()
```

### Pytest fixtures

In your project's `conftest.py`:

```python
pytest_plugins = ["dyno_lab.fixtures"]
```

Then in tests:

```python
def test_something(dyno_tmp, dyno_env, dyno_proc):
    dyno_tmp.write("config.json", '{"key": "val"}')
    with dyno_env(MY_VAR="test"):
        recorder = dyno_proc(default_stdout="ok")
        ...
```

### Pytest markers

```python
# conftest.py
from dyno_lab.markers import register_markers

def pytest_configure(config):
    register_markers(config)
```

Then decorate tests:

```python
import pytest

@pytest.mark.unit
def test_fast_thing(): ...

@pytest.mark.integration
def test_with_filesystem(): ...

@pytest.mark.smoke
def test_service_health(): ...

@pytest.mark.parity
def test_all_providers_match(): ...
```

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest -q

# Run pre-commit
pre-commit run --all-files
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
