"""This module is used for storing the main functions requested.

Issue Tracker for the output team.
For instance, functions dealing with percentage output, description output,
and colorization of text.
"""

import gator
import colorama as color
from gatorgrade.output import output_percentage_printing

color.init()


def run_commands_and_return_results(commands_input):
    """Receive commands and send results to other output methods.

    Args:
        commands_input (dict{str: List[dict{str:str, ...}],
        str: List[List[str]]}): The first parameter which
        contains commands.

    Returns:
        List[tuple[str, bool, str]]

    Commands are received as dictionary of two keys, shell commands / gator
    commands.

    An Example of arg input for this function is as follows :

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
        except Exception as command_exception:  # pylint: disable=W0703
            bad_command = command_exception.__class__
            result = (command, False, bad_command)
            print(
                "Whoops! ",
                command,
                "didn't work for some reason.",
                "Check out the diagnostic to find the type of error.",
            )
        results.append(result)

    return results


def sort_checks_by_result(results):
    """
    Process results and determine if the check passed or failed.

    Args:
        results: list[(check_result_element1, check_result_element2),(...)]]
    """
    passed_checks = []
    failed_checks = []
    # Iterate through results tuples
    for result in results:
        # Grab the boolean from the check tuple
        check_result = result[1]
        # Add passing checks to the passed check list and failing checks to
        # the failed check list
        if check_result is True:
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


def run_and_display_command_checks(commands):
    """Run commands through gatorgrader and display them to the user."""
    results = run_commands_and_return_results(commands)
    sort_checks_by_result(results)
    output_percentage_printing.print_percentage(results)


# Display a sample output of how the function could display a result object from GatorGrader
sample_result = [
    ("No TODOS in text", True, ""),
    ("Has an if statement", False, "No if statements found"),
]
sort_checks_by_result(sample_result)
