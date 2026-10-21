# Contributing to GatorGrade

Thank you for helping improve GatorGrade! Contributions include code,
documentation, tests, bug reports, and pull request reviews. Start with the
[README](README.md) to understand how the tool works, and follow our
[Code of Conduct](CODE_OF_CONDUCT.md) in all project interactions.

> [!NOTE]
>
> This guide covers GatorGrade: configuration, command execution, scoring,
> reports, history, and hints. For changes to GatorGrader's check
> implementations, see the [GatorGrader contribution guide][gg].

## Table of Contents

- [Use of AI](#use-of-ai)
- [Finding ways to help](#finding-ways-to-help)
- [Raising and tracking issues](#raising-and-tracking-issues)
- [Development setup](#development-setup)
- [Coding standards](#coding-standards)
- [Testing and checks](#testing-and-checks)
- [Contributor scripts](#contributor-scripts)
- [Documentation and debugging](#documentation-and-debugging)
- [Making a pull request](#making-a-pull-request)
- [Reviewing a pull request](#reviewing-a-pull-request)
- [Merging and releasing](#merging-and-releasing)
- [Getting help and external resources](#getting-help-and-external-resources)

## Use of AI

You are responsible for reviewing and testing AI-assisted code,
documentation, and communication for accuracy, safety, and respectful language.
Do not submit unreviewed output or claim verification you did not perform.

Disclose substantial AI assistance in contributions and project communication.
In affected commits, describe what the tool contributed and how you verified
it in the body, and add an `AI-Assisted: <tool name>` trailer.

## Finding ways to help

Browse the [issue tracker][issues] and existing [pull requests][pulls] before
starting work. Look for the [good-first-issue][first] and
[help-wanted][help-issues] labels. If no beginner issues are available, report
a reproducible bug, improve documentation, add a regression test, or review
an existing pull request.

Read related discussions to avoid duplicating another contributor's work.
If work overlaps, coordinate in the issue comments. Make small, incremental
changes that reviewers can understand and verify.

## Raising and tracking issues

Every proposed change needs an issue, including small documentation fixes.
Search existing issues and pull requests first, then [open an issue][new-issue]
if the problem or proposal has not been reported. Before starting work,
comment on the issue to identify yourself and any teammates working on it.
Broader design discussion in the issue comments is encouraged but optional.

Choose the bug report or feature request template in the issue chooser and
complete its prompts. These templates request the environment, reproduction
steps, and examples needed to understand the report. For other changes,
open a blank issue describing the problem, proposed scope, and how the result
can be verified. Remove credentials and private assignment or student data
from examples and output.

If you discover another problem while working, search for an existing report
and create an issue if needed, even when your pull request is already open.
Link related work and keep the current pull request focused.

Every pull request must link its issue or issues. Comment the pull request URL
on **each linked issue**. Repeat this for any issues linked after the pull
request opens. Use a closing keyword only when the pull request resolves the
issue; use a reference when it addresses only part of the work.

## Development setup

### Prerequisites

Install [Git][git] and [uv][uv-install], and use Python 3.11 or later. CI
currently tests Python 3.11 through 3.14 on Linux, macOS, and Windows. Use uv
for dependency management, virtual environments, and running project tasks.

### Fork, clone, and create a branch

Fork [GatorEducator/gatorgrade][repository] on GitHub. Replace YOUR-USERNAME
below with your GitHub username, then run:

```bash
git clone https://github.com/YOUR-USERNAME/gatorgrade.git
cd gatorgrade
git remote add upstream https://github.com/GatorEducator/gatorgrade.git
git switch -c docs/contribution-guide
```

Choose a descriptive branch name for your issue. Submit the eventual pull
request from your fork to the upstream repository's main branch.

### Base development environment

From the repository root, run:

```bash
uv sync --dev
uv run gatorgrade --version
uv run gatorgrade --help
```

The sync command creates the project environment, installs development
dependencies, and installs this checkout in editable mode. Python source
changes are available on the next run without reinstalling the package.
Run sync again after dependency or package metadata changes. Keep dependency
changes and their lockfile updates together.

### Auto-hint and CI environment

For auto-hint work or to reproduce CI's dependency setup, run:

```bash
uv sync --dev --extra auto-hint
uv run --extra auto-hint task all
uv run --extra auto-hint task test-coverage
```

The extra includes the remote client and local model dependencies, including
PyTorch. Full type checking currently needs these libraries, so install the
extra before running the complete verification suite. Package availability
depends on Python, operating system, and architecture. Report unsupported
combinations in an issue with the resolver output. A base installation is
useful for other contributions, but does not verify that the extra installs
or that a real model works on your machine.

### Running the edited checkout against an assignment

Keep the assignment separate from the GatorGrade checkout. In the assignment
directory containing its gatorgrade.yml, run:

```bash
uv run --project /absolute/path/to/gatorgrade gatorgrade --no-report-history
```

Replace the project path with your checkout's absolute path; quote it if it
contains spaces. The project option selects GatorGrade's environment while
preserving the assignment as the working directory. For auto-hint testing,
add uv's --extra auto-hint option before the gatorgrade command.

Confirm the imported source comes from your checkout:

```bash
uv run --project /absolute/path/to/gatorgrade python -c \
  "import gatorgrade; print(gatorgrade.__file__)"
```

The uvx gatorgrade command selects a release rather than this editable
environment. Check paths and versions before reporting that a local change
has no effect.

For a small existing example, run these commands from the repository root:

```bash
cd tests/test_assignment
uv run --project ../.. gatorgrade --no-report-history
cd ../..
```

Inspect the example's configuration and source to understand its expected
passing and failing checks. It is a test fixture, not a complete manual test
suite. Exercise your change with a disposable assignment copy or temporary
configuration and describe the expected result in your pull request.

## Coding standards

These requirements also apply to test functions and Python tools in scripts/.

- Keep source in gatorgrade/ and tests in tests/, mirroring source structure.
  Maintain behavior across the Python versions and operating systems in CI.
- Keep text files, including Markdown, within 80 columns. Use the project's
  Ruff formatter, configured for 79 columns, and its import ordering.
- Keep function bodies contiguous, without blank lines inside them.
- Add parameter and return type hints to every function.
- Use snake_case for functions and variables, PascalCase for classes, and
  UPPER_SNAKE_CASE for constants.
- Extract hard-coded strings, integers, and floats into named constants at
  the top of the module and use those constants throughout.
- Put imports at the top of the file, grouped as standard library,
  third-party, and local imports. Use absolute local imports and trailing
  commas where the formatter requires them.
- In new files, write single-line docstrings that start with a capital letter
  and end with a period. Preserve established docstring styles in existing
  files, including multi-line argument documentation.
- Start comments with a lowercase letter, except proper nouns and identifiers
  requiring capitals. See the allowed proper nouns in [scripts/ccl.py].
  Preserve existing comments during refactoring and use one space between
  sentences.
- Do not use backticks in comments, docstrings, or other prose inside source
  files. Use plain identifier names there.
- Use pathlib.Path for filesystem operations, rather than string paths.
- Catch specific exceptions and provide meaningful error messages.
- Use Pydantic models for data validation and JSON serialization.
- Suppress lint rules with inline noqa comments, such as
  `# noqa: PLR0913`, rather than pylint disable comments.

Preserve existing CLI flags, configuration formats, and JSON/Markdown report
behavior unless the issue calls for a compatibility change. Document intended
breaking changes and their migration path in the pull request.

## Testing and checks

Run tasks from the repository root. Start with focused tests while developing,
then run the required checks before submitting or updating a pull request:

```bash
uv run task all
uv run task test-coverage
```

The all task runs linting, type checks, randomized tests, and the direct-test
analysis. The separate test-coverage task measures executed statements and
branches, with a configured minimum of 95%. Aim for full function, statement,
and branch coverage. CI also runs a separate Markdown spelling check using
[the project spelling configuration](.github/cspell.json).

| Purpose | Command |
| --- | --- |
| Required combined checks | `uv run task all` |
| Linting and format checks | `uv run task lint` |
| Check Python formatting | `uv run task format` |
| Fix Python formatting | `uv run task format-fix` |
| Type checks | `uv run task typecheck` |
| Tests | `uv run task test` |
| Tests without console output | `uv run task test-silent` |
| Statement and branch coverage | `uv run task test-coverage` |
| Detailed direct-test analysis | `uv run task test-coverage-check-verbose` |
| Markdown lint | `uv run task rumdl-check` |
| Fix Markdown formatting | `uv run task rumdl-fix` |
| Comment case check | `uv run task comments-check` |
| Fix comment case | `uv run task comments-fix` |

Type checking includes mypy, ty, pyrefly, zuban, and symbex. Linting includes
Ruff, comment case, version consistency, and Markdown checks. Fix commands
modify files; inspect their diffs before including changes in your PR.

To run one existing test:

```bash
uv run pytest tests/input/test_checks.py::test_shell_check_with_description
```

Useful task variants include test-not-random, test-propertybased,
test-not-propertybased, test-autohint, test-not-autohint, and test-parallel.
For example, the base development path can run:

```bash
uv run task test-not-autohint
```

A subset is useful during development; it does not replace the required
checks. Record failures and environment limitations accurately in your PR.

### Writing tests

- Name tests descriptively with a test_ prefix. Group them by the function
  they exercise and order them logically within each group.
- Keep tests independent so randomized execution works locally and in CI.
- Add regression tests for bug fixes, including relevant failure paths.
- Mark Hypothesis property-based tests with `@pytest.mark.propertybased`.
- Mark tests that exercise the optional extra with `@pytest.mark.autohint`.
- Keep test cases from producing console output. Use pytest capture fixtures
  to assert output. The shared fixture in [tests/conftest.py] also redirects
  application streams and subprocess output; account for it when debugging.

## Contributor scripts

The Python tools in scripts/ support the standard tasks. Run them through uv
from the repository root; prefer the configured tasks for routine checks.

- [scripts/ccl.py] checks comment capitalization. The comments-check task
  checks gatorgrade/, tests/, and scripts/. The comments-fix task rewrites
  comments in those directories.
- [scripts/vsc.py] checks that the version in gatorgrade/version.py matches
  pyproject.toml. The vsc task runs during linting. For an intentional version
  update, `uv run -m scripts.vsc fix` copies the project version into the Python
  version file; review the resulting diff.
- [scripts/tsc.py] statically analyzes direct test calls. The configured
  test-coverage-check task requires 75% direct-test coverage and writes the
  ignored tsc.json report. This is distinct from executed statement/branch
  coverage and does not prove that assertions detect incorrect behavior.
  Running the script directly without a threshold uses a different default
  of 100%; use the task for the project's configured threshold.
- The optional mutation-testing helpers list survivors, show mutation diffs,
  and run one mutant. See the [mutation-testing guide](scripts/MUTATION.md)
  for commands and prerequisites. The shell helpers require Bash and sqlite3
  and use cosmic-ray.sqlite in the repository root. On Windows, use an
  environment providing those tools.

The test_mutant.sh helper temporarily modifies a source file and restores it
on normal completion. Run it only with your work saved and inspect the diff
afterward; interruption can leave the mutation and its .backup file behind.
Mutation testing is optional and is not part of the all task.

## Documentation and debugging

Update the README when changing installation, configuration, CLI options, or
reports. Update this guide when changing contributor workflows. Keep
docstrings and examples consistent with behavior. Documentation-only changes
must also pass Markdown linting and CI spelling checks. Keep specialized
mutation instructions in their existing guide and link to them here.

For debugging, start with the smallest failing test or assignment. Use
gatorgrade's --version and --verbose options to inspect the environment and
configuration. Record the working directory: selecting a configuration by
path does not automatically relocate the assignment's files.

For manual verification, describe the configuration, input files, exact
command, expected output, actual output, OS, and Python version. Exercise both
passing and failing behavior where relevant. Run against a disposable copy
when changing files to trigger a check, and remove credentials from output.

## Making a pull request

1. Create or find the issue and comment with your name and teammates.
1. Work on a descriptive branch in your fork and keep the change focused.
1. Add tests and documentation, then run the required checks.
1. Use [Conventional Commits 1.0.0][conventional-commits] for commit messages.
   For example: `docs: explain editable installs` or
   `fix(reports): preserve check metadata`. Use feat for features and fix for
   bug fixes; other useful types include docs, test, refactor, and chore.
   Scopes are optional. Mark breaking changes with ! before the colon or a
   BREAKING CHANGE footer, as described in the specification.
1. Push your branch and open a pull request targeting
   GatorEducator/gatorgrade's main branch. Use a draft if work is incomplete.
1. Complete the [pull request template](.github/pull_request_template.md).
   Explain the problem, resulting behavior, compatibility changes, and tests.
   List contributors and link every relevant issue. Use `Closes #123` only
   for an issue the PR fully resolves.
1. Comment the PR URL on every linked issue, including later additions.
1. Respond to review feedback and rerun relevant checks after changes.

When consolidating documentation, state in the PR description which sections
were moved or removed and where their replacements live. Preserve useful
links and entry points so readers can still find the information.

## Reviewing a pull request

Reviewing is a contribution even if you do not author the change. Read the
linked issue, description, and diff, then check out the proposed branch. One
option, if you use the [GitHub CLI][github-cli], is:

```bash
gh pr checkout 123 --repo GatorEducator/gatorgrade
```

Save existing work before switching branches. Run uv sync --dev, adding the
auto-hint extra when appropriate, then focused tests and the required checks.
Test user-visible changes against an assignment. Report the commands you ran,
results, OS, and Python version, and identify anything you could not verify.

Submit a GitHub review with Comment, Approve, or Request changes. A favorable
conversation comment does not count as an approval. Approve only when you are
willing to endorse the change based on your review and verification.

Authors should address human and automated review comments. Verify suggested
changes; if a suggestion is incorrect, explain why with evidence. Summarize
how requested changes were addressed and request another review when ready.

## Merging and releasing

Before merge, GitHub Actions must pass and the PR must be reviewed by at least
one team member and one member of the Integration team, such as a senior
GatorGrader team member. Outside contributors can ask in the PR comments for
help identifying the appropriate reviewers.

Maintainers handle merging and publication. A merge does not guarantee an
immediate package release. Keep using the editable checkout to test changes
that have not reached a published version. Detailed release procedures are
maintainer documentation and are outside this guide.

## Getting help and external resources

Ask questions about a change in its issue or pull request so others can find
the discussion. For general contribution questions, search existing issues
and open an issue if needed. Report conduct concerns using the contact in the
[Code of Conduct](CODE_OF_CONDUCT.md).

- [GatorGrade README](README.md)
- [uv installation][uv-install]
- [uv project documentation][uv-projects]
- [Git documentation][git]
- [pytest documentation][pytest]
- [Conventional Commits 1.0.0][conventional-commits]
- [GitHub pull request reviews][rv]
- [Mutation testing](scripts/MUTATION.md)

[first]: https://github.com/GatorEducator/gatorgrade/labels/good-first-issue
[conventional-commits]: https://www.conventionalcommits.org/en/v1.0.0/
[gg]: https://github.com/GatorEducator/gatorgrader/blob/master/CONTRIBUTING.md
[git]: https://git-scm.com/doc
[github-cli]: https://cli.github.com/manual/gh_pr_checkout
[rv]: https://docs.github.com/pull-requests/reviewing-changes-in-pull-requests
[help-issues]: https://github.com/GatorEducator/gatorgrade/labels/help-wanted
[issues]: https://github.com/GatorEducator/gatorgrade/issues
[new-issue]: https://github.com/GatorEducator/gatorgrade/issues/new/choose
[pulls]: https://github.com/GatorEducator/gatorgrade/pulls
[pytest]: https://docs.pytest.org/en/stable/
[repository]: https://github.com/GatorEducator/gatorgrade
[scripts/ccl.py]: scripts/ccl.py
[scripts/tsc.py]: scripts/tsc.py
[scripts/vsc.py]: scripts/vsc.py
[tests/conftest.py]: tests/conftest.py
[uv-install]: https://docs.astral.sh/uv/getting-started/installation/
[uv-projects]: https://docs.astral.sh/uv/guides/projects/
