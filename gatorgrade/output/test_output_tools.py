"""Test suite for output_tools.py."""
import pytest
from output import output_tools

def test_split_command_string_splits_at_correct_delimiter():
    command = "--description Complete all TODOs in writing/reflection.md MatchFileFragment --fragment TODO --count 0 --exact"

    expected_list = ["--description", "Complete", "all", "TODOs", "in", "writing/reflection.md", "MatchFileFragment",
    "--fragment", "TODO", "--count", "0", "--exact"]

    actual_list = output_tools.split_command_string(command)

    assert expected_list == actual_list

def test_split_command_string_multiple_spaces_in_a_row():
    command = "This is   a    bad command   "

    expected_list = ["This", "is", "a", "bad", "command"]

    actual_list = output_tools.split_command_string(command)

    assert expected_list == actual_list

def test_split_command_string_bad_argument() :
    
    command = 1234

    expected_message = "an error has occurred.  Please make sure your command is in the proper format"

    actual_message = output_tools.split_command_string(command)

    assert expected_message == actual_message



