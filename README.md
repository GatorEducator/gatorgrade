# GatorGrade: A Python Tool to Implement GatorGrader

GatorGrade is a Python tool that executes GatorGrader, an automatic grading tool
that can be used to check assignments through user-created checks. GatorGrade is
the newer Python-based version of
[GatorGradle](https://github.com/GatorEducator/gatorgradle/blob/master/README.md).

## Installing GatorGrade

GatorGrade requires Python 3.7 or later. To install GatorGrade, we recommend
using the [`pipx`](https://pypa.github.io/pipx/) Python application installer.
Once you have `pipx` installed, you can install GatorGrade by running
`pipx install gatorgrade`.

## Using GatorGrade

To use GatorGrade to run GatorGrader checks for an assignment, the assignment
must contain a `gatorgrade.yml` file that defines the GatorGrader checks.
Instructors, for more information on configuring the `gatorgrade.yml` file, see
the [Configuring GatorGrader Checks](#configuring-gatorgrader-checks) section
below.

To use GatorGrade to run GatorGrader checks, run the `gatorgrade` command within
the assignment. This command will produce output that shows the passing
(:heavy_check_mark:) or failing status (:x:) of each GatorGrader check as well
as the overall percentage of passing checks. The following is the output of
running GatorGrade on the [GatorGrade Hello
World](https://github.com/GatorEducator/gatorgrade-hello-world/tree/main)
assignment.

```console
Running set up commands...
Installing dependencies from lock file

No dependencies to install or update
Setup complete!
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

## Configuring GatorGrader Checks

Instructors can configure GatorGrader checks for an assignment by creating a
`gatorgrade.yml` file. In this file, you can configure GatorGrader checks to run
within a file context (i.e. for a specific file; `MatchFileFragment` is an
example of a GatorGrader check that should be run within a file context) _or_ in
the global context (i.e. for the assignment in general; `CountCommits` is an
example of a GatorGrader check that should be run in the global context).

To configure GatorGrader checks to run within a file context, specify the path
to the file as a key (or nested keys) before specifying the GatorGrader checks.
For each GatorGrader check, define a `description` to print in the
output, the name of the `check`, and any `options` specific to the GatorGrader check.

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

To configure GatorGrader checks to run in the global context, specify the
GatorGrader checks at the top level of the `gatorgrade.yml` file (i.e. not
nested within any path).

```yml
- description: Have a total of 8 commits, 5 of which were created by you
  check: CountCommits
  options:
    count: 8
```

### Using GatorGrade to Generate A Boilerplate `gatorgrade.yml` File

For convenience, instructors can use GatorGrade to generate a boilerplate
`gatorgrade.yml` file that contains files or folders given to the GatorGrade command.

To generate a `gatorgrade.yml` file, run `gatorgrade generate <TARGET_PATH_LIST>`,
where `<TARGET_PATH_LIST>` is a list of relative paths to files or folders you
want to include in the `gatorgrade.yml` file. These paths must correspond to
existing files or folders in the current directory. Any given folders will be
expanded to the files they contain. Please note that files and folders that
start with `__` or `.` and empty folders will be automatically ignored.

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

### Mutation Testing Commands

#### Initial Setup and Full Run

Initialize cosmic-ray mutation testing session:

```bash
uv run task cosmic-ray-init
```

Run baseline tests to verify tests pass without mutations:

```bash
uv run task cosmic-ray-baseline
```

Execute mutation testing on entire codebase:

```bash
uv run task cosmic-ray-exec
```

#### Viewing Results

Generate formatted report of all mutation testing results:

```bash
uv run cr-report cosmic-ray.sqlite
```

Count killed vs survived mutants (summary):

```bash
uv run cr-report cosmic-ray.sqlite | grep -c "KILLED"
uv run cr-report cosmic-ray.sqlite | grep -c "SURVIVED"
```

Show only survived mutants with file and line information:

```bash
uv run cr-report cosmic-ray.sqlite | grep -B2 "SURVIVED"
```

Query survived mutants from database (detailed):

```bash
sqlite3 cosmic-ray.sqlite "SELECT m.job_id, m.module_path, m.operator_name,
m.occurrence, m.start_pos_row FROM mutation_specs m JOIN work_results r ON
m.job_id = r.job_id WHERE r.test_outcome = 'SURVIVED';"
```

Use helper script to list survivors in readable format:

```bash
scripts/list_survivors.sh 10
```

Show diff for a specific mutant (replace JOB_ID with actual ID):

```bash
scripts/show_mutant_diff.sh <job_id>
```

#### Understanding Mutation Output

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
sqlite3 cosmic-ray.sqlite "SELECT diff FROM work_results WHERE job_id = '<job_id>';"
```

#### Incremental Workflow for Killing Survived Mutants

This workflow allows you to focus on one surviving mutant at a time, test it
immediately, and write tests to kill it without rerunning the full mutation
suite.

Step 1: List surviving mutants:

```bash
scripts/list_survivors.sh 10
```

Step 2: View the diff for a specific mutant (copy job_id from step 1):

```bash
scripts/show_mutant_diff.sh <job_id>
```

Step 3: Test the specific mutant to verify it survives:

```bash
scripts/test_mutant.sh <job_id>
```

This will show you the diff and run tests with the mutation applied.

Step 4: Analyze the code and write or enhance tests to cover the mutated code
path.

Step 5: Test the mutant again to see if your new tests kill it:

```bash
scripts/test_mutant.sh <job_id>
```

If it now shows "KILLED", your tests are working!

Step 6: Run all tests to ensure nothing broke:

```bash
uv run task test
```

Step 7 (Optional): Periodically rerun the full mutation suite to update
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

#### Tips for Writing Tests to Kill Mutants

- Focus on edge cases and boundary conditions
- Add assertions for intermediate values, not just final results
- Test error conditions and exception handling
- Verify state changes and side effects
- Use parametrized tests to cover multiple scenarios

## Contributing to GatorGrade

If you would like to contribute to GatorGrade, please refer to the [GatorGrade
Wiki](https://github.com/GatorEducator/gatorgrade/wiki/Contributing-Guidelines)
for contributing guidelines.
