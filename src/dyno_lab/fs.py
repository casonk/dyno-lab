"""Filesystem fixture utilities.

Covers the ``tempfile.TemporaryDirectory`` / ``tmp_path`` patterns
used in archility, auto-pass, intake, and personal-finance.

Usage (context manager)::

    from dyno_lab.fs import TempWorkdir, make_tree

    with TempWorkdir() as wd:
        wd.write("config.json", '{"key": "value"}')
        wd.write("data/input.txt", "line1\\nline2")
        assert (wd.path / "config.json").exists()
        wd.assert_exists("config.json")
        wd.assert_contains("config.json", "key")

Usage (make_tree)::

    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        make_tree(root, {
            "AGENTS.md": "agents\\n",
            "src/mypackage/__init__.py": "",
            "src/mypackage/core.py": "VALUE = 1\\n",
            "tests/test_core.py": "def test_value(): assert VALUE == 1\\n",
        })
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any


def make_tree(root: Path, files: dict[str, str]) -> None:
    """Create a tree of files under *root* from a ``{relative_path: content}`` dict.

    Intermediate directories are created automatically::

        make_tree(root, {
            "AGENTS.md": "agents\\n",
            "docs/diagrams/repo-architecture.puml": "@startuml\\n@enduml\\n",
        })
    """
    for rel_path, content in files.items():
        target = root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


class TempWorkdir:
    """A temporary working directory with convenience helpers.

    Implements the context manager protocol — the temp dir is removed on exit.

    Attributes
    ----------
    path:
        The root ``Path`` of the temporary directory.

    Example::

        with TempWorkdir() as wd:
            wd.write("config.toml", "[project]\\nname = 'demo'\\n")
            (wd.path / "src").mkdir()
            wd.assert_exists("config.toml")
            wd.assert_contains("config.toml", "demo")
    """

    def __init__(self) -> None:
        self._tmpdir: tempfile.TemporaryDirectory[str] | None = None
        self.path: Path = Path()

    def __enter__(self) -> "TempWorkdir":
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name)
        return self

    def __exit__(self, *args: Any) -> None:
        if self._tmpdir is not None:
            self._tmpdir.cleanup()

    # ------------------------------------------------------------------ #
    # File helpers
    # ------------------------------------------------------------------ #

    def write(self, rel_path: str, content: str, encoding: str = "utf-8") -> Path:
        """Write *content* to *rel_path* (creating parents as needed).

        Returns the absolute ``Path`` of the created file.
        """
        target = self.path / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding=encoding)
        return target

    def read(self, rel_path: str, encoding: str = "utf-8") -> str:
        """Read and return the text content of *rel_path*."""
        return (self.path / rel_path).read_text(encoding=encoding)

    def mkdir(self, rel_path: str) -> Path:
        """Create a directory at *rel_path* (and any parents).

        Returns the absolute ``Path`` of the created directory.
        """
        target = self.path / rel_path
        target.mkdir(parents=True, exist_ok=True)
        return target

    def populate(self, files: dict[str, str]) -> None:
        """Populate the workdir from a ``{relative_path: content}`` dict.

        Equivalent to calling :func:`make_tree` on ``self.path``::

            wd.populate({
                "src/pkg/__init__.py": "",
                "tests/test_pkg.py": "def test_pass(): pass\\n",
            })
        """
        make_tree(self.path, files)

    # ------------------------------------------------------------------ #
    # Assertion helpers
    # ------------------------------------------------------------------ #

    def assert_exists(self, rel_path: str) -> None:
        """Raise ``AssertionError`` if *rel_path* does not exist."""
        target = self.path / rel_path
        if not target.exists():
            raise AssertionError(f"Expected path does not exist: {target}")

    def assert_not_exists(self, rel_path: str) -> None:
        """Raise ``AssertionError`` if *rel_path* exists."""
        target = self.path / rel_path
        if target.exists():
            raise AssertionError(f"Path should not exist but does: {target}")

    def assert_contains(self, rel_path: str, text: str) -> None:
        """Raise ``AssertionError`` if *rel_path* does not contain *text*."""
        content = self.read(rel_path)
        if text not in content:
            raise AssertionError(
                f"Expected {text!r} in {rel_path}.\nActual:\n{content[:500]}"
            )
