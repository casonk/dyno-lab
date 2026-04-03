"""Tests for dyno_lab.preflight."""

from __future__ import annotations

import os
import socket
import unittest
from unittest.mock import MagicMock, patch

from dyno_lab.preflight import (
    PreflightError,
    PreflightSuite,
    check_env,
    check_import,
    check_port,
    check_tool,
    check_url,
    pytest_collection_modifyitems,
)

# ---------------------------------------------------------------------------
# check_tool
# ---------------------------------------------------------------------------


class TestCheckTool(unittest.TestCase):
    def test_found_tool(self):
        """A tool that exists (python) is reported as found."""
        self.assertTrue(check_tool("python") or check_tool("python3"))

    def test_missing_tool(self):
        """A nonsense tool name returns False."""
        self.assertFalse(check_tool("__nonexistent_tool_xyz__"))

    def test_which_none_returns_false(self):
        with patch("shutil.which", return_value=None):
            self.assertFalse(check_tool("anything"))

    def test_which_path_returns_true(self):
        with patch("shutil.which", return_value="/usr/bin/git"):
            self.assertTrue(check_tool("git"))


# ---------------------------------------------------------------------------
# check_import
# ---------------------------------------------------------------------------


class TestCheckImport(unittest.TestCase):
    def test_stdlib_module(self):
        self.assertTrue(check_import("os"))

    def test_missing_package(self):
        self.assertFalse(check_import("__no_such_package_xyz__"))

    def test_importerror_returns_false(self):
        with patch("importlib.import_module", side_effect=ImportError("nope")):
            self.assertFalse(check_import("anything"))


# ---------------------------------------------------------------------------
# check_env
# ---------------------------------------------------------------------------


class TestCheckEnv(unittest.TestCase):
    def test_present_nonempty(self):
        with patch.dict(os.environ, {"MY_TEST_KEY": "hello"}):
            self.assertTrue(check_env("MY_TEST_KEY"))

    def test_missing_key(self):
        env_copy = {k: v for k, v in os.environ.items() if k != "MY_MISSING_KEY"}
        with patch.dict(os.environ, env_copy, clear=True):
            self.assertFalse(check_env("MY_MISSING_KEY"))

    def test_empty_string_is_false(self):
        with patch.dict(os.environ, {"MY_EMPTY": ""}):
            self.assertFalse(check_env("MY_EMPTY"))


# ---------------------------------------------------------------------------
# check_port
# ---------------------------------------------------------------------------


class TestCheckPort(unittest.TestCase):
    def test_refused_connection_returns_false(self):
        self.assertFalse(check_port("127.0.0.1", 19999, timeout=0.1))

    def test_successful_connection_returns_true(self):
        # Create a real listening socket so we have something to connect to.
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        _, port = server.getsockname()
        try:
            self.assertTrue(check_port("127.0.0.1", port, timeout=2.0))
        finally:
            server.close()

    def test_exception_returns_false(self):
        with patch("socket.create_connection", side_effect=OSError("fail")):
            self.assertFalse(check_port("127.0.0.1", 80))


# ---------------------------------------------------------------------------
# check_url
# ---------------------------------------------------------------------------


class TestCheckUrl(unittest.TestCase):
    def test_success_returns_true(self):
        fake_resp = MagicMock()
        fake_resp.status = 200
        fake_resp.__enter__ = lambda s: s
        fake_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=fake_resp):
            self.assertTrue(check_url("http://example.com"))

    def test_error_status_returns_false(self):
        fake_resp = MagicMock()
        fake_resp.status = 404
        fake_resp.__enter__ = lambda s: s
        fake_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=fake_resp):
            self.assertFalse(check_url("http://example.com/missing"))

    def test_exception_returns_false(self):
        with patch("urllib.request.urlopen", side_effect=OSError("unreachable")):
            self.assertFalse(check_url("http://192.0.2.1/nowhere"))


# ---------------------------------------------------------------------------
# PreflightSuite / PreflightReport
# ---------------------------------------------------------------------------


