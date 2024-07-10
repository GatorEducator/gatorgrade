"""Returns the list of commands to be run through gatorgrader."""

from pathlib import Path
import typer
from gatorgrade.input.command_line_generator import generate_checks
from gatorgrade.input.in_file_path import parse_yaml_file
from gatorgrade.input.in_file_path import reformat_yaml_data


def parse_config(file: Path, specified_checks: list = None):
    """Parse the input yaml file and generate specified checks.

    Args:
        file: Yaml file containing gatorgrade and shell command checks
        specified_checks: List of specific checks to run
    Returns:
        Returns a dictionary that specifies shell commands and gatorgrade commands
    """
    # parse the YAML file using parse_yaml_file provided by gatorgrade
    parsed_yaml_file = parse_yaml_file(file)

    # the parsed YAML file contains some contents in a list and thus
    # the tool should generate a GatorGrader check for each element in list
    if len(parsed_yaml_file) > 0:
        # after reformatting the parse YAML file,
        # use it to generate all of the checks;
        # these will be valid checks that are now
        # ready for execution with this tool
        reformatted_yaml_data = reformat_yaml_data(parsed_yaml_file)
        # Filter the reformat_yaml_data to only include specified checks
            # Check if specified_checks is provided and not empty
        if specified_checks:
            try:
                specified_checks_list = [int(check.strip()) for check in specified_checks.split(',')]
            except ValueError:
                raise typer.BadParameter("Checks must be a comma-separated list of integers.")
            # Adjust for 1-based indices by subtracting 1 from each
            specified_checks_list = [i - 1 for i in specified_checks_list]
            # Validate if any specified check is out of range
            if any(i >= len(reformatted_yaml_data) or i < 0 for i in specified_checks_list):
                raise ValueError("One or more specified checks are out of range.")
            reformatted_yaml_data = [reformatted_yaml_data[i] for i in specified_checks_list if i < len(reformatted_yaml_data)]
        parse_con = generate_checks(reformatted_yaml_data)
        return parse_con
    # return an empty list because of the fact that the
    # parsing process did not return a list with content;
    # allow the calling function to handle the empty list
    return []
