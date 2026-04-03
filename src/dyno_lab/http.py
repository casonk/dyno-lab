"""HTTP session mocking utilities.

Covers the custom HTTP mock session pattern from doseido and intake,
where ``requests.Session`` is replaced with a scripted object.

Usage::

    from dyno_lab.http import SequenceSession, StaticSession, RaisingSession
    from unittest.mock import patch

    # Scripted multi-call sequence:
    session = SequenceSession(responses=["<html>page1</html>", "<html>page2</html>"])
    with patch("mymodule.requests.Session", return_value=session):
        result = my_function_that_calls_get_twice()

    assert session.call_count == 2
    assert session.urls_called() == ["/page1", "/page2"]

    # Static single response:
    session = StaticSession(body='{"status": "ok"}', status_code=200)

    # Always raises:
    session = RaisingSession()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class _FakeResponse:
    """Minimal stand-in for ``requests.Response``."""

    body: str
    status_code: int = 200
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def text(self) -> str:
        return self.body

    def json(self) -> Any:
        import json

        return json.loads(self.body)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@dataclass
class _CapturedRequest:
    """A recorded HTTP request."""

    method: str
    url: str
    params: dict[str, Any] | None
    kwargs: dict[str, Any]


class SequenceSession:
    """HTTP session mock that returns scripted responses in order.

    Each call to ``.get()`` or ``.post()`` pops the next *response* from the list.
    If responses are exhausted, raises ``StopIteration``.

    Parameters
    ----------
    responses:
        Ordered list of response bodies (strings) or ``_FakeResponse`` objects.
    default_status_code:
        HTTP status applied to plain-string responses.

    Attributes
    ----------
    calls:
        Every :class:`_CapturedRequest` made to this session.

    Example::

        session = SequenceSession([
            '{"results": []}',
            '<html>fallback page</html>',
        ])
        with patch("myapp.http_session", session):
            items = fetch_items()

        assert session.call_count == 2
    """

    def __init__(
        self,
        responses: list[str | _FakeResponse],
        *,
        default_status_code: int = 200,
    ) -> None:
        self._responses: list[_FakeResponse] = [
            r if isinstance(r, _FakeResponse) else _FakeResponse(r, default_status_code)
            for r in responses
        ]
        self.calls: list[_CapturedRequest] = []

    def _pop(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None,
        kwargs: dict[str, Any],
    ) -> _FakeResponse:
        self.calls.append(_CapturedRequest(method=method, url=url, params=params, kwargs=kwargs))
        if not self._responses:
            raise StopIteration("SequenceSession: no more scripted responses")
        return self._responses.pop(0)

    def get(self, url: str, params: dict[str, Any] | None = None, **kwargs: Any) -> _FakeResponse:
        return self._pop("GET", url, params, kwargs)

    def post(self, url: str, params: dict[str, Any] | None = None, **kwargs: Any) -> _FakeResponse:
        return self._pop("POST", url, params, kwargs)

    @property
    def call_count(self) -> int:
        return len(self.calls)

    def urls_called(self) -> list[str]:
        return [c.url for c in self.calls]

    def __enter__(self) -> SequenceSession:
        return self

    def __exit__(self, *args: Any) -> None:
        pass


class StaticSession:
    """HTTP session mock that always returns the same response.

    Useful for tests that only care about parsing the response, not the
    number of calls::

        session = StaticSession('{"items": [1, 2, 3]}')
        with patch("myapp.get_session", return_value=session):
            result = fetch_all()
    """

    def __init__(self, body: str = "", status_code: int = 200) -> None:
        self._response = _FakeResponse(body, status_code)
        self.calls: list[_CapturedRequest] = []

    def _record(self, method: str, url: str, params: Any, kwargs: dict[str, Any]) -> _FakeResponse:
        self.calls.append(_CapturedRequest(method=method, url=url, params=params, kwargs=kwargs))
        return self._response

    def get(self, url: str, params: Any = None, **kwargs: Any) -> _FakeResponse:
        return self._record("GET", url, params, kwargs)

    def post(self, url: str, params: Any = None, **kwargs: Any) -> _FakeResponse:
        return self._record("POST", url, params, kwargs)

    def __enter__(self) -> StaticSession:
        return self

    def __exit__(self, *args: Any) -> None:
        pass


class RaisingSession:
    """HTTP session mock that always raises an exception.

    Simulates network errors or CAPTCHA blocks::

        session = RaisingSession(exc=ConnectionError("timeout"))
        with patch("myapp.get_session", return_value=session):
            result = safe_fetch()  # should return None / empty

    Parameters
    ----------
    exc:
        The exception instance to raise.  Defaults to ``ConnectionError``.
    """

    def __init__(self, exc: BaseException | None = None) -> None:
        self._exc = exc or ConnectionError("RaisingSession: simulated network error")

    def get(self, *args: Any, **kwargs: Any) -> None:
        raise self._exc

    def post(self, *args: Any, **kwargs: Any) -> None:
        raise self._exc

    def __enter__(self) -> RaisingSession:
        return self

    def __exit__(self, *args: Any) -> None:
        pass
