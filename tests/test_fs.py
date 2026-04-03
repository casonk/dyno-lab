"""Tests for dyno_lab.fs — filesystem fixture utilities."""

import unittest

from dyno_lab.fs import TempWorkdir, make_tree


class TestMakeTree(unittest.TestCase):
    def test_creates_nested_files(self):
        with TempWorkdir() as wd:
            make_tree(
                wd.path,
                {
                    "AGENTS.md": "agents\n",
                    "src/pkg/__init__.py": "",
                    "src/pkg/core.py": "VALUE = 1\n",
                    "tests/test_core.py": "def test_pass(): pass\n",
                },
            )
            self.assertTrue((wd.path / "AGENTS.md").is_file())
            self.assertTrue((wd.path / "src" / "pkg" / "core.py").is_file())
            self.assertTrue((wd.path / "tests" / "test_core.py").is_file())

    def test_file_content_is_preserved(self):
        with TempWorkdir() as wd:
            make_tree(wd.path, {"README.md": "# Hello\n"})
            content = (wd.path / "README.md").read_text(encoding="utf-8")
            self.assertEqual(content, "# Hello\n")


class TestTempWorkdir(unittest.TestCase):
    def test_path_is_valid_directory(self):
        with TempWorkdir() as wd:
            self.assertTrue(wd.path.is_dir())

    def test_write_creates_file(self):
        with TempWorkdir() as wd:
            p = wd.write("hello.txt", "world\n")
            self.assertTrue(p.is_file())
            self.assertEqual(p.read_text(encoding="utf-8"), "world\n")

    def test_write_creates_nested_directories(self):
        with TempWorkdir() as wd:
            wd.write("a/b/c.txt", "deep\n")
            self.assertTrue((wd.path / "a" / "b" / "c.txt").is_file())

    def test_read_returns_file_content(self):
        with TempWorkdir() as wd:
            wd.write("data.txt", "line1\nline2\n")
            content = wd.read("data.txt")
            self.assertEqual(content, "line1\nline2\n")

    def test_mkdir_creates_directory(self):
        with TempWorkdir() as wd:
            d = wd.mkdir("sub/dir")
            self.assertTrue(d.is_dir())

    def test_populate_creates_tree(self):
        with TempWorkdir() as wd:
            wd.populate(
                {
                    "README.md": "# Repo\n",
                    "src/__init__.py": "",
                }
            )
            wd.assert_exists("README.md")
            wd.assert_exists("src/__init__.py")

    def test_assert_exists_passes_for_present_file(self):
        with TempWorkdir() as wd:
            wd.write("present.txt", "x")
            wd.assert_exists("present.txt")

    def test_assert_exists_raises_for_absent_file(self):
        with TempWorkdir() as wd, self.assertRaises(AssertionError):
            wd.assert_exists("absent.txt")

    def test_assert_not_exists_passes_for_absent_file(self):
        with TempWorkdir() as wd:
            wd.assert_not_exists("not-here.txt")

    def test_assert_not_exists_raises_for_present_file(self):
        with TempWorkdir() as wd:
            wd.write("present.txt", "x")
            with self.assertRaises(AssertionError):
                wd.assert_not_exists("present.txt")

    def test_assert_contains_passes_when_text_present(self):
        with TempWorkdir() as wd:
            wd.write("notes.txt", "important content")
            wd.assert_contains("notes.txt", "important")

    def test_assert_contains_raises_when_text_absent(self):
        with TempWorkdir() as wd:
            wd.write("notes.txt", "nothing here")
            with self.assertRaises(AssertionError):
                wd.assert_contains("notes.txt", "expected_text")

    def test_directory_cleaned_up_after_exit(self):
        with TempWorkdir() as wd:
            captured_path = wd.path
            wd.write("temp.txt", "data")
        self.assertFalse(captured_path.exists())


if __name__ == "__main__":
    unittest.main()
