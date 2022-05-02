    # look for matchfilefragment and match file regex

def test_parse_config_check_gg_matchfilefragment():
    """Test to make sure keywords like MatchFileFragment and MatchFileRegex appear inside the gator grader check list."""
    # Given the path to the test yml file
    config = "test/input/yml_test_files/gatorgrade.yml" # Make fixture that will create yml file to be parsed instead of expected file
    # When the parse_config is run
    output = parse_config(config)
    # Then assert that match file fragment and match file regex exists
    assert "MatchFileFragment" in output["gatorgrader"][0]
    assert set([["--desription", "Complete all TODOs", ], [], []]) == set(output["gatorgrader"])  # Assert that output["gatorgrader"] is equal to expected output

def test_parse_config_check_shell_contains_command():
    """Test to make sure that the shell commands are found inside the 'shell' list."""
    # Given the path to the test yml file
    config = "test/input/yml_test_files/gatorgrade.yml"
    # When the parse_config is run
    output = parse_config(config)
    # Then assert that command is present in the shell
    assert "command" in output["shell"]

     # do a test that makes sure shell checks are in the list with the shell key and vice versa
     # have an input file that has one gator grade check and one shell check
     # run the parse config function
     # do a dictionary call to check whether the output[shell] has the value of the lists of shell checks 
    

     
    # the parse config function will call jacobs functionality and then use the output of that to call tugi's function and will return the output of tugi's function 
    
    # jacobs function as output is tugi's functions input

    # parse config should take as an argument the name of the gator grade file

    # WHEN THIS IS IN A PR include a note that it wont be merged until parse_config is written