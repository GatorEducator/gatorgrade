"""Generates a list of commands to be run through gatorgrader."""
from collections import namedtuple
from typing import List
import yaml
from gatorgrade.input.set_up_shell import run_setup

# Represent data for a check from the configuration file.
# Every check will have data (`check`) and some may also have a `file_context`,
# which is a file path associated with the check to be used when running the check.
CheckData = namedtuple("CheckData", ["file_context", "check"])


def parse_yaml_file(file_path):
    """Parse a YAML file and return its contents as a list of dictionaries."""
    with open(file_path, encoding="utf8") as file:
        data = yaml.load_all(file, Loader=yaml.FullLoader)
        return list(data)


def reformat_yaml_data(data):
    """Reformat the raw data from a YAML file into a list of tuples."""
    reformatted_data = []
    if len(data) == 2:
        setup_commands = data.pop(0)  # Removes the setup commands
        run_setup(setup_commands)
    add_checks_to_list(None, data[0], reformatted_data)
    return reformatted_data


def add_checks_to_list(path, data_list, reformatted_data) -> List[CheckData]:
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
