# AGENTS.md

This document provides guidelines for AI agents contributing to this repository.

## Overview of Instructions

- **Always use `uv`:** This project uses `uv` for all dependency management,
  virtual environments, and task running. Do not use `pip` or `venv` directly.
- **Follow all guidelines:** This document contains the complete set of
  guidelines from `AGENTS.md` and `docs/plan.md`. You must follow them strictly.
- **Verify your changes:** Before committing any changes, you must run all
  linters and tests to ensure your changes are correct and follow the project's
  style. Use `uv run task all`.
- **Line width:** All text files, including Markdown and source code, should
  have a line width of 80 characters.
- **Permission to run commands:** You have permission to run all commands in
  this file to verify their functionality.
- **Incremental changes:** Make small, incremental changes. This makes it easier
  to review your work and catch errors early.
- **Communicate clearly:** When you propose changes, explain what you've done
  and why.
- **Create and Follow a TODO List**: Always create a TODO list and then
  follow that list. Do not stop until the tools that you call make it clear
  that you have completed all the tasks in the TODO list.

## Notification Instructions

- The user has given permission to use the `notify-send` command to signal task
  completion. Here is an example of the command:

  ```bash
  notify-send "Question from Coding Agent" \
    "Please clarify how to complete the testing task."
  ```

- The user wants a `notify-send` notification whenever I ask a question.

- Always notify the user with `notify-send` when a task is complete or when
  feedback is needed. I have standing permission to use the notification tool.

- You should also use the following command to notify the user when you are
  finished with a task or need further help:

  ```bash
  timeout 2 zellij pipe -- \
    "zjstatus::notify::󰵰 Agent finished. This is really fun. "
  ```

- Note that this command will only display in the current Zellij session.
  Please also note that you need to add a space at the end of the notification.

- You should use both notification methods as appropriate, making sure that the
  Zellij command is always prefaced with a timeout of 2 seconds.

## Build, Lint, and Test Commands

- **Install dependencies:** `uv sync --dev`
- **Run all tasks:** `uv run task all`
- **Run all linters:** `uv run task lint`
- **Format code:** `uv run task format` (check), `uv run task format-fix` (fix)
- **Lint code:** `uv run task check`
- **Type check:** `uv run task typecheck` (runs mypy, ty, pyrefly, and zuban),
  or individual checkers: `uv run task mypy`, `uv run task ty`,
  `uv run task pyrefly`, `uv run task symbex`
- **Test all:** `uv run task test`
- **Test with coverage:** `uv run task test-coverage`
- **Test variants:** `uv run task test-not-property`,
  `uv run task test-not-random`, `uv run task test-silent`
- **Run a single test:** `pytest tests/test_file.py::test_function` or
  `uv run pytest tests/test_file.py::test_function`
- **Markdown lint:** `uv run task markdownlint`
- **Comment check:** `uv run task comments-check` (check) or
  `uv run comment-fix` (auto-fix)

## Code Requirements

All the Python code should follow these standards:

- **Function bodies:** No blank lines within function bodies - keep code
  contiguous.
- **Docstrings:** Single-line docstrings starting with a capital letter, ending
  with a period. Follow this for new files. In existing files, preserve the
  established docstring style even if it is multi-line with `Args` sections.
- **Comments:** Other comments start with a lowercase letter; preserve existing
  comments during refactoring. The only exception is when the first word of the
  comment is a proper noun (e.g., `GatorGrader`, `GatorGrade`, `GitHub`) or an
  identifier that must start with a capital letter (e.g., `GITHUB_ENV`).
- **No backticks in comments:** Do not use backticks in comments, docstrings,
  or any other prose text within source code files. Backticks are reserved for
  Markdown formatting in `.md` files only. If you need to refer to a code
  identifier, write it plainly (e.g., "transformers" not "`transformers`").
- **Imports:** Group imports in this order: standard library, third-party,
  local imports. Use absolute imports (`from gatorgrade.module import <name>`).
  Finally, make sure that all imports are placed at the top of the file. Do not
  place imports into the middle of a file or even at the start of a function or
  class.
- **Formatting:** Use `ruff format` (line length 79 for lint, 88 for isort);
  trailing commas enabled or the corresponding task called `uv run task ruff-format`.
- **Types:** All functions must have type hints for parameters and return
  values.
- **Naming:** snake_case for functions/variables, PascalCase for classes,
  UPPER_SNAKE_CASE for constants.
- **Constants over literals:** All hard-coded strings, integers, and floats
  must be extracted into named constants (UPPER_SNAKE_CASE) at the top of
  the module. Use the constant everywhere the value is needed, not the raw
  literal.
