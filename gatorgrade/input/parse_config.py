"""Returns the list of commands to be run through gatorgrader."""

from pathlib import Path
from typing import Any, List, Tuple

import yaml

from gatorgrade.input.checks import validate_positive_nonzero_int
from gatorgrade.input.command_line_generator import generate_checks
from gatorgrade.input.in_file_path import (
    DATA_WITH_SETUP_LENGTH,
    parse_yaml_file,
    reformat_yaml_data,
)

NAME_FIELD = "name"
BASELINE_WEIGHT_FIELD = "baseline_weight"


def get_project_name(file: Path) -> str | None:
    """Extract the optional project name from a gatorgrade YAML config file.

    The project name is specified in the front matter of the YAML file as:

        name: "Theory of Computation Final Examination"
        setup: |
          ...
        ---
        - checks...

    Args:
        file: Path to the gatorgrade YAML configuration file.

    Returns:
        The project name string if specified, or None if not present.

    """
    try:
        parsed_yaml_file = parse_yaml_file(file)
        if len(parsed_yaml_file) >= DATA_WITH_SETUP_LENGTH and isinstance(
            parsed_yaml_file[0], dict
        ):
            return parsed_yaml_file[0].get(NAME_FIELD, None)
    except Exception:
        pass
    return None


def parse_config(
    file: Path, baseline_weight: int = 1
) -> Tuple[List[Any], str | None]:
    """Parse the input YAML file and generate specified checks.

    Args:
        file: YAML file containing gatorgrade and shell command checks
        baseline_weight: Default weight for checks that do not specify one
    Returns:
        Returns a tuple of (checks, error_message). When successful,
        checks contains the list of checks and error_message is None.
        On failure, checks is empty and error_message contains details.

    """
    # validate the baseline_weight so that it is a positive integer;
    # note that this is already checked by the validation of the
    # command-line arguments provided by the person using the program;
    # however, adding the check here in case this function is called
    # directly without going through the command-line argument validation
    error = validate_positive_nonzero_int(
        baseline_weight, BASELINE_WEIGHT_FIELD
    )
    if error:
        return [], error
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
            parse_con = generate_checks(
                reformat_yaml_data(parsed_yaml_file), baseline_weight
            )
            return parse_con, None
        # return an empty list because of the fact that the
        # parsing process did not return a list with content;
        # allow the calling function to handle the empty list
        return [], None
    except (yaml.YAMLError, ValueError, TypeError, IndexError) as error:
        return [], str(error)
