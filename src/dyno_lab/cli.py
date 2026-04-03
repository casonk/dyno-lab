"""CLI capture and invocation helpers.

Covers the ``io.StringIO`` + ``sys.stdout`` / ``sys.stderr`` pattern used in
nordility and archility, and the ``(exit_code, stdout, stderr)`` return shape.

Usage (function call)::

    from dyno_lab.cli import capture_cli

    code, out, err = capture_cli(main, ["connect"])
    assert code == 0
    assert "VPN Connected" in out

Usage (mixin)::

    from dyno_lab.cli import CLITestMixin
    from dyno_lab.base import DynoTestCase

    class MyCLITests(CLITestMixin, DynoTestCase):
        def test_connect(self):
            result = self.run_cli(main, ["connect"])
            self.assertExitCode(result.exit_code)
            self.assertIn("VPN Connected", result.stdout)

Usage (pytest fixture)::

    def test_cli(dyno_cli):
        result = dyno_cli(main, ["connect"])
        assert result.exit_code == 0
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any
from unittest.mock import patch


@dataclass
class CliResult:
    """Result of a captured CLI invocation.

    Attributes
    ----------
    exit_code:
        Integer return value from the CLI entry point.
    stdout:
        Text written to ``sys.stdout`` during the call.
    stderr:
        Text written to ``sys.stderr`` during the call.
    """

    exit_code: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        """Alias for ``stdout`` — the primary captured output."""
        return self.stdout

    def assert_success(self) -> None:
        """Raise ``AssertionError`` unless ``exit_code == 0``."""
        if self.exit_code != 0:
            raise AssertionError(
                f"CLI exited with code {self.exit_code}.\n"
                f"stdout: {self.stdout}\nstderr: {self.stderr}"
            )

    def assert_failure(self, expected_code: int | None = None) -> None:
        """Raise ``AssertionError`` unless the CLI exited with a non-zero code."""
        if self.exit_code == 0:
            raise AssertionError("CLI succeeded but failure was expected.")
        if expected_code is not None and self.exit_code != expected_code:
            raise AssertionError(
                f"Expected exit code {expected_code}, got {self.exit_code}."
            )

    def assert_output_contains(self, text: str) -> None:
        """Raise ``AssertionError`` unless *text* appears in stdout."""
        if text not in self.stdout:
            raise AssertionError(
                f"Expected {text!r} in stdout.\nActual stdout:\n{self.stdout[:500]}"
            )

    def assert_error_contains(self, text: str) -> None:
        """Raise ``AssertionError`` unless *text* appears in stderr."""
        if text not in self.stderr:
            raise AssertionError(
                f"Expected {text!r} in stderr.\nActual stderr:\n{self.stderr[:500]}"
            )


def capture_cli(
    func: Any,
    args: list[str] | None = None,
    stdin: str | None = None,
) -> tuple[int, str, str]:
    """Call *func(args)* with captured stdout/stderr.

    Parameters
    ----------
    func:
        The CLI entry point — expected to accept a list of string args and
        return an integer exit code.
    args:
        Argument list passed to *func*.  Defaults to ``[]``.
    stdin:
        Optional text to use as ``sys.stdin``.

    Returns
    -------
    tuple[int, str, str]
        ``(exit_code, stdout_text, stderr_text)``

    Example::

        code, out, err = capture_cli(main, ["connect"])
        assert code == 0
        assert "Connected" in out
    """
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    patches: list[Any] = [
        patch("sys.stdout", new=stdout_buf),
        patch("sys.stderr", new=stderr_buf),
    ]
    if stdin is not None:
        patches.append(patch("sys.stdin", new=io.StringIO(stdin)))

    with patches[0], patches[1]:
        if len(patches) > 2:
            with patches[2]:
                exit_code = func(args or [])
        else:
            exit_code = func(args or [])

    return (int(exit_code or 0), stdout_buf.getvalue(), stderr_buf.getvalue())


def capture_cli_result(
    func: Any,
    args: list[str] | None = None,
    stdin: str | None = None,
) -> CliResult:
    """Like :func:`capture_cli` but returns a :class:`CliResult`."""
    code, out, err = capture_cli(func, args, stdin)
    return CliResult(exit_code=code, stdout=out, stderr=err)


class CLITestMixin:
    """Mixin for ``unittest.TestCase`` subclasses that test CLI entry points.

    Provides ``run_cli`` which returns a :class:`CliResult`::

        class MyTests(CLITestMixin, DynoTestCase):
            def test_connect(self):
                result = self.run_cli(main, ["connect"])
                result.assert_success()
                result.assert_output_contains("Connected")
    """

    def run_cli(
        self,
        func: Any,
        args: list[str] | None = None,
        stdin: str | None = None,
    ) -> CliResult:
        """Invoke *func(args)* with captured I/O and return a :class:`CliResult`."""
        return capture_cli_result(func, args, stdin)
