"""Test suite for parse_config function for Liam"""


from gatorgrade.input.in_file_path import parse_config

def test_parse_config_setup_shell_checks():
    """Run a yml file without shell setup commands to see if the program allows a yml file without those commands."""
    # given the path to the test yml file
    config = "tests/input/yml_test_files/gatorgrade_no_shell_setup_check.yml"
    # when the parse_config function is run
    output = parse_config(config)
    # then run a yml file without shell commands and see if the program can handle that
    assert output["gatorgrader"][0] == ["--description", "Have 8 commits", "CountCommits", "--count", "8"]





      # we want the test to be testing the user experience which is why we are using test files here.



   



    

     

     
    

     
    # the parse config function will call jacobs functionality and then use the output of that to call tugi's function and will return the output of tugi's function 
    
    # jacobs function as output is tugi's functions input

    # parse config should take as an argument the name of the gator grade file

    # WHEN THIS IS IN A PR include a note that it wont be merged until parse_config is written