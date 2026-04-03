"""Attribute monkeypatching utilities.

Provides :class:`AttrPatch`, a context manager that temporarily sets one or
more attributes on any object and automatically restores or removes them on
exit.

Works with instance attributes, class attributes, module-level constants, and
attributes that did not exist before patching (those are deleted on exit).

Usage::

    from dyno_lab.patch import AttrPatch

    class Cfg:
        debug = False

    cfg = Cfg()
    with AttrPatch(cfg, debug=True):
        assert cfg.debug is True
    assert cfg.debug is False  # restored

    # Non-existent attribute is deleted on exit:
    with AttrPatch(cfg, new_flag=42):
        assert cfg.new_flag == 42
    assert not hasattr(cfg, "new_flag")
"""

from __future__ import annotations

import contextlib
from typing import Any

_MISSING = object()


class AttrPatch:
    """Patch and auto-restore object attributes.

    Parameters
    ----------
    obj:
        The target object (instance, class, or module).
    **attrs:
        Keyword arguments mapping attribute names to temporary values.

    Usage::

        with AttrPatch(cfg, debug=True, timeout=0):
            ...  # cfg.debug is True, cfg.timeout is 0 here

    Attributes that did not exist on *obj* before entering are deleted (not
    restored) on exit.
    """

    def __init__(self, obj: Any, **attrs: Any) -> None:
        self._obj = obj
        self._attrs = attrs
        self._saved: dict[str, Any] = {}

    def __enter__(self) -> AttrPatch:
        for name, value in self._attrs.items():
            prior = getattr(self._obj, name, _MISSING)
            self._saved[name] = prior
            setattr(self._obj, name, value)
        return self

    def __exit__(self, *args: Any) -> None:
        for name, prior in self._saved.items():
            if prior is _MISSING:
                with contextlib.suppress(AttributeError):
                    delattr(self._obj, name)
            else:
                setattr(self._obj, name, prior)
        self._saved.clear()
