"""Returns the list of commands to be run through gatorgrader"""
from command_line_generator import generate_checks # Import function to generate shell and gatorgrader checks
from in_file_path import parse_yaml_file, reformat_yml_data, add_checks_to_list # Import functions to parse and set up yaml file 

def parse_config(file):
    """Parse the input yaml file and generate specified checks
    
    Args:
        file: Yaml file containing gatorgrade and shell command checks 
    """
    generate_checks(reformat_yaml_data(parse_yaml_file(file))) # Call previously generated function to modify file

    # Create Args section in docstring