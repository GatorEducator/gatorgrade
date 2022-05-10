"""Test suite for output_functions.py."""

from gatorgrade.output import output_functions


def test_run_commands_and_return_results_returns_correct_results():
    """Make sure the receive function in output_functions.py runs
    and returns the correct results in the form of a tuple list"""

    # given a dictionary containing a list of commands
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
                "input/hello-world.py",
            ]
        ],
    }

    expected_result = [("Check TODOs", True, "")]

    # when the dictionary is run through the function
    actual_result = output_functions.run_commands_and_return_results(commands)

    # the result is a list containing a tuple with a string, a boolean and another string
    assert expected_result == actual_result


def test_bad_command_creates_diagnostic():
    """an improperly formatted command should produce a failed test and a diagnostic"""

    # given an improperly written command
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

    # when run through the function
    results = str(output_functions.run_commands_and_return_results(bad_command))

    # an exception is raised and printed without the program failing
    assert "gator.exceptions" in results
