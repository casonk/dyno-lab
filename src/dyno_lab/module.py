"""Dynamic module loading by filesystem path.

Covers the ``importlib.util.spec_from_file_location`` pattern from
pushshift_python's HPC metric script tests.

Usage::

    from dyno_lab.module import load_module_by_path

    metric_maker = load_module_by_path(
        "Great_Lakes_HPC/pys/metric_maker.py",
        repo_root=Path(__file__).parents[2],
    )
    assert metric_maker.conspiracy_labler("['conspiracy']") == 1
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_module_by_path(
    path: str | Path,
    module_name: str | None = None,
    *,
    repo_root: str | Path | None = None,
) -> object:
    """Import and return a module from an arbitrary filesystem path.

    Parameters
    ----------
    path:
        Path to the ``.py`` file — either absolute or relative to *repo_root*.
    module_name:
        Name to register the module under in ``sys.modules``.
        Defaults to the stem of the filename (without ``.py``).
    repo_root:
        Base directory used to resolve a relative *path*.
        Defaults to the current working directory.

    Returns
    -------
    object
        The loaded module object.

    Raises
    ------
    FileNotFoundError
        If the resolved path does not exist.

    Example::

        metric_maker = load_module_by_path(
            "Great_Lakes_HPC/pys/metric_maker.py",
            repo_root=REPO_ROOT,
        )
        assert metric_maker.SOME_CONSTANT == expected
    """
    base = Path(repo_root or Path.cwd())
    resolved = (base / path).resolve()

    if not resolved.exists():
        raise FileNotFoundError(f"Module file not found: {resolved}")

    name = module_name or resolved.stem

    spec = importlib.util.spec_from_file_location(name, resolved)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create module spec for: {resolved}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module
