"""Tests for dyno_lab.cli — CLI capture and invocation helpers."""

import sys
import unittest

from dyno_lab.base import DynoTestCase
from dyno_lab.cli import CliResult, CLITestMixin, capture_cli


def _exit_zero(args):
    print("success output")
    return 0


def _exit_one(args):
    print("error output", file=sys.stderr)
    return 1


def _echo_args(args):
    print(" ".join(args))
    return 0


def _echo_stdin(args):
    line = sys.stdin.readline()
    print(f"got: {line.strip()}")
    return 0


class TestCaptureCliFunction(unittest.TestCase):
    def test_captures_stdout_and_exit_code(self):
        code, out, err = capture_cli(_exit_zero)
        self.assertEqual(code, 0)
        self.assertIn("success output", out)
        self.assertEqual(err, "")

    def test_captures_stderr_on_failure(self):
        code, out, err = capture_cli(_exit_one)
        self.assertEqual(code, 1)
        self.assertIn("error output", err)

    def test_passes_args_to_function(self):
        code, out, _ = capture_cli(_echo_args, ["hello", "world"])
        self.assertIn("hello world", out)

    def test_captures_stdin_input(self):
        code, out, _ = capture_cli(_echo_stdin, stdin="test_line\n")
        self.assertEqual(code, 0)
        self.assertIn("test_line", out)


class TestCliResult(unittest.TestCase):
    def test_assert_success_passes_for_zero(self):
        result = CliResult(exit_code=0, stdout="ok", stderr="")
        result.assert_success()

    def test_assert_success_raises_for_nonzero(self):
        result = CliResult(exit_code=1, stdout="", stderr="err")
        with self.assertRaises(AssertionError):
            result.assert_success()

    def test_assert_failure_passes_for_nonzero(self):
        result = CliResult(exit_code=2, stdout="", stderr="")
        result.assert_failure()

    def test_assert_failure_checks_exact_code(self):
        result = CliResult(exit_code=2, stdout="", stderr="")
        with self.assertRaises(AssertionError):
            result.assert_failure(expected_code=1)

    def test_assert_output_contains_passes(self):
        result = CliResult(exit_code=0, stdout="Connected", stderr="")
        result.assert_output_contains("Connected")

    def test_assert_output_contains_raises_when_absent(self):
        result = CliResult(exit_code=0, stdout="nope", stderr="")
        with self.assertRaises(AssertionError):
            result.assert_output_contains("Connected")

    def test_assert_error_contains_passes(self):
        result = CliResult(exit_code=1, stdout="", stderr="boom")
        result.assert_error_contains("boom")

    def test_output_property_aliases_stdout(self):
        result = CliResult(exit_code=0, stdout="hello", stderr="")
        self.assertEqual(result.output, "hello")


class TestCLITestMixin(CLITestMixin, DynoTestCase):
    def test_run_cli_returns_cli_result(self):
        result = self.run_cli(_exit_zero)
        self.assertIsInstance(result, CliResult)
        self.assertExitCode(result.exit_code)

    def test_run_cli_captures_stderr(self):
        result = self.run_cli(_exit_one)
        self.assertIn("error output", result.stderr)


if __name__ == "__main__":
    unittest.main()
