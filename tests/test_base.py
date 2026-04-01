"""Tests for dyno_lab.base — DynoTestCase extended assertions."""

import tempfile
import unittest

from dyno_lab.base import DynoTestCase


class TestFileAssertions(DynoTestCase):
    def test_assertFileExists_passes_for_real_file(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            path = f.name
        self.assertFileExists(path)

    def test_assertFileExists_fails_for_missing_file(self):
        with self.assertRaises(AssertionError):
            self.assertFileExists("/tmp/__dyno_lab_does_not_exist__.txt")

    def test_assertDirExists_passes_for_real_dir(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertDirExists(d)

    def test_assertFileContains_passes_when_present(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("hello world\n")
            path = f.name
        self.assertFileContains(path, "hello")

    def test_assertFileContains_fails_when_absent(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("nothing special\n")
            path = f.name
        with self.assertRaises(AssertionError):
            self.assertFileContains(path, "MISSING_TEXT")

    def test_assertFileNotContains_passes_when_absent(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("safe content\n")
            path = f.name
        self.assertFileNotContains(path, "forbidden")


class TestCollectionAssertions(DynoTestCase):
    def test_assertContainsAll_passes_when_all_present(self):
        self.assertContainsAll(["a", "b", "c"], ["a", "b"])

    def test_assertContainsAll_fails_when_item_missing(self):
        with self.assertRaises(AssertionError):
            self.assertContainsAll(["a", "b"], ["a", "z"])

    def test_assertNoneOf_passes_when_none_present(self):
        self.assertNoneOf(["a", "b", "c"], ["x", "y"])

    def test_assertNoneOf_fails_when_item_present(self):
        with self.assertRaises(AssertionError):
            self.assertNoneOf(["a", "b", "c"], ["b"])

    def test_assertDictSubset_passes_for_matching_subset(self):
        self.assertDictSubset({"key": "val"}, {"key": "val", "extra": 1})

    def test_assertDictSubset_fails_for_wrong_value(self):
        with self.assertRaises(AssertionError):
            self.assertDictSubset({"key": "wrong"}, {"key": "val"})

    def test_assertDictSubset_fails_for_missing_key(self):
        with self.assertRaises(AssertionError):
            self.assertDictSubset({"missing": "x"}, {"key": "val"})


class TestNumericAssertions(DynoTestCase):
    def test_assertApproxEqual_passes_for_close_values(self):
        self.assertApproxEqual(1.0000001, 1.0)

    def test_assertApproxEqual_fails_for_distant_values(self):
        with self.assertRaises(AssertionError):
            self.assertApproxEqual(1.5, 1.0)

    def test_assertApproxEqual_handles_zero(self):
        self.assertApproxEqual(0.0, 0.0)


class TestCLIAssertions(DynoTestCase):
    def test_assertExitCode_passes_for_zero(self):
        self.assertExitCode(0)

    def test_assertExitCode_fails_for_nonzero(self):
        with self.assertRaises(AssertionError):
            self.assertExitCode(1)

    def test_assertOutputContains_passes(self):
        self.assertOutputContains("hello world", "hello")

    def test_assertOutputContains_fails_when_absent(self):
        with self.assertRaises(AssertionError):
            self.assertOutputContains("hello world", "goodbye")


if __name__ == "__main__":
    unittest.main()