- **File operations:** Use `pathlib.Path` for all filesystem operations, never
  string paths.
- **Error handling:** Use specific exceptions, not generic `Exception`; provide
  meaningful error messages.

## Project Structure Requirements

- Source code in `gatorgrade/` directory.
- Tests in `tests/` directory with matching structure to source.
- Use `uv` for dependency management, virtual environments, and task running.
- Support Python 3.12, 3.12, 3.13, and 3.14 on MacOS, Linux, and Windows.
- Use Pydantic models for data validation and JSON serialization.

## Testing Requirements

All test cases should follow these standards:

- Since a test case is a Python function, it should always follow the code
  requirements above.
- Test cases should have a descriptive name that starts with `test_`.
- Test cases should be grouped by the function they are testing.
- Test cases should be ordered in a way that makes sense to the reader.
- Test cases should be independent of each other so that they can be run in a
  random order without affecting the results or each other.
- Test cases must work both on a local machine and in a CI environment.
- Test cases should aim to achieve full function, statement, and branch
  coverage.
- Property-based tests, such as those that use the `hypothesis` package, must be
  marked with `@pytest.mark.property`.
- Test cases should not produce any console output.

## Making Changes

1. **Understand:** Thoroughly understand the request and the relevant codebase.
   Use the available tools to explore the code.
1. **Plan:** Formulate a clear plan before making any changes.
1. **Implement:** Make small, incremental changes.
1. **Verify:** Run `uv run task all` to ensure your changes are correct and
   follow the project's style.
1. **Commit:** The software developer will always commit the changes.
1. **Rules**: Always follow the rules in this file and in the `docs/plan.md`
   file.
1. **Completion**: When you are finished with tasks, please summarize what tasks
   you completed, how you completed them, the challenges you faced, how you
   overcame them, and the rules that you followed during completion of the tasks.

## Additional Notes for the Coding Agent

Note: This file is specifically for coding agents and this section can be used
by the coding agent to add additional details about this project that would
be helpful for the agent to know when it is run again. Every time a coding
agent finishes a task, it should add notes here as it deems appropriate.
The coding agent should write the notes as a Markdown list.

- The `ccl` (Comment Case Linter) tool is installed as a project entry
  point in `gatorgrade/comments_checker.py`. It uses Tree-sitter to parse
  Python files into a CST and checks that comments start with lowercase
  letters (with proper-noun exceptions). Run `uv run ccl check` to check
  and `uv run ccl fix` to auto-fix. The task `uv run task comments` also
  runs `ccl check`.
- The `ccl` command replaced the earlier `scripts/check_comments_lowercase.py`
  approach. The old script file has been removed.
- `tree-sitter` and `tree-sitter-python` are now production dependencies
  because `ccl` is an installed entry point.
- Proper nouns allowed in comments: `CountCommits`, `GatorGrade`,
  `GatorGrader`, `GatorGraderCheck`, `GITHUB_ENV`,
  `GITHUB_STEP_SUMMARY`, `JSON`, `MatchFileFragment`, `ShellCheck`,
  `STDOUT`, `STDERR`, `TODO`, `FIXME`, `NOTE`. "Typo" is NOT a proper
  noun and was removed from the exceptions list.
- Suppress lint rules with inline `# noqa: PLR...` comments (e.g.,
  `# noqa: PLR0913`), not `# pylint: disable`.
- Weight is always `int` throughout the codebase (refactored from
  `int | float`). Validate with `validate_positive_nonzero_int()` in
  `gatorgrade/input/checks.py`.
- `generate_checks()` in `command_line_generator.py` validates all
  check data upfront and raises `ValueError` on any invalid weight or
  outputlimit (fail-fast). It no longer creates error `ShellCheck`
  objects for misconfigured checks.
- `parse_config()` returns `(checks, error_message)`. Both YAML parse
  errors and validation errors are returned as the error string, which
  `main.py` displays with `Rule`-based formatting.
- `EXIT_MESSAGE` is defined in `gatorgrade/main.py` and is the string
  displayed below error details in configuration error boxes.
- **Never run `git stash`:** This command is destructive and risks losing
  uncommitted work. If you need to temporarily set aside changes, create a
  commit or use `git worktree` instead. The developer will handle any
  rebasing or history cleanup.
- **Creativity is welcome:** Every once in a while, feel free to slip
  in a bit of flair like a pun, a limerick, a dad joke, a haiku about
  test cases, or anything else that might make the developer smile.
  Don't force it; let it come naturally when the moment feels right.
