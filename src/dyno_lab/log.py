"""Log record capture utilities.

Provides :class:`LogCapture`, a context manager that attaches a temporary
handler to a Python logger and collects emitted records for assertion.

Usage::

    import logging
    from dyno_lab.log import LogCapture

    with LogCapture("mypackage", level=logging.WARNING) as lc:
        logging.getLogger("mypackage").warning("something went wrong")
        logging.getLogger("mypackage").debug("ignored at WARNING level")

    lc.assert_logged(logging.WARNING, "went wrong")
    lc.assert_not_logged(logging.DEBUG, "ignored")
    assert lc.count(logging.WARNING) == 1
    assert lc.messages() == ["something went wrong"]
"""

from __future__ import annotations

import logging
from typing import Any


class _ListHandler(logging.Handler):
    """A :class:`logging.Handler` that appends records to a list."""

    def __init__(self, records: list[logging.LogRecord], level: int) -> None:
        super().__init__(level=level)
        self._records = records

    def emit(self, record: logging.LogRecord) -> None:
        self._records.append(record)


class LogCapture:
    """Capture log records emitted during a test.

    Parameters
    ----------
    logger_name:
        Name passed to :func:`logging.getLogger`.  ``None`` uses the root logger.
    level:
        Minimum level to capture.  Defaults to :data:`logging.DEBUG`.

    Usage::

        with LogCapture("mypackage", level=logging.WARNING) as lc:
            logging.getLogger("mypackage").warning("oops")
        lc.assert_logged(logging.WARNING, "oops")
        assert lc.count(logging.WARNING) == 1
    """

    def __init__(
        self,
        logger_name: str | None = None,
        level: int = logging.DEBUG,
    ) -> None:
        self._logger_name = logger_name
        self._level = level
        self._records: list[logging.LogRecord] = []
        self._handler: _ListHandler | None = None
        self._original_level: int | None = None

    def __enter__(self) -> "LogCapture":
        self._records.clear()
        logger = logging.getLogger(self._logger_name)
        self._original_level = logger.level
        if logger.level == logging.NOTSET or logger.level > self._level:
            logger.setLevel(self._level)
        self._handler = _ListHandler(self._records, level=self._level)
        logger.addHandler(self._handler)
        return self

    def __exit__(self, *args: Any) -> None:
        logger = logging.getLogger(self._logger_name)
        if self._handler is not None:
            logger.removeHandler(self._handler)
            self._handler = None
        if self._original_level is not None:
            logger.setLevel(self._original_level)
            self._original_level = None

    @property
    def records(self) -> list[logging.LogRecord]:
        """All captured :class:`logging.LogRecord` objects."""
        return list(self._records)

    def messages(self, level: int | None = None) -> list[str]:
        """Return :meth:`~logging.LogRecord.getMessage` for each captured record.

        Parameters
        ----------
        level:
            If given, only return messages for records at exactly *level*.
        """
        recs = self._records if level is None else [r for r in self._records if r.levelno == level]
        return [r.getMessage() for r in recs]

    def count(self, level: int | None = None) -> int:
        """Return the number of captured records, optionally filtered by *level*."""
        if level is None:
            return len(self._records)
        return sum(1 for r in self._records if r.levelno == level)

    def assert_logged(self, level: int, fragment: str) -> None:
        """Raise ``AssertionError`` if no record at *level* contains *fragment*."""
        for record in self._records:
            if record.levelno == level and fragment in record.getMessage():
                return
        level_name = logging.getLevelName(level)
        raise AssertionError(
            f"No {level_name} log record containing {fragment!r} was found.\n"
            f"Captured messages: {self.messages()!r}"
        )

    def assert_not_logged(self, level: int, fragment: str) -> None:
        """Raise ``AssertionError`` if any record at *level* contains *fragment*."""
        for record in self._records:
            if record.levelno == level and fragment in record.getMessage():
                level_name = logging.getLevelName(level)
                raise AssertionError(
                    f"Unexpected {level_name} log record containing {fragment!r} was found."
                )
