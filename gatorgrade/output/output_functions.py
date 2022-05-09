"""This module is used for storing the main functions requested.

The requested functions are located at the Github Issue Tracker
for the output team. For instance, functions dealing with percentage
output, description output, and colorization of text.
"""

import colorama as color
import gator


color.init()


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
        List[tuple(str, bool, str)]

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
        # catch the exception that would be retursned and print
        try:
            result = gator.grader(command)
        # disable pylint so the more general Exception class can be used
        except Exception as command_exception:  # pylint: disable=W0703
            bad_command = command_exception.__class__
            result = (command, False, bad_command)
        results.append(result)

    return results


def sort_checks_by_result(results):
    """
    Process results and determine if the check passed or failed.

    Args:
        results: list[(description, passed, diagnostic),(...)]
    """
    passed_checks = []
    failed_checks = []
    # Iterate through results tuples
    for result in results:
        # Add passing checks to the passed check list and failing checks to
        # the failed check list
        if result[1] is True:
            passed_checks.append(result)
        else:
            failed_checks.append(result)
    output_passed_checks(passed_checks)
    output_failed_checks(failed_checks)


def output_passed_checks(passed_checks):
    """Output the results for all of the checks that passed using the passed_checks list."""
    for check in passed_checks:
        requirement = check[0]
        # Use colorama to style passing check
        print(f"{color.Fore.GREEN}\u2714  {color.Style.RESET_ALL}{requirement}")


def output_failed_checks(failed_checks):
    """Output the results for all of the checks that did not pass using the failed_checks list."""
    for check in failed_checks:
        # Extract the details of each check
        requirement = check[0]
        description = check[2]
        # Use colorama to print and style "X"
        print(f"{color.Fore.RED}\u2718  {color.Style.RESET_ALL}{requirement}")
        print(f"    {color.Fore.YELLOW}\u2192  {description}")
        return bool
