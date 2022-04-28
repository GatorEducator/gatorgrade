"""Test suite for parse_config function."""

from gatorgrade.input.in_file_path import command_line_generator_list

def test_parse_config_gg_check_in_file_context_contains_file():
    # Given the path to the test yml file
    config = "tests/input/gatorgrade_one_gg_check_in_file_context.yml"
    # when the command_line_generator_list function is run
    output = command_line_generator_list(config)
    # then assert that the file path exists in the first index of the list
    assert "file.py" in output[0][0]  

def test_parse_config_gg_check_no_file_context_contains_no_file():
    # Given the path to the test yml file
    config = "tests/input/gatorgrade_one_gg_check_no_file_context.yml"
    # When command_line_generator_list is run
    output = command_line_generator_list(config)

    # Then assert that there is no file path indicated in the first index of list
    assert output[0][0] == ["--description", "Have 8 commits", "CountCommits", "--count", "8"]




def test_parse_config_gg_check_in_file_context_contains_file():
    # Given the path to the test yml file
    

    # When command_line_generator_list is run
    config = command_line_generator_list(config)

    # Then assert