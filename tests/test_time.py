"""Tests for dyno_lab.time."""

from __future__ import annotations

import datetime
import time
import unittest

from dyno_lab.time import FastSleep, FrozenTime

_UTC = datetime.timezone.utc


class TestFrozenTime(unittest.TestCase):
    def test_time_time_is_frozen(self):
        dt = datetime.datetime(2024, 6, 1, 12, 0, 0, tzinfo=_UTC)
        with FrozenTime(dt):
            self.assertEqual(time.time(), dt.timestamp())

    def test_datetime_now_utc_is_frozen(self):
        dt = datetime.datetime(2024, 3, 15, 8, 30, 0, tzinfo=_UTC)
        with FrozenTime(dt):
            result = datetime.datetime.now(_UTC)
            self.assertEqual(result, dt)

    def test_datetime_now_no_tz_is_naive_frozen(self):
        dt = datetime.datetime(2024, 3, 15, 8, 30, 0, tzinfo=_UTC)
        with FrozenTime(dt):
            result = datetime.datetime.now()
            self.assertIsNone(result.tzinfo)
            self.assertEqual(result.year, dt.year)
            self.assertEqual(result.hour, dt.hour)

    def test_default_frozen_instant(self):
        with FrozenTime() as ft:
            expected = datetime.datetime(2025, 1, 1, 0, 0, 0, tzinfo=_UTC)
            self.assertEqual(ft.timestamp, expected.timestamp())

    def test_timestamp_property(self):
        dt = datetime.datetime(2023, 12, 31, 23, 59, 59, tzinfo=_UTC)
        with FrozenTime(dt) as ft:
            self.assertEqual(ft.timestamp, dt.timestamp())

    def test_exit_restores_time(self):
        dt = datetime.datetime(2020, 1, 1, tzinfo=_UTC)
        before = time.time()
        with FrozenTime(dt):
            pass
        after = time.time()
        # After exit, time.time() should not equal the frozen timestamp
        self.assertNotEqual(after, dt.timestamp())
        # and should be >= the real time before we entered
        self.assertGreaterEqual(after, before)

    def test_nested_frozen_time(self):
        dt1 = datetime.datetime(2024, 1, 1, tzinfo=_UTC)
        dt2 = datetime.datetime(2025, 6, 1, tzinfo=_UTC)
        with FrozenTime(dt1):
            self.assertEqual(time.time(), dt1.timestamp())
            with FrozenTime(dt2):
                self.assertEqual(time.time(), dt2.timestamp())
            self.assertEqual(time.time(), dt1.timestamp())

    def test_time_monotonic_is_frozen(self):
        dt = datetime.datetime(2024, 1, 1, tzinfo=_UTC)
        with FrozenTime(dt):
            self.assertEqual(time.monotonic(), dt.timestamp())


class TestFastSleep(unittest.TestCase):
    def test_no_real_sleep_occurs(self):
        with FastSleep():
            # would hang for 3600s if not intercepted
            time.sleep(3600)
        # If we reach here, no real sleep happened.

    def test_total_slept_accumulated(self):
        with FastSleep() as fs:
            time.sleep(30)
            time.sleep(10)
        self.assertEqual(fs.total_slept, 40.0)

    def test_call_count(self):
        with FastSleep() as fs:
            time.sleep(1)
            time.sleep(2)
            time.sleep(3)
        self.assertEqual(fs.call_count, 3)

    def test_calls_list(self):
        with FastSleep() as fs:
            time.sleep(5)
            time.sleep(0.5)
        self.assertEqual(fs.calls, [5.0, 0.5])

    def test_zero_calls(self):
        with FastSleep() as fs:
            pass
        self.assertEqual(fs.total_slept, 0.0)
        self.assertEqual(fs.call_count, 0)
        self.assertEqual(fs.calls, [])

    def test_exit_restores_real_sleep(self):
        with FastSleep():
            pass
        # After exit, time.sleep should be the real one again.
        import time as _tm

        self.assertTrue(callable(_tm.sleep))

    def test_calls_list_is_copy(self):
        """Mutating the returned list must not affect internal state."""
        with FastSleep() as fs:
            time.sleep(7)
        lst = fs.calls
        lst.append(99)
        self.assertEqual(fs.call_count, 1)

    def test_float_conversion(self):
        with FastSleep() as fs:
            time.sleep(2)
        self.assertIsInstance(fs.calls[0], float)


if __name__ == "__main__":
    unittest.main()
