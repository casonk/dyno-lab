"""Tests for dyno_lab.env — environment variable patching utilities."""

import os
import unittest

from dyno_lab.env import EnvPatch, env_defaults, patched_env


class TestEnvDefaults(unittest.TestCase):
    def test_returns_string_dict(self):
        result = env_defaults(MY_VAR="value", OTHER_VAR="123")
        self.assertEqual(result, {"MY_VAR": "value", "OTHER_VAR": "123"})

    def test_coerces_non_string_values(self):
        result = env_defaults(PORT="8080", DEBUG="True")
        self.assertIsInstance(result["PORT"], str)


class TestEnvPatch(unittest.TestCase):
    def test_context_manager_sets_env(self):
        with EnvPatch({"DYNO_TEST_VAR": "hello"}):
            self.assertEqual(os.environ.get("DYNO_TEST_VAR"), "hello")

    def test_context_manager_restores_on_exit(self):
        original = os.environ.get("DYNO_TEST_VAR2", "__absent__")
        with EnvPatch({"DYNO_TEST_VAR2": "temporary"}):
            self.assertEqual(os.environ["DYNO_TEST_VAR2"], "temporary")
        self.assertEqual(os.environ.get("DYNO_TEST_VAR2", "__absent__"), original)

    def test_preserves_unrelated_env_vars(self):
        os.environ["DYNO_PRESERVE_ME"] = "keep"
        with EnvPatch({"DYNO_NEW_VAR": "new"}):
            self.assertEqual(os.environ.get("DYNO_PRESERVE_ME"), "keep")
        del os.environ["DYNO_PRESERVE_ME"]

    def test_decorator_mode_applies_env(self):
        captured: list[str] = []

        @EnvPatch.decorator({"DYNO_DEC_VAR": "decorated"})
        def inner():
            captured.append(os.environ.get("DYNO_DEC_VAR", "missing"))

        inner()
        self.assertEqual(captured, ["decorated"])

    def test_decorator_restores_after_call(self):
        @EnvPatch.decorator({"DYNO_DEC_RESTORE": "temp"})
        def inner():
            pass

        inner()
        self.assertNotIn("DYNO_DEC_RESTORE", os.environ)


class TestPatchedEnv(unittest.TestCase):
    def test_sets_and_restores_env(self):
        with patched_env(DYNO_INLINE="inline_val"):
            self.assertEqual(os.environ.get("DYNO_INLINE"), "inline_val")
        self.assertNotIn("DYNO_INLINE", os.environ)

    def test_multiple_keys(self):
        with patched_env(KEY_A="a", KEY_B="b"):
            self.assertEqual(os.environ.get("KEY_A"), "a")
            self.assertEqual(os.environ.get("KEY_B"), "b")


if __name__ == "__main__":
    unittest.main()
