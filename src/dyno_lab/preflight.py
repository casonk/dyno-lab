"""CI pre-flight checks and pytest skip markers.

Provides standalone check functions, a fluent ``PreflightSuite`` builder, and
pytest skip-marker decorators / collection hook that integrate with the portfolio
CI workflow.

Standalone checks::

    from dyno_lab.preflight import check_tool, check_import, check_env

    if not check_tool("plantuml"):
        print("plantuml not found")

Fluent suite::

    from dyno_lab.preflight import PreflightSuite

    report = (
        PreflightSuite()
        .require_tool("git", "make")
        .require_env("CI")
        .require_import("pytest")
        .run()
    )
    report.raise_if_failed()

Pytest skip markers (activate via ``pytest_plugins = ["dyno_lab.fixtures"]``)::

    from dyno_lab.preflight import requires_tool, requires_env, requires_import

    @requires_tool("plantuml")
    def test_render_diagram(): ...

    @requires_env("NORDVPN_KEY")
    def test_live_connect(): ...

    @requires_import("psycopg2")
    def test_db_query(): ...
"""

from __future__ import annotations

import importlib
import os
import shutil
import socket
import urllib.request
from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Standalone check functions
# ---------------------------------------------------------------------------


def check_tool(name: str) -> bool:
    """Return ``True`` if *name* is found on PATH via :func:`shutil.which`."""
    return shutil.which(name) is not None


def check_import(package: str) -> bool:
    """Return ``True`` if *package* can be imported with :func:`importlib.import_module`."""
    try:
        importlib.import_module(package)
        return True
    except Exception:  # noqa: BLE001
        return False


def check_env(key: str) -> bool:
    """Return ``True`` if ``os.environ[key]`` is a non-empty string."""
    return bool(os.environ.get(key))


def check_port(host: str, port: int, timeout: float = 2.0) -> bool:
    """Return ``True`` if a TCP connection to *host*:*port* succeeds."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:  # noqa: BLE001
        return False


def check_url(url: str, timeout: float = 5.0) -> bool:
    """Return ``True`` if *url* responds with HTTP status < 400."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            return resp.status < 400
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# PreflightSuite, PreflightReport, PreflightError
# ---------------------------------------------------------------------------


@dataclass
class _CheckResult:
    """Result of a single pre-flight check."""

    label: str
    passed: bool
    detail: str = ""

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        suffix = f" — {self.detail}" if self.detail else ""
        return f"[{status}] {self.label}{suffix}"


class PreflightError(RuntimeError):
    """Raised by :meth:`PreflightReport.raise_if_failed` when checks fail."""


class PreflightReport:
    """Aggregated results from a :class:`PreflightSuite` run.

    Attributes
    ----------
    results:
        All :class:`_CheckResult` objects, in evaluation order.
    """

    def __init__(self, results: list[_CheckResult]) -> None:
        self.results = results

    @property
    def passed(self) -> list[_CheckResult]:
        """Checks that passed."""
        return [r for r in self.results if r.passed]

    @property
    def failed(self) -> list[_CheckResult]:
        """Checks that failed."""
        return [r for r in self.results if not r.passed]

    @property
    def all_passed(self) -> bool:
        """``True`` when every check passed."""
        return all(r.passed for r in self.results)

    def raise_if_failed(self) -> None:
        """Raise :class:`PreflightError` listing all failed checks."""
        if self.failed:
            lines = [str(r) for r in self.failed]
            raise PreflightError(
                f"{len(self.failed)} pre-flight check(s) failed:\n  " + "\n  ".join(lines)
            )

    def __str__(self) -> str:
        total = len(self.results)
        n_pass = len(self.passed)
        n_fail = len(self.failed)
        lines = [f"Pre-flight: {n_pass}/{total} passed, {n_fail} failed"]
        for r in self.results:
            lines.append(f"  {r}")
        return "\n".join(lines)


