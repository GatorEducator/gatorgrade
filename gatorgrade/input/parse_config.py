"""Returns the list of commands to be run through gatorgrader."""
from gatorgrade.input.command_line_generator import (
    generate_checks,
)  # Import function to generate shell and gatorgrader checks
from gatorgrade.input.in_file_path import (
    parse_yaml_file,
    reformat_yaml_data,
)  # Import functions to parse and set up yaml file


def parse_config(file):
    """Parse the input yaml file and generate specified checks.

    Args:
        file: Yaml file containing gatorgrade and shell command checks
    Returns:
        Returns a dictionary that specifies shell commands and gatorgrade commands
    """
    parse_con = generate_checks(
        reformat_yaml_data(parse_yaml_file(file))
    )  # Call previously generated function to modify file
    return parse_con
