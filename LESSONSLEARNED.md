# LESSONSLEARNED.md — dyno-lab

Tracked durable lessons for `dyno-lab`.
Unlike `CHATHISTORY.md`, this file should keep only reusable lessons that should
change how future sessions work in this repo.

## How To Use

- Read this file after `AGENTS.md` and before `CHATHISTORY.md` when resuming work.
- Add lessons that generalize beyond a single session.
- Keep entries concise and action-oriented.
- Do not use this file for transient status updates or full session logs.

## Lessons

- Document the repository around its real execution, curation, or integration flow
  instead of only the top-level folder list.
- Keep local-only, private, reference-only, or generated boundaries explicit so
  published or runtime behavior is not confused with offline material or non-committable inputs.
- Re-run repo-appropriate validation after changing generated artifacts, diagrams,
  workflows, or other CI-facing files so formatting and compatibility issues are
  caught before push.
- Do not import `pytest` at module import time in `dyno_lab` core modules — it is
  an optional dev dependency.  Guard pytest imports inside `fixtures.py` and
  `markers.py` only, where pytest is the expected runtime.
- Keep each `dyno_lab` module narrowly focused on one concern.  When a new portfolio
  test pattern is discovered, add it to the appropriate existing module or create a
  new single-responsibility module — do not pile unrelated helpers into `base.py`.
- The `SubprocessPatch.target` default patches the standard library directly
  (`"subprocess.run"`), which works for most cases.  When a module under test imports
  `subprocess` into its own namespace, set `target` to the module-qualified path
  (e.g. `"mymodule.subprocess.run"`) to intercept the call correctly.
- Pin `ruff` to a specific version in both `.pre-commit-config.yaml` and CI so local
  and hosted formatter results stay identical.  Mismatched ruff versions produce
  implicit string-concat join differences that fail `ruff format --check` in CI even
  when pre-commit passes locally.
- Avoid `init` as a PlantUML element alias — it is a reserved keyword (initial
  pseudostate) that causes PlantUML to assume activity diagram mode, silently
  breaking `rectangle` + `-->` arrow syntax.  Use `publicapi`, `pkg_init`, or
  any other non-reserved name.
- Prefer `!pragma layout elk` over `smetana` in PlantUML component/package
  diagrams.  `elk` is bundled with PlantUML, handles cross-package arrows
  reliably, and matches the rest of the portfolio's diagram style.
- draw.io cells must always use `whiteSpace=wrap;html=1;overflow=hidden;` AND be
  sized with adequate height for their text content.  As a rule: allow at least
  22px per line of text at font size 12 plus 16px top/bottom padding, so a
  3-line box needs at least 82px height.  Never size a container smaller than
  its children, and always add `overflow=hidden` to swimlane containers so any
  overflow is clipped rather than visually escaping the block boundary.
- draw.io starter diagrams should never use "Focus Root" placeholder labels.
  Replace them with the actual module or component names before committing.
- For downstream repos that import sibling helpers like `auto_pass` inside
  function bodies, the most stable test seam is a fake package injected into
  `sys.modules`; patching the original import path is often too late because
  the import happens inside the function under test.
- If repo docs and service units advertise `pytest -q` from the checkout root,
  keep the `src/` package importable during in-repo test runs instead of
  assuming an editable install is already present.

### dyno-lab API call signatures

- `SubprocessPatch(side_effect)` — takes a **callable** as the first arg, not
  keyword `returncode=`/`stdout=`. Wrap `build_completed_process` in a lambda:
  `SubprocessPatch(lambda *a, **kw: build_completed_process(0, "out", ""))`.
- `EnvPatch({"KEY": "val"})` — positional dict, not keyword args.
  `clear=True` wipes the entire environment for the block.
- `TempWorkdir()` has no `cd=` parameter; use `.path` attribute for the
  directory, or `os.chdir(ctx.path)` if a chdir is needed.
- `load_module_by_path(path, name, repo_root=REPO_ROOT)` is a drop-in
  replacement for hand-rolled `importlib.util.spec_from_file_location` patterns.

### dyno-lab module inventory (v0.2.0+)

- `dyno_lab.preflight` adds `requires_tool`, `requires_env`, `requires_import` pytest marks
  that auto-skip tests when tools/env vars/packages are absent. Add
  `pytest_plugins = ["dyno_lab.fixtures"]` to `conftest.py` to activate the hook.
- `PreflightSuite` can be run as a standalone CI step before pytest to surface environment
  problems early (missing binaries, unset keys, unreachable ports).
- `dyno_lab.time.FrozenTime` freezes `time.time()`, `time.monotonic()`, and
  `datetime.datetime.now()` via a subclass override — no freezegun dependency required.
- `dyno_lab.time.FastSleep` replaces `time.sleep()` with a no-op and records all calls;
  use `fs.total_slept` / `fs.call_count` to assert retry/backoff timing.
- `dyno_lab.log.LogCapture` captures Python logging records; use `assert_logged(level, fragment)`
  and `assert_not_logged(level, fragment)` to assert on log output without relying on stdout.
- `dyno_lab.patch.AttrPatch(obj, attr=value)` patches and auto-restores object/class/module
  attributes; if the attribute didn't exist before, it is deleted on exit.
