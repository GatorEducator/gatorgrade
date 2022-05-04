# GatorGrade: A Python Tool to Implement GatorGrader

GatorGrade is a Python tool that executes GatorGrader, an automatic grading tool
that can be used to check assignments through user-created checks. GatorGrade is
the newer Python-based version of
[GatorGradle](https://github.com/GatorEducator/gatorgradle/blob/master/README.md).

## Table of Contents

- [Installing GatorGrade](#installing-gatorgrade)
  - [Including GatorGrade in Your Project](#including-gatorgrade-in-your-project)
- [Using GatorGrade](#using-gatorgrade)
  - [Running Checks](#running-checks)
    - [Interpreting Output](#interpreting-output)
  - [Generating a gatorgrade.yml File](#generating-a-gatorgrade.yml-file)
    - [Configuring GatorGrade Checks](#configuring-gatorgrade-checks)
- [Contributing to GatorGrade](#contributing-to-gatorgrade)
  - [Installing Dev Environment](#installing-dev-environment)
- [Contributors](#contributors)

## Installing GatorGrade

Installing GatorGrade requires a version of Python greater than 3.7. You can
install GatorGrade from PyPi using `pip` or `pipx` package installers. This
method of installation allows for GatorGrade to be accessible to all Python
projects on your computer.

### Including GatorGrade in Your Project

To include GatorGrade in your project we recommend using the `Poetry` package
manager. When using `Poetry` to install, use the `poetry add` command to add
the GatorGrade package. If you use another package manager, you can add
GatorGrade as a dependency the same way you would with other `pip` or `pipx` packages.

## Using GatorGrade

You can use GatorGrade as a student or instructor to run a series of
pre-prescribed checks against a project. Additionally, instructors can use
GatorGrade to to generate a `gatorgrade.yml` file that configures the checks.

### Running Checks

To run checks against an assignment, use the `gator grade` command.

#### Interpreting Output

All gatorgrader checks will be displayed as output.  Checks that
have passed gatorgrader will be green, while failing checks will be red.
The overall percentage of passed checks will be shown
at the bottom of the display.

### Generating a gatorgrade.yml file

Generate team

#### Configuring GatorGrade Checks

Input team

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

## Contributors
