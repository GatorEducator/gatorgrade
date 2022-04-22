# GatorGrade: A Python Tool to Implement GatorGrader

GatorGrade is a Python tool that executes GatorGrader, an automatic grading tool that can be used to check assignments through user-created checks. GatorGrade is the newer Python-based version of GatorGradle which can be found on GitHub at this link: https://github.com/GatorEducator/gatorgradle/blob/master/README.md. GatorGrade takes in a gatorgrader.yml file and tests each check for correctness against the code that it is connected to.

## Table of Contents:

- Installing GatorGrade
  - Including GatorGrade in Your Project
- Using GatorGrade
  - Running Checks
    - Interpreting Output (Output Team)
  - Generating a gatorgrade.yml File (Generate Team)
    - Configuring GatorGrade Checks (Input Team)
- Contributing to GatorGrade
  - Installing Dev Environment
- Contributors

## Installing GatorGrade

Installing GatorGrade requires a version of Python greater than 3.7. You can install GatorGrade from PyPi using `pip` or `pipx` package installers. This method of installation allows for GatorGrade to be accessible to all Python projects on your computer.

### Including GatorGrade in Your Project

To include GatorGrade in you project you can use `Poetry`. Once Poetry has been installed you can use `poetry add` to add the GatorGrade package.

## Using GatorGrade

You can use GatorGrade as a student or instructor to run a series of pre-prescribed checks against a project. Additionally, instructors can use GatorGrade to to generate a `gatorgrade.yml` file that configures the checks.

### Running Checks

To run checks against an assignment, use the `gator grade` command.

#### Interpreting Output 

Output team

### Generating a gatorgrade.yml file

Generate team

#### Configuring GatorGrade Checks

Input team

## Contributing to GatorGrade

If you'd like to contribute to GatorGrade, refer to the GatorGrade wiki with details on contributing guidelines here: https://github.com/GatorEducator/gatorgrade/wiki/Contributing-Guidelines.

### Installing Dev Environment

To install the dev environment, you must first have a version of python greater than 3.7 as well as Poetry. After cloning the GatorGrade repository onto your computer, run a `poetry install` to install all of the necessary dependencies onto your computer. Now you can begin to contribute to the project following the contributing guidelines.

## Contributors