"""Tests for dyno_lab.log."""

from __future__ import annotations

import logging
import unittest

from dyno_lab.log import LogCapture


class TestLogCapture(unittest.TestCase):
    def test_captures_warning(self):
        with LogCapture("test.cap", level=logging.DEBUG) as lc:
            logging.getLogger("test.cap").warning("something went wrong")
        self.assertEqual(lc.count(logging.WARNING), 1)

    def test_captures_multiple_levels(self):
        with LogCapture("test.multi") as lc:
            log = logging.getLogger("test.multi")
            log.debug("debug message")
            log.info("info message")
            log.error("error message")
        self.assertEqual(lc.count(), 3)
        self.assertEqual(lc.count(logging.DEBUG), 1)
        self.assertEqual(lc.count(logging.INFO), 1)
        self.assertEqual(lc.count(logging.ERROR), 1)

    def test_messages_returns_text(self):
        with LogCapture("test.msgs") as lc:
            logging.getLogger("test.msgs").info("hello world")
        self.assertIn("hello world", lc.messages())

    def test_messages_filtered_by_level(self):
        with LogCapture("test.filter") as lc:
            log = logging.getLogger("test.filter")
            log.warning("warn this")
            log.info("ignore this")
        warn_msgs = lc.messages(logging.WARNING)
        self.assertEqual(warn_msgs, ["warn this"])

    def test_assert_logged_passes(self):
        with LogCapture("test.assert") as lc:
            logging.getLogger("test.assert").error("critical failure")
        lc.assert_logged(logging.ERROR, "critical failure")  # must not raise

    def test_assert_logged_fails(self):
        with LogCapture("test.assert2") as lc:
            logging.getLogger("test.assert2").info("something else")
        with self.assertRaises(AssertionError):
            lc.assert_logged(logging.ERROR, "missing text")

    def test_assert_not_logged_passes(self):
        with LogCapture("test.notlog") as lc:
            logging.getLogger("test.notlog").info("benign message")
        lc.assert_not_logged(logging.ERROR, "benign message")  # must not raise

    def test_assert_not_logged_fails(self):
        with LogCapture("test.notlog2") as lc:
            logging.getLogger("test.notlog2").error("bad thing happened")
        with self.assertRaises(AssertionError):
            lc.assert_not_logged(logging.ERROR, "bad thing")

    def test_records_property(self):
        with LogCapture("test.recs") as lc:
            logging.getLogger("test.recs").warning("rec test")
        recs = lc.records
        self.assertEqual(len(recs), 1)
        self.assertIsInstance(recs[0], logging.LogRecord)

    def test_root_logger_capture(self):
        with LogCapture(None) as lc:
            logging.getLogger().warning("root warning")
        self.assertGreaterEqual(lc.count(logging.WARNING), 1)

    def test_handler_removed_after_exit(self):
        logger = logging.getLogger("test.cleanup")
        before = len(logger.handlers)
        with LogCapture("test.cleanup"):
            pass
        self.assertEqual(len(logger.handlers), before)

    def test_count_zero_when_nothing_logged(self):
        with LogCapture("test.empty") as lc:
            pass
        self.assertEqual(lc.count(), 0)


if __name__ == "__main__":
    unittest.main()
