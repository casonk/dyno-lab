"""auto-pass test doubles for downstream repo integration tests.

These helpers cover the common pattern used across intake, nordility,
shock-relay, and snowbridge:

- import ``load_config_environment`` inside a helper function
- import ``resolve_keepassxc_entry`` and ``KeepassCommandError`` inside the
  same helper
- try one or more candidate KeePass entry paths until a non-not-found result
  is returned

Usage::

    from dyno_lab.auto_pass import AutoPassPatch, AutoPassRecorder

    recorder = AutoPassRecorder(
        responses={
            "service/token": {"value": "secret"},
        }
    )
    with AutoPassPatch(recorder):
        result = helper_under_test()

    assert recorder.load_calls[0].profile == "infra"
    assert recorder.resolve_calls[0].entry == "service/token"
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any
from unittest.mock import patch


@dataclass(frozen=True)
class AutoPassLoadCall:
    """Recorded ``load_config_environment()`` call."""

    path: object
    profile: object
    override: bool
    environ: object


@dataclass(frozen=True)
class AutoPassResolveCall:
    """Recorded ``resolve_keepassxc_entry()`` call."""

    entry: str
    attrs_map: dict[str, str]
    allow_interactive: bool
    config: object


class StubKeepassCommandError(RuntimeError):
    """Default fake ``KeepassCommandError`` used by :class:`AutoPassRecorder`."""


def _coerce_outcomes(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    return [value]


class AutoPassRecorder:
    """Recorder + scripted responder for fake ``auto_pass`` imports."""

    KeepassCommandError = StubKeepassCommandError

    def __init__(self, responses: dict[str, Any] | None = None) -> None:
        self._responses: dict[str, list[Any]] = {
            entry: _coerce_outcomes(outcome) for entry, outcome in (responses or {}).items()
        }
        self.load_calls: list[AutoPassLoadCall] = []
        self.resolve_calls: list[AutoPassResolveCall] = []

    def keepass_error(self, message: str) -> StubKeepassCommandError:
        """Return a fake ``KeepassCommandError`` with the provided message."""
        return self.KeepassCommandError(message)

    def add_response(self, entry: str, outcome: Any) -> None:
        """Queue an additional response for *entry*."""
        self._responses.setdefault(entry, []).extend(_coerce_outcomes(outcome))

    def load_config_environment(
        self,
        path: object,
        *,
        override: bool = False,
        profile: object = None,
        environ: object = None,
    ) -> tuple[dict[str, str], dict[str, str]]:
        self.load_calls.append(
            AutoPassLoadCall(
                path=path,
                profile=profile,
                override=override,
                environ=environ,
            )
        )
        return {}, {}

    def resolve_keepassxc_entry(
        self,
        entry: str,
        attrs_map: dict[str, str],
        *,
        allow_interactive: bool = False,
        config: object = None,
    ) -> dict[str, str]:
        self.resolve_calls.append(
            AutoPassResolveCall(
                entry=entry,
                attrs_map=dict(attrs_map),
                allow_interactive=allow_interactive,
                config=config,
            )
        )
        queued = self._responses.get(entry)
        if not queued:
            raise AssertionError(f"Unexpected auto-pass entry lookup: {entry!r}")
        outcome = queued.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        if callable(outcome):
            resolved = outcome(entry=entry, attrs_map=dict(attrs_map))
            return dict(resolved)
        return dict(outcome)


@dataclass
class AutoPassPatch:
    """Context manager that injects a fake ``auto_pass`` package into imports."""

    recorder: AutoPassRecorder
    _patcher: Any = field(default=None, init=False, repr=False)

    def __enter__(self) -> AutoPassRecorder:
        package = ModuleType("auto_pass")
        envfile = ModuleType("auto_pass.envfile")
        keepassxc = ModuleType("auto_pass.keepassxc")

        envfile.load_config_environment = self.recorder.load_config_environment
        keepassxc.resolve_keepassxc_entry = self.recorder.resolve_keepassxc_entry
        keepassxc.KeepassCommandError = self.recorder.KeepassCommandError

        package.envfile = envfile
        package.keepassxc = keepassxc

        self._patcher = patch.dict(
            sys.modules,
            {
                "auto_pass": package,
                "auto_pass.envfile": envfile,
                "auto_pass.keepassxc": keepassxc,
            },
            clear=False,
        )
        self._patcher.start()
        return self.recorder

    def __exit__(self, *args: Any) -> None:
        if self._patcher is not None:
            self._patcher.stop()
