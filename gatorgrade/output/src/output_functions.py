"""
This class is used for storing the main functions requested from the Github.

Issue Tracker for the output team.
For instance, functions dealing with percentage output, description output,
and colorization of text.
"""
from colorama import init, Fore, Style
from gatorgrade.output.output_functions import run_commands_and_return_results
from gatorgrade.output.output_percentage_printing import print_percentage

init()


def sort_checks_by_result(results):
    """
    Process results and determine if the check passed or failed.

    Argument `results` is: list[(check_result_element1, check_result_element2),(...)]]
    """
    passed_checks = []
    failed_checks = []
    # iterate through results tuples
    for i in results:
        for j in i:
            if isinstance(j, bool):
                if j is True:
                    passed_checks.append(i)
                else:
                    failed_checks.append(i)
    output_passed_checks(passed_checks)
    output_failed_checks(failed_checks)


def output_passed_checks(passed_checks):
    """Output the results for all of the checks that passed using the passed_checks list."""
    for i in passed_checks:
        requirement = i[0]
        # Use colorama to style passing check
        print(f"{Fore.GREEN}\u2714  {Style.RESET_ALL}{requirement}")


def output_failed_checks(failed_checks):
    """Output the results for all of the checks that did not pass using the failed_checks list."""
    for i in failed_checks:
        # Extract the details of each check
        requirement = i[0]
        description = i[2]
        # Use colorama to print and style "X"
        print(f"{Fore.RED}\u2718  {Style.RESET_ALL}{requirement}")
        print(f"    {Fore.YELLOW}\u2192  {description}")


def run_and_display_command_checks(commands) :
    """The final function which runs commands through gatorgrader and displays them to the user"""
    results = run_commands_and_return_results(commands)
    sort_checks_by_result(results)
    print_percentage(results)


# Display a sample output of how the function could display a result object from GatorGrader
sample_result = [
    ("Has an if statement", False, "No if statements found")
]
# sort_checks_by_result(sample_result)

sample_commands = {'shell': [{'description': 'Pass HTMLHint', 'command': 'htmlhint'}], 'gatorgrader': [['--description', 'Complete all TODOs', 'MatchFileFragment', '--fragment', 'TODO', '--count', '0', '--exact', '--directory', './home/dir/subdir', '--file', 'yayaya.py'], ['--description', 'Use an if statement', 'MatchFileRegex', '--regex', 'if .?:', '--count', '1', '--directory', './home/dir/subdir', '--file', 'yayaya.py'], ['--description', 'Complete all TODOs', 'MatchFileFragment', '--fragment', 'TODO', '--count', '0', '--exact', '--directory', './home/dir/subdir', '--file', 'module.py'], ['--description', 'Use an if statement', 'MatchFileRegex', '--regex', 'if .?:', '--count', '1', '--directory', './home/dir/subdir', '--file', 'module.py'], ['--description', 'Have a total of 8 commits, 5 of which were created by you', 'CountCommitts', '--fragment', 'TODO', '--count', '0', '--exact']]}

run_and_display_command_checks(sample_commands)