"""Generates a list of commands to be run through gatorgrader."""

import random
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


def add_quotes_to_yaml(file_path: Path, new_quotes: List[str]):
    """Add motivational quotes to the YAML file under the key 'motivational_quotes'."""
    if not file_path.exists():
        print(f"Error: File not found at {file_path}")
        return
    
    try:
        with open(file_path, encoding=DEFAULT_ENCODING) as file:
            data = yaml.safe_load(file) or {}  # Load existing data or start fresh
        
        # Ensure 'motivational_quotes' exists in the YAML structure
        if "motivational_quotes" not in data:
            data["motivational_quotes"] = []

        # Append new quotes, avoiding duplicates
        existing_quotes = set(data["motivational_quotes"])
        for quote in new_quotes:
            if quote not in existing_quotes:
                data["motivational_quotes"].append(quote)
        
        # Write the updated data back to the file
        with open(file_path, 'w', encoding=DEFAULT_ENCODING) as file:
            yaml.safe_dump(data, file)
        
        print("Motivational quotes added successfully!")
    
    except yaml.YAMLError as e:
        print(f"Error processing YAML file: {e}")


def get_random_quote(file_path: Path) -> str:
    """Retrieve a random motivational quote from the YAML file."""
    if not file_path.exists():
        return "No motivational quotes available. Add some to the YAML file!"

    try:
        with open(file_path, encoding=DEFAULT_ENCODING) as file:
            data = yaml.safe_load(file)
            quotes = data.get("motivational", [])
            return random.choice(quotes) if quotes else "No motivational quotes available."
    except Exception as e:
        return f"Error retrieving quotes: {e}"