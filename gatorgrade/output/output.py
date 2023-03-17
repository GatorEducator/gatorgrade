"""Run checks and display whether each has passed or failed."""

import json
import subprocess
from pathlib import Path
from typing import List
from typing import Union

import gator
import rich

from gatorgrade.input.checks import GatorGraderCheck
from gatorgrade.input.checks import ShellCheck
from gatorgrade.output.check_result import CheckResult

# Disable rich's default highlight to stop number coloring
rich.reconfigure(highlight=False)


def _run_shell_check(check: ShellCheck) -> CheckResult:
    """Run a shell check.

    Args:
        check: The shell check to run.

    Returns:
        The result of running the shell check as a CheckResult.
    """
    result = subprocess.run(
        check.command,
        shell=True,
        check=False,
        timeout=300,
        stdout=subprocess.PIPE,
        # Redirect STDERR to STDOUT so STDOUT and STDERR can be captured
        # together as diagnostic
        stderr=subprocess.STDOUT,
    )
    passed = result.returncode == 0
    diagnostic = (
        "" if passed else result.stdout.decode().strip().replace("\n", "\n     ")
    )  # Add spaces after each newline to indent all lines of diagnostic
    return CheckResult(
        passed=passed, description=check.description, diagnostic=diagnostic
    )


def _run_gg_check(check: GatorGraderCheck) -> CheckResult:
    """Run a GatorGrader check.

    Args:
        check: The GatorGrader check to run.

    Returns:
        The result of running the GatorGrader check as a CheckResult.
    """
    try:
        result = gator.grader(check.gg_args)
        passed = result[1]
        description = result[0]
        diagnostic = result[2]
    # If arguments are formatted incorrectly, catch the exception and
    # return it as the diagnostic message
    # Disable pylint to catch any type of exception thrown by GatorGrader
    except Exception as command_exception:  # pylint: disable=W0703
        passed = False
        description = f'Invalid GatorGrader check: "{" ".join(check.gg_args)}"'
        diagnostic = f'"{command_exception.__class__}" thrown by GatorGrader'
    return CheckResult(passed=passed, description=description, diagnostic=diagnostic)


def create_report_json(
    passed_count,
    check_information,
    checkResults: List[CheckResult],
    percent_passed,
    reportFile: Path,
):
    """Take checks and put them into json format in the provided reportFile Path.

    Args:
        passed_count: the number of checks that passed
        check_information: the basic information about checks and their params
        checkResults: the list of check results that will be put in json
        percent_passed: the percentage of checks that passed
        reportFile: the location where the json will be put
    """
    # create list to hold the key values for the dictionary that
    # will be converted into json
    overall_key_list = ["amount correct", "percentage score", "checks"]

    checks_dict = {}
    overall_dict = {}

    # for each check:
    for i in range(len(check_information)):
        # grab all of the information out of it, as well as check result status and description
        checks_dict.update(
            {
                i: {
                    "description": checkResults[i].description,
                    "status": checkResults[i].passed,
                }
            }
        )
        # add the remaining information from check_information
        # if there are gg_args, add all of them
        try:
            for arg in check_information[i].gg_args:
                arg_index = check_information[i].gg_args.index(arg)
                if arg == "--fragment":
                    checks_dict[i].update(
                        {"Fragment": check_information[i].gg_args[arg_index + 1]}
                    )
                if arg == "tag":
                    checks_dict[i].update(
                        {"Tag": check_information[i].gg_args[arg_index + 1]}
                    )
                if arg == "--count":
                    checks_dict[i].update(
                        {"Count": check_information[i].gg_args[arg_index + 1]}
                    )
                if arg == "--directory":
                    checks_dict[i].update(
                        {"Directory": check_information[i].gg_args[arg_index + 1]}
                    )
                if arg == "--file":
                    checks_dict[i].update(
                        {"File": check_information[i].gg_args[arg_index + 1]}
                    )
        # if not, is a shell check, include
        except:
            checks_dict[i].update({"Command": check_information[i].command})

    # create the dictionary for all of the check information
    overall_dict = dict(
        zip(overall_key_list, [passed_count, percent_passed, checks_dict])
    )

    # use json.dump in order to turn the check results into json
    # create the file that was requested from cli input and
    # put the json into it
    with open(reportFile, "w") as fp:
        json.dump(overall_dict, fp)


