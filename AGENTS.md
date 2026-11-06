# AGENTS.md

This document provides guidelines for AI agents contributing to this repository.

## Overview of Instructions

- **Always use `uv`:** Use uv for all dependency management, virtual
  environments, and task running. Do not use pip or venv directly.
- **Follow all guidelines:** Follow this file and applicable nested AGENTS.md.
  Routine agent work does not require reading CONTRIBUTING.md; consult it
  when editing contributor guidance or preparing issues, PRs, and reviews.
- **Verify your changes:** Before handoff or any authorized commit, run all
  linters and tests with `uv run task all`; report failures and limitations.
- **Line width:** All text files should have a line width of 80 characters.
- **Permission to run commands:** You may run verification commands here;
  this does not authorize publication, hook installation, or Git mutations.
- **Incremental changes:** Make small, incremental changes; avoid unrelated
  repairs. Inspect git status and diffs first and preserve existing work.
- **Communicate clearly:** Explain what changed and why.
- **Create and Follow a TODO List:** Always create and follow a TODO list.
  Use tool results to verify completion; report blockers honestly.

## Notification Instructions

Send a desktop notification for questions, feedback requests, and completion.
Standing permission covers notification calls, not installation. Adapt the
message; report unavailable tools or desktop access. See
[AI Agent Permissions](README.md#ai-agent-permissions).

Linux:

```bash
notify-send "Coding agent" "Task complete or feedback needed."
```

macOS:

```bash
osascript -e 'display notification "Task complete." with title "Agent"'
```

Windows, in PowerShell with BurntToast installed (process-only policy bypass):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command {
  Import-Module BurntToast
  New-BurntToastNotification -Text "Agent", "Task complete."
}
```

One-time setup in a regular PowerShell terminal, only with authorization:

```powershell
Install-Module -Name BurntToast -Scope CurrentUser
```

Optionally, inside Zellij with the tools available, also send a session
notification. It does not replace the desktop notification. Keep the
two-second timeout and trailing message space; no special font is needed.

```bash
timeout 2 zellij pipe -- \
  "zjstatus::notify::Agent finished. This is really fun. "
```

## Build, Lint, and Test Commands

Run from the repository root; review diffs after fix commands.

- **Install dependencies:** `uv sync --dev`; for code/full type checks use
  `uv sync --dev --extra auto-hint`. Keep dependency and lock updates together.
- **Run all tasks:** `uv run task all`; after syncing the extra, use
  `uv run --no-sync task all` to avoid re-syncing.
- **Run all linters:** `uv run task lint`
- **Format code:** `uv run task format` (check), `uv run task format-fix` (fix)
- **Lint code:** `uv run task check`
- **Type check:** `uv run task typecheck` (mypy, ty, pyrefly, zuban, symbex)
- **Test all:** `uv run task test`
- **Test with coverage:** Also run `uv run task test-coverage`; all includes
  static direct-test coverage, not executed statement/branch coverage.
- **Test variants:** `uv run task test-not-propertybased`,
  `uv run task test-not-random`, `uv run task test-silent`
- **Run a focused test:** `uv run pytest tests/input/test_checks.py`
- **Markdown lint:** `uv run task rumdl-check`
- **Comment check:** `uv run task comments-check` (check),
  `uv run task comments-fix` (fix)
- **Local hooks:** Install only with developer authorization. Check working
  files with `uv run pre-commit run --files` followed by explicit paths;
  never implicitly stash. Hooks check commit messages, not PR titles.
  Smoke tests export the Git index, not the working tree; do not stage to
  test them. See [local checks](docs/PRE_COMMIT.md) for details.

## Code Requirements

All Python code, including tests, should follow these standards:

- **Function bodies:** No blank lines within function bodies; keep contiguous.
- **Docstrings:** Single-line, capitalized, ending with a period in new files.
  In existing files, preserve established styles, including multi-line Args.
- **Comments:** Start lowercase except proper nouns or identifiers such as
  GatorGrade or GITHUB_ENV; preserve existing comments during refactoring.
- **Sentences:** Use one space between sentences in comments.
- **No backticks in comments:** No backticks in comments, docstrings, or other
  source prose; write identifiers plainly. Markdown formatting belongs in .md.
- **Imports:** Group standard library, third-party, then local imports.
  Use absolute imports such as `from gatorgrade.module import name`;
  put all imports at the top, not inside functions or classes.
- **Formatting:** Use configured Ruff formatting (79 columns, trailing
  commas), e.g. `uv run task ruff-format`; the separate isort setting is 88.
- **Types:** All functions need parameter and return type hints.
- **Naming:** snake_case functions/variables, PascalCase classes,
  UPPER_SNAKE_CASE constants.
- **Constants over literals:** Extract hard-coded strings, integers, and
  floats into named module-top constants; reuse them instead of raw literals.
- **File operations:** Use pathlib.Path for filesystem operations.
- **Error handling:** Catch specific exceptions, not generic Exception;
  provide meaningful messages. Never add secrets or debugging leftovers.

## Project Structure Requirements

- Source code belongs in gatorgrade/; tests mirror source under tests/.
- Use uv for dependency management, environments, and task running.
- Preserve compatibility with Python 3.11–3.14 on macOS, Linux, and Windows
  (CI); metadata also permits 3.10, which CI does not verify.
- Reuse existing validation and JSON serialization; Pydantic is not a
  declared dependency. Preserve CLI, configuration, and report compatibility
  unless the request calls for a change; document intended migration steps.

## Testing Requirements

- Tests follow the Python code requirements above.
- Use descriptive test_ names; group by function and order logically.
- Tests must be independent, support random ordering, and work locally and
  in CI. Add behavior, regression, and relevant failure-path tests.
- Aim for full function, statement, and branch coverage. Preserve the 95%
  executed and 75% direct-test floors; never lower or game measurement.
- Mark Hypothesis tests with `@pytest.mark.propertybased`; use the autohint
  marker for auto-hint tests. Never remove failing tests merely to pass.
- Tests should not produce console output.

## Making Changes

1. **Understand:** Explore the request and relevant code. Follow the
   [Code of Conduct](CODE_OF_CONDUCT.md); review generated work and verify
   APIs/references against sources. Claim only verification actually done.
1. **Plan:** Create a clear plan before changing files.
1. **Implement:** Make small changes; update affected docstrings, examples,
   README, and contributor documentation. Ask before adding runtime
   dependencies, changing CI, renaming public APIs, or removing checks/tests
   unless explicitly requested.
1. **Verify:** Run `uv run task all` and separate executed coverage. Fix
   introduced failures and report existing ones. For user-visible changes,
   test a disposable assignment against the edited checkout and verify its
   import origin; record directory, inputs/configuration, command, expected
   and actual output, exit code, OS, and Python version, including relevant
   passing/failing JSON cases. Redact credentials and private student data.
1. **Commit:** The software developer commits. Do not stage, commit, create
   branches, switch checkouts, push, or publish without explicit authorization.
   Follow [commit standards](docs/COMMIT_MESSAGES.md); disclose substantial
   AI assistance, known model/version, and actual verification so the
   developer can include the required body and Assisted-by trailer.
1. **Rules:** Changes normally need an issue: check duplicates, prepare an
   issue/team comment before starting, or justify a minor-change exception
   in the PR; ask a maintainer when unsure. Complete the PR template, target
   main, link relevant issues, and prepare the PR URL comment for every
   linked issue, including later links. Draft communication unless publishing
   is authorized. Before merge, require passing CI and a team member plus
   Integration team review; use formal reviews, not conversation approvals.
1. **Completion:** Summarize completed tasks, methods, challenges, applicable
   rules, verification commands/results, environment, and limitations.

## Additional Notes for the Coding Agent

Append durable project notes as a Markdown list when useful, not routine logs.

- **Comment tool:** [scripts/ccl.py](scripts/ccl.py) replaces the old script
  and installed ccl entry point. Use comments-check/comments-fix above;
  its proper-noun allowlist is authoritative. Tree-sitter packages are dev
  dependencies. Use inline noqa, not pylint disable, for lint suppressions.
- **Validation:** Weights are positive nonzero integers, not booleans; retain
  validate_positive_nonzero_int in gatorgrade/input/checks.py and fail-fast
  generate_checks validation of weights/outputlimit. parse_config returns
  checks/error_message; main.py displays errors and EXIT_MESSAGE.
- **Never run `git stash`:** Preserve existing tracked, untracked, and staged
  work. Use a separate worktree or developer-authorized commit if necessary;
  the developer handles rebasing and cleanup.
- **Creativity is welcome:** Occasional natural flair is optional.
- Keep documented task names and inline local file references valid.
