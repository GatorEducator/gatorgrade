"""This module is used for storing the main functions requested from the Github Issue Tracker for the output team.
For instance, functions dealing with percentage output, description output, and colorization of text."""

import gator
import os
import output_tools
from typing import List, Tuple

# Commands are received as dictionary of two keys, shell commands / gator commands
# In the dictionary
def receive_command(commands_input):
    """Main command function to pass commands and send results to other methods."""

    # Get first element in list, which is gatorgrader commands
    gatorcommands = commands_input.get('gatorgrade')
    results = []

    for command in gatorcommands:
        # If command is formatted incorrectly in yaml files, catch the exception that would be returned and print
        try:
            result = gator.grader(command)
            results.append(result)
        except Exception as e:
            print(
                "\033[91m \033[1m \033[4m An exception was detected when running the command : \033[0m \n\n \033[91m",
                " ".join(command),
                "\033[0m",
            )
            print("Exception is as follows: \n ", e)
    # Send results to output methods
    # print_percentage(results)
    # print_description(results)
    return results
