"""Smoke test scaffolding.

Covers the end-to-end health-check pattern from shock-relay
(send/receive/confirm flows) in a reusable, test-framework-agnostic way.

Usage::

    from dyno_lab.smoke import SmokeTest, SmokeResult, SmokeRunner

    class TelegramSmoke(SmokeTest):
        name = "telegram-send-receive"

        def run(self) -> SmokeResult:
            try:
                send_message(config, chat_id="123", message="ping")
                return SmokeResult.passed(self.name)
            except Exception as exc:
                return SmokeResult.failed(self.name, str(exc))

    runner = SmokeRunner([TelegramSmoke()])
    summary = runner.run_all()
    summary.raise_if_failed()
"""

from __future__ import annotations

import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class SmokeResult:
    """Result of a single smoke test.

    Attributes
    ----------
    name:
        Human-readable test name.
    passed:
        ``True`` when the test succeeded.
    message:
        Short summary of the outcome.
    details:
        Optional extended output (e.g. stack trace, response body).
    """

    name: str
    passed: bool
    message: str
    details: str = ""

    @classmethod
    def ok(cls, name: str, message: str = "ok", details: str = "") -> "SmokeResult":
        """Return a passing result."""
        return cls(name=name, passed=True, message=message, details=details)

    # Keep the original name as an alias for backward compatibility
    passed_result = ok

    @classmethod
    def failed(cls, name: str, message: str, details: str = "") -> "SmokeResult":
        """Return a failing result."""
        return cls(name=name, passed=False, message=message, details=details)

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.name}: {self.message}"


class SmokeTest(ABC):
    """Abstract base class for a single smoke test.

    Subclass and implement :meth:`run`.  Use :class:`SmokeRunner` to collect
    and execute multiple tests together::

        class MyServiceSmoke(SmokeTest):
            name = "my-service-ping"

            def run(self) -> SmokeResult:
                try:
                    response = ping_service()
                    return SmokeResult.ok(self.name, f"latency={response.latency_ms}ms")
                except Exception as exc:
                    return SmokeResult.failed(self.name, str(exc))
    """

    #: Override in subclasses to give each test a stable name.
    name: str = "unnamed-smoke-test"

    @abstractmethod
    def run(self) -> SmokeResult:
        """Execute the smoke test and return a :class:`SmokeResult`."""

    def run_safe(self) -> SmokeResult:
        """Execute :meth:`run`, catching any unexpected exceptions.

        Any unhandled exception is converted into a failing :class:`SmokeResult`
        so a runner can continue to the next test.
        """
        try:
            return self.run()
        except Exception as exc:  # noqa: BLE001
            return SmokeResult.failed(
                name=self.name,
                message=f"Unexpected exception: {type(exc).__name__}: {exc}",
                details=traceback.format_exc(),
            )


@dataclass
class SmokeSummary:
    """Aggregated results from a :class:`SmokeRunner` run.

    Attributes
    ----------
    results:
        All :class:`SmokeResult` objects, in execution order.
    """

    results: list[SmokeResult] = field(default_factory=list)

    @property
    def passed(self) -> list[SmokeResult]:
        return [r for r in self.results if r.passed]

    @property
    def failed(self) -> list[SmokeResult]:
        return [r for r in self.results if not r.passed]

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)

    def raise_if_failed(self) -> None:
        """Raise ``AssertionError`` if any test failed.

        Includes a summary of all failures::

            summary = runner.run_all()
            summary.raise_if_failed()
        """
        if self.failed:
            lines = [f"  {r}" for r in self.failed]
            raise AssertionError(
                f"{len(self.failed)} smoke test(s) failed:\n" + "\n".join(lines)
            )

    def __str__(self) -> str:
        total = len(self.results)
        n_pass = len(self.passed)
        n_fail = len(self.failed)
        lines = [f"Smoke tests: {n_pass}/{total} passed, {n_fail} failed"]
        for r in self.results:
            lines.append(f"  {r}")
        return "\n".join(lines)


class SmokeRunner:
    """Collect and execute multiple :class:`SmokeTest` instances.

    Usage::

        runner = SmokeRunner([
            TelegramSmoke(config),
            TwilioSmoke(config),
            GmailSmoke(config),
        ])
        summary = runner.run_all()
        print(summary)
        summary.raise_if_failed()
    """

    def __init__(self, tests: list[SmokeTest]) -> None:
        self._tests = tests

    def run_all(self) -> SmokeSummary:
        """Run every registered test and return a :class:`SmokeSummary`."""
        results = [test.run_safe() for test in self._tests]
        return SmokeSummary(results=results)
