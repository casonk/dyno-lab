"""Tests for dyno_lab.smoke — smoke test scaffolding."""

import unittest

from dyno_lab.smoke import SmokeResult, SmokeRunner, SmokeTest


class _AlwaysPassSmoke(SmokeTest):
    name = "always-pass"

    def run(self) -> SmokeResult:
        return SmokeResult.ok(self.name, "service healthy")


class _AlwaysFailSmoke(SmokeTest):
    name = "always-fail"

    def run(self) -> SmokeResult:
        return SmokeResult.failed(self.name, "connection refused")


class _RaisesSmoke(SmokeTest):
    name = "raises-unexpectedly"

    def run(self) -> SmokeResult:
        raise RuntimeError("unexpected crash")


class TestSmokeResult(unittest.TestCase):
    def test_ok_creates_passing_result(self):
        r = SmokeResult.ok("my-test", "all good")
        self.assertTrue(r.passed)
        self.assertEqual(r.message, "all good")

    def test_failed_creates_failing_result(self):
        r = SmokeResult.failed("my-test", "timeout")
        self.assertFalse(r.passed)
        self.assertIn("timeout", r.message)

    def test_str_shows_pass_status(self):
        r = SmokeResult.ok("ping", "ok")
        self.assertIn("PASS", str(r))
        self.assertIn("ping", str(r))

    def test_str_shows_fail_status(self):
        r = SmokeResult.failed("ping", "err")
        self.assertIn("FAIL", str(r))


class TestSmokeTestRunSafe(unittest.TestCase):
    def test_run_safe_returns_result_normally(self):
        result = _AlwaysPassSmoke().run_safe()
        self.assertTrue(result.passed)

    def test_run_safe_catches_unexpected_exceptions(self):
        result = _RaisesSmoke().run_safe()
        self.assertFalse(result.passed)
        self.assertIn("RuntimeError", result.message)
        self.assertIn("unexpected crash", result.message)


class TestSmokeRunner(unittest.TestCase):
    def test_all_passed_when_all_tests_pass(self):
        runner = SmokeRunner([_AlwaysPassSmoke(), _AlwaysPassSmoke()])
        summary = runner.run_all()
        self.assertTrue(summary.all_passed)
        self.assertEqual(len(summary.passed), 2)
        self.assertEqual(len(summary.failed), 0)

    def test_all_failed_collected_in_summary(self):
        runner = SmokeRunner([_AlwaysPassSmoke(), _AlwaysFailSmoke()])
        summary = runner.run_all()
        self.assertFalse(summary.all_passed)
        self.assertEqual(len(summary.failed), 1)
        self.assertEqual(summary.failed[0].name, "always-fail")

    def test_exception_in_test_does_not_abort_runner(self):
        runner = SmokeRunner([_RaisesSmoke(), _AlwaysPassSmoke()])
        summary = runner.run_all()
        self.assertEqual(len(summary.results), 2)

    def test_raise_if_failed_raises_on_failure(self):
        runner = SmokeRunner([_AlwaysFailSmoke()])
        summary = runner.run_all()
        with self.assertRaises(AssertionError) as ctx:
            summary.raise_if_failed()
        self.assertIn("always-fail", str(ctx.exception))

    def test_raise_if_failed_passes_when_all_ok(self):
        runner = SmokeRunner([_AlwaysPassSmoke()])
        summary = runner.run_all()
        summary.raise_if_failed()  # should not raise

    def test_summary_str_shows_counts(self):
        runner = SmokeRunner([_AlwaysPassSmoke(), _AlwaysFailSmoke()])
        summary = runner.run_all()
        text = str(summary)
        self.assertIn("1/2", text)


if __name__ == "__main__":
    unittest.main()
