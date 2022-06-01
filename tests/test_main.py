"""Tests for the main file of the project.

In the tests below, print statements that print Typer's captured stdout will only display output when tests fail.
These print statements are required because disabling output capture through pytest does not work on Typer's output capturing.
"""

import pytest
from typer.testing import CliRunner

from gatorgrade import main

runner = CliRunner()


def test_gatorgrade_runs():
    """Test that ensures that the default command runs correctly."""

    assert True


def test_generate_creates_valid_yml():
    """Test that ensures that the generate command creates
    the .yml file correctly."""
    result = runner.invoke(main.app, ["generate"])
    print(result.stdout)

    assert result.exit_code == 0


def test_generate_fails_with_existing_yml():
    """Test that ensures that a second yml file isn't generated
    without the force command."""
    result = runner.invoke(main.app, ["generate"])
    print(result.stdout)

    assert result.exit_code == 0


def test_generate_force_option_creates_yml():
    """Test that ensures the force command works correctly."""
    result = runner.invoke(main.app, ["generate"])
    print(result.stdout)

    assert result.exit_code == 0


@pytest.mark.parametrize(
    "assignment_path,expected_checks",
    [
        (
            "./tests/test_assignment",
            [
                "\u2714  Complete all TODOs",
                "\u2714  Use an if statement",
                "|=====================================|\n|Passing all GatorGrader Checks "
                "100.0%|\n|=====================================|",
            ],
        )
    ],
)
def test_full_integration_creates_valid_output(assignment_path, expected_checks, chdir):
    """Tests full integration pipeline to ensure input assignments give the correct output."""
    chdir(assignment_path)
    result = runner.invoke(main.app)
    print(result.stdout)

    assert result.exit_code == 0
    for output_check in expected_checks:
        assert output_check in result.stdout
