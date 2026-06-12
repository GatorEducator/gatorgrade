# GatorGrade

GatorGrade is a Python tool that automates the assessment of student
assignments by running configurable checks. It supports both
[GatorGrader](https://github.com/GatorEducator/gatorgrader) checks and custom
shell commands. GatorGrade produces rich output showing pass and fail status,
computes weighted scores, and can generate reports in JSON or Markdown format.
This tool is the Python-based successor to
[GatorGradle](https://github.com/GatorEducator/gatorgradle).

## Installation

GatorGrade requires Python 3.10 or later.

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

## Quick Start

An assignment must contain a `gatorgrade.yml` file that defines the checks to
run. Run GatorGrade from the assignment directory:

```bash
gatorgrade
```

GatorGrade will run each check and display a summary of passing and failing
checks along with a weighted score.

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
GatorGrader check or a shell command check.

### GatorGrader Checks

GatorGrader checks verify specific aspects of source code or writing.

```yaml
- description: Complete all TODOs
  check: MatchFileFragment
  options:
    fragment: TODO
    count: 0
```

### Shell Command Checks

Shell command checks run arbitrary shell commands.

```yaml
- description: Run pylint
  command: pylint src/*.py --disable=all --enable=E
```

### File Context Checks

Checks can target specific files by nesting them under a file path.

```yaml
- src:
  - hello_world.py:
    - description: Complete all TODOs
      check: MatchFileFragment
      options:
        fragment: TODO
        count: 0
```

### Setup Commands

You can include setup commands that run before the checks.

```yaml
setup: |
  pip install -r requirements.txt
  echo "Setup complete"

- description: Run tests
  command: pytest
```

### Weight

Each check can have an optional weight that affects the overall score. The
weight must be a positive integer.

```yaml
- description: Critical check
  check: MatchFileFragment
  weight: 10
  options:
    fragment: TODO
    count: 0
```

Checks without an explicit weight use the baseline weight. The default baseline
weight is 1. You can change it with `--baseline-weight`.

### Output Limit

Each check can have an optional output limit that controls how many diagnostic
lines are displayed if the check fails. The limit must be a positive integer.

```yaml
- description: Limited check
  command: echo "test"
  outputlimit: 3
```

If a check does not specify an output limit, GatorGrade uses the global limit
set by `--output-limit`.

## Reports

GatorGrade can generate reports in JSON or Markdown format.

### JSON Report

Save a JSON report to a file:

```bash
gatorgrade --report FILE JSON report.json
```

### Markdown Report

Save a Markdown report to a file:

```bash
gatorgrade --report FILE MD report.md
```

### GitHub Actions

Write a Markdown report to the GitHub Actions job summary:

```bash
gatorgrade --report ENV MD GITHUB_STEP_SUMMARY
```

Write a JSON report to a GitHub Actions environment variable:

```bash
gatorgrade --report ENV JSON GITHUB_ENV
```

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

[GatorGrade Wiki]: https://github.com/GatorEducator/gatorgrade/wiki/Contributing-Guidelines
