"""Tests for dyno_lab.module — dynamic module loading."""

import tempfile
import unittest
from pathlib import Path

from dyno_lab.module import load_module_by_path


class TestLoadModuleByPath(unittest.TestCase):
    def test_loads_module_with_simple_function(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod_file = Path(tmp) / "my_util.py"
            mod_file.write_text("def greet(name): return f'hello {name}'\n", encoding="utf-8")

            mod = load_module_by_path(mod_file)
            self.assertEqual(mod.greet("world"), "hello world")

    def test_loads_module_relative_to_repo_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subdir = root / "scripts"
            subdir.mkdir()
            script = subdir / "helper.py"
            script.write_text("ANSWER = 42\n", encoding="utf-8")

            mod = load_module_by_path("scripts/helper.py", repo_root=root)
            self.assertEqual(mod.ANSWER, 42)

    def test_raises_for_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            load_module_by_path("/tmp/__dyno_lab_no_such_file__.py")

    def test_custom_module_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod_file = Path(tmp) / "compute.py"
            mod_file.write_text("result = 7 * 6\n", encoding="utf-8")

            mod = load_module_by_path(mod_file, module_name="custom_compute")
            self.assertEqual(mod.result, 42)

    def test_safe_reference_parsing_rejects_exploit(self):
        """Mirrors the pushshift_python pattern: safe parse should reject __import__."""
        with tempfile.TemporaryDirectory() as tmp:
            mod_file = Path(tmp) / "safe_parse.py"
            mod_file.write_text(
                """
import ast

def safe_parse(value):
    if not isinstance(value, str):
        return []
    try:
        parsed = ast.literal_eval(value)
    except (ValueError, SyntaxError):
        raise ValueError(f"unsafe or unparseable: {value!r}")
    if not isinstance(parsed, list):
        raise ValueError(f"expected list, got {type(parsed).__name__}")
    return parsed
""",
                encoding="utf-8",
            )

            mod = load_module_by_path(mod_file)
            self.assertEqual(mod.safe_parse("['a', 'b']"), ["a", "b"])
            with self.assertRaises(ValueError):
                mod.safe_parse("__import__('os').system('echo unsafe')")


if __name__ == "__main__":
    unittest.main()
