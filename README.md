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

## Contributing to GatorGrade

If you would like to contribute to GatorGrade, please refer to the [GatorGrade
Wiki](https://github.com/GatorEducator/gatorgrade/wiki/Contributing-Guidelines)
for contributing guidelines.
