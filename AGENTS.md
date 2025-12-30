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
- **Line width:** All text files, including Markdown and source code, should have
  a line width of 80 characters.
- **Permission to run commands:** You have permission to run all commands in this
  file to verify their functionality.
- **Incremental changes:** Make small, incremental changes. This makes it easier
  to review your work and catch errors early.
- **Communicate clearly:** When you propose changes, explain what you've done
  and why.

## Notification Instructions

- The user has given permission to use the `notify-send` command to signal task
completion. Here is an example of the command: `notify-send "Question from
Coding Agent" "Please clarify how to complete the testing task."`.
- The user wants a `notify-send` notification whenever I ask a question.
- Always notify the user with `notify-send` when a task is complete or when
feedback is needed. I have standing permission to use the notification tool.
- You should also use the following command to notify the user when you are
finished with a task or need further help:
`timeout 2 zellij pipe -- "zjstatus::notify::󰵰 Agent finished. This is really fun. "`
- Note that this command will only display in the current Zellij session. Please
also note that you need to add a space at the end of the notification.
- You should use both notification methods as appropriate, making sure that the
Zellij command is always prefaced with a timeout of 2 seconds.

## Build, Lint, and Test Commands

- **Install dependencies:** `uv sync --dev`
- **Run all tasks:** `uv run task all`
- **Run all linters:** `uv run task lint`
- **Format code:** `uv run task format` (check), `uv run task format-fix` (fix)
- **Lint code:** `uv run task check`
- **Type check:** `uv run task mypy`, `uv run task ty`, `uv run task symbex`
- **Test all:** `uv run task test`
- **Test with coverage:** `uv run task test-coverage`
- **Test variants:** `uv run task test-not-property`, `uv run task test-not-random`,
  `uv run task test-silent`
- **Run a single test:** `pytest tests/test_file.py::test_function` or
  `uv run pytest tests/test_file.py::test_function`
- **Markdown lint:** `uv run task markdownlint`

## Code Requirements

All the Python code should follow these standards:

- **Function bodies:** No blank lines within function bodies - keep code
contiguous.
- **Docstrings:** Single-line docstrings starting with a capital letter, ending
with a period.
- **Comments:** Other comments start with a lowercase letter; preserve existing
comments during refactoring.
- **Imports:** Group imports in this order: standard library, third-party, local
imports. Use absolute imports (`from pytest_brightest.module import`). Finally,
make sure that all imports are placed at the top of the file. Do not place
imports into the middle of a file or even at the start of a function or class.
- **Formatting:** Use `ruff format` (line length 79 for lint, 88 for isort);
  trailing commas enabled.
- **Types:** All functions must have type hints for parameters and return values.
- **Naming:** snake_case for functions/variables, PascalCase for classes,
  UPPER_SNAKE_CASE for constants.
- **File operations:** Use `pathlib.Path` for all file system operations, never
  string paths.
- **Error handling:** Use specific exceptions, not generic `Exception`; provide
  meaningful error messages.

## Project Structure Requirements

- Source code in `src/pytest_brightest/` directory.
- Tests in `tests/` directory with matching structure to source.
- Use `uv` for dependency management, virtual environments, and task running.
- Support Python 3.11, 3.12, and 3.13 on MacOS, Linux, and Windows.
- Use Pydantic models for data validation and JSON serialization.

## Project Behavior Requirements

- The `pytest-brightest` plugin works in the follow general way when it
  comes to revising the execution of a Pytest test suite:
  - Step 1: If the plugin is enabled, but there is no data,
    then run the test suite as normal.
  - Step 2: If the plugin is enabled and there is data, then run the
    test suite based on the data from the prior run of the plugin.
  - Step 3: Use the data collected by pytest-json-report to compute
    the values for the cost and failure data for each test case and
    for the test modules.
  - Step 4: While keeping all prior data that was recorded by the tool,
    the plugin will then update the data with the new cost and failure
    data for each test case and for the test modules.
  - Step 5: The plugin will then write the updated data to the
    `pytest-brightest.json` file in the configured directory.
- Critically, the `pytest-brightest` plugin should not, for instance,
  delete data from a prior run unless the tool is beyond the maximum
  amount of test runs that it is configured to persist.

## Test Requirements

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
- Property-based tests must be marked with `@pytest.mark.property`.
- Test cases should not produce any console output.

## Making Changes

1. **Understand:** Thoroughly understand the request and the relevant codebase.
   Use the available tools to explore the code.
2. **Plan:** Formulate a clear plan before making any changes.
3. **Implement:** Make small, incremental changes.
4. **Verify:** Run `uv run task all` to ensure your changes are correct and
   follow the project's style.
5. **Commit:** Write a clear and concise commit message explaining the "why" of
   your changes.
6. **Rules**: Always follow the rules in this file and in the `docs/plan.md`
   file.
7. **Completion**: When you are finished with tasks, please summarize what tasks
   you completed, how you completed them, the challenges you faced, how you
   overcame them, and the rules that you followed during completion of the tasks.

## Additional Notes for the Coding Agent

Note: This file is specifically for coding agents and this section can be used
by the coding agent to add additional details about this project that would
be helpful for the agent to know when it is run again. Every time a coding
agent finishes a task, it should add notes here as it deems appropriate.
The coding agent should write the notes as a Markdown list.
