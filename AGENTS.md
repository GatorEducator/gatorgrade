# AGENTS.md

This document provides guidelines for AI agents contributing to this repository.

## Overview of Instructions

- **Always use `uv`:** This project uses `uv` for all dependency management,
  virtual environments, and task running. Do not use `pip` or `venv` directly.
- **Follow all guidelines:** Read and follow [CONTRIBUTING.md](CONTRIBUTING.md)
  before making changes. It contains the shared contributor requirements,
  issue workflow, setup, coding standards, tests, and scripts. Follow the
  additional agent-specific rules in this file as well.
- **Verify your changes:** Before committing any changes, you must run all
  linters and tests to ensure your changes are correct and follow the project's
  style. Follow [testing and checks](CONTRIBUTING.md#testing-and-checks),
  including `uv run task all` and the separate coverage task.
- **Permission to run commands:** You have permission to run all commands in
  this file to verify their functionality.
- **Incremental changes:** Make small, incremental changes. This makes it easier
  to review your work and catch errors early.
- **Communicate clearly:** When you propose changes, explain what you've done
  and why.
- **Publishing issues and comments:** Contributor workflow requirements do
  not authorize agents to publish issues or comments. Prepare drafts unless
  the developer explicitly authorizes those external actions.
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

## Shared Contributor Requirements

Use [CONTRIBUTING.md](CONTRIBUTING.md) as the authoritative source for shared
commands, code and testing requirements, documentation, and review practices.
Its [contributor scripts](CONTRIBUTING.md#contributor-scripts) section explains
the comment checker, version checker, direct-test analysis, and optional
mutation helpers. Keep shared instructions there instead of duplicating them
in this file.

## Making Changes

1. **Understand:** Thoroughly understand the request and the relevant codebase.
   Use the available tools to explore the code.
1. **Plan:** Formulate a clear plan before making any changes.
1. **Implement:** Make small, incremental changes.
1. **Verify:** Run the [required checks](CONTRIBUTING.md#testing-and-checks)
   and report the results and any verification limitations.
1. **Commit:** The software developer will always commit the changes.
1. **Rules**: Always follow this file and [CONTRIBUTING.md](CONTRIBUTING.md).
1. **Completion**: When you are finished with tasks, please summarize what tasks
   you completed, how you completed them, the challenges you faced, how you
   overcame them, and the rules followed during completion of the tasks.

## Additional Notes for the Coding Agent

Note: This file is specifically for coding agents and this section can be used
by the coding agent to add additional details about this project that would
be helpful for the agent to know when it is run again. Every time a coding
agent finishes a task, it should add notes here as it deems appropriate.
The coding agent should write the notes as a Markdown list.

- Shared standards and current checker commands live in CONTRIBUTING.md.
  Its AI-policy link is an intentional placeholder until the dedicated policy
  is published.
- Issue-report prompts live in .github/ISSUE_TEMPLATE/. Keep the contribution
  guide's issue workflow and the pull request checklist aligned with them.
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