def create_markdown_report_file(json_file: Path):
    """Create a markdown file using the created json to use in github actions summary, among other places.

    Args:
        json_file: the path at which the json is stored.
    """
    markdown_file = "insights.md"

    # create the markdown file if it doesn't already exist
    file = open(markdown_file, "w")
    file.write("# Gatorgrade Insights")
    file.close()

    # load the json from the json file
    file = open(json_file)
    json_str = file.read()
    json_object = json.loads(json_str)
    file.close()

    # write the amt correct and percentage score to md file
    file = open(markdown_file, "a")
    file.write(f"\n\n**Amount Correct:** {(json_object.get('amount correct'))}\n")
    file.write(f"**Percentage Correct:** {(json_object.get('percentage score'))}\n")

    passing_checks = []
    failing_checks = []
    # split checks into passing and not passing
    for check in json_object.get("checks"):
        # if the check is passing
        if json_object.get("checks").get(check).get("status") == True:
            passing_checks.append(json_object.get("checks").get(check))
        # if the check is failing
        else:
            failing_checks.append(json_object.get("checks").get(check))

    # give short info about passing checks as students have already
    # satisfied that requirement
    file.write("\n## Passing Checks\n")
    for check in passing_checks:
        file.write(f"\n### ✓ {check.get('description')}\n")

    # give extended information about failing checks to help
    # students solve them without looking in the gg yml file
    file.write("\n## Failing Checks\n")
    # for each failing check, print out all related information
    for check in failing_checks:
        # for each key val pair in the check dictionary
        for i in check:
            if i == "description":
                file.write(f"\n### ✕ {check.get('description')}\n")
            elif i != "status":
                file.write(f"\n**{i}** {check[i]}\n")


def run_checks(
    checks: List[Union[ShellCheck, GatorGraderCheck]], reportFile: Path
) -> bool:
    """Run shell and GatorGrader checks and display whether each has passed or failed.

        Also, print a list of all failed checks with their diagnostics and a summary message that
        shows the overall fraction of passed checks.

    Args:
        checks: The list of shell and GatorGrader checks to run.
    """
    results = []
    # run each of the checks
    for check in checks:
        result = None
        # run a shell check; this means
        # that it is going to run a command
        # in the shell as a part of a check
        if isinstance(check, ShellCheck):
            result = _run_shell_check(check)
        # run a check that GatorGrader implements
        elif isinstance(check, GatorGraderCheck):
            result = _run_gg_check(check)
        # there were results from running checks
        # and thus they must be displayed
        if result is not None:
            result.print()
            results.append(result)

    # determine if there are failures and then display them
    failed_results = list(filter(lambda result: not result.passed, results))
    # only print failures list if there are failures to print
    if len(failed_results) > 0:
        print("\n-~-  FAILURES  -~-\n")
        for result in failed_results:
            result.print(show_diagnostic=True)
    # determine how many of the checks passed and then
    # compute the total percentage of checks passed
    passed_count = len(results) - len(failed_results)
    # prevent division by zero if no results
    if len(results) == 0:
        percent = 0
    else:
        percent = round(passed_count / len(results) * 100)

    # run the json creation function
    create_report_json(passed_count, checks, results, percent, reportFile)
    create_markdown_report_file(reportFile)

    # compute summary results and display them in the console
    summary = f"Passed {passed_count}/{len(results)} ({percent}%) of checks for {Path.cwd().name}!"
    summary_color = "green" if passed_count == len(results) else "bright white"
    print_with_border(summary, summary_color)
    # determine whether or not the run was a success or not:
    # if all of the tests pass then the function returns True;
    # otherwise the function must return False
    summary_status = True if passed_count == len(results) else False
    return summary_status


def print_with_border(text: str, rich_color: str):
    """Print text with a border.

    Args:
        text: Text to print
        rich_color: Color of text to print
    """
    upleft = "\u250f"
    # Upper left corner
    upright = "\u2513"
    # Upper right corner
    downleft = "\u2517"
    # Lower left corner
    downright = "\u251B"
    # Lower right corner
    vert = "\u2503"
    # Vertical line
    horz = "\u2501"
    # Horizontal line

    line = horz * (len(text) + 2)
    rich.print(f"[{rich_color}]\n\t{upleft}{line}{upright}")
    rich.print(f"[{rich_color}]\t{vert} {text} {vert}")
    rich.print(f"[{rich_color}]\t{downleft}{line}{downright}\n")
