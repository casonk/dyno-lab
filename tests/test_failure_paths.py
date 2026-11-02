"""The branches where a dyno-lab helper must fail, or refuse, correctly.

A test helper that fails to fail is a silent bug in every suite that uses it, so each case
here feeds a helper something wrong and checks it complains, and says what is wrong.
"""

from __future__ import annotations

import datetime
import itertools
import tempfile
import unittest
import warnings
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from dyno_lab import preflight
from dyno_lab.auto_pass import AutoPassRecorder
from dyno_lab.base import DynoTestCase
from dyno_lab.cli import CliResult
from dyno_lab.delivery import LeasedDeliveryDriver, assert_leased_delivery_contract
from dyno_lab.http import RaisingSession, StaticSession
from dyno_lab.markers import MARKERS, register_markers
from dyno_lab.module import load_module_by_path
from dyno_lab.time import FrozenTime


class TestBaseAssertionsFail(DynoTestCase):
    def test_assertDirExists_fails_for_a_missing_directory_and_names_it(self):
        with self.assertRaisesRegex(AssertionError, "Expected directory does not exist"):
            self.assertDirExists("/tmp/__dyno_lab_no_such_directory__")

    def test_assertDirExists_fails_for_a_file(self):
        with tempfile.NamedTemporaryFile() as f, self.assertRaises(AssertionError):
            self.assertDirExists(f.name)

    def test_assertFileNotContains_fails_when_the_text_is_there(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8") as f:
            f.write("a secret value")
            f.flush()
            with self.assertRaisesRegex(AssertionError, "Did not expect 'secret'"):
                self.assertFileNotContains(f.name, "secret")
            self.assertFileNotContains(f.name, "absent")  # and passes when it is not

    def test_assertApproxEqual_against_zero_uses_an_absolute_tolerance(self):
        self.assertApproxEqual(0.0, 0, rel=1e-6)
        self.assertApproxEqual(1e-9, 0, rel=1e-6)
        with self.assertRaisesRegex(AssertionError, "not approximately equal to 0"):
            self.assertApproxEqual(0.01, 0, rel=1e-6)

    def test_assertApproxEqual_a_custom_message_replaces_the_default(self):
        with self.assertRaisesRegex(AssertionError, "custom words"):
            self.assertApproxEqual(5, 0, msg="custom words")


class TestCliResultAssertionsFail(unittest.TestCase):
    def test_assert_failure_rejects_a_successful_exit(self):
        with self.assertRaisesRegex(AssertionError, "succeeded but failure was expected"):
            CliResult(exit_code=0, stdout="", stderr="").assert_failure()

    def test_assert_failure_checks_the_expected_code_when_given(self):
        result = CliResult(exit_code=2, stdout="", stderr="")
        result.assert_failure()
        result.assert_failure(2)
        with self.assertRaisesRegex(AssertionError, "Expected exit code 3, got 2"):
            result.assert_failure(3)

    def test_assert_error_contains_shows_what_stderr_actually_held(self):
        result = CliResult(exit_code=1, stdout="", stderr="the real error text")
        result.assert_error_contains("real error")
        with self.assertRaises(AssertionError) as caught:
            result.assert_error_contains("something else")
        self.assertIn("Expected 'something else' in stderr", str(caught.exception))
        self.assertIn("the real error text", str(caught.exception))

    def test_a_long_stderr_is_truncated_in_the_message(self):
        result = CliResult(exit_code=1, stdout="", stderr="x" * 2000)
        with self.assertRaises(AssertionError) as caught:
            result.assert_error_contains("nope")
        self.assertLess(len(str(caught.exception)), 700)


class _Queue:
    """A correct in-memory leased queue; subclasses break one rule at a time."""

    def __init__(self) -> None:
        self.status = "empty"
        self.payload: dict[str, Any] = {}
        self.tokens = itertools.count(1)

    def enqueue(self, payload: Mapping[str, Any]) -> str:
        self.payload, self.status = dict(payload), "pending"
        return "op-1"

    def claim(self, worker: str) -> dict[str, Any] | None:
        if self.status != "pending":
            return None
        self.status = "leased"
        return {
            "operation_id": "op-1",
            "lease_token": f"lease-{next(self.tokens)}",
            "payload": dict(self.payload),
        }

    def complete(self, claim: Mapping[str, Any], worker: str) -> None:
        self.status = "complete"

    def fail(
        self, claim: Mapping[str, Any], worker: str, error: Mapping[str, Any], delay: int
    ) -> None:
        self.status = "pending"

    def driver(self) -> LeasedDeliveryDriver:
        return LeasedDeliveryDriver(self.enqueue, self.claim, self.complete, self.fail)


class TestDeliveryContractRejectsBrokenAdapters(unittest.TestCase):
    PAYLOAD = {"kind": "message", "to": "x"}

    def check(self, queue: _Queue, pattern: str) -> None:
        with self.assertRaisesRegex(AssertionError, pattern):
            assert_leased_delivery_contract(queue.driver(), self.PAYLOAD)

    def test_a_correct_adapter_passes_and_reports_both_lease_tokens(self):
        result = assert_leased_delivery_contract(_Queue().driver(), self.PAYLOAD)
        self.assertEqual(result.operation_id, "op-1")
        self.assertNotEqual(result.first_lease_token, result.retry_lease_token)

    def test_a_blank_operation_id_is_rejected(self):
        class Blank(_Queue):
            def enqueue(self, payload):
                super().enqueue(payload)
                return "   "

        self.check(Blank(), "non-empty operation ID")

    def test_an_empty_queue_after_enqueue_is_rejected(self):
        class Empty(_Queue):
            def claim(self, worker):
                return None

        self.check(Empty(), "queue was empty")

    def test_a_claim_without_text_ids_is_rejected(self):
        for field in ("operation_id", "lease_token"):
            with self.subTest(field=field):

                class Missing(_Queue):
                    def claim(self, worker, field=field):
                        claim = super().claim(worker)
                        if claim is not None:
                            claim.pop(field)
                        return claim

                self.check(Missing(), f"must contain '{field}' as text")

        class NotText(_Queue):
            def claim(self, worker):
                claim = super().claim(worker)
                if claim is not None:
                    claim["lease_token"] = 7
                return claim

        self.check(NotText(), "must contain 'lease_token' as text")

    def test_a_claim_without_an_object_payload_is_rejected(self):
        for bad in (None, "text", ["list"]):
            with self.subTest(payload=bad):

                class Bad(_Queue):
                    def claim(self, worker, bad=bad):
                        claim = super().claim(worker)
                        if claim is not None:
                            claim["payload"] = bad
                        return claim

                self.check(Bad(), "must contain an object payload")

    def test_a_changed_payload_is_rejected(self):
        class Changed(_Queue):
            def claim(self, worker):
                claim = super().claim(worker)
                if claim is not None:
                    claim["payload"] = {"kind": "other"}
                return claim

        self.check(Changed(), "payload differs from the enqueued payload")

    def test_a_claim_for_a_different_operation_is_rejected(self):
        class Wrong(_Queue):
            def claim(self, worker):
                claim = super().claim(worker)
                if claim is not None:
                    claim["operation_id"] = "someone-else"
                return claim

        self.check(Wrong(), "does not match the enqueued operation")

    def test_a_retry_that_changes_identity_is_rejected(self):
        # The first claim must pass its own check, so the identity changes only on the second call.
        class DriftsOnRetry(_Queue):
            calls = 0

            def claim(self, worker):
                claim = super().claim(worker)
                DriftsOnRetry.calls += 1
                if claim is not None and DriftsOnRetry.calls == 2:
                    claim["operation_id"] = "drifted"
                return claim

        DriftsOnRetry.calls = 0
        self.check(DriftsOnRetry(), "retry claim did not preserve the operation identity")

    def test_a_retry_that_reuses_the_lease_token_is_rejected(self):
        class SameToken(_Queue):
            def claim(self, worker):
                claim = super().claim(worker)
                if claim is not None:
                    claim["lease_token"] = "always-the-same"
                return claim

        self.check(SameToken(), "must issue a fresh lease token")

    def test_a_completed_operation_that_can_still_be_claimed_is_rejected(self):
        class NeverDone(_Queue):
            def complete(self, claim, worker):
                self.status = "pending"  # complete() forgets to remove it

        self.check(NeverDone(), "completed delivery remained claimable")


class TestRecorderAndSessions(unittest.TestCase):
    def test_a_list_of_responses_is_consumed_in_order_and_then_runs_out(self):
        recorder = AutoPassRecorder({"entry": [{"a": "1"}, {"a": "2"}]})
        self.assertEqual(recorder.resolve_keepassxc_entry("entry", {"a": "a"}), {"a": "1"})
        self.assertEqual(recorder.resolve_keepassxc_entry("entry", {"a": "a"}), {"a": "2"})
        with self.assertRaisesRegex(AssertionError, "Unexpected auto-pass entry lookup: 'entry'"):
            recorder.resolve_keepassxc_entry("entry", {"a": "a"})

    def test_add_response_extends_an_existing_entry_and_creates_a_new_one(self):
        recorder = AutoPassRecorder({"entry": {"a": "1"}})
        recorder.add_response("entry", {"a": "2"})
        recorder.add_response("other", [{"b": "x"}, {"b": "y"}])
        self.assertEqual(recorder.resolve_keepassxc_entry("entry", {})["a"], "1")
        self.assertEqual(recorder.resolve_keepassxc_entry("entry", {})["a"], "2")
        self.assertEqual(recorder.resolve_keepassxc_entry("other", {})["b"], "x")
        self.assertEqual(recorder.resolve_keepassxc_entry("other", {})["b"], "y")

    def test_an_unknown_entry_fails_loudly_rather_than_returning_nothing(self):
        with self.assertRaises(AssertionError):
            AutoPassRecorder().resolve_keepassxc_entry("never-scripted", {})

    def test_a_callable_response_receives_the_entry_and_a_copy_of_the_attrs(self):
        seen: dict[str, Any] = {}

        def respond(*, entry: str, attrs_map: dict[str, str]) -> dict[str, str]:
            seen.update(entry=entry, attrs=attrs_map)
            attrs_map["mutated"] = "yes"  # must not leak back into the caller's dict
            return {"password": "from-callable"}

        recorder = AutoPassRecorder({"entry": respond})
        attrs = {"password": "password"}
        self.assertEqual(
            recorder.resolve_keepassxc_entry("entry", attrs), {"password": "from-callable"}
        )
        self.assertEqual(seen["entry"], "entry")
        self.assertNotIn("mutated", attrs)

    def test_both_fake_sessions_work_as_context_managers_and_do_not_swallow_errors(self):
        with StaticSession("body") as session:
            self.assertIsInstance(session, StaticSession)
        with RaisingSession(RuntimeError("boom")) as raising:
            self.assertIsInstance(raising, RaisingSession)
            with self.assertRaisesRegex(RuntimeError, "boom"):
                raising.get("http://example.invalid")
        with self.assertRaises(KeyError), StaticSession():
            raise KeyError("propagates")
        with self.assertRaises(KeyError), RaisingSession():
            raise KeyError("propagates")


class TestPreflightPieces(unittest.TestCase):
    def test_require_port_and_require_url_register_labelled_checks(self):
        suite = (
            preflight.PreflightSuite()
            .require_port("db.local", 5432)
            .require_url("http://x.test/health")
        )
        with (
            patch.object(preflight, "check_port", return_value=True) as port,
            patch.object(preflight, "check_url", return_value=False) as url,
        ):
            report = suite.run()
        port.assert_called_once_with("db.local", 5432, 2.0)
        url.assert_called_once_with("http://x.test/health", 5.0)
        self.assertEqual(
            {r.label: r.passed for r in report.results},
            {"port:db.local:5432": True, "url:http://x.test/health": False},
        )
        self.assertFalse(report.all_passed)

    def test_a_check_that_raises_counts_as_failed_not_as_a_crash(self):
        suite = preflight.PreflightSuite().require_env("A_VARIABLE")
        with patch.object(preflight, "check_env", side_effect=RuntimeError("surprise")):
            report = suite.run()  # must not raise
        self.assertFalse(report.all_passed)
        self.assertEqual([r.label for r in report.failed], ["env:A_VARIABLE"])
        self.assertEqual(report.passed, [])

    def test_the_skip_decorators_build_the_marks_the_plugin_reads(self):
        # This repository's own session does not load the plugin that registers these marks,
        # so pytest warns that they are unknown; that is not what is being tested.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", pytest.PytestUnknownMarkWarning)
            for factory, name, args in (
                (preflight.requires_tool, "requires_tool", ("git", "make")),
                (preflight.requires_env, "requires_env", ("TOKEN",)),
                (preflight.requires_import, "requires_import", ("yaml",)),
            ):
                with self.subTest(mark=name):
                    mark = factory(*args)
                    self.assertEqual(mark.name, name)
                    self.assertEqual(mark.args, args)


class TestMarkersModuleAndTime(unittest.TestCase):
    def test_register_markers_adds_every_marker_with_its_description(self):
        lines: list[str] = []

        class Config:
            def addinivalue_line(self, name: str, line: str) -> None:
                lines.append(f"{name}|{line}")

        register_markers(Config())
        self.assertEqual(len(lines), len(MARKERS))
        for name, description in MARKERS.items():
            self.assertIn(f"markers|{name}: {description}", lines)

    def test_a_file_python_cannot_load_is_an_import_error_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            odd = Path(tmp) / "notpython.unknownext"
            odd.write_text("x = 1\n", encoding="utf-8")
            with self.assertRaisesRegex(ImportError, "Could not create module spec"):
                load_module_by_path(str(odd))

    def test_a_missing_module_file_is_reported_as_not_found(self):
        with self.assertRaises(FileNotFoundError):
            load_module_by_path("/tmp/__dyno_lab_no_such_module__.py")

    def test_frozen_utcnow_is_the_frozen_instant_without_a_timezone(self):
        instant = datetime.datetime(2026, 11, 2, 12, 30, tzinfo=datetime.timezone.utc)
        with FrozenTime(instant):
            now = datetime.datetime.utcnow()  # noqa: DTZ003 - the thing under test
        self.assertEqual(now, datetime.datetime(2026, 11, 2, 12, 30))
        self.assertIsNone(now.tzinfo)


if __name__ == "__main__":
    unittest.main()
