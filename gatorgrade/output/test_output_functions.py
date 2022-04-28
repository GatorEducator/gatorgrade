"""Test suite for output_functions.py."""

import pytest
from output import output_functions


def test_receive_command_function_returns_no_error():
    """Make sure the receive function in output_functions.py runs"""

    command_type_lists = []
    commands = []
    command1 = [
        "--description",
        "Complete all TODOs",
        "MatchFileFragment",
        "--fragment",
        "TODO",
        "--count",
        "0",
        "--exact",
        "--directory",
        "/output/",
        "--file",
        "output_tools.py",
    ]
    command2 = [
        "--description",
        "Complete all TODOs",
        "MatchFileFragment",
        "--fragment",
        "Frog",
        "--count",
        "1",
        "--exact",
        "--directory",
        "/output/",
        "--file",
        "output_tools.py",
    ]
    commands.append(command1)
    commands.append(command2)
    command_type_lists[0].append(commands)
    try:
        output_functions.receive_command(command_type_lists)
    except Exception as exc:
        assert False, f"'Command receive function' raised an exception {exc}"
