"""Shared pytest marker definitions.

Register these markers in your ``conftest.py``::

    pytest_plugins = ["dyno_lab.fixtures"]

Or register manually::

    from dyno_lab.markers import register_markers

    def pytest_configure(config):
        register_markers(config)

Marker semantics
----------------
unit
    Pure unit test — no filesystem I/O, no network, no subprocesses.

integration
    Multi-component or filesystem test — may create temp directories,
    patch subprocesses, or compose multiple modules.

smoke
    End-to-end health check — may require a live service or environment
    configuration (e.g. ``shock-relay`` send/receive flows).

parity
    Contract / provider parity test — validates that multiple independent
    implementations conform to a shared schema or interface.

slow
    Test expected to take several seconds.  Excluded from fast local runs.

external
    Requires a live external service, credential, or real subprocess
    that cannot be safely mocked.  Should not run in CI by default.
"""

from __future__ import annotations

from typing import Any

MARKERS: dict[str, str] = {
    "unit": "pure unit test (no I/O, no network)",
    "integration": "multi-component or filesystem test",
    "smoke": "end-to-end health check",
    "parity": "contract / provider parity test",
    "slow": "test expected to take several seconds",
    "external": "requires a live external service or credential",
    "requires_tool": "skip test if named tool(s) not found on PATH",
    "requires_env": "skip test if named env var(s) not set",
    "requires_import": "skip test if named package(s) not importable",
}


def register_markers(config: Any) -> None:
    """Register all dyno-lab markers with a pytest ``Config`` object.

    Call from ``pytest_configure`` in your project's ``conftest.py``::

        from dyno_lab.markers import register_markers

        def pytest_configure(config):
            register_markers(config)
    """
    for name, description in MARKERS.items():
        config.addinivalue_line("markers", f"{name}: {description}")
