"""Test suite for output_functions.py."""

from output import output_functions
from gator import exceptions
import pytest


def test_run_commands_and_return_results_returns_correct_results():
    """Make sure the receive function in output_functions.py runs
    and returns the correct results in the form of a tuple list"""

    commands = {
        "shell": [{"description": "Run program", "command": "mdl"}],
        "gatorgrader": [
            [
                "--description",
                "Check TODOs",
                "MatchFileFragment",
                "--fragment",
                "TODO",
                "--count",
                "0",
                "--exact",
                "--directory",
                "../output",
                "--file",
                "output_functions.py",
            ]
        ],
    }

    expected_result = [("Check TODOs", True, "")]
    actual_result = output_functions.run_commands_and_return_results(commands)

    assert expected_result == actual_result


def test_bad_command_creates_diagnostic(capsys):
    """an improperly formatted command should produce a failed test and a diagnostic"""

    bad_command = {
        "gatorgrader": [
            [
                "--description",
                "Have a total of 8 commits, 5 of which were created by you",
                "CountCommitts",
                "--fragment",
                "TODO",
                "--count",
                "0",
                "--exact",
            ]
        ]
    }

    output_functions.run_commands_and_return_results(bad_command)
    out, err = capsys.readouterr()

    assert "Whoops" in out
