"""Returns the list of commands to be run through gatorgrader."""

from pathlib import Path
from thefuzz import fuzz


from gatorgrade.input.command_line_generator import generate_checks
from gatorgrade.input.in_file_path import parse_yaml_file
from gatorgrade.input.in_file_path import reformat_yaml_data


def parse_config(file: Path, check_include: str = None, check_exclude: str = None):
    """Parse the input yaml file and generate specified checks.

    Args:
        file: Yaml file containing gatorgrade and shell command checks
        check_include: Description of checks to include
        check_exclude: Description of checks to exclude
    Returns:
        Returns a tuple that contains:
        - A dictionary specifying shell commands and gatorgrade commands
        - A boolean variable indicating if there is a match for the specified checks
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
        match = True
        # Filter the reformat_yaml_data to only include specified checks
        if check_include:
            # Generate the checks that are included
            check_list = [check for check in reformatted_yaml_data if fuzz.partial_ratio(check_include, check[1]['description']) >= 80]
            match = True if len(check_list) > 0 else False       
            parse_con = generate_checks(check_list)
            return (parse_con, match)       

        if check_exclude:
            # Generate the checks that are excluded
            check_list = [check for check in reformatted_yaml_data if fuzz.partial_ratio(check_exclude, check[1]['description']) < 80]
            match = True if len(check_list) > 0 else False
            parse_con = generate_checks(check_list)
            return (parse_con, match)

        parse_con = generate_checks(reformatted_yaml_data)
        return (parse_con, match)
    # return an empty list because of the fact that the
    # parsing process did not return a list with content;
    # allow the calling function to handle the empty list
    return []
