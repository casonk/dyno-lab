"""Tests for dyno_lab.auto_pass."""

import unittest

from dyno_lab.auto_pass import AutoPassPatch, AutoPassRecorder


class TestAutoPassRecorder(unittest.TestCase):
    def test_records_load_and_resolve_calls(self) -> None:
        recorder = AutoPassRecorder(
            responses={
                "service/token": {"value": "secret"},
            }
        )

        recorder.load_config_environment("/tmp/auto-pass.env.local", profile="infra")
        resolved = recorder.resolve_keepassxc_entry(
            "service/token",
            {"value": "password"},
        )

        self.assertEqual(resolved, {"value": "secret"})
        self.assertEqual(recorder.load_calls[0].profile, "infra")
        self.assertEqual(recorder.resolve_calls[0].entry, "service/token")
        self.assertEqual(recorder.resolve_calls[0].attrs_map, {"value": "password"})

    def test_raises_scripted_keepass_error(self) -> None:
        recorder = AutoPassRecorder(
            responses={
                "service/token": AutoPassRecorder().keepass_error("not found"),
            }
        )

        with self.assertRaises(recorder.KeepassCommandError):
            recorder.resolve_keepassxc_entry("service/token", {"value": "password"})


class TestAutoPassPatch(unittest.TestCase):
    def test_injects_fake_auto_pass_modules(self) -> None:
        recorder = AutoPassRecorder(
            responses={
                "service/token": {"value": "secret"},
            }
        )

        with AutoPassPatch(recorder):
            from auto_pass.envfile import load_config_environment
            from auto_pass.keepassxc import KeepassCommandError, resolve_keepassxc_entry

            load_config_environment("/tmp/auto-pass.env.local", profile="work")
            resolved = resolve_keepassxc_entry("service/token", {"value": "password"})

        self.assertEqual(resolved["value"], "secret")
        self.assertIs(KeepassCommandError, recorder.KeepassCommandError)
        self.assertEqual(recorder.load_calls[0].profile, "work")
        self.assertEqual(recorder.resolve_calls[0].entry, "service/token")


if __name__ == "__main__":
    unittest.main()