class PreflightSuite:
    """Fluent builder for a set of pre-flight checks.

    Chain ``require_*`` calls then call :meth:`run` to evaluate all checks and
    return a :class:`PreflightReport`::

        report = (
            PreflightSuite()
            .require_tool("git", "make")
            .require_env("CI")
            .require_import("pytest")
            .run()
        )
        report.raise_if_failed()
    """

    def __init__(self) -> None:
        self._checks: list[tuple[str, Any]] = []

    def require_tool(self, *names: str) -> "PreflightSuite":
        """Add a tool-on-PATH check for each name."""
        for name in names:
            self._checks.append((f"tool:{name}", lambda n=name: check_tool(n)))
        return self

    def require_import(self, *packages: str) -> "PreflightSuite":
        """Add an importability check for each package."""
        for pkg in packages:
            self._checks.append((f"import:{pkg}", lambda p=pkg: check_import(p)))
        return self

    def require_env(self, *keys: str) -> "PreflightSuite":
        """Add a non-empty env-var check for each key."""
        for key in keys:
            self._checks.append((f"env:{key}", lambda k=key: check_env(k)))
        return self

    def require_port(self, host: str, port: int, timeout: float = 2.0) -> "PreflightSuite":
        """Add a TCP connectivity check."""
        self._checks.append(
            (f"port:{host}:{port}", lambda h=host, p=port, t=timeout: check_port(h, p, t))
        )
        return self

    def require_url(self, url: str, timeout: float = 5.0) -> "PreflightSuite":
        """Add an HTTP reachability check."""
        self._checks.append((f"url:{url}", lambda u=url, t=timeout: check_url(u, t)))
        return self

    def run(self) -> PreflightReport:
        """Evaluate all registered checks and return a :class:`PreflightReport`."""
        results: list[_CheckResult] = []
        for label, fn in self._checks:
            try:
                ok = fn()
            except Exception:  # noqa: BLE001
                ok = False
            results.append(_CheckResult(label=label, passed=ok))
        return PreflightReport(results)


# ---------------------------------------------------------------------------
# Pytest skip-marker decorators
# ---------------------------------------------------------------------------


def requires_tool(*names: str) -> Any:
    """Return a ``pytest.mark.requires_tool`` mark for the given tool names."""
    import pytest  # local import — only needed when running under pytest

    return pytest.mark.requires_tool(*names)


def requires_env(*keys: str) -> Any:
    """Return a ``pytest.mark.requires_env`` mark for the given env-var keys."""
    import pytest

    return pytest.mark.requires_env(*keys)


def requires_import(*packages: str) -> Any:
    """Return a ``pytest.mark.requires_import`` mark for the given package names."""
    import pytest

    return pytest.mark.requires_import(*packages)


# ---------------------------------------------------------------------------
# Pytest plugin hook
# ---------------------------------------------------------------------------


def pytest_collection_modifyitems(items: list[Any], config: Any) -> None:  # noqa: ARG001
    """Auto-skip tests marked with ``requires_tool``, ``requires_env``, or ``requires_import``.

    Activated automatically when ``pytest_plugins = ["dyno_lab.fixtures"]`` is
    set in ``conftest.py``.
    """
    import pytest

    for item in items:
        for marker in item.iter_markers("requires_tool"):
            for name in marker.args:
                if not check_tool(name):
                    item.add_marker(pytest.mark.skip(reason=f"requires tool on PATH: {name!r}"))
                    break

        for marker in item.iter_markers("requires_env"):
            for key in marker.args:
                if not check_env(key):
                    item.add_marker(pytest.mark.skip(reason=f"requires env var: {key!r}"))
                    break

        for marker in item.iter_markers("requires_import"):
            for pkg in marker.args:
                if not check_import(pkg):
                    item.add_marker(
                        pytest.mark.skip(reason=f"requires importable package: {pkg!r}")
                    )
                    break
