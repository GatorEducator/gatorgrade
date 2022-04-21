"""Test suite for output_tools.py."""
import pytest
from output import output_tools

def test_split_command_string_splits_at_correct_delimiter():
    command = "--description Complete all TODOs in writing/reflection.md MatchFileFragment --fragment TODO --count 0 --exact"

    expected_list = ["--description", "Complete", "all", "TODOs", "in", "writing/reflection.md", "MatchFileFragment",
    "--fragment", "TODO", "--count", "0", "--exact"]

    actual_list = output_tools.split_command_string(command)

    assert expected_list == actual_list

def test_remove_excess_spaces():
    command = "This is   a    bad command   "

    expected_string = "This is a bad command"

    actual_string = output_tools.remove_excess_spaces(command)

    assert expected_string == actual_string

def test_split_command_string_bad_argument() :
    
    command = 1234

    expected_message = "an error has occurred.  Please make sure your command is in the proper format"

    actual_message = output_tools.split_command_string(command)

    assert expected_message == actual_message





