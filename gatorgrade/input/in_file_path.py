"""Generates a list of commands to be run through gatorgrader."""

from collections import namedtuple
from pathlib import Path
from typing import Any
from typing import List

import yaml

from gatorgrade.input.set_up_shell import run_setup

# Represent data for a check from the configuration file.
# Every check will have data (`check`) and some may also have a `file_context`,
# which is a file path associated with the check to be used when running the check.
CheckData = namedtuple("CheckData", ["file_context", "check"])

# define the default encoding
DEFAULT_ENCODING = "utf8"


def parse_yaml_file(file_path: Path) -> List[Any]:
    """Parse a YAML file and return its contents as a list of dictionaries."""
    # confirm that the file exists before attempting to read from it
    if file_path.exists():
        # read the contents of the specified file using the default
        # encoding and then parse that file using the yaml package
        with open(file_path, encoding=DEFAULT_ENCODING) as file:
            # after parsing with the yaml module, return a list
            # of all of the contents specified in the file
            data = yaml.load_all(file, Loader=yaml.FullLoader)
            return list(data)
    # some aspect of the file does not exist
    # (i.e., wrong file or wrong directory)
    # and thus parsing with YAML is not possible;
    # return a blank list that calling function handles
    return []


def reformat_yaml_data(data):
    """Reformat the raw data from a YAML file into a list of tuples."""
    reformatted_data = []
    if len(data) == 2:
        setup_commands = data.pop(0)  # Removes the setup commands
        run_setup(setup_commands)
    add_checks_to_list(None, data[0], reformatted_data)
    return reformatted_data


def add_checks_to_list(path, data_list, reformatted_data):
    """Recursively loop through the data and add checks that are found to the reformatted list."""
    current_path = path  # Saves the current path to keep track of the location
    for ddict in data_list:
        for item in ddict:
            if isinstance(
                ddict[item], list
            ):  # Checks if the current dictionary has another list as its value
                if not path:
                    path = item
                else:
                    path = f"{path}/{item}"
                add_checks_to_list(
                    path, ddict[item], reformatted_data
                )  # Runs this same function on the list inside of a dictionary
                path = current_path
            else:  # Adds the current check to the reformatted data list
                reformatted_data.append(CheckData(file_context=path, check=ddict))
                break