class TestPreflightSuite(unittest.TestCase):
    def test_all_pass_when_conditions_met(self):
        report = (
            PreflightSuite()
            .require_tool("python" if check_tool("python") else "python3")
            .require_import("os")
            .run()
        )
        self.assertTrue(report.all_passed)
        self.assertEqual(len(report.failed), 0)

    def test_failure_recorded_for_missing_tool(self):
        report = PreflightSuite().require_tool("__no_such_tool_xyz__").run()
        self.assertFalse(report.all_passed)
        self.assertEqual(len(report.failed), 1)

    def test_mixed_results(self):
        report = (
            PreflightSuite()
            .require_tool("__no_such_tool_xyz__")
            .require_import("os")
            .run()
        )
        self.assertEqual(len(report.passed), 1)
        self.assertEqual(len(report.failed), 1)

    def test_raise_if_failed_raises_preflight_error(self):
        report = PreflightSuite().require_tool("__no_such_tool_xyz__").run()
        with self.assertRaises(PreflightError):
            report.raise_if_failed()

    def test_raise_if_failed_silent_on_all_pass(self):
        report = PreflightSuite().require_import("os").run()
        report.raise_if_failed()  # must not raise

    def test_str_representation(self):
        report = PreflightSuite().require_import("os").run()
        text = str(report)
        self.assertIn("Pre-flight", text)
        self.assertIn("passed", text)

    def test_require_env_pass(self):
        with patch.dict(os.environ, {"SOME_VAR": "yes"}):
            report = PreflightSuite().require_env("SOME_VAR").run()
        self.assertTrue(report.all_passed)

    def test_require_env_fail(self):
        env_copy = {k: v for k, v in os.environ.items() if k != "ABSENT_VAR"}
        with patch.dict(os.environ, env_copy, clear=True):
            report = PreflightSuite().require_env("ABSENT_VAR").run()
        self.assertFalse(report.all_passed)

    def test_multiple_tools_chained(self):
        report = (
            PreflightSuite()
            .require_tool("python" if check_tool("python") else "python3")
            .require_tool("sh")
            .run()
        )
        self.assertEqual(len(report.results), 2)


# ---------------------------------------------------------------------------
# pytest_collection_modifyitems hook
# ---------------------------------------------------------------------------


class TestPytestCollectionHook(unittest.TestCase):
    def _make_item(self, markers_by_name: dict):
        """Build a fake pytest item whose iter_markers returns pre-built Mark objects."""
        item = MagicMock()

        def _iter_markers(name):
            return markers_by_name.get(name, [])

        item.iter_markers = _iter_markers
        item.add_marker = MagicMock()
        return item

    def _mark(self, name: str, *args: str):
        """Create a lightweight stand-in for a pytest Mark."""
        m = MagicMock()
        m.name = name
        m.args = args
        return m

    def test_skip_added_for_missing_tool(self):
        mark = self._mark("requires_tool", "__no_such_tool_xyz__")
        item = self._make_item({"requires_tool": [mark]})
        pytest_collection_modifyitems([item], MagicMock())
        item.add_marker.assert_called_once()
        reason = str(item.add_marker.call_args[0][0])
        self.assertIn("requires tool on PATH", reason)

    def test_no_skip_for_present_tool(self):
        tool = "python" if check_tool("python") else "python3"
        mark = self._mark("requires_tool", tool)
        item = self._make_item({"requires_tool": [mark]})
        pytest_collection_modifyitems([item], MagicMock())
        item.add_marker.assert_not_called()

    def test_skip_added_for_missing_env(self):
        env_copy = {k: v for k, v in os.environ.items() if k != "ABSENT_ENV_VAR"}
        mark = self._mark("requires_env", "ABSENT_ENV_VAR")
        item = self._make_item({"requires_env": [mark]})
        with patch.dict(os.environ, env_copy, clear=True):
            pytest_collection_modifyitems([item], MagicMock())
        item.add_marker.assert_called_once()

    def test_skip_added_for_missing_import(self):
        mark = self._mark("requires_import", "__no_such_pkg__")
        item = self._make_item({"requires_import": [mark]})
        pytest_collection_modifyitems([item], MagicMock())
        item.add_marker.assert_called_once()


if __name__ == "__main__":
    unittest.main()
