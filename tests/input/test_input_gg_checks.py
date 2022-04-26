"""Test suite for parse_config function."""

from gatorgrade.input.in_file_path import parse_config

def test_parse_config_gg_check_in_file_context_contains_file():
    # Given the path to the test yml file
    config = "tests/input/gatorgrade_one_gg_check_in_file_context.yml"
    # when the parse_config function is run
    output = parse_config(config)
    # then assert that the file path exists in the first index of the list
    assert "file.py" in output[0]  

def test_parse_config_gg_check_no_file_context_contains_no_file():
    # Given the path to the test yml file
    config = "tests/input/gatorgrade_one_gg_check_no_file_context.yml"
    # When parse_config is run
    output = parse_config(config)

    # Then assert that there is no file path indicated in the first index of list
    assert output[0] == ["--description", "Have 8 commits", "CountCommits", "--count", "8"]


