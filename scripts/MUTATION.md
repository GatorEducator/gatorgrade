# Mutation Testing with GatorGrade

This document explains how to perform mutation testing on GatorGrade using
cosmic-ray. It covers both manual workflows for developers who want to perform
mutation testing using command-line tools such as Cosmic-Ray. The scripts that
are referenced in this document are included in the `scripts/` directory of the
GitHub repository for GatorGrade, which is where this document is located.

## Table of Contents

- [Overview](#overview)
- [Manual Mutation Testing](#manual-mutation-testing)
  - [Initial Setup](#initial-setup)
  - [Viewing Results](#viewing-results)
  - [Understanding Mutation Output](#understanding-mutation-output)
  - [Incremental Workflow](#incremental-workflow)
  - [Tips for Writing Tests](#tips-for-writing-tests)
- [Helper Scripts Reference](#helper-scripts-reference)

---

## Overview

GatorGrade uses [cosmic-ray](https://cosmic-ray.readthedocs.io/) for mutation
testing. Mutation testing works by introducing small, deliberate changes
(mutations) to your code and verifying that your tests can detect these
changes. If a mutation causes tests to fail, the mutant is "killed" (good!). If
tests still pass with the mutation, the mutant "survives" (potentially
indicating missing test coverage or an equivalent mutant).

The cosmic-ray configuration is located in `cosmic-ray.toml` and specifies:

- **module-path**: `gatorgrade` (the code to mutate)
- **timeout**: `10.0` seconds per test run
- **test-command**: `pytest -x --tb=short -q` (stops on first failure)
- **distributor**: `local` (runs on local machine)

---

## Manual Mutation Testing

### Initial Setup

Initialize cosmic-ray mutation testing session:

```bash
uv run task cosmic-ray-init
```

This creates a `cosmic-ray.sqlite` database containing all mutation
specifications.

Run baseline tests to verify tests pass without mutations:

```bash
uv run task cosmic-ray-baseline
```

Execute mutation testing on entire codebase:

```bash
uv run task cosmic-ray-exec
```

This runs all tests against each mutant and records results in the database.

### Viewing Results

Generate formatted report of all mutation testing results:

```bash
uv run task cosmic-ray-report
```

Count killed vs survived mutants (summary):

```bash
uv run task cosmic-ray-report | grep -c "KILLED"
uv run task cosmic-ray-report | grep -c "SURVIVED"
```

Show only survived mutants with file and line information:

```bash
uv run task cosmic-ray-report | grep -B2 "SURVIVED"
```

Query survived mutants from database (detailed):

```bash
sqlite3 cosmic-ray.sqlite "SELECT m.job_id, m.module_path, m.operator_name,
m.occurrence, m.start_pos_row FROM mutation_specs m JOIN work_results r
ON m.job_id = r.job_id WHERE r.test_outcome = 'SURVIVED';"
```

Use helper script to list survivors in readable format:

```bash
scripts/list_survivors.sh 10
```

Show diff for a specific mutant (replace JOB_ID with actual ID):

```bash
scripts/show_mutant_diff.sh <job_id>
```

### Understanding Mutation Output

When querying the database, each line contains:

```
job_id|module_path|operator_name|occurrence|start_pos_row
```

For example:

```
33a053b45f654126811817a256780083|gatorgrade/output/output.py|core/AddNot|13|194
```

This means:

- **job_id**: `33a053b45f654126811817a256780083` (unique identifier)
- **module_path**: `gatorgrade/output/output.py` (file that was mutated)
- **operator_name**: `core/AddNot` (type of mutation - adds `not` operator)
- **occurrence**: `13` (13th occurrence of this operator type in the file)
- **start_pos_row**: `194` (line number where mutation occurs)

To see the actual code change (diff) for any mutant:

```bash
sqlite3 cosmic-ray.sqlite "SELECT diff FROM work_results WHERE
job_id = '<job_id>';"
```

Or use the helper script:

```bash
scripts/show_mutant_diff.sh <job_id>
```

### Incremental Workflow

This workflow allows you to focus on one surviving mutant at a time, test it
immediately, and write tests to kill it without rerunning the full mutation
suite.

**Step 1**: List surviving mutants:

```bash
scripts/list_survivors.sh 10
```

**Step 2**: View the diff for a specific mutant (copy job_id from step 1):

```bash
scripts/show_mutant_diff.sh <job_id>
```

**Step 3**: Test the specific mutant to verify it survives:

```bash
scripts/test_mutant.sh <job_id>
```

This will show you the diff and run tests with the mutation applied.

**Step 4**: Analyze the code and write or enhance tests to cover the mutated
code path.

**Step 5**: Test the mutant again to see if your new tests kill it:

```bash
scripts/test_mutant.sh <job_id>
```

If it now shows "KILLED", your tests are working!

**Step 6**: Run all tests to ensure nothing broke:

```bash
uv run task test
```

**Step 7** (Optional): Periodically rerun the full mutation suite to update
statistics:

```bash
rm cosmic-ray.sqlite
uv run task cosmic-ray-init
uv run task cosmic-ray-exec
```

**Note**: The helper scripts (`test_mutant.sh`, `show_mutant_diff.sh`,
`list_survivors.sh`) are available in the `scripts/` directory and work by
querying the cosmic-ray.sqlite database and using the `cosmic-ray apply`
command to apply individual mutations. They automatically change to the project
root directory when executed.

### Tips for Writing Tests

- Focus on edge cases and boundary conditions
- Add assertions for intermediate values, not just final results
- Test error conditions and exception handling
- Verify state changes and side effects
- Use parametrized tests to cover multiple scenarios

---

## Helper Scripts Reference

GatorGrade provides three helper scripts to simplify mutation testing:

### `scripts/list_survivors.sh`

Lists surviving mutants with their details.

**Usage**:

```bash
scripts/list_survivors.sh [limit]
```

**Default limit**: 10

**Output format**:

```
Job ID = abc123...
Location = gatorgrade/output/output.py:194
Operator = core/AddNot
Occurrence = 13
---
```

### `scripts/show_mutant_diff.sh`

Shows the diff for a specific mutant.

**Usage**:

```bash
scripts/show_mutant_diff.sh <job_id>
```

**Output**:

- Mutant details (file, operator, line, status)
- Unified diff showing the mutation

### `scripts/test_mutant.sh`

Tests a single mutant by applying it and running tests.

**Usage**:

```bash
scripts/test_mutant.sh <job_id>
```

**Process**:

1. Backs up original file
2. Applies mutation using `cosmic-ray apply`
3. Runs test suite
4. Restores original file
5. Reports KILLED or SURVIVED

**Exit codes**:

- `0`: Mutant was killed (tests failed)
- `1`: Mutant survived (tests passed)

## References

- [Cosmic Ray Documentation](https://cosmic-ray.readthedocs.io/)
- [Mutation Testing Wikipedia](https://en.wikipedia.org/wiki/Mutation_testing)
- [Equivalent Mutant Problem on
  Wikipedia](https://en.wikipedia.org/wiki/Mutation_testing#Equivalent_mutants)
