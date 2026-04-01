"""dyno-lab — portfolio-wide test bench utilities.

Public surface:

    from dyno_lab.base import DynoTestCase
    from dyno_lab.proc import ProcessRecorder, SubprocessPatch, build_completed_process
    from dyno_lab.env import EnvPatch, env_defaults
    from dyno_lab.fs import TempWorkdir, make_tree
    from dyno_lab.cli import capture_cli, CliResult, CLITestMixin
    from dyno_lab.http import SequenceSession, StaticSession, RaisingSession
    from dyno_lab.schema import assert_row_width, assert_parity
    from dyno_lab.module import load_module_by_path
    from dyno_lab.markers import MARKERS
    from dyno_lab.smoke import SmokeTest, SmokeResult, SmokeRunner

Pytest fixtures (add to conftest.py with ``pytest_plugins = ["dyno_lab.fixtures"]``):

    dyno_tmp, dyno_env, dyno_proc, dyno_cli
"""

from dyno_lab.base import DynoTestCase
from dyno_lab.cli import CliResult, CLITestMixin, capture_cli
from dyno_lab.env import EnvPatch, env_defaults
from dyno_lab.fs import TempWorkdir, make_tree
from dyno_lab.http import RaisingSession, SequenceSession, StaticSession
from dyno_lab.markers import MARKERS
from dyno_lab.module import load_module_by_path
from dyno_lab.proc import ProcessRecorder, SubprocessPatch, build_completed_process
from dyno_lab.schema import assert_parity, assert_row_width
from dyno_lab.smoke import SmokeResult, SmokeRunner, SmokeTest

__all__ = [
    "DynoTestCase",
    "capture_cli",
    "CliResult",
    "CLITestMixin",
    "EnvPatch",
    "env_defaults",
    "TempWorkdir",
    "make_tree",
    "RaisingSession",
    "SequenceSession",
    "StaticSession",
    "MARKERS",
    "load_module_by_path",
    "ProcessRecorder",
    "SubprocessPatch",
    "build_completed_process",
    "assert_parity",
    "assert_row_width",
    "SmokeResult",
    "SmokeRunner",
    "SmokeTest",
]
