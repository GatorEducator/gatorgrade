"""Run checks and display whether each has passed or failed."""
import json
import os
import subprocess
from pathlib import Path
from typing import List
from typing import Tuple
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

    # Add spaces after each newline to indent all lines of diagnostic
    diagnostic = (
        "" if passed else result.stdout.decode().strip().replace("\n", "\n     ")
    )
    return CheckResult(
        passed=passed,
        description=check.description,
        json_info=check.json_info,
        diagnostic=diagnostic,
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
    return CheckResult(
        passed=passed,
        description=description,
        json_info=check.json_info,
        diagnostic=diagnostic,
    )


def create_report_json(
    passed_count,
    checkResults: List[CheckResult],
    percent_passed,
) -> dict:
    """Take checks and put them into json format in a dictionary.

    Args:
        passed_count: the number of checks that passed
        check_information: the basic information about checks and their params
        checkResults: the list of check results that will be put in json
        percent_passed: the percentage of checks that passed
    """
    # create list to hold the key values for the dictionary that
    # will be converted into json
    overall_key_list = ["amount_correct", "percentage_score", "checks"]

    checks_list = []
    overall_dict = {}

    # for each check:
    for i in range(len(checkResults)):
        # grab all of the information in it and add it to the checks list
        results_json = checkResults[i].json_info
        results_json["status"] = checkResults[i].passed
        if not checkResults[i].passed:
            results_json["diagnostic"] = checkResults[i].diagnostic
        checks_list.append(results_json)

    # create the dictionary for all of the check information
    overall_dict = dict(
        zip(overall_key_list, [passed_count, percent_passed, checks_list])
    )
    return overall_dict


def create_markdown_report_file(json: dict) -> str:
    """Create a markdown file using the created json to use in github actions summary, among other places.

    Args:
        json: a dictionary containing the json that should be converted to markdown
    """
    markdown_contents = ""
    passing_checks = []
    failing_checks = []

    num_checks = len(json.get("checks"))

    # write the total, amt correct and percentage score to md file
    markdown_contents += f"# Gatorgrade Insights\n\n**Project Name:** {Path.cwd().name}\n**Amount Correct:** {(json.get('amount_correct'))}/{num_checks} ({(json.get('percentage_score'))}%)\n"

    # split checks into passing and not passing
    for check in json.get("checks"):
        # if the check is passing
        if check["status"] == True:
            passing_checks.append(check)
        # if the check is failing
        else:
            failing_checks.append(check)

    # give short info about passing checks
    markdown_contents += "\n## Passing Checks\n"
    for check in passing_checks:
        if "description" in check:
            markdown_contents += f"\n- [x] {check['description']}"
        else:
            markdown_contents += f"\n- [x] {check['check']}"

    # give extended information about failing checks
    markdown_contents += "\n\n## Failing Checks\n"
    # for each failing check, print out all related information
    for check in failing_checks:
        # for each key val pair in the check dictionary
        if "description" in check:
            markdown_contents += f"\n- [ ] {check['description']}"
        else:
            markdown_contents += f"\n- [ ] {check['check']}"

        if "options" in check:
            for i in check.get("options"):
                if "command" == i:
                    val = check["options"]["command"]
                    markdown_contents += f"\n\t- **command** {val}"
                if "fragment" == i:
                    val = check["options"]["fragment"]
                    markdown_contents += f"\n\t- **fragment:** {val}"
                if "tag" == i:
                    val = check["options"]["tag"]
                    markdown_contents += f"\n\t- **tag:** {val}"
                if "count" == i:
                    val = check["options"]["count"]
                    markdown_contents += f"\n\t- **count:** {val}"
                if "directory" == i:
                    val = check["options"]["directory"]
                    markdown_contents += f"\n\t- **directory:** {val}"
                if "file" == i:
                    val = check["options"]["file"]
                    markdown_contents += f"\n\t- **file:** {val}"
        elif "command" in check:
            val = check["command"]
            markdown_contents += f"\n\t- **command:** {val}"
        if "diagnostic" in check:
            markdown_contents += f"\n\t- **diagnostic:** {check['diagnostic']}"
        markdown_contents += "\n"

    return markdown_contents


def configure_report(report_params: Tuple[str, str, str], report_output_data: dict):
    """Put together the contents of the report depending on the inputs of the user.

    Args:
        report_params: The details of what the user wants the report to look like
            report_params[0]: file or env
            report_params[1]: json or md
            report_params[2]: name of the file or env
        report_output_data: the json dictionary that will be used or converted to md
    """
    # if the user wants markdown, convert the json into md
    if report_params[1] == "md":
        report_output_data = create_markdown_report_file(report_output_data)

    # if the user wants the data stored in a file:
    if report_params[0] == "file":
        # try to store it in that file
        try:
            # Second argument has to be json or md
            if report_params[1] != "json" and report_params[1] != "md":
                rich.print(
                    "\n[red]The second argument of report has to be 'md' or 'json' "
                )
            else:
                with open(report_params[2], "w", encoding="utf-8") as file:
                    if report_params[1] == "json":
                        file.write(json.dumps(report_output_data))
                    else:
                        file.write(str(report_output_data))
        except:
            rich.print(
                "\n[red]Can't open or write the target file, check if you provide a valid path"
            )
    elif report_params[0] == "env":
        if report_params[2] == "GITHUB_STEP_SUMMARY":
            env_file = os.getenv("GITHUB_STEP_SUMMARY")
            with open(env_file, "a") as env_file:
                env_file.write(str(report_output_data))
        else:
            os.environ[report_params[2]] = str(report_output_data)
    else:
        rich.print("\n[red]The first argument of report has to be 'env' or 'file' ")


def run_checks(
    checks: List[Union[ShellCheck, GatorGraderCheck]], report: Tuple[str, str, str]
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

    # if the report is wanted, create output in line with their specifications
    if all(report):
        report_output_data = create_report_json(passed_count, results, percent)
        configure_report(report, report_output_data)

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
