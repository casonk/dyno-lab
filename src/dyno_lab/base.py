"""Extended base test case for portfolio-wide unittest usage.

Usage::

    from dyno_lab.base import DynoTestCase

    class MyTests(DynoTestCase):
        def test_something(self):
            self.assertFileExists(path)
            self.assertFileContains(path, "expected text")
            self.assertContainsAll(["a", "b", "c"], ["a", "b"])
            self.assertDictSubset({"key": "val"}, full_dict)
"""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any


class DynoTestCase(unittest.TestCase):
    """``unittest.TestCase`` with additional assertions common across the portfolio."""

    # ------------------------------------------------------------------ #
    # Filesystem assertions
    # ------------------------------------------------------------------ #

    def assertFileExists(self, path: str | Path, msg: str | None = None) -> None:
        """Assert that *path* exists and is a file."""
        p = Path(path)
        if not p.is_file():
            self.fail(msg or f"Expected file does not exist: {p}")

    def assertDirExists(self, path: str | Path, msg: str | None = None) -> None:
        """Assert that *path* exists and is a directory."""
        p = Path(path)
        if not p.is_dir():
            self.fail(msg or f"Expected directory does not exist: {p}")

    def assertFileContains(self, path: str | Path, text: str, msg: str | None = None) -> None:
        """Assert that the file at *path* contains the substring *text*."""
        content = Path(path).read_text(encoding="utf-8")
        if text not in content:
            self.fail(msg or f"Expected {text!r} in {path}.\nActual content:\n{content[:500]}")

    def assertFileNotContains(self, path: str | Path, text: str, msg: str | None = None) -> None:
        """Assert that the file at *path* does NOT contain the substring *text*."""
        content = Path(path).read_text(encoding="utf-8")
        if text in content:
            self.fail(msg or f"Did not expect {text!r} in {path}.")

    # ------------------------------------------------------------------ #
    # Collection assertions
    # ------------------------------------------------------------------ #

    def assertContainsAll(
        self,
        container: Any,
        items: list[Any],
        msg: str | None = None,
    ) -> None:
        """Assert that every element of *items* is in *container*."""
        missing = [item for item in items if item not in container]
        if missing:
            self.fail(msg or f"Missing items: {missing!r}")

    def assertNoneOf(
        self,
        container: Any,
        items: list[Any],
        msg: str | None = None,
    ) -> None:
        """Assert that none of *items* appear in *container*."""
        present = [item for item in items if item in container]
        if present:
            self.fail(msg or f"Unexpected items found: {present!r}")

    def assertDictSubset(
        self,
        subset: dict[str, Any],
        whole: dict[str, Any],
        msg: str | None = None,
    ) -> None:
        """Assert that every key/value in *subset* appears in *whole*."""
        mismatches: list[str] = []
        for key, expected in subset.items():
            if key not in whole:
                mismatches.append(f"missing key {key!r}")
            elif whole[key] != expected:
                mismatches.append(f"{key!r}: expected {expected!r}, got {whole[key]!r}")
        if mismatches:
            self.fail(msg or "Dict subset mismatch:\n  " + "\n  ".join(mismatches))

    # ------------------------------------------------------------------ #
    # Numeric assertions
    # ------------------------------------------------------------------ #

    def assertApproxEqual(
        self,
        first: float,
        second: float,
        rel: float = 1e-6,
        msg: str | None = None,
    ) -> None:
        """Assert that two floats are within *rel* relative tolerance of each other."""
        if second == 0:
            if abs(first) > rel:
                self.fail(msg or f"{first} not approximately equal to 0 (rel={rel})")
            return
        if abs(first - second) / abs(second) > rel:
            self.fail(msg or f"{first} not approximately equal to {second} (rel={rel})")

    # ------------------------------------------------------------------ #
    # CLI / output assertions
    # ------------------------------------------------------------------ #

    def assertExitCode(self, code: int, expected: int = 0, msg: str | None = None) -> None:
        """Assert that an exit code equals *expected*."""
        if code != expected:
            self.fail(msg or f"Expected exit code {expected}, got {code}")

    def assertOutputContains(
        self, output: str, text: str, label: str = "output", msg: str | None = None
    ) -> None:
        """Assert that a captured output string contains *text*."""
        if text not in output:
            self.fail(msg or f"Expected {text!r} in {label}.\nActual:\n{output[:500]}")
