"""Test suite for output_functions.py."""

from output import output_functions


def test_receive_command_function_returns_correct_results():
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
    actual_result = output_functions.run_commands_and_return_results(
        commands
    )

    assert expected_result == actual_result
