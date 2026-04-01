"""Tests for dyno_lab.http — HTTP session mocking utilities."""

import json
import unittest

from dyno_lab.http import RaisingSession, SequenceSession, StaticSession


class TestSequenceSession(unittest.TestCase):
    def test_returns_responses_in_order(self):
        session = SequenceSession(["first", "second", "third"])
        r1 = session.get("/a")
        r2 = session.get("/b")
        r3 = session.get("/c")
        self.assertEqual(r1.text, "first")
        self.assertEqual(r2.text, "second")
        self.assertEqual(r3.text, "third")

    def test_records_calls(self):
        session = SequenceSession(["ok"])
        session.get("/path", params={"q": "test"})
        self.assertEqual(session.call_count, 1)
        self.assertEqual(session.urls_called(), ["/path"])

    def test_raises_when_responses_exhausted(self):
        session = SequenceSession(["only_one"])
        session.get("/a")
        with self.assertRaises(StopIteration):
            session.get("/b")

    def test_json_parsing(self):
        session = SequenceSession(['{"status": "ok"}'])
        r = session.get("/api")
        self.assertEqual(r.json(), {"status": "ok"})

    def test_raise_for_status_on_error_code(self):
        from dyno_lab.http import _FakeResponse

        session = SequenceSession([_FakeResponse("not found", status_code=404)])
        r = session.get("/missing")
        with self.assertRaises(RuntimeError):
            r.raise_for_status()

    def test_post_is_also_recorded(self):
        session = SequenceSession(["posted"])
        session.post("/submit", params={"data": "x"})
        self.assertEqual(session.calls[0].method, "POST")

    def test_context_manager_protocol(self):
        with SequenceSession(["ok"]) as session:
            r = session.get("/test")
        self.assertEqual(r.text, "ok")


class TestStaticSession(unittest.TestCase):
    def test_always_returns_same_response(self):
        session = StaticSession('{"items": [1, 2]}')
        r1 = session.get("/a")
        r2 = session.get("/b")
        self.assertEqual(r1.text, r2.text)

    def test_records_all_calls(self):
        session = StaticSession("data")
        session.get("/x")
        session.get("/y")
        session.post("/z")
        self.assertEqual(len(session.calls), 3)

    def test_json_response(self):
        session = StaticSession(json.dumps({"key": "val"}))
        r = session.get("/api")
        self.assertEqual(r.json()["key"], "val")


class TestRaisingSession(unittest.TestCase):
    def test_get_raises(self):
        session = RaisingSession()
        with self.assertRaises(ConnectionError):
            session.get("/any")

    def test_post_raises(self):
        session = RaisingSession()
        with self.assertRaises(ConnectionError):
            session.post("/any")

    def test_custom_exception(self):
        session = RaisingSession(exc=ValueError("CAPTCHA detected"))
        with self.assertRaises(ValueError):
            session.get("/any")


if __name__ == "__main__":
    unittest.main()
