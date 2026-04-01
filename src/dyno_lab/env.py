"""Environment variable patching utilities.

Covers the ``patch.dict(os.environ, ...)`` pattern used extensively in auto-pass.

Usage (context manager)::

    from dyno_lab.env import EnvPatch, env_defaults

    DEFAULTS = env_defaults(
        MY_APP_DB_PATH="/tmp/db.kdbx",
        MY_APP_PASSWORD="test-pass",
    )

    with EnvPatch(DEFAULTS):
        result = my_function()

Usage (decorator)::

    @EnvPatch.decorator({"MY_ENV": "value"})
    def test_something():
        ...

Usage (pytest fixture)::

    def test_something(dyno_env):
        with dyno_env(MY_APP_DB_PATH="/tmp/db.kdbx"):
            ...
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from unittest.mock import patch


def env_defaults(**kwargs: str) -> dict[str, str]:
    """Build a default environment dict for use with :class:`EnvPatch`.

    All values must be strings.  Convenience wrapper to make test-module
    constants self-documenting::

        DEFAULTS = env_defaults(
            AUTO_PASS_KEEPASSXC_DB_PATH="/tmp/test-db.kdbx",
            AUTO_PASS_KEEPASSXC_DB_PASSWORD="test-password",
            AUTO_PASS_KEEPASSXC_KEY_FILE="",
        )
    """
    return {k: str(v) for k, v in kwargs.items()}


class EnvPatch:
    """Context manager / decorator that patches ``os.environ`` for the duration.

    Parameters
    ----------
    env:
        Mapping of environment variable names to values to apply.
    clear:
        When ``True``, the entire environment is replaced with *env*.
        When ``False`` (default), *env* is merged on top of the existing
        environment and restored on exit.
    """

    def __init__(self, env: dict[str, str], *, clear: bool = False) -> None:
        self._env = env
        self._clear = clear
        self._patcher: Any = None

    def __enter__(self) -> "EnvPatch":
        self._patcher = patch.dict(os.environ, self._env, clear=self._clear)
        self._patcher.start()
        return self

    def __exit__(self, *args: Any) -> None:
        if self._patcher is not None:
            self._patcher.stop()

    @classmethod
    def decorator(cls, env: dict[str, str], *, clear: bool = False):  # noqa: ANN206
        """Return a decorator that applies an env patch to a test function::

        @EnvPatch.decorator({"MY_VAR": "value"})
        def test_something():
            assert os.environ["MY_VAR"] == "value"
        """

        def _decorator(func: Any) -> Any:
            def _wrapper(*args: Any, **kwargs: Any) -> Any:
                with cls(env, clear=clear):
                    return func(*args, **kwargs)

            _wrapper.__name__ = func.__name__
            _wrapper.__doc__ = func.__doc__
            return _wrapper

        return _decorator


@contextmanager
def patched_env(**kwargs: str) -> Iterator[None]:
    """Inline context manager for brief env patches::

    with patched_env(HOME="/tmp/fake-home", PATH="/usr/bin"):
        result = subprocess.run(["myapp"], capture_output=True, text=True)
    """
    with patch.dict(os.environ, {k: str(v) for k, v in kwargs.items()}):
        yield
