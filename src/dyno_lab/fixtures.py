"""Pytest fixtures for dyno-lab utilities.

Activate by adding to your project's ``conftest.py``::

    pytest_plugins = ["dyno_lab.fixtures"]

Or import individual fixtures::

    from dyno_lab.fixtures import dyno_tmp, dyno_env, dyno_proc, dyno_cli

Available fixtures
------------------
dyno_tmp
    A :class:`~dyno_lab.fs.TempWorkdir` already entered.  The temp dir is
    cleaned up automatically after the test.

dyno_env
    A factory that returns an :class:`~dyno_lab.env.EnvPatch` context manager.

dyno_proc
    A factory that returns a configured :class:`~dyno_lab.proc.ProcessRecorder`.

dyno_cli
    A callable that runs a CLI entry point with captured I/O and returns a
    :class:`~dyno_lab.cli.CliResult`.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest

from dyno_lab.cli import CliResult, capture_cli_result
from dyno_lab.env import EnvPatch
from dyno_lab.fs import TempWorkdir
from dyno_lab.markers import register_markers
from dyno_lab.preflight import pytest_collection_modifyitems as _preflight_hook
from dyno_lab.proc import ProcessRecorder

# Re-expose so pytest picks up the pre-flight skip logic from this module.
pytest_collection_modifyitems = _preflight_hook


def pytest_configure(config: Any) -> None:
    """Auto-register dyno-lab markers when this plugin is loaded."""
    register_markers(config)


@pytest.fixture
def dyno_tmp() -> Generator[TempWorkdir, None, None]:
    """Yield an entered :class:`~dyno_lab.fs.TempWorkdir`.

    The directory is cleaned up after the test::

        def test_something(dyno_tmp):
            dyno_tmp.write("config.toml", "[project]\\nname = 'demo'\\n")
            dyno_tmp.assert_exists("config.toml")
    """
    with TempWorkdir() as wd:
        yield wd


@pytest.fixture
def dyno_env() -> Any:
    """Return a factory for :class:`~dyno_lab.env.EnvPatch` context managers.

    Usage::

        def test_something(dyno_env):
            with dyno_env(MY_VAR="value", OTHER_VAR="x"):
                result = my_function()
    """

    def _factory(**kwargs: str) -> EnvPatch:
        return EnvPatch({k: str(v) for k, v in kwargs.items()})

    return _factory


@pytest.fixture
def dyno_proc() -> Any:
    """Return a factory for :class:`~dyno_lab.proc.ProcessRecorder` instances.

    Usage::

        def test_something(dyno_proc):
            recorder = dyno_proc(default_stdout="VPN Connected")
            with SubprocessPatch(recorder):
                result = client.connect()
            assert recorder.call_count == 1
    """

    def _factory(
        responses: list[Any] | None = None,
        *,
        default_returncode: int = 0,
        default_stdout: str = "",
        default_stderr: str = "",
    ) -> ProcessRecorder:
        return ProcessRecorder(
            responses=responses,
            default_returncode=default_returncode,
            default_stdout=default_stdout,
            default_stderr=default_stderr,
        )

    return _factory


@pytest.fixture
def dyno_cli() -> Any:
    """Return a callable that invokes a CLI entry point with captured I/O.

    Usage::

        def test_connect(dyno_cli):
            result = dyno_cli(main, ["connect"])
            assert result.exit_code == 0
            assert "Connected" in result.stdout
    """

    def _invoke(
        func: Any,
        args: list[str] | None = None,
        stdin: str | None = None,
    ) -> CliResult:
        return capture_cli_result(func, args, stdin)

    return _invoke
