"""This file is used for storing supporting functions and tools that are used by the methods in output_functions.
The main use of this class is to de-clutter output_functions.py for better readability.
One example of a function to be written here is the splitting of strings retrieved from the input team, at spaces, into lists."""

from typing import List


def get_simple_command_string(command: List[str]) -> str:
    """This function takes a list of strings and combines them to one single string."""

    command_string = " ".join(command)
    return command_string
