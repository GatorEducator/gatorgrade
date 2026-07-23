<div align="center">
  <img alt="GatorGrade logo" src="https://raw.githubusercontent.com/GatorEducator/gatorgrade/main/.github/logo/GatorGrade.png" width="90%">
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

### Using uv tool install

Install globally so `gatorgrade` is available on your `PATH`:

```bash
uv tool install gatorgrade
```

After installation, run `gatorgrade` directly without `uvx`:

```bash
gatorgrade
```

### Using pipx

Install globally:

```bash
pipx install gatorgrade
```

After installation, run `gatorgrade` directly without `pipx`:

```bash
gatorgrade
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
weighted score and additional diagnostic information. If you want to use
GatorGrade's auto-hinting feature, you need to run it with
`uvx --from 'gatorgrade[auto-hint]' gatorgrade` as this will load in the
optional
dependencies that support hint generation.

## Command-Line Options

The following options control how GatorGrade runs:

- `--config`, `-c`: Specify a custom configuration file. The default is
  `gatorgrade.yml`. If the file is not found in the current working
  directory, gatorgrade also looks in the directory specified by
  `--config-dir` (or the default platform-specific config directory).
- `--report`, `-r`: Generate a report with three arguments in the format
  `destination format name`. The destination is `FILE` or `ENV`. The format is
  `JSON` or `MD`. The name is the output file path or the environment variable
  name. Examples:
  - `gatorgrade --report FILE JSON report.json`
  - `gatorgrade --report ENV MD GITHUB_STEP_SUMMARY`
- `--report-history`, `--no-report-history`: Enable or disable automatic JSON
  report history. History is enabled by default and is saved in the
  platform-specific user data directory. Automatic history is independent of
  `--report`.
- `--report-history-max-count`: Set the maximum number of automatic reports to
  retain. The default is 100. The value must be a positive integer.
- `--report-history-max-mb`: Set the maximum total size of automatic reports in
  MiB. The default is 100. The value must be a positive integer. Oldest history
  files are removed when either retention limit is exceeded.
- `--github-env`, `-g`: Write report data to the `GITHUB_ENV` file in GitHub
  Actions. Takes two arguments: the format (`JSON` or `MD`) and the name of the
  environment variable to set. When provided and the `GITHUB_ENV` environment
  variable is set, the report data is appended to that file for use by downstream
  workflow steps. This flag is independent of `--report`. Examples:
  - `gatorgrade --github-env json JSON_REPORT`
  - `gatorgrade --github-env md MD_REPORT`
- `--output-limit`, `-o`: Set the maximum number of diagnostic lines to display
  for a failing check. The default is 5. Must be at least 1.
- `--baseline-weight`, `-b`: Set the default weight for checks that do not
  specify an explicit weight. The default is 1. Must be at least 1.
- `--progress-bar`, `--no-progress-bar`: Show or hide the progress bar while
  checks run. The default is to show the progress bar.
- `--show-diagnostics`, `--no-show-diagnostics`: Show or hide diagnostic
  details for failing checks. The default is to show diagnostics.
- `--config-dir`, `-d`: Specify the directory for configuration files. The
  default is the platform-specific user config directory for gatorgrade. When the
  configuration file is not found in the current directory, gatorgrade looks in
  this directory.
- `--verbose`, `--no-verbose`: Show detailed configuration information before
  running checks. The default is to not show verbose information. Use this to see
  which config file, config directory, and CLI options are active.
- `--auto-hint`, `--no-auto-hint`: Automatically generate hints for failing
  checks using a local language model. The default is to not generate hints.
  Requires the `auto-hint` extra. Use together with `--auto-hint-model` to choose
  a different model.
- `--auto-hint-model`: Model identifier for auto-hint generation. The default
  for local models is `Qwen/Qwen2.5-0.5B-Instruct`. The default for remote
  servers is `Qwen/Qwen3.6-35B-A3B`. This option requires `--auto-hint`.
- `--auto-hint-url`: URL of an OpenAI-compatible API server for remote hint
  generation. When provided, the remote model is used instead of the local model.
  Falls back to the default local model on any remote server errors. This option
  requires `--auto-hint`.
- `--auto-hint-api-key`: API key for the remote auto-hint server. This option
  requires `--auto-hint-url`.
- `--auto-hint-track`, `--no-auto-hint-track`: Save or skip saving auto-hint
  generation details to `autohints.json` in the current working directory.
  Tracking is enabled by default and only applies when `--auto-hint` is active
  and hints are generated.
- `--filter-query`: Search term for pre-run check filtering. When provided,
  only checks matching this query are included or excluded. Filtering happens
  before checks run; if the filter keeps 10 of 400 checks, only those 10 run.
  This flag is the trigger for filtering; the other three filter flags have
  sensible defaults when this one is given. When combined with
  `--filter-failed-last` or `--filter-passed-last`, the text query runs second,
  narrowing the already status-filtered pool. The "Selected from N checks"
  summary line reports the size of that post-status, pre-text pool.
  - Examples:
    - `gatorgrade --filter-query "todo"`
    - `gatorgrade --filter-query "if" --filter-mode FUZZY`
- `--filter-mode`: Matching mode for the filter query. One of `EXACT`
  (case-insensitive whole-field equality), `CONTAINS` (case-insensitive substring
  containment, the default), or `FUZZY` (split query into words, each word
  matches as subsequence or by edit-distance closeness, all words required).
  Requires `--filter-query`.
- `--filter-by`: Field to match the filter query against. One of `DESCRIPTION`
  (the check description), `NAME` (the check name, or the shell command for
  top-level shell checks), `HINT` (the optional hint), or `ANY` (all three
  fields, the default). Requires `--filter-query`.
- `--filter-type`: Whether to keep or discard matching checks. `INCLUDE` (the
  default) keeps only the matching checks; `EXCLUDE` drops the matching checks
  and keeps the rest. Requires `--filter-query`.
- `--filter-fuzzy-threshold`: How aggressively the Levenshtein distance
  fallback matches words in FUZZY mode. A float between `0.0` (only exact
  subsequence matches, no typo tolerance) and `1.0` (any two words are considered
  close). The default is `0.4`, which allows "checking" to match "check" but
  keeps most unrelated words apart. Only used with `--filter-mode FUZZY`.
- `--filter-failed-last`: Select checks that failed in at least one of the
  newest number of retained history reports. Historical matching uses exact check
  IDs. This status filter runs first, before any `--filter-query` text filter,
  which then narrows the already-reduced pool. If no usable history exists, all
  checks are run with a warning. The value must be a positive integer.
- `--filter-passed-last`: Select checks that passed in all the newest number of
  retained history reports. Historical matching internally uses exact check
  identifiers. This status filter runs first, before any `--filter-query` text
  filter. When combined with `--filter-failed-last`, the two status filters
  intersect their matching checks first; any text filter then narrows that
  intersection. If no usable history exists, all checks are run with a warning.
  The value must be a positive integer.
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

### Project Name

An optional `name` field in the front matter sets a custom project name that
appears in the summary output and in reports. If no name is specified, the
current directory name is used.

```yaml
name: "Theory of Computation Final Examination"
setup: |
  uv sync --dev --no-install-project
