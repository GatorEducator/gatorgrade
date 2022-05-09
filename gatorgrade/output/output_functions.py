"""This module is used for storing the main functions requested.

The requested functions are located at the Github Issue Tracker
for the output team. For instance, functions dealing with percentage
output, description output, and colorization of text.
"""

import gator


def run_commands_and_return_results(commands_input):
    """Run commands through GatorGrader and send results to other output methods.

    Args:

        Commands are received as dictionary of two keys, shell commands / gator
        commands.

        commands_input (dict{str: List[dict{str:str, ...}],
        str: List[List[str]]}): The first parameter which
        contains commands.

        An Example of arg input for this function is as follows :

        {'shell': [{'description': 'Run program', 'command': 'mdl'}],
        'gatorgrader': [['--description', 'do command', 'commandType',
        '--arg', '1', '--directory', './home', '--file', 'file.py']]}

    Returns:
        List[tuple[str, bool, str]]

        Each tuple in the list is the result of a specific command
        being run.

        The first string is the description which comes directly from the command.
        The boolean describes whether the command passed or failed the check.
        The final string will either a diagnostic for a failed check or a blank
        string for a passed check.




    """
    # Get first element in list, which is gatorgrader commands
    gatorcommands = commands_input.get("gatorgrader")
    results = []

    for command in gatorcommands:
        # If command is formatted incorrectly in yaml files,
        # catch the exception that would be returned and print
        try:
            result = gator.grader(command)
        except Exception as command_exception:  # pylint: disable=W0703
            bad_command = command_exception.__class__
            result = (command, False, bad_command)
        results.append(result)

    return results
