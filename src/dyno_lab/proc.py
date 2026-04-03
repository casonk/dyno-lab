"""Subprocess mocking utilities.

Covers the patterns found across nordility, auto-pass, and personal-finance:

- ``build_completed_process`` — quick ``CompletedProcess`` factory
- ``ProcessRecorder`` — records every call and returns scripted responses
- ``SubprocessPatch`` — context manager that patches ``subprocess.run``

Usage (unittest)::

    from dyno_lab.proc import ProcessRecorder, SubprocessPatch, build_completed_process

    recorder = ProcessRecorder(default_stdout="ok")
    with SubprocessPatch(recorder):
        result = subprocess.run(["mycmd", "arg"], capture_output=True, text=True)

    assert recorder.calls[0].args == ["mycmd", "arg"]

Usage (pytest)::

    def test_something(dyno_proc):
        recorder = dyno_proc(default_returncode=0, default_stdout="done")
        with SubprocessPatch(recorder):
            ...
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import patch


@dataclass
class CapturedCall:
    """A single recorded ``subprocess.run`` invocation."""

    args: list[str] | tuple[str, ...]
    kwargs: dict[str, Any]


def build_completed_process(
    args: list[str] | tuple[str, ...] | None = None,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    """Return a ``CompletedProcess`` with the given fields.

    Shorthand for tests that need to return a canned process result::

        def fake_run(cmd, **kw):
            return build_completed_process(cmd, stdout="VPN Connected")
    """
    return subprocess.CompletedProcess(
        args=args or [],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


class ProcessRecorder:
    """Records subprocess.run calls and returns scripted responses.

    Parameters
    ----------
    responses:
        Ordered list of ``CompletedProcess`` objects to return.
        If exhausted, *default* values are used instead.
    default_returncode:
        Return code to use when *responses* is exhausted.
    default_stdout:
        stdout to use when *responses* is exhausted.
    default_stderr:
        stderr to use when *responses* is exhausted.

    Attributes
    ----------
    calls:
        List of every ``CapturedCall`` made to this recorder.

    Example — single scripted response::

        recorder = ProcessRecorder(responses=[
            build_completed_process(stdout="found entry"),
            build_completed_process(returncode=1, stderr="not found"),
        ])
        with SubprocessPatch(recorder):
            ...

    Example — multiple calls with default fallback::

        recorder = ProcessRecorder(default_stdout="ok")
        with SubprocessPatch(recorder):
            subprocess.run(["cmd", "a"])
            subprocess.run(["cmd", "b"])

        assert len(recorder.calls) == 2
    """

    def __init__(
        self,
        responses: list[subprocess.CompletedProcess[str]] | None = None,
        *,
        default_returncode: int = 0,
        default_stdout: str = "",
        default_stderr: str = "",
    ) -> None:
        self._responses = list(responses or [])
        self._default_returncode = default_returncode
        self._default_stdout = default_stdout
        self._default_stderr = default_stderr
        self.calls: list[CapturedCall] = []

    def __call__(
        self,
        args: list[str] | tuple[str, ...],
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append(CapturedCall(args=args, kwargs=kwargs))
        if self._responses:
            return self._responses.pop(0)
        return build_completed_process(
            args=args,
            returncode=self._default_returncode,
            stdout=self._default_stdout,
            stderr=self._default_stderr,
        )

    @property
    def call_count(self) -> int:
        """Total number of subprocess.run calls recorded."""
        return len(self.calls)

    def commands(self) -> list[list[str] | tuple[str, ...]]:
        """Return the args from every recorded call."""
        return [c.args for c in self.calls]

    def stdin_inputs(self) -> list[str]:
        """Return the ``input=`` kwarg from every recorded call
        (empty string if absent)."""
        return [c.kwargs.get("input", "") for c in self.calls]


@dataclass
class SubprocessPatch:
    """Context manager that patches ``subprocess.run`` with a callable.

    Parameters
    ----------
    side_effect:
        Any callable that accepts ``(args, **kwargs)`` — typically a
        ``ProcessRecorder`` or a plain ``fake_run`` function.
    target:
        The dotted import path to ``subprocess.run`` in the module under test.
        Defaults to ``"subprocess.run"`` which patches the standard library
        directly and works for most cases.

    Usage::

        recorder = ProcessRecorder(default_stdout="connected")
        with SubprocessPatch(recorder, target="nordility.client.subprocess.run"):
            result = client.connect()
    """

    side_effect: Any
    target: str = "subprocess.run"
    _patcher: Any = field(default=None, init=False, repr=False)

    def __enter__(self) -> "SubprocessPatch":
        self._patcher = patch(self.target, side_effect=self.side_effect)
        self._patcher.start()
        return self

    def __exit__(self, *args: Any) -> None:
        if self._patcher is not None:
            self._patcher.stop()