---
```

### Due Date

An optional due date field in the front matter shows a countdown in the
summary output. The field can be named `due_date` (recommended),
`duedate`, `due`, or `date`. The format is `YYYY-MM-DD` (midnight) or
`YYYY-MM-DDTHH:MM:SS` (ISO 8601). If more than one of the approved names
for the due date field is found, the deadline associated with the attribute
`due_date` is used and `gatorgrade` outputs a warning message.

```yaml
due_date: "2026-12-15T23:59:00"
setup: |
  uv sync --dev --no-install-project
---
```

Using the colors defined by the terminal window, when the due date is
approaching (i.e., within 24 hours) the countdown is shown in yellow.
Otherwise, when the assignment is overdue, it is shown in red.

### System Prompt File

An optional `system_prompt_file` field in the front matter specifies a file
containing a custom system prompt for the auto-hint generator. The file can
contain any valid Markdown. When provided, this prompt replaces the built-in
system prompt entirely. GatorGrade searches for the file in the current
directory, alongside the configuration file, and then in the config directory.

```yaml
system_prompt_file: systemprompt.md
setup: |
  uv sync --dev --no-install-project
---
```

### Validation Phrases File

An optional `validation_phrases_file` field in the front matter specifies a
JSON file that defines quality rules for generated hints. The file must
contain an object with optional `must_contain` and `cannot_contain` lists of
phrases. Every generated hint is checked against these rules and flagged as
low quality if it violates them.

```json
{
  "must_contain": ["fix"],
  "cannot_contain": ["direct answer is", "complete solution"]
}
```

GatorGrade searches for the file in the current directory, alongside the
configuration file, and then in the config directory.

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

### Automatic Report History

GatorGrade automatically saves one JSON report for each completed run in the
platform-specific user data directory. Automatic history is enabled by default
and can be disabled with `--no-report-history`.

Each saved report is tagged with a **project scope**, consisting of a hash of
the config file path and optional project name. When you use the history-based
`--filter-failed-last` or `--filter-passed-last`, only reports matching the
current project's scope are considered. This keeps history from different
projects isolated even though all reports share the same directory.

History is limited to 100 reports and 100 MiB by default. The limits can be
changed with `--report-history-max-count` and `--report-history-max-mb`. The
oldest history files are removed when either limit is exceeded. These automatic
history files are separate from reports written with `--report` or
`--github-env`.

Use `--filter-failed-last` to run only checks that failed in at least one of the
newest retained reports. Historical matching uses each check's exact `check_id`.
This status filter runs first, narrowing the check list to only those with
matching history. When `--filter-query` is also supplied, the text query runs
second on that already-narrowed pool; the "Selected from N checks" summary line
reports the size of that post-status, pre-text pool.

Use `--filter-passed-last` to run only checks that passed in all of the newest
retained reports. A check is considered "passed" if it appears in a report
and did not fail in that report. Historical matching uses each check's exact
`check_id`. Like `--filter-failed-last`, this status filter runs first; when
both status filters are supplied together they intersect their matching checks,
and any `--filter-query` text filter then narrows that intersection second.

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
