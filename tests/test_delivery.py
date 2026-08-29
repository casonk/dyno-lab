"""Tests for the leased delivery conformance helper."""

from __future__ import annotations

import itertools
import unittest
from collections.abc import Mapping
from typing import Any

from dyno_lab.delivery import LeasedDeliveryDriver, assert_leased_delivery_contract


class _InMemoryDelivery:
    def __init__(self) -> None:
        self._operation_id = "operation-1"
        self._payload: dict[str, Any] | None = None
        self._status = "empty"
        self._tokens = itertools.count(1)

    def enqueue(self, payload: Mapping[str, Any]) -> str:
        self._payload = dict(payload)
        self._status = "pending"
        return self._operation_id

    def claim(self, worker_id: str) -> dict[str, Any] | None:
        if self._status != "pending" or self._payload is None:
            return None
        self._status = "leased"
        return {
            "operation_id": self._operation_id,
            "lease_token": f"lease-{next(self._tokens)}",
            "payload": dict(self._payload),
            "worker_id": worker_id,
        }

    def complete(self, claim: Mapping[str, Any], worker_id: str) -> None:
        if claim["worker_id"] != worker_id:
            raise AssertionError("wrong worker")
        self._status = "complete"

    def fail(
        self,
        claim: Mapping[str, Any],
        worker_id: str,
        problem: Mapping[str, Any],
        retry_after_seconds: int,
    ) -> None:
        if claim["worker_id"] != worker_id or problem["code"] != "dyno-conformance-retry":
            raise AssertionError("unexpected retry")
        if retry_after_seconds != 0:
            raise AssertionError("expected immediate retry")
        self._status = "pending"


class LeasedDeliveryContractTests(unittest.TestCase):
    def test_exercises_enqueue_retry_and_completion(self) -> None:
        queue = _InMemoryDelivery()
        exercise = assert_leased_delivery_contract(
            LeasedDeliveryDriver(
                enqueue=queue.enqueue,
                claim=queue.claim,
                complete=queue.complete,
                fail=queue.fail,
            ),
            {"message": "hello"},
        )

        self.assertEqual(exercise.operation_id, "operation-1")
        self.assertNotEqual(exercise.first_lease_token, exercise.retry_lease_token)

    def test_rejects_adapter_that_reuses_a_lease_token(self) -> None:
        queue = _InMemoryDelivery()
        original_claim = queue.claim

        def reused_token(worker_id: str) -> dict[str, Any] | None:
            value = original_claim(worker_id)
            if value is not None:
                value["lease_token"] = "same-token"
            return value

        with self.assertRaisesRegex(AssertionError, "fresh lease token"):
            assert_leased_delivery_contract(
                LeasedDeliveryDriver(
                    enqueue=queue.enqueue,
                    claim=reused_token,
                    complete=queue.complete,
                    fail=queue.fail,
                ),
                {"message": "hello"},
            )
