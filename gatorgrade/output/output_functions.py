"""
This module is used for storing the main functions requested.

The requested functions are located at the Github Issue Tracker
for the output team. For instance, functions dealing with percentage
output, description output, and colorization of text.
"""

import gator
from gator import exceptions



def run_commands_and_return_results(commands_input):
    """
    Receive commands and send results to other output methods.

    Commands are received as dictionary of two keys, shell commands / gator
    commands.

    An Example of input for this function is as follows :

    {'shell': [{'description': 'Run program', 'command': 'mdl'}],
    'gatorgrader': [['--description', 'do command', 'commandType',
    '--arg', '1', '--directory', './home', '--file', 'file.py']]}
    """
    # Get first element in list, which is gatorgrader commands
    gatorcommands = commands_input.get("gatorgrader")
    results = []

    for command in gatorcommands:
        # If command is formatted incorrectly in yaml files,
        # catch the exception that would be returned and print
        try:
            result = gator.grader(command)
        except Exception as e:
            bad_command = "Whoops!", e.__class__
            result = (command, False, bad_command)
        results.append(result)
    # Send results to output methods, to be uncommented when
    # functions are merged
    # print_percentage(results)
    # print_description(results)
    return results

