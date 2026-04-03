# Changelog — dyno-lab

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.2.0] — 2026-04-03

### Added

- `dyno_lab.preflight` — CI pre-flight checks: `check_tool`, `check_import`, `check_env`,
  `check_port`, `check_url`; `PreflightSuite` / `PreflightReport` / `PreflightError` for
  standalone CI validation; `requires_tool`, `requires_env`, `requires_import` pytest mark
  factories that auto-skip tests when the named tool / env var / package is absent;
  `pytest_collection_modifyitems` hook wired into `dyno_lab.fixtures`
- `dyno_lab.time` — `FrozenTime` context manager (freezes `time.time`, `time.monotonic`,
  `datetime.datetime.now`); `FastSleep` context manager (makes `time.sleep` instant and
  records all calls)
- `dyno_lab.log` — `LogCapture` context manager with `assert_logged`, `assert_not_logged`,
  `messages`, and `count` helpers
- `dyno_lab.patch` — `AttrPatch` context manager for patching and auto-restoring arbitrary
  object / class / module attributes

## [0.1.0] — 2026-04-01

### Added

- `dyno_lab.base` — `DynoTestCase` with filesystem, collection, numeric, and CLI assertions
- `dyno_lab.proc` — `ProcessRecorder`, `SubprocessPatch`, `build_completed_process`
- `dyno_lab.env` — `EnvPatch`, `patched_env`, `env_defaults`
- `dyno_lab.fs` — `TempWorkdir`, `make_tree`
- `dyno_lab.cli` — `capture_cli`, `capture_cli_result`, `CliResult`, `CLITestMixin`
- `dyno_lab.http` — `SequenceSession`, `StaticSession`, `RaisingSession`
- `dyno_lab.schema` — `assert_row_width`, `assert_schema_keys`, `assert_schema_shape`, `assert_parity`, `assert_unique_keys`
- `dyno_lab.module` — `load_module_by_path`
- `dyno_lab.markers` — `MARKERS`, `register_markers`
- `dyno_lab.fixtures` — pytest fixtures: `dyno_tmp`, `dyno_env`, `dyno_proc`, `dyno_cli`
- `dyno_lab.smoke` — `SmokeTest`, `SmokeResult`, `SmokeSummary`, `SmokeRunner`
- Full test suite (79 tests across 9 test files)
