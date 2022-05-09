"""Test suite for parse_config function."""

import pytest
from gatorgrade.input.parse_config import parse_config


def test_parse_config_gg_check_in_file_context_contains_file():
    """Test to make sure gatorgrader checks that have a file context include the file name in the list of lists."""
    # Given the path to the test yml file
    config = "tests/input/yml_test_files/gatorgrade_one_gg_check_in_file.yml"
    # when the parse_config function is run
    output = parse_config(config)
    # then assert that the file path exists in the first index of the list
    assert "file.py" in output["gatorgrader"][0]


def test_parse_config_check_gg_matchfilefragment():
    """Test to make sure keywords like MatchFileFragment appear inside the gator grader check list."""
    # Given the path to the test yml file
    config = "tests/input/yml_test_files/gatorgrade_matchfilefragment.yml"
    # When the parse_config is run
    output = parse_config(config)
    # Then assert that match file fragment exists
    assert ["--description", "Complete all TODOs", "MatchFileFragment", "--fragment", "TODO", "--count", "0", "--exact", "--directory", "path/to", "--file", "file.py"] == output["gatorgrader"][0]
    # Assert that output["gatorgrader"] is equal to expected output


def test_parse_config_gg_check_no_file_context_contains_no_file():
    """Test to make sure gator grader checks that have no file context do not show the file name in the outputted list."""
    # Given the path to the test yml file
    config = "tests/input/yml_test_files/gatorgrade_one_gg_check_no_file_context.yml"
    # When parse_config is run
    output = parse_config(config)
    # Then assert that there is no file path indicated in the first index of list
    assert output["gatorgrader"][0] == [
        "--description",
        "Have 8 commits",
        "CountCommits",
        "--count",
        "8",
    ]


def test_parse_config_puts_checks_in_correct_keys():
    """Test to make sure that gatorgrader checks are put inside the gatorgrader list and that shell commands are put inside the shell list."""
    # Given the path to the test yml file
    config = "tests/input/yml_test_files/gatorgrader_both_checks.yml"
    # When parse_config is run
    output = parse_config(config)
    # Then assert that there will be outputs in the shell and in gatorgrader
    assert {"description": "Pass MDL", "command": "mdl ."} in output["shell"]
    assert [
        "--description",
        "Complete all TODOs",
        "MatchFileFragment",
        "--fragment",
        "TODO",
        "--count",
        "0",
        "--exact"
    ] in output["gatorgrader"]


def test_parse_config_yml_file_runs_setup_shell_checks():
    """Run a yml file without shell setup commands to see if the program allows a yml file without those commands."""
    # given the path to the test yml file
    config = "tests/input/yml_test_files/gatorgrade_no_shell_setup_check.yml"
    # when the parse_config function is run
    output = parse_config(config)
    # then run a yml file without shell commands and see if the program can handle that
    assert output["gatorgrader"][0] == [
        "--description",
        "Have 8 commits",
        "CountCommits",
        "--count",
        "8",
    ]


def test_parse_config_check_shell_contains_command():
    """Test to make sure that the shell commands are found inside the 'shell' list."""
    # Given the path to the test yml file
    config = "tests/input/yml_test_files/gatorgrade_one_shell_command_check.yml"
    # When the parse_config is run
    output = parse_config(config)
    # Then assert that command is present in the shell
    assert output["shell"][0] == {"description": "Pass MDL", "command": "mdl ."}
