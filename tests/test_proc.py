"""Tests for dyno_lab.proc — subprocess mocking utilities."""

import subprocess
import unittest

from dyno_lab.proc import (
    ProcessRecorder,
    SubprocessPatch,
    build_completed_process,
)


class TestBuildCompletedProcess(unittest.TestCase):
    def test_defaults_produce_zero_returncode(self):
        result = build_completed_process()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")

    def test_custom_values_are_set(self):
        result = build_completed_process(
            args=["my", "cmd"],
            returncode=1,
            stdout="out",
            stderr="err",
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "out")
        self.assertEqual(result.stderr, "err")
        self.assertEqual(result.args, ["my", "cmd"])


class TestProcessRecorder(unittest.TestCase):
    def test_records_calls(self):
        recorder = ProcessRecorder(default_stdout="ok")
        recorder(["cmd", "a"])
        recorder(["cmd", "b"])
        self.assertEqual(recorder.call_count, 2)
        self.assertEqual(recorder.commands(), [["cmd", "a"], ["cmd", "b"]])

    def test_returns_default_when_no_responses(self):
        recorder = ProcessRecorder(default_returncode=0, default_stdout="done")
        result = recorder(["cmd"])
        self.assertEqual(result.stdout, "done")
        self.assertEqual(result.returncode, 0)

    def test_pops_scripted_responses_in_order(self):
        recorder = ProcessRecorder(
            responses=[
                build_completed_process(stdout="first"),
                build_completed_process(returncode=1, stderr="second-err"),
            ]
        )
        r1 = recorder(["cmd"])
        r2 = recorder(["cmd"])
        self.assertEqual(r1.stdout, "first")
        self.assertEqual(r2.returncode, 1)
        self.assertEqual(r2.stderr, "second-err")

    def test_falls_back_to_default_after_responses_exhausted(self):
        recorder = ProcessRecorder(
            responses=[build_completed_process(stdout="scripted")],
            default_stdout="fallback",
        )
        recorder(["cmd"])
        r2 = recorder(["cmd"])
        self.assertEqual(r2.stdout, "fallback")

    def test_stdin_inputs_captured(self):
        recorder = ProcessRecorder()
        recorder(["cmd"], input="password\n")
        recorder(["cmd"], input="second\n")
        self.assertEqual(recorder.stdin_inputs(), ["password\n", "second\n"])


class TestSubprocessPatch(unittest.TestCase):
    def test_patches_subprocess_run(self):
        recorder = ProcessRecorder(default_stdout="patched")
        with SubprocessPatch(recorder):
            result = subprocess.run(["echo", "hi"], capture_output=True, text=True)
        self.assertEqual(result.stdout, "patched")
        self.assertEqual(recorder.call_count, 1)
        self.assertEqual(recorder.calls[0].args, ["echo", "hi"])

    def test_restores_after_context_exit(self):
        recorder = ProcessRecorder(default_stdout="fake")
        with SubprocessPatch(recorder):
            pass
        # After exiting, real subprocess.run should work again
        result = subprocess.run(["echo", "real"], capture_output=True, text=True)
        self.assertIn("real", result.stdout)


if __name__ == "__main__":
    unittest.main()
