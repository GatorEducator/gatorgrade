# GatorGrade: Automated Assignment Assessment Tool

GatorGrade is a Python tool that automates the assessment of student
assignments by running configurable checks. It supports both GatorGrader
checks (an automatic grading tool) and custom shell commands. GatorGrade
produces rich output showing pass/fail status and can generate reports in
JSON or Markdown format, including integration with GitHub Actions. This
tool is the newer Python-based version of
[GatorGradle](https://github.com/GatorEducator/gatorgradle).

## Installing GatorGrade

GatorGrade requires Python 3.10 or later. You can install GatorGrade using
any of the following methods:

### Using uvx (Recommended for One-Time Use)

To run GatorGrade without installing it globally, use `uvx`:

```bash
uvx gatorgrade
```

This will download and run the latest version of GatorGrade from PyPI.

### Using pipx

Alternatively, you can use `pipx` to install GatorGrade globally:

```bash
pipx install gatorgrade
```

### Installing from Source for Development

To install GatorGrade from source in editable mode:

```bash
uv pip install -e .
```

This links the `gatorgrade` command to your local source code, allowing
you to test changes immediately.

### Installing from Source with uv sync

If the repository contains a `uv.lock` file, you can install all
dependencies and the package:

```bash
uv sync
```

Then activate the virtual environment to use `gatorgrade`.

## Using GatorGrade

To use GatorGrade to run checks for an assignment, the assignment must
contain a `gatorgrade.yml` file that defines the checks to run. For more
information on configuring this file, see the [Configuring
Checks](#configuring-checks) section below.

To run GatorGrade checks, execute the `gatorgrade` command within the
assignment directory:

```bash
gatorgrade
```

This will display the passing (✓) or failing (✕) status of each check
along with the overall percentage of passing checks.

### Command-Line Options

- `--config`, `-c`: Specify a custom configuration file (default:
  `gatorgrade.yml`)
- `--report`, `-r`: Generate a report in the format `destination:format:name`
  (e.g., `file:json:report.json` or `env:md:GITHUB_STEP_SUMMARY`)
- `--status-bar`, `--no-status-bar`: Enable or disable the progress bar

### Example Output

```console
Running set up commands...
Finished!

✔  Complete all TODOs
✔  Call the say_hello function
✘  Write at least 25 words in writing/reflection.md

-~-  FAILURES  -~-

✘  Write at least 25 words in writing/reflection.md
   → Found 3 word(s) in total of file reflection.md

         ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
         ┃ Passed 5/7 (71%) of checks for assignment-name!       ┃
         ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

## Configuring Checks

Checks are defined in a `gatorgrade.yml` file. Each check can be either a
GatorGrader check or a shell command check. Checks can run within a file
context (specific file) or in the global context (entire assignment).

### GatorGrader Checks

GatorGrader checks verify specific aspects of student work:

```yml
- description: Complete all TODOs
  check: MatchFileFragment
  options:
    fragment: TODO
    count: 0
```

### Shell Command Checks

Shell command checks run arbitrary shell commands:

```yml
- description: Run pylint
  command: pylint src/*.py --disable=all --enable=E
```

### File Context Checks

Checks can target specific files by nesting them under a file path:

```yml
- src:
    - hello_world.py:
        - description: Complete all TODOs
          check: MatchFileFragment
          options:
            fragment: TODO
            count: 0
```

### Setup Commands

You can include setup commands that run before checks:

```yml
setup: |
  pip install -r requirements.txt
  echo "Setup complete"

- description: Run tests
  command: pytest
```

### Report Configuration

Generate reports in JSON or Markdown format:

```bash
# Save JSON report to a file
gatorgrade --report "file:json:report.json"

# Save Markdown report to a file
gatorgrade --report "file:md:report.md"

# Output to GitHub Actions job summary
gatorgrade --report "env:md:GITHUB_STEP_SUMMARY"
```

This generates checks that verify TODO comments in the specified files.

## Using GatorGrade

To use GatorGrade to run GatorGrader checks for an assignment, the assignment
must contain a `gatorgrade.yml` file that defines the GatorGrader checks.
Instructors, for more information on configuring the `gatorgrade.yml` file, see
the [Configuring GatorGrader Checks](#configuring-gatorgrader-checks) section
below.

The following is the output of running GatorGrade on the [GatorGrade Hello
World](https://github.com/GatorEducator/gatorgrade-hello-world/tree/main)
assignment.

```console
Running set up commands...
Finished!

✔  Complete all TODOs
✔  Call the say_hello function
✔  Call the say_hello_color function
✘  Complete all TODOs
✘  Write at least 25 words in writing/reflection.md
✔  Pass pylint
✔  Have a total of 5 commits, 2 of which were created by you

-~-  FAILURES  -~-

✘  Complete all TODOs
   → Found 3 fragment(s) in the reflection.md or the output
✘  Write at least 25 words in writing/reflection.md
   → Found 3 word(s) in total of file reflection.md

         ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
         ┃ Passed 5/7 (71%) of checks for gatorgrade-hello-world! ┃
         ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

## Configuring Checks

Instructors can configure checks for an assignment by creating a
`gatorgrade.yml` file. The file supports two types of checks:
GatorGrader checks (e.g., `MatchFileFragment`, `CountCommits`) and shell
command checks.

To configure checks that run within a file context (i.e., for a specific
file), specify the path to the file as a key (or nested keys) before
specifying the checks:

```yml
- src:
    - hello_world.py:
        - description: Complete all TODOs
          check: MatchFileFragment
          options:
            fragment: TODO
            count: 0
        - description: Define a print statement
          check: MatchFileFragment
          options:
            fragment: print(
            count: 1
```

To configure checks that run in the global context (i.e., for the
assignment in general), specify the checks at the top level of the
`gatorgrade.yml` file:

```yml
- description: Have a total of 8 commits, 5 of which were created by you
  check: CountCommits
  options:
    count: 8
```

To configure a shell command check, use the `command` key instead of
`check`:

```yml
- description: Run pylint
  command: pylint src/*.py --disable=all --enable=E
```

## Development Commands

### Testing Commands

Run all tests with verbose output:

```bash
uv run task test
```

Run tests without output:

```bash
uv run task test-silent
```

Run tests with coverage tracking:

```bash
uv run task test-coverage
```

Run tests without property-based tests:

```bash
uv run task test-not-property
```

Run tests without order randomization:

```bash
uv run task test-not-random
```

### Linting and Formatting Commands

Run all linting checks:

```bash
uv run task lint
```

Check code formatting:

```bash
uv run task format
```

Fix code formatting:

```bash
uv run task format-fix
```

Run ruff linting checks:

```bash
uv run task ruff-check
```

### Type Checking Commands

Run all type checkers:

```bash
uv run task typecheck
```

Run the `mypy` type checker:

```bash
uv run task mypy
```

Run the `ty` type checker:

```bash
uv run task ty
```

Run the `pyrefly` type checker:

```bash
uv run task pyrefly
```

Run `symbex` checks for typed and documented functions:

```bash
uv run task symbex
```

### Complete Check

Run all linting and testing commands:

```bash
uv run task all
```

### Mutation Testing

For comprehensive information about mutation testing with GatorGrade, including
manual workflows, helper scripts, and specifications for automated mutation
testing agents, please see [MUTATION.md](MUTATION.md).

## Contributing to GatorGrade

If you would like to contribute to GatorGrade, please refer to the [GatorGrade
Wiki](https://github.com/GatorEducator/gatorgrade/wiki/Contributing-Guidelines)
for contributing guidelines.
