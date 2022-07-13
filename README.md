# GatorGrade: A Python Tool to Implement GatorGrader

GatorGrade is a Python tool that executes GatorGrader, an automatic grading tool
that can be used to check assignments through user-created checks. GatorGrade is
the newer Python-based version of
[GatorGradle](https://github.com/GatorEducator/gatorgradle/blob/master/README.md).

## Table of Contents

- [Installing GatorGrade](#installing-gatorgrade)
- [Using GatorGrade](#using-gatorgrade)
  - [Running Checks](#running-checks)
    - [Interpreting Output](#interpreting-output)
  - [Generating a gatorgrade.yml File](#generating-a-gatorgrade.yml-file)
    - [Configuring GatorGrade Checks](#configuring-gatorgrade-checks)
- [Contributing to GatorGrade](#contributing-to-gatorgrade)
  - [Installing Dev Environment](#installing-dev-environment)
- [Contributors](#contributors)

## Installing GatorGrade

GatorGrade requires Python 3.7 or later. To install GatorGrade, we recommend
using the [`pipx`](https://pypa.github.io/pipx/) Python application installer.
Once you have `pipx` installed, you can install GatorGrade by running `pipx install gatorgrade`.

## Using GatorGrade

You can use GatorGrade as a student or instructor to run a series of
pre-prescribed checks against a project. Additionally, instructors can use
GatorGrade to to generate a `gatorgrade.yml` file that configures the checks.

### Running Checks

To run checks against an assignment, use the `gatorgrade` command.

#### Interpreting Output

All GatorGrader checks will be displayed as output. Checks that
have passed gatorgrader will have a green check mark (:heavy_check_mark:)
next to the description. Failing checks will show a red (:x:) next to the
description. The overall percentage of passed checks will be shown
at the bottom of the display. Anything less than 100% will appear in
red, while 100% of checks passed will appear in green.

### Generating a gatorgrade.yml file

The generation of `gatorgrade.yml` file can be used to create assignments.

In the terminal within the main directory.

Use `gatorgrade generate <TARGET_PATH_LIST>` to generate `gatorgrade.yml` file.

`<TARGET_PATH_LIST>` should be a list of paths to files or folders that
will be included in the generated `gatorgrade.yml`. These paths will be
relative to where you run `gatorgrade generate`.

Paths should be precisely named since they will be exactly matched.
Please note that files and folders that start with `__` or `.` will
automatically be ignored.

#### Configuring GatorGrade Checks

There are multiple customizable options with GatorGrade!
GatorGrader checks are able to be configured to run
within a specific file context and without any file path.

To configure a check to be run within the context of a file path,
please be sure to include the path to the file before the check.
Then, you can define a description for the check by using the `description` key,
and use the `check` and `options` keys
for the name of the check and the options for the check.
See example below for reference.

```yml
- path/to:
    - file.py:
        - description: Complete all TODO
          check: MatchFileFragment
          options:
            fragment: TODO
            count: 0
```

To configure a check without a specified file path, just start with
the description for the check by using the `description` key, and use
the `check` and `options` keys for the name of the check
and the options for the check.
See example below for reference.

```yml
- description: Have a total of 8 commits, 5 of which were created by you
  check: CountCommits
  options:
    count: 8
```

## Contributing to GatorGrade

If you'd like to contribute to GatorGrade, refer to the
[GatorGrade wiki](https://github.com/GatorEducator/gatorgrade/wiki/Contributing-Guidelines)
with details on contributing guidelines.

### Installing Dev Environment

To install the dev environment, you must first have a version of python greater
than 3.7 as well as Poetry. After cloning the GatorGrade repository onto your
computer, run a `poetry install` to install all of the necessary dependencies
onto your computer. Now you can begin to contribute to the project following
the contributing guidelines.
