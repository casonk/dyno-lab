"""Conformance helper for durable, leased at-least-once delivery adapters.

The helper deliberately knows no provider, database, or retry scheduler. A
downstream adapter supplies four small callbacks and proves the invariant that
a pending operation is claimed with a token, may be requeued, receives a new
lease on retry, and disappears only after completion.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

Claim = Mapping[str, Any]


@dataclass(frozen=True)
class LeasedDeliveryDriver:
    """Callback adapter for :func:`assert_leased_delivery_contract`.

    ``claim`` must return ``None`` when no due work exists. A returned claim
    must include an operation ID, a lease token, and the original payload.
    ``fail`` must make a zero-delay retry due, while ``complete`` must remove
    the command from future claims.
    """

    enqueue: Callable[[Mapping[str, Any]], str]
    claim: Callable[[str], Claim | None]
    complete: Callable[[Claim, str], None]
    fail: Callable[[Claim, str, Mapping[str, Any], int], None]


@dataclass(frozen=True)
class LeasedDeliveryExercise:
    """Useful evidence returned by a successful contract exercise."""

    operation_id: str
    first_lease_token: str
    retry_lease_token: str


def _require_claim(claim: Claim | None, *, expected_payload: Mapping[str, Any]) -> Claim:
    if claim is None:
        raise AssertionError("expected a due delivery claim, but queue was empty")
    for key in ("operation_id", "lease_token"):
        if key not in claim or not isinstance(claim[key], str):
            raise AssertionError(f"delivery claim must contain {key!r} as text")
    if "payload" not in claim or not isinstance(claim["payload"], Mapping):
        raise AssertionError("delivery claim must contain an object payload")
    if dict(claim["payload"]) != dict(expected_payload):
        raise AssertionError("delivery claim payload differs from the enqueued payload")
    return claim


def assert_leased_delivery_contract(
    driver: LeasedDeliveryDriver,
    payload: Mapping[str, Any],
    *,
    first_worker: str = "dyno-first-worker",
    retry_worker: str = "dyno-retry-worker",
) -> LeasedDeliveryExercise:
    """Exercise the minimal safe lifecycle for a leased delivery adapter.

    The function asserts one enqueue, one leased claim, a zero-delay retry,
    one replacement lease, and a final completion. It is intentionally a
    narrow conformance smoke test, not a replacement for an adapter's detailed
    provider, database, and failure-injection suite.
    """

    expected_payload = dict(payload)
    operation_id = driver.enqueue(expected_payload)
    if not isinstance(operation_id, str) or not operation_id.strip():
        raise AssertionError("enqueue must return a non-empty operation ID")

    first_claim = _require_claim(driver.claim(first_worker), expected_payload=expected_payload)
    if first_claim["operation_id"] != operation_id:
        raise AssertionError("claim operation ID does not match the enqueued operation")
    driver.fail(
        first_claim,
        first_worker,
        {"code": "dyno-conformance-retry"},
        0,
    )

    retry_claim = _require_claim(driver.claim(retry_worker), expected_payload=expected_payload)
    if retry_claim["operation_id"] != operation_id:
        raise AssertionError("retry claim did not preserve the operation identity")
    if retry_claim["lease_token"] == first_claim["lease_token"]:
        raise AssertionError("retry claim must issue a fresh lease token")
    driver.complete(retry_claim, retry_worker)
    if driver.claim("dyno-empty-worker") is not None:
        raise AssertionError("completed delivery remained claimable")

    return LeasedDeliveryExercise(
        operation_id=operation_id,
        first_lease_token=str(first_claim["lease_token"]),
        retry_lease_token=str(retry_claim["lease_token"]),
    )
