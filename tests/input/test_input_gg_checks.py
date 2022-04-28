"""Test suite for parse_config function."""

from gatorgrade.input.in_file_path import parse_config

def test_parse_config_gg_check_in_file_context_contains_file():
    # Given the path to the test yml file
    config = "tests/input/gatorgrade_one_gg_check_in_file_context.yml"
    # when the parse_config function is run
    output = parse_config(config)
    # then assert that the file path exists in the first index of the list
    assert "file.py" in output[0][0]  

def test_parse_config_gg_check_no_file_context_contains_no_file():
    # Given the path to the test yml file
    config = "tests/input/gatorgrade_one_gg_check_no_file_context.yml"
    # When parse_config is run
    output = parse_config(config)

    # Then assert that there is no file path indicated in the first index of list
    assert output == ["--description", "Have 8 commits", "CountCommits", "--count", "8"]


def test_parse_config_puts_checks_in_correct_keys():
    # Given the path to the test yml file
    config = "tests/input/gatorgrader_both_checks.yml"
    # When parse_config is run
    output = parse_config(config)
    # Then assert that 
    assert {"description": "Pass MDL", "command": "mdl ."} in output["shell"]
    assert ["description", "Complete All TODOs", "check", "MatchFileFragment"] in output["gatorgrader"]













    # look for matchfilefragment and match file regex

    # test for format 

     # a test to see if setup shell commands are needed, run a yml file without shell commands and see if the program can handle that

     # test for shell checks 

     # do a test that makes sure shell checks are in the list with the shell key and vice versa
     # have an input file that has one gator grade check and one shell check
     # run the parse config function
     # do a dictionary call to check whether the output[shell] has the value of the lists of shell checks 
    

     
    # the parse config function will call jacobs functionality and then use the output of that to call tugi's function and will return the output of tugi's function 
    
    # jacobs function as output is tugi's functions input

    # parse config should take as an argument the name of the gator grade file

    # WHEN THIS IS IN A PR include a note that it wont be merged until parse_config is written