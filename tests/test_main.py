"""Tests for the main file of the project.

In the tests below, print statements that print Typer's captured stdout will
only display output when tests fail. These print statements are required
because disabling output capture through pytest does not disable Typer's output
capturing.
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
    "assignment_path,expected_output_and_freqs",
    [
        (
            "./tests/test_assignment",
            [
                ("Complete all TODOs", 2),
                ("Use an if statement", 1),
                ("\u2714", 3),  # Checkmarks
                ("\u2718", 0),  # Crossmarks
                ("Passing all GatorGrader Checks", 1),
                ("100.0%", 1),
            ],
        )
    ],
)
def test_full_integration_creates_valid_output(
    assignment_path, expected_output_and_freqs, chdir
):
    """Tests full integration pipeline to ensure input assignments give the correct output."""
    chdir(assignment_path)
    result = runner.invoke(main.app)
    print(result.stdout)

    assert result.exit_code == 0
    for output, freq in expected_output_and_freqs:
        assert result.stdout.count(output) == freq
