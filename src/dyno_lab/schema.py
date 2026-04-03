"""Schema and contract validation helpers.

Covers the provider-parity and row-width patterns from personal-finance,
and the schema-shape validation patterns from doseido.

Usage::

    from dyno_lab.schema import assert_row_width, assert_parity, assert_schema_keys

    # Validate that every provider module produces identically shaped rows:
    assert_parity(
        [module_a, module_b, module_c],
        factory=lambda m: m.StatementRecord(**base_kwargs()),
        extractor=lambda r: r.as_row(),
        attribute="row width",
    )

    # Validate that a row has exactly the expected number of columns:
    assert_row_width(record.as_row(), expected=19)

    # Validate that a dict contains all required keys:
    assert_schema_keys(payload, required=["id", "name", "status"])
"""

from __future__ import annotations

from typing import Any


def assert_row_width(row: list[Any] | tuple[Any, ...], expected: int) -> None:
    """Assert that *row* has exactly *expected* elements.

    Raises ``AssertionError`` with a descriptive message on mismatch::

        assert_row_width(record.as_row(), expected=19)
    """
    actual = len(row)
    if actual != expected:
        raise AssertionError(
            f"Row width mismatch: expected {expected} columns, got {actual}."
            f"\nRow: {row!r}"
        )


def assert_schema_keys(
    mapping: dict[str, Any],
    required: list[str],
    *,
    label: str = "mapping",
) -> None:
    """Assert that *mapping* contains every key in *required*.

    Extra keys are allowed.  Missing keys raise ``AssertionError``::

        assert_schema_keys(payload, required=["id", "name", "status"])
    """
    missing = [k for k in required if k not in mapping]
    if missing:
        raise AssertionError(
            f"{label} is missing required keys: {missing!r}\n"
            f"Available keys: {list(mapping.keys())!r}"
        )


def assert_schema_shape(
    mapping: dict[str, Any],
    expected: dict[str, type],
    *,
    label: str = "mapping",
) -> None:
    """Assert that every key in *expected* exists in *mapping* with the right type.

    Example::

        assert_schema_shape(record, {
            "id": str,
            "amount": float,
            "active": bool,
        })
    """
    errors: list[str] = []
    for key, expected_type in expected.items():
        if key not in mapping:
            errors.append(f"missing key {key!r}")
        elif not isinstance(mapping[key], expected_type):
            errors.append(
                f"{key!r}: expected {expected_type.__name__}, "
                f"got {type(mapping[key]).__name__} ({mapping[key]!r})"
            )
    if errors:
        raise AssertionError(f"{label} schema errors:\n  " + "\n  ".join(errors))


def assert_parity(
    modules: list[Any],
    factory: Any,
    extractor: Any,
    *,
    attribute: str = "result",
) -> None:
    """Assert that every module in *modules* produces the same shape.

    Parameters
    ----------
    modules:
        List of module objects (or any objects) to compare.
    factory:
        Callable ``(module) -> object`` that produces the thing to compare.
    extractor:
        Callable ``(result) -> comparable_value`` that extracts the
        attribute to compare.  A common pattern is ``lambda r: len(r.as_row())``.
    attribute:
        Human-readable name of the attribute being compared (for error messages).

    Example — all provider modules produce a 19-column row::

        assert_parity(
            [bank_hunt, bank_macu, cred_co],
            factory=lambda m: m.StatementRecord(**base_kwargs()),
            extractor=lambda r: len(r.as_row()),
            attribute="row width",
        )
    """
    if not modules:
        return

    results = [(m, extractor(factory(m))) for m in modules]
    reference_module, reference_value = results[0]
    mismatches: list[str] = []
    for mod, value in results[1:]:
        if value != reference_value:
            mismatches.append(
                f"  {getattr(mod, '__name__', repr(mod))}: "
                f"{attribute}={value!r} (expected {reference_value!r} from "
                f"{getattr(reference_module, '__name__', repr(reference_module))})"
            )
    if mismatches:
        raise AssertionError(
            f"Provider parity failure for {attribute}:\n" + "\n".join(mismatches)
        )


def assert_unique_keys(
    specs: list[Any], key_attr: str = "key", label: str = "specs"
) -> None:
    """Assert that every object in *specs* has a unique value for *key_attr*.

    Covers the ``test_provider_keys_are_unique`` pattern::

        assert_unique_keys(PROVIDER_SPECS, key_attr="key")
    """
    keys = [getattr(s, key_attr) for s in specs]
    seen: set[Any] = set()
    dupes: list[Any] = []
    for k in keys:
        if k in seen:
            dupes.append(k)
        seen.add(k)
    if dupes:
        raise AssertionError(f"{label}: duplicate {key_attr} values found: {dupes!r}")
