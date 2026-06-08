"""Returns the list of commands to be run through gatorgrader."""

from pathlib import Path
from typing import Any, List, Tuple

import yaml

from gatorgrade.input.command_line_generator import generate_checks
from gatorgrade.input.in_file_path import parse_yaml_file, reformat_yaml_data


def parse_config(file: Path) -> Tuple[List[Any], str | None]:
    """Parse the input YAML file and generate specified checks.

    Args:
        file: YAML file containing gatorgrade and shell command checks
    Returns:
        Returns a tuple of (checks, error_message). When successful,
        checks contains the list of checks and error_message is None.
        On failure, checks is empty and error_message contains details.

    """
    try:
        # parse the YAML file using parse_yaml_file provided by gatorgrade
        parsed_yaml_file = parse_yaml_file(file)
        # the parsed YAML file contains some contents in a list and thus
        # the tool should generate a GatorGrader check for each element in list
        if len(parsed_yaml_file) > 0:
            # after reformatting the parse YAML file,
            # use it to generate all of the checks;
            # these will be valid checks that are now
            # ready for execution with this tool
            parse_con = generate_checks(reformat_yaml_data(parsed_yaml_file))
            return parse_con, None
        # return an empty list because of the fact that the
        # parsing process did not return a list with content;
        # allow the calling function to handle the empty list
        return [], None
    except yaml.YAMLError as error:
        return [], str(error)
