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
