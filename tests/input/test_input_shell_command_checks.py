""" Test suite for shell commands"""

from gatorgrade.input.in_file_path import parse_config

# Not gonna have file path and will have command in it in

def test_parse_config_setup_shell():
    # Given the path to the test yml file
    config = "tests/input/gatorgrade.yml"
    # When parse_config is run
    output = parse_config(config)

    # Then assert that setup should be the indicated function
    assert "setup" in output

def test_setup_shell_commands():
    # Given
    # When
    # Then






# def test_parse_config_gg_check_no_file_context_contains_no_file():
#     # Given the path to the test yml file
#     config = "tests/input/gatorgrade_one_gg_check_no_file_context.yml"                        # Example of function test
#     # When parse_config is run
#     output = parse_config(config)

#     # Then assert that there is no file path indicated in the first index of list
#     assert output[0] == ["--description", "Have 8 commits", "CountCommits", "--count", "8"] 

