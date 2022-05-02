"""Test suite for parse_config function for Liam"""


from gatorgrade.input.in_file_path import parse_config

def test_parse_config_setup_shell_checks():
    """Run a yml file without shell setup commands to see if the program allows a yml file without those commands."""
    # given the path to the test yml file
    config = "tests/input/yml_test_files/gatorgrade_no_shell_setup_check.yml"
    # when the parse_config function is run
    output = parse_config(config)
    # then run a yml file without shell commands and see if the program can handle that
    assert ["setup", "./script.sh", "poetry install", "echo 'Setup Complete!'"] not in output["shell"]



def test_parse_config_has_same_format():
    """Test the outputted format of parse_config to make sure it is returning a list inside a dictionary."""
    # given the path to two test yml files, one being correctly formated, the other being incorrect
    config_one = "tests/input/yml_test_files/gatorgrade_two_in_file_context_checks.yml"
    config_two = "tests/input/yml_test_files/gatorgrade_two_in_file_context_checks_incorrect_format.yml"
    # when parse_config is run twice
    output_one = parse_config(config_one)
    output_two = parse_config(config_two)
    # then assert that the format is incorrect or something like that





   



    

     

     # test for shell checks 

     # do a test that makes sure shell checks are in the list with the shell key and vice versa
     # have an input file that has one gator grade check and one shell check
     # run the parse config function
     # do a dictionary call to check whether the output[shell] has the value of the lists of shell checks 
    

     
    # the parse config function will call jacobs functionality and then use the output of that to call tugi's function and will return the output of tugi's function 
    
    # jacobs function as output is tugi's functions input

    # parse config should take as an argument the name of the gator grade file

    # WHEN THIS IS IN A PR include a note that it wont be merged until parse_config is written