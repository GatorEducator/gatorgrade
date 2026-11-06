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
- [Local checks and hooks](#local-checks-and-hooks)
- [Coding standards](#coding-standards)
- [Testing and checks](#testing-and-checks)
- [Contributor scripts](#contributor-scripts)
- [Documentation and debugging](#documentation-and-debugging)
- [Making a pull request](#making-a-pull-request)
- [Reviewing a pull request](#reviewing-a-pull-request)
- [Merging and releasing](#merging-and-releasing)
- [Getting help and external resources](#getting-help-and-external-resources)

## Use of AI

Review and test AI-assisted code, documentation, and communication for
accuracy, safety, and respectful language. You remain responsible for the
result; only claim verification you performed.

Disclose substantial AI assistance in contributions and project communication.
In affected commit bodies, explain the tool's contribution and how you
verified it, then add an `Assisted-by: <tool name>` trailer. Include the
model and version when known.

## Finding ways to help

Check [issues][issues], [pull requests][pulls], and related discussions before
starting. Look for [good-first-issue][first] and [help-wanted][help-issues]
labels. You can improve examples or documentation, report a reproducible
bug, add a regression test, or review a pull request.

Coordinate overlapping work in issue comments. Keep changes small and easy
to review and verify.

## Raising and tracking issues

Changes normally need an issue. Decide minor fixes, such as typos or small
documentation changes, case by case. If you skip an issue, explain the scope
and reason in the PR. Ask a maintainer when unsure.

- Search issues and pull requests for duplicates, then
  [open an issue][new-issue] if needed.
- Before starting, comment on the issue with your name and any teammates.
  Broader design discussion is encouraged but optional.
- Complete the bug report or feature request template. Keep reproduction
  steps, expected behavior, and environment details in the issue; see the
  [bug report template][bug-template]. For other changes, explain the
  problem, scope, and verification. Remove credentials and private
  assignment or student data from examples and output.
- Check duplicates and open an issue for other problems you discover, even
  if your PR is already open. Link related work and keep the PR focused.
- Link relevant issues in the PR and comment its URL on **each linked
  issue**, including links added later. Use closing keywords only for fully
  resolved issues; use references for partial or related work.

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
uv run task hooks-install
uv run gatorgrade --version
uv run gatorgrade --help
```

Sync creates the environment, installs development dependencies, and makes
this checkout editable: Python edits take effect without reinstalling.
Sync again after dependency or package metadata changes, and keep dependency
changes with their lockfile updates.

Contributors install hooks in each new clone; agents need explicit developer
authorization before installing them. They check staged changes and commit
messages, not PR titles. See [local checks and hooks](#local-checks-and-hooks) for
full checks, and isolated hook smoke tests.

### CI environment and optional dependencies

Documentation-only contributors do not need auto-hint dependencies. For code
changes or to reproduce CI's dependency setup, run:

```bash
uv sync --dev --extra auto-hint
uv run --extra auto-hint task all
uv run --extra auto-hint task test-coverage
```

The extra includes the remote client and local model dependencies, including
PyTorch, needed for full type checking. Availability depends on Python, OS,
and architecture; report unsupported combinations with the resolver output.
A base installation does not verify that the extra installs or that a real
model works on your machine.

### Local checks and hooks

The setup command installs both pre-commit and commit-msg hooks. Installation
is local to each clone; cloning or syncing alone does not enable them. The
configured Node and hook tools are installed in isolated environments on
first use, which needs network access. Runtime dependencies are unchanged.

- Every commit runs the documented-task and coverage-setting guards.
- Changed Markdown runs Markdown and spelling checks using the project rules.
- Python, TOML, YAML, shell, or lock changes run uv run task all and the
  separate executed statement/branch coverage task. Full type checks need
  the auto-hint extra described above; documentation-only commits do not.
- Commit messages use the same basic Conventional Commits header checks as
  CI. Custom types and either breaking marker are accepted; PR titles are
  not checked by the hooks.

A failed hook aborts a normal commit without auto-formatting or editing
source. Fix the issue, stage the correction, and retry. Code checks run the
whole project, so unfinished untracked source can affect them too.

Check working files without installing hooks or implicitly stashing changes:

```bash
uv run pre-commit run --files AGENTS.md CONTRIBUTING.md
```

Replace the paths with the files to check. For all tracked files, use
uv run task hooks-check; it selects the full code suite and may temporarily
stash tracked edits not staged for commit. Agents must use explicit files.
These commands run pre-commit-stage checks, not the commit-message stage.

Run uv run task test-hooks for isolated rejection/recovery smoke tests of
commit messages, staged task names, Markdown, branch coverage, and Python.
The script exports the Git index, not necessarily uncommitted working files;
do not stage files merely to exercise a patch. It installs hooks and makes
synthetic commits only in a disposable checkout. CI also runs these tests.

Linked Git checkouts share hooks; use a dedicated clone for differing configs.
Hooks are opt-in and can be bypassed. They cannot prove truthful AI disclosure,
appropriate commit types, or compliance with every instruction. CI runs
independently; maintainers must configure required checks and bypass limits
for merge blocking. Hook installation does not change repository settings.
See the [configuration](.pre-commit-config.yaml),
[commit standards](docs/COMMIT_MESSAGES.md), and
[pre-commit documentation](https://pre-commit.com/) for details.

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
- Use the project's Ruff formatter, configured for 79 columns, and its
  import ordering.
- Keep text files, including Markdown, within 80 columns.
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
- Reuse existing validation and serialization patterns. Pydantic is not a
  declared dependency; do not assume it is available.
- Suppress lint rules with inline noqa comments, such as
  `# noqa: PLR0913`, rather than pylint disable comments.

Preserve existing CLI flags and report behavior unless the issue calls for
a compatibility change. Document intended breaking changes and their
migration path in the pull request.

This includes configuration formats and JSON/Markdown reports.

## Testing and checks

Run tasks from the repository root. Start with focused tests while developing,
then run the required checks before submitting or updating a pull request.
For documentation-only changes, run Markdown checks locally and use CI for
the full suite; report checks you did not run locally.

```bash
uv run task all
uv run task test-coverage
```

The all task runs linting, type checks, randomized tests, and the direct-test
analysis. The separate test-coverage task measures executed statements and
branches.

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

### Writing tests

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

Focused tests do not replace the required checks. Report failures and
environment limitations in your PR.

- Name tests descriptively with a test_ prefix. Group them by the function
  they exercise and order them logically within each group.
- Keep tests independent and runnable locally and in CI.
- Add or update tests for new behavior and regression cases, including
  relevant failure paths. Do not remove failing tests to make the suite pass.
- Verify tests also work with randomized execution.
- Mark Hypothesis property-based tests with `@pytest.mark.propertybased`.
  The contribution guard verifies this for collected Hypothesis tests.
- Mark tests that exercise the optional extra with `@pytest.mark.autohint`.
- Keep test cases from producing console output. Use pytest capture fixtures
  to assert output. The shared fixture in [tests/conftest.py] also redirects
  application streams and subprocess output; account for it when debugging.

### Test coverage

Aim for full function, statement, and branch coverage. If complete coverage
is not possible, explain the uncovered behavior in the PR. The configured
minimum for executed statement and branch coverage is 95%. Do not lower the
threshold or game coverage to pass.

```bash
uv run task test-coverage
```

The all task separately requires 75% direct-test coverage through static
analysis. This does not replace executed statement and branch coverage; see
[Contributor scripts](#contributor-scripts) for the distinction.

### Code linting

Ruff checks formatting, imports, docstrings, snake_case function names, and
absolute imports. Pytest rejects unregistered markers instead of treating
them as warnings.

Type checking includes mypy, ty, pyrefly, zuban, and symbex. Linting includes
Ruff, comment case, version consistency, and Markdown checks.

Fix commands modify files; inspect their diffs before including changes in
your PR.

### Continuous integration

[GitHub Actions][ci] runs the project's automated checks. The test matrix
covers the Python versions and operating systems listed under
[Prerequisites](#prerequisites). CI also checks commit headers and runs
isolated installed-hook smoke tests.

Linting, type checks, and coverage run in separate jobs. CI also runs a
separate Markdown spelling check using
[the project spelling configuration](.github/cspell.json).

Run local checks and review CI results. Report failures and limitations;
only claim checks passed if you ran them.

## Contributor scripts

### Automated contribution policy

The pull request template provides fields checked by the Contribution Policy
workflow: problem, changes, compatibility, verification, contributors,
linked issues or a minor-change exception, AI assistance, documentation
changes, and limitations. Complete these fields and target main. For AI
assistance, choose none or used; if used, identify the tool, its contribution,
and your verification. These declarations cannot prove truth or test quality.

Metadata validation always checks out refs/heads/main, never an
event-selected branch or PR code. It reads the actual target from the event
and rejects other targets. The workflow and validator must first land on
main; policy changes take effect after merge. Fenced examples do not
supply declarations.

Local hooks can be bypassed; maintainers must configure required CI checks
and reviews in GitHub for merge-time enforcement.

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

Update the README for installation, configuration, CLI, or report changes;
update this guide for contributor workflow changes. Keep docstrings and
examples accurate. Documentation-only changes still need Markdown linting
and the applicable CI documentation checks.
Keep specialized mutation instructions in their existing guide and link to
them here.

For debugging, start with the smallest failing test or disposable assignment.
Use GatorGrade with --version and --verbose to inspect the environment and
configuration. Record the working directory: selecting a configuration by
path does not automatically relocate the assignment's files.

Record manual checks with:

- Working directory, configuration, input files, and exact command.
- Expected and actual output, exit code, OS, and Python version.
- Passing and failing cases where relevant, including JSON report output.

Use disposable files to trigger checks. Remove credentials and private data
from shared logs.

## Making a pull request

Follow [GitHub Flow][flow] and the [pull request template][pr-template]:

1. Create or find an issue when required; comment with your name and
   teammates. For a minor change without an issue, explain why in the PR.
1. Work on a descriptive branch in your fork and keep the change focused.
1. Add tests and documentation, then run the required checks.
1. Follow the [commit message standards](docs/COMMIT_MESSAGES.md), based on
   Conventional Commits 1.0.0, including body and breaking-change footers.
1. Push your branch and open a pull request targeting the main branch of
   GatorEducator/gatorgrade. Use a draft if work is incomplete.
1. Complete every applicable template field. Explain the problem, resulting
   behavior, compatibility changes, verification commands and results, and
   anything you could not test. List contributors and link every relevant
   issue. Use `Closes #123` only for an issue the PR fully resolves.
1. Comment the PR URL on every linked issue, including later additions.
1. Respond to review feedback and rerun relevant checks after changes.

When reorganizing documentation, list moved or removed sections and their
new locations in the PR description. Preserve useful links and entry points;
adding a guide does not require deleting other documentation.

## Reviewing a pull request

Reviews are contributions too. Read the linked issue, description, and diff,
then check out the branch. With the [GitHub CLI][github-cli]:

```bash
gh pr checkout 123 --repo GatorEducator/gatorgrade
```

Save existing work before switching branches. Follow
[Base development environment](#base-development-environment) and
[CI environment and optional dependencies][ci-environment]
to set up the checkout, then run focused tests and required checks. Test
user-visible changes against a disposable assignment. Report commands,
results, OS, Python version, and anything you could not verify.

Submit a GitHub review: Comment, Approve, or Request changes. A favorable
conversation comment is not approval. Approve only changes you can endorse
based on your review and verification.

Address human and automated feedback. Verify suggestions; explain incorrect
ones with evidence. Summarize your updates and request another review.

## Merging and releasing

Before merge, GitHub Actions must pass and the PR must be reviewed by at least
one team member and one member of the Integration team, such as a senior
GatorGrader team member. Outside contributors can ask in the PR comments for
help identifying the appropriate reviewers.

Maintainers merge and publish releases. A merge does not mean a release is
immediately available; use the editable checkout until then. Publishing
workflows and detailed release procedures remain in maintainer documentation.

## Getting help and external resources

Ask change-specific questions in the issue or PR. For general help, search
existing issues before opening one. Report conduct concerns using the
contact in the [Code of Conduct](CODE_OF_CONDUCT.md).

- [Project README](README.md)
- [uv installation][uv-install]
- [uv project documentation][uv-projects]
- [Git documentation][git]
- [pytest documentation][pytest]
- [Conventional Commits 1.0.0][conventional-commits]
- [GitHub pull request reviews][rv]
- [Mutation testing](scripts/MUTATION.md)

[bug-template]: .github/ISSUE_TEMPLATE/bug_report.md
[ci]: .github/workflows/main.yml
[ci-environment]: #ci-environment-and-optional-dependencies
[first]: https://github.com/GatorEducator/gatorgrade/labels/good-first-issue
[conventional-commits]: https://www.conventionalcommits.org/en/v1.0.0/
[flow]: https://docs.github.com/en/get-started/using-github/github-flow
[gg]: https://github.com/GatorEducator/gatorgrader/blob/master/CONTRIBUTING.md
[git]: https://git-scm.com/doc
[github-cli]: https://cli.github.com/manual/gh_pr_checkout
[rv]: https://docs.github.com/pull-requests/reviewing-changes-in-pull-requests
[help-issues]: https://github.com/GatorEducator/gatorgrade/labels/help-wanted
[issues]: https://github.com/GatorEducator/gatorgrade/issues
[new-issue]: https://github.com/GatorEducator/gatorgrade/issues/new/choose
[pulls]: https://github.com/GatorEducator/gatorgrade/pulls
[pr-template]: .github/pull_request_template.md
[pytest]: https://docs.pytest.org/en/stable/
[repository]: https://github.com/GatorEducator/gatorgrade
[scripts/ccl.py]: scripts/ccl.py
[scripts/tsc.py]: scripts/tsc.py
[scripts/vsc.py]: scripts/vsc.py
[tests/conftest.py]: tests/conftest.py
[uv-install]: https://docs.astral.sh/uv/getting-started/installation/
[uv-projects]: https://docs.astral.sh/uv/guides/projects/
