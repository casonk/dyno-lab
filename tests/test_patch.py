"""Tests for dyno_lab.patch."""

from __future__ import annotations

import types
import unittest

from dyno_lab.patch import AttrPatch


class _Cfg:
    debug = False
    timeout = 30


class TestAttrPatch(unittest.TestCase):
    def test_instance_attr_patched_and_restored(self):
        cfg = _Cfg()
        cfg.debug = False
        with AttrPatch(cfg, debug=True):
            self.assertTrue(cfg.debug)
        self.assertFalse(cfg.debug)

    def test_class_attr_patched_and_restored(self):
        with AttrPatch(_Cfg, timeout=99):
            self.assertEqual(_Cfg.timeout, 99)
        self.assertEqual(_Cfg.timeout, 30)

    def test_nonexistent_attr_deleted_on_exit(self):
        cfg = _Cfg()
        self.assertFalse(hasattr(cfg, "new_flag"))
        with AttrPatch(cfg, new_flag=42):
            self.assertEqual(cfg.new_flag, 42)
        self.assertFalse(hasattr(cfg, "new_flag"))

    def test_multiple_attrs_patched_simultaneously(self):
        cfg = _Cfg()
        with AttrPatch(cfg, debug=True, timeout=0):
            self.assertTrue(cfg.debug)
            self.assertEqual(cfg.timeout, 0)
        self.assertFalse(cfg.debug)
        self.assertEqual(cfg.timeout, 30)

    def test_module_level_constant(self):
        mod = types.ModuleType("fake_mod")
        mod.VERSION = "1.0"
        with AttrPatch(mod, VERSION="2.0"):
            self.assertEqual(mod.VERSION, "2.0")
        self.assertEqual(mod.VERSION, "1.0")

    def test_nested_patches(self):
        cfg = _Cfg()
        with AttrPatch(cfg, timeout=10):
            self.assertEqual(cfg.timeout, 10)
            with AttrPatch(cfg, timeout=5):
                self.assertEqual(cfg.timeout, 5)
            self.assertEqual(cfg.timeout, 10)
        self.assertEqual(cfg.timeout, 30)

    def test_context_manager_returns_self(self):
        cfg = _Cfg()
        with AttrPatch(cfg, debug=True) as p:
            self.assertIsInstance(p, AttrPatch)

    def test_exception_inside_context_still_restores(self):
        cfg = _Cfg()
        try:
            with AttrPatch(cfg, debug=True):
                raise ValueError("boom")
        except ValueError:
            pass
        self.assertFalse(cfg.debug)


if __name__ == "__main__":
    unittest.main()
