"""Time and datetime mocking utilities.

Provides context managers that freeze or accelerate time in tests without
requiring third-party libraries such as *freezegun*.

Usage::

    import datetime
    import time
    from dyno_lab.time import FrozenTime, FastSleep

    # Freeze time at a fixed instant:
    dt = datetime.datetime(2024, 6, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
    with FrozenTime(dt) as ft:
        assert time.time() == dt.timestamp()
        assert datetime.datetime.now(datetime.timezone.utc) == dt
        assert ft.timestamp == dt.timestamp()

    # Replace sleep() with a no-op recorder:
    with FastSleep() as fs:
        time.sleep(30)
        time.sleep(10)
    assert fs.total_slept == 40.0
    assert fs.call_count == 2
    assert fs.calls == [30, 10]
"""

from __future__ import annotations

import datetime
from typing import Any
from unittest.mock import patch

_UTC = datetime.timezone.utc
_DEFAULT_FROZEN = datetime.datetime(2025, 1, 1, 0, 0, 0, tzinfo=_UTC)


class FrozenTime:
    """Freeze :func:`time.time`, :func:`time.monotonic`, and
    :meth:`datetime.datetime.now`.

    Parameters
    ----------
    frozen:
        The :class:`datetime.datetime` instant to freeze at.  Defaults to
        ``2025-01-01T00:00:00Z``.

    Usage::

        dt = datetime.datetime(2024, 6, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        with FrozenTime(dt) as ft:
            assert time.time() == dt.timestamp()
            assert datetime.datetime.now(datetime.timezone.utc) == dt
            assert ft.timestamp == dt.timestamp()
    """

    def __init__(self, frozen: datetime.datetime | None = None) -> None:
        self._frozen = frozen if frozen is not None else _DEFAULT_FROZEN
        self._patchers: list[Any] = []

    @property
    def timestamp(self) -> float:
        """The frozen instant as a POSIX timestamp."""
        return self._frozen.timestamp()

    def __enter__(self) -> "FrozenTime":
        ts = self.timestamp

        self._patchers = [
            patch("time.time", return_value=ts),
            patch("time.monotonic", return_value=ts),
            patch(
                "datetime.datetime",
                _make_frozen_datetime_class(self._frozen),
            ),
        ]
        for p in self._patchers:
            p.start()
        return self

    def __exit__(self, *args: Any) -> None:
        for p in reversed(self._patchers):
            p.stop()
        self._patchers.clear()


def _make_frozen_datetime_class(frozen: datetime.datetime) -> type:
    """Return a :class:`datetime.datetime` subclass with a frozen ``now()``."""

    class _FrozenDatetime(datetime.datetime):
        @classmethod
        def now(cls, tz: datetime.tzinfo | None = None) -> "datetime.datetime":  # type: ignore[override]
            if tz is None:
                return frozen.replace(tzinfo=None)
            return frozen.astimezone(tz)

        @classmethod
        def utcnow(cls) -> "datetime.datetime":  # type: ignore[override]
            return frozen.replace(tzinfo=None)

    _FrozenDatetime.__name__ = "datetime"
    _FrozenDatetime.__qualname__ = "datetime"
    return _FrozenDatetime


class FastSleep:
    """Replace :func:`time.sleep` with a no-op that records calls.

    Usage::

        with FastSleep() as fs:
            time.sleep(30)
            time.sleep(10)
        assert fs.total_slept == 40.0
        assert fs.call_count == 2
        assert fs.calls == [30, 10]
    """

    def __init__(self) -> None:
        self._calls: list[float] = []
        self._patcher: Any = None

    def _fake_sleep(self, seconds: float) -> None:
        self._calls.append(float(seconds))

    def __enter__(self) -> "FastSleep":
        self._calls.clear()
        self._patcher = patch("time.sleep", side_effect=self._fake_sleep)
        self._patcher.start()
        return self

    def __exit__(self, *args: Any) -> None:
        if self._patcher is not None:
            self._patcher.stop()
            self._patcher = None

    @property
    def calls(self) -> list[float]:
        """List of each argument passed to :func:`time.sleep`."""
        return list(self._calls)

    @property
    def call_count(self) -> int:
        """Number of :func:`time.sleep` calls recorded."""
        return len(self._calls)

    @property
    def total_slept(self) -> float:
        """Sum of all sleep durations."""
        return sum(self._calls)
