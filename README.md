<div align="center">
  <img alt="GatorGrade logo" src=".github/logo/GatorGrade.png" width="90%">
</div>

# GatorGrade

GatorGrade is a Python tool that automates the assessment of student
assignments by running configurable checks. It supports both
[GatorGrader](https://github.com/GatorEducator/gatorgrader) checks and custom
shell commands. GatorGrade produces rich output showing pass and fail status,
computes weighted scores, and can generate reports in JSON or Markdown format.
This tool is the Python-based successor to
[GatorGradle](https://github.com/GatorEducator/gatorgradle).

## Quick Start

Navigate to a directory containing a `gatorgrade.yml` file and run:

```bash
uvx gatorgrade
```

GatorGrade runs all checks and displays a summary. See
[Command-Line Options](#command-line-options) and [Reports](#reports) for
detailed usage.

## Installation

GatorGrade requires Python 3.11 or later.

### Using uvx

Run the latest version without installing:

```bash
uvx gatorgrade
```

### Using pipx

Install globally:

```bash
pipx install gatorgrade
```

### Installing from Source

Install in editable mode for development:

```bash
uv pip install -e .
```

Or use `uv sync` if the repository contains a `uv.lock` file:

```bash
uv sync
```

## Configuration Overview

An assignment must contain a `gatorgrade.yml` file that defines the checks to
run. If you installed `gatorgrade` with `uv` or `pipx`, then run GatorGrade from
the assignment directory with the command `gatorgrade`. Alternatively, if you
use `uvx`, run GatorGrade with the command `uvx gatorgrade`. GatorGrade will run
each check and display a summary of passing and failing checks along with a
weighted score and additional diagnostic information.

## Command-Line Options

The following options control how GatorGrade runs:

- `--config`, `-c`: Specify a custom configuration file. The default is
  `gatorgrade.yml`.
- `--report`, `-r`: Generate a report with three arguments in the format
  `destination format name`. The destination is `FILE` or `ENV`. The format is
  `JSON` or `MD`. The name is the output file path or the environment variable
  name. Examples:
  - `gatorgrade --report FILE JSON report.json`
  - `gatorgrade --report ENV MD GITHUB_STEP_SUMMARY`
- `--github-env`, `-g`: Write report data to the `GITHUB_ENV` file in GitHub
  Actions. Takes two arguments: the format (`JSON` or `MD`) and the name of
  the environment variable to set. When provided and the `GITHUB_ENV`
  environment variable is set, the report data is appended to that file for
  use by downstream workflow steps. This flag is independent of `--report`.
  Examples:
  - `gatorgrade --github-env json JSON_REPORT`
  - `gatorgrade --github-env md MD_REPORT`
- `--output-limit`, `-o`: Set the maximum number of diagnostic lines to
  display for a failing check. The default is 5. Must be at least 1.
- `--baseline-weight`, `-b`: Set the default weight for checks that do not
  specify an explicit weight. The default is 1. Must be at least 1.
- `--progress-bar`, `--no-progress-bar`: Show or hide the progress bar while
  checks run. The default is to show the progress bar.
- `--show-diagnostics`, `--no-show-diagnostics`: Show or hide diagnostic details
  for failing checks. The default is to show diagnostics.
- `--version`: Show the GatorGrade version and exit.

## Configuring Checks

Checks are defined in a `gatorgrade.yml` file. Each check can be either a
GatorGrader check or a shell command check. The following example shows a
representative configuration. It is not exhaustive. You can combine these
features in any way that fits your assignment.

### Example Configuration

```yaml
setup: |
  pip install -r requirements.txt

---
- src:
  - main.py:
    - description: Complete all TODOs
      check: MatchFileFragment
      weight: 2
      options:
        fragment: TODO
        count: 0
        exact: true
    - description: Define a greet function
      check: MatchFileFragment
      options:
        fragment: "def greet("
        count: 1
  - tests:
    - test_main.py:
      - description: Write at least three test cases
        check: MatchFileFragment
        options:
          fragment: "def test_"
          count: 3
- writing:
  - reflection.md:
    - description: Write at least 100 words
      check: CountMarkdownWords
      weight: 3
      options:
        count: 100
- description: Pass all tests
  check: ShellCommand
  outputlimit: 5
  command: pytest --tb=short
- description: Check code formatting
  check: ShellCommand
  command: ruff format --check src/
```

### Setup Commands

The `setup` section runs shell commands before the checks. If a setup command
fails, GatorGrade exits immediately.

### File Context Checks

Checks nested under a file path run in that file's context. The path is
converted into `--directory` and `--file` arguments for GatorGrader.

### Global Checks

Checks at the top level run without a file context. These are useful for
repository-wide checks or shell commands.

### Weight

Each check can have an optional weight. The weight must be a positive integer.
Checks without an explicit weight use the baseline weight. The default baseline
weight is 1. You can change it with `--baseline-weight`.

### Output Limit

Each check can have an optional output limit that controls how many diagnostic
lines are displayed if the check fails. The limit must be a positive integer. If
a check does not specify an output limit, GatorGrade uses the global limit set
by `--output-limit`.

## Reports

GatorGrade can generate reports in JSON or Markdown format.

### File Reports

Save a report directly to a file path:

```bash
# JSON report
gatorgrade --report FILE JSON report.json

# Markdown report
gatorgrade --report FILE MD report.md
```

### Environment Variable Reports

Save a report to the file path stored in an environment variable. This is
useful for CI systems where the output location is provided as an environment
variable. For example, in GitHub Actions:

```bash
# Write Markdown to the job summary
gatorgrade --report ENV MD GITHUB_STEP_SUMMARY
```

You can also use any custom environment variable:

```bash
export MY_REPORT="/tmp/report.json"
gatorgrade --report ENV JSON MY_REPORT
```

### GitHub Actions Environment Variable (`--github-env`)

When running in GitHub Actions, the `--github-env` flag writes report data
to the `GITHUB_ENV` file, making it available to downstream workflow steps
as an environment variable. This flag is independent of `--report`.

```bash
# Append JSON_REPORT=<json> to the GITHUB_ENV file
gatorgrade --github-env json JSON_REPORT

# Append MD_REPORT=<markdown> to the GITHUB_ENV file
gatorgrade --github-env md MD_REPORT
```

The first argument is the format (`JSON` or `MD`). The second argument is the
name of the environment variable to set. If the `GITHUB_ENV` environment
variable is not set (i.e., not running in GitHub Actions), the flag is
silently ignored.

For more information about how these environment variables work in GitHub
Actions, see the documentation for
[setting an environment variable](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-an-environment-variable)
and
[adding a job summary](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#adding-a-job-summary).

## Example Output

```text
Running Set Up Command(s)

Finished!

Running Check(s)

  Complete all TODOs
  Call the say_hello function
  Write at least 25 words in writing/reflection.md

Failing Check(s)

  Write at least 25 words in writing/reflection.md
     Diagnostic: Found 3 word(s) in total of file reflection.md
     Weight: 1

- Project: assignment-name
- Checks: 2/3 (67%)
- Points: 2/3 (67%)
```

## Development

### Testing

Run all tests:

```bash
uv run task test
```

Run tests without output:

```bash
uv run task test-silent
```

Run tests with coverage:

```bash
uv run task test-coverage
```

Run tests with direct coverage checks:

```bash
uv run task test-coverage-check-verbose
```

### Linting and Formatting

Run all linting checks:

```bash
uv run task lint
```

Fix code formatting:

```bash
uv run task format-fix
```

### Type Checking

Run all type checkers:

```bash
uv run task typecheck
```

### Complete Check

Run all linting and testing commands:

```bash
uv run task all
```

### Mutation Testing

For information about mutation testing with GatorGrade, see
[MUTATION.md](scripts/MUTATION.md).

## Contributing

If you would like to contribute to GatorGrade, please refer to the
[GatorGrade Wiki] for contributing guidelines.

[gatorgrade wiki]: https://github.com/GatorEducator/gatorgrade/wiki/Contributing-Guidelines
