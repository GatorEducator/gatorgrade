"""This module is used for storing the main functions requested.

The requested functions are located at the Github Issue Tracker
for the output team. For instance, functions dealing with percentage
output, description output, and colorization of text.
"""
import colorama as color

color.init()


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
    for i in passed_checks:
        requirement = i[0]
        # Use colorama to style passing check
        print(f"{color.Fore.GREEN}\u2714  {color.Style.RESET_ALL}{requirement}")


def output_failed_checks(failed_checks):
    """Output the results for all of the checks that did not pass using the failed_checks list."""
    for i in failed_checks:
        # Extract the details of each check
        requirement = i[0]
        description = i[2]
        # Use colorama to print and style "X"
        print(f"{color.Fore.RED}\u2718  {color.Style.RESET_ALL}{requirement}")
        print(f"    {color.Fore.YELLOW}\u2192  {description}")
        return bool


# Display a sample output of how the function could display a result object from GatorGrader
sample_result = [
    ("No TODOS in text", True, ""),
    ("Has an if statement", False, "No if statements found"),
]
sort_checks_by_result(sample_result)
