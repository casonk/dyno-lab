"""Tests for dyno_lab.schema — schema and contract validation helpers."""

import unittest
from dataclasses import dataclass
from typing import Any

from dyno_lab.schema import (
    assert_parity,
    assert_row_width,
    assert_schema_keys,
    assert_schema_shape,
    assert_unique_keys,
)


class TestAssertRowWidth(unittest.TestCase):
    def test_passes_for_correct_width(self):
        assert_row_width(["a", "b", "c"], expected=3)

    def test_fails_for_wrong_width(self):
        with self.assertRaises(AssertionError) as ctx:
            assert_row_width(["a", "b"], expected=3)
        self.assertIn("expected 3", str(ctx.exception))
        self.assertIn("got 2", str(ctx.exception))


class TestAssertSchemaKeys(unittest.TestCase):
    def test_passes_when_all_keys_present(self):
        assert_schema_keys({"id": 1, "name": "x", "extra": True}, required=["id", "name"])

    def test_fails_when_key_missing(self):
        with self.assertRaises(AssertionError) as ctx:
            assert_schema_keys({"id": 1}, required=["id", "status"])
        self.assertIn("status", str(ctx.exception))


class TestAssertSchemaShape(unittest.TestCase):
    def test_passes_for_correct_types(self):
        assert_schema_shape(
            {"id": "abc", "amount": 1.5, "active": True},
            {
                "id": str,
                "amount": float,
                "active": bool,
            },
        )

    def test_fails_for_wrong_type(self):
        with self.assertRaises(AssertionError) as ctx:
            assert_schema_shape({"id": 123}, {"id": str})
        self.assertIn("id", str(ctx.exception))

    def test_fails_for_missing_key(self):
        with self.assertRaises(AssertionError) as ctx:
            assert_schema_shape({}, {"id": str})
        self.assertIn("missing key", str(ctx.exception))


class _FakeModule:
    """Simulates a provider module."""

    def __init__(self, name: str, row_width: int) -> None:
        self.__name__ = name
        self._width = row_width

    class _Record:
        def __init__(self, width: int) -> None:
            self._width = width

        def as_row(self) -> list[Any]:
            return ["x"] * self._width

    def make_record(self) -> "_FakeModule._Record":
        return self._Record(self._width)


class TestAssertParity(unittest.TestCase):
    def test_passes_when_all_match(self):
        modules = [_FakeModule("a", 5), _FakeModule("b", 5), _FakeModule("c", 5)]
        assert_parity(
            modules,
            factory=lambda m: m.make_record(),
            extractor=lambda r: len(r.as_row()),
            attribute="row width",
        )

    def test_fails_when_one_differs(self):
        modules = [_FakeModule("a", 5), _FakeModule("b", 4)]
        with self.assertRaises(AssertionError) as ctx:
            assert_parity(
                modules,
                factory=lambda m: m.make_record(),
                extractor=lambda r: len(r.as_row()),
                attribute="row width",
            )
        self.assertIn("row width", str(ctx.exception))
        self.assertIn("b", str(ctx.exception))

    def test_empty_modules_list_does_not_raise(self):
        assert_parity([], factory=lambda m: m, extractor=lambda r: r)


@dataclass
class _Spec:
    key: str


class TestAssertUniqueKeys(unittest.TestCase):
    def test_passes_for_unique_keys(self):
        specs = [_Spec("alpha"), _Spec("beta"), _Spec("gamma")]
        assert_unique_keys(specs)

    def test_fails_for_duplicate_keys(self):
        specs = [_Spec("alpha"), _Spec("beta"), _Spec("alpha")]
        with self.assertRaises(AssertionError) as ctx:
            assert_unique_keys(specs)
        self.assertIn("alpha", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
