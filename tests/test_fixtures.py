"""Tests for dyno_lab.fixtures: the pytest plugin loads, registers its markers and its fixtures work.

The fixtures only run inside a pytest session, so each test runs a small inner session in
this process with the plugin loaded by name, exactly as a downstream ``conftest.py`` would.
"""

from __future__ import annotations

import itertools
import tempfile
import textwrap
import unittest
from pathlib import Path

import pytest

from dyno_lab import fixtures
from dyno_lab.preflight import pytest_collection_modifyitems as preflight_hook

_COUNTER = itertools.count(1)


def run_inner(source: str, *extra: str) -> tuple[int, dict[str, str]]:
    """Run *source* as a test module under the plugin; return the exit code and outcome per test."""
    outcomes: dict[str, str] = {}

    class Collect:
        def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
            if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
                outcomes[report.nodeid.split("::")[-1]] = report.outcome

    with tempfile.TemporaryDirectory() as tmp:
        # A new module name each time: Python caches imported modules by name across sessions.
        path = Path(tmp) / f"test_inner_{next(_COUNTER)}.py"
        path.write_text(textwrap.dedent(source), encoding="utf-8")
        code = pytest.main(
            [
                "-p",
                "dyno_lab.fixtures",
                "-p",
                "no:cacheprovider",
                "--rootdir",
                tmp,
                "-q",
                "--no-header",
                str(path),
                *extra,
            ],
            plugins=[Collect()],
        )
    return int(code), outcomes


class TestPluginWiring(unittest.TestCase):
    def test_the_plugin_reuses_the_preflight_skip_hook(self):
        self.assertIs(fixtures.pytest_collection_modifyitems, preflight_hook)

    def test_its_markers_are_registered_so_strict_markers_accepts_them(self):
        code, outcomes = run_inner(
            """
            import pytest

            @pytest.mark.requires_env("DYNO_LAB_SURELY_UNSET_VARIABLE")
            def test_marked():
                raise AssertionError("must have been skipped")
            """,
            "--strict-markers",
        )
        self.assertEqual(outcomes, {"test_marked": "skipped"})
        self.assertEqual(code, 0)  # skipping is not failing

    def test_an_unregistered_marker_is_still_rejected_under_strict_markers(self):
        code, _ = run_inner(
            """
            import pytest

            @pytest.mark.not_a_dyno_lab_marker
            def test_marked():
                pass
            """,
            "--strict-markers",
        )
        self.assertNotEqual(code, 0)  # proves the previous test could have failed


class TestFixtures(unittest.TestCase):
    def test_dyno_tmp_gives_a_writable_directory_that_is_removed_afterwards(self):
        code, outcomes = run_inner(
            """
            seen = []

            def test_use(dyno_tmp):
                dyno_tmp.write("config.toml", "[project]\\nname = 'demo'\\n")
                dyno_tmp.assert_exists("config.toml")
                assert dyno_tmp.path.is_dir()
                seen.append(dyno_tmp.path)

            def test_gone():
                assert seen and not seen[0].exists()
            """,
        )
        self.assertEqual(outcomes, {"test_use": "passed", "test_gone": "passed"})
        self.assertEqual(code, 0)

    def test_dyno_env_sets_stringified_values_only_inside_the_block(self):
        code, outcomes = run_inner(
            """
            import os

            def test_env(dyno_env):
                assert "DYNO_FIXTURE_VAR" not in os.environ
                with dyno_env(DYNO_FIXTURE_VAR=5, OTHER="x"):
                    assert os.environ["DYNO_FIXTURE_VAR"] == "5"
                    assert os.environ["OTHER"] == "x"
                assert "DYNO_FIXTURE_VAR" not in os.environ
            """,
        )
        self.assertEqual((code, outcomes), (0, {"test_env": "passed"}))

    def test_dyno_proc_builds_a_recorder_with_the_defaults_it_was_given(self):
        code, outcomes = run_inner(
            """
            def test_proc(dyno_proc):
                plain = dyno_proc()
                assert plain.call_count == 0
                custom = dyno_proc(default_returncode=3, default_stdout="out", default_stderr="err")
                assert custom.call_count == 0
                assert custom is not plain
            """,
        )
        self.assertEqual((code, outcomes), (0, {"test_proc": "passed"}))

    def test_dyno_cli_captures_exit_code_and_both_streams(self):
        code, outcomes = run_inner(
            """
            import sys

            def main(args=None):
                print("hello", args)
                print("oops", file=sys.stderr)
                return 4

            def test_cli(dyno_cli):
                result = dyno_cli(main, ["go"])
                assert result.exit_code == 4
                assert "hello" in result.stdout and "go" in result.stdout
                assert "oops" in result.stderr
            """,
        )
        self.assertEqual((code, outcomes), (0, {"test_cli": "passed"}))


if __name__ == "__main__":
    unittest.main()
