"""Run checks and display whether each has passed or failed."""

import datetime
import json
import os
import subprocess
from pathlib import Path
from typing import List
from typing import Tuple
from typing import Union

import gator
import rich
from rich.progress import BarColumn
from rich.progress import Progress
from rich.progress import TextColumn
from rich.panel import Panel

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
        # Fetch the path from gatorgrade arguments
        # the path pattern are 4 consistent string in the list
        # --dir `dir_name` --file `file_name`
        file_path = None
        for i in range(len(check.gg_args)):
            if check.gg_args[i] == "--directory":
                dir_name = check.gg_args[i + 1]
                file_name = check.gg_args[i + 3]
                file_path = dir_name + "/" + file_name
                break
    # If arguments are formatted incorrectly, catch the exception and
    # return it as the diagnostic message
    # Disable pylint to catch any type of exception thrown by GatorGrader
    except Exception as command_exception:  # pylint: disable=W0703
        passed = False
        description = f'Invalid GatorGrader check: "{" ".join(check.gg_args)}"'
        diagnostic = f'"{command_exception.__class__}" thrown by GatorGrader'
        file_path = None
    return CheckResult(
        passed=passed,
        description=description,
        json_info=check.json_info,
        diagnostic=diagnostic,
        path=file_path,
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
    overall_key_list = ["amount_correct", "percentage_score", "report_time", "checks"]
    checks_list = []
    overall_dict = {}
    report_generation_time = datetime.datetime.now()
    formatted_time = report_generation_time.strftime("%Y-%m-%d %H:%M:%S")
    # for each check:
    for i in range(len(checkResults)):
        # grab all of the information in it and add it to the checks list
        results_json = checkResults[i].json_info
        results_json["status"] = checkResults[i].passed
        if checkResults[i].path:
            results_json["path"] = checkResults[i].path
        if not checkResults[i].passed:
            results_json["diagnostic"] = checkResults[i].diagnostic
        checks_list.append(results_json)
    # create the dictionary for all of the check information
    overall_dict = dict(
        zip(
            overall_key_list,
            [passed_count, percent_passed, formatted_time, checks_list],
        )
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
    num_checks = len(json.get("checks"))  # type: ignore
    # write the total, amt correct and percentage score to md file
    markdown_contents += f"# Gatorgrade Insights\n\n**Project Name:** {Path.cwd().name}\n**Amount Correct:** {(json.get('amount_correct'))}/{num_checks} ({(json.get('percentage_score'))}%)\n"
    # split checks into passing and not passing
    for check in json.get("checks"):  # type: ignore
        # if the check is passing
        if check["status"]:
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


def configure_report(
    report_params: Tuple[str, str, str], report_output_data_json: dict
):
    """Put together the contents of the report depending on the inputs of the user.

    Args:
        report_params: The details of what the user wants the report to look like
            report_params[0]: file or env
            report_params[1]: json or md
            report_params[2]: name of the file or env
        report_output_data: the json dictionary that will be used or converted to md
    """
    report_format = report_params[0]
    report_type = report_params[1]
    report_name = report_params[2]
    if report_type not in ("json", "md"):
        raise ValueError(
            "\n[red]The second argument of report has to be 'md' or 'json' "
        )
    # if the user wants markdown, get markdown content based on json
    if report_type == "md":
        report_output_data_md = create_markdown_report_file(report_output_data_json)
    # if the user wants the data stored in a file
    if report_format == "file":
        if report_type == "md":
            write_json_or_md_file(report_name, report_type, report_output_data_md)  # type: ignore
        else:
            write_json_or_md_file(report_name, report_type, report_output_data_json)
    # the user wants the data stored in an environment variable; do not attempt
    # to save to the environment variable if it does not exist in the environment
    elif report_format == "env":
        if report_name == "GITHUB_STEP_SUMMARY":
            env_file = os.getenv("GITHUB_STEP_SUMMARY", None)
            if env_file is not None:
                if report_type == "md":
                    write_json_or_md_file(env_file, report_type, report_output_data_md)  # type: ignore
                else:
                    write_json_or_md_file(
                        env_file, report_type, report_output_data_json
                    )
        # Add json report into the GITHUB_ENV environment variable for data collection purpose;
        # note that this is an undocumented side-effect of running gatorgrade with command-line
        # arguments that save data to the GITHUB_STEP_SUMMARY environment variable. The current
        # implementation of this approach should not cause the setting to fail when GatorGrade
        # is run with the same command-line for which it is normally run in a GitHub Actions
        # convert the data to a JSON string so that it can potentially be saved
        json_string = json.dumps(report_output_data_json)
        # check to see if the GITHUB_ENV environment variable is set
        env_file = os.getenv("GITHUB_ENV", None)
        # the environment variable is defined and thus it is acceptable
        # to write a key-value pair to the GITHUB_ENV environment file
        # (note that the comment on the previous line is correct; this
        # environment variable is a pointer to a file that allows for
        # key-value pairs in one step to be passed to the next step
        # inside of GitHub Actions and it is done through a file)
        if env_file is not None:
            # if it is, append the JSON string to the GITHUB_ENV file;
            # note that this step is specifically helpful when running
            # GatorGrade inside of a GitHub Actions workflow because
            # this variable called GITHUB_ENV is used to store environment
            # variables that are available to all of the subsequent steps
            with open(os.environ["GITHUB_ENV"], "a") as env_file:  # type: ignore
                env_file.write(f"JSON_REPORT={json_string}\n")  # type: ignore
    else:
        raise ValueError(
            "\n[red]The first argument of report has to be 'env' or 'file' "
        )


def write_json_or_md_file(file_name, content_type, content):
    """Write a markdown or json file."""
    # try to store content in a file with user chosen format
    try:
        # Second argument has to be json or md
        with open(file_name, "w", encoding="utf-8") as file:
            if content_type == "json":
                json.dump(content, file, indent=4)
            else:
                file.write(str(content))
        return True
    except Exception as e:
        raise ValueError(
            "\n[red]Can't open or write the target file, check if you provide a valid path"
        ) from e


def run_checks(
    checks: List[Union[ShellCheck, GatorGraderCheck]],
    report: Tuple[str, str, str],
    running_mode=False,
    no_status_bar=False,
) -> bool:
    """Run shell and GatorGrader checks and display whether each has passed or failed.

        Also, print a list of all failed checks with their diagnostics and a summary message that
        shows the overall fraction of passed checks.

    Args:
        checks: The list of shell and GatorGrader checks to run.
        running_mode: Convert the Progress Bar to update based on checks ran/not ran.
        no_status_bar: Option to completely disable all Progress Bar options.
    """
    results = []
    # run each of the checks
    # check how many tests are being ran
    total_checks = len(checks)
    # run checks with no progress bar
    if no_status_bar:
        for check in checks:
            result = None
            command_ran = None
            # run a shell check; this means
            # that it is going to run a command
            # in the shell as a part of a check;
            # store the command that ran in the
            # field called run_command that is
            # inside of a CheckResult object but
            # not initialized in the constructor
            if isinstance(check, ShellCheck):
                result = _run_shell_check(check)
                command_ran = check.command
                result.run_command = command_ran
            # run a check that GatorGrader implements
            elif isinstance(check, GatorGraderCheck):
                result = _run_gg_check(check)
                # check to see if there was a command in the
                # GatorGraderCheck. This code finds the index of the
                # word "--command" in the check.gg_args list if it
                # is available (it is not available for all of
                # the various types of GatorGraderCheck instances),
                # and then it adds 1 to that index to get the actual
                # command run and then stores that command in the
                # result.run_command field that is initialized to
                # an empty string in the constructor for CheckResult
                if "--command" in check.gg_args:
                    index_of_command = check.gg_args.index("--command")
                    index_of_new_command = int(index_of_command) + 1
                    result.run_command = check.gg_args[index_of_new_command]
            # there were results from running checks
            # and thus they must be displayed
            if result is not None:
                result.print()
                results.append(result)
    else:
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(
                bar_width=40,
                style="red",
                complete_style="green",
                finished_style="green",
            ),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        ) as progress:
            # add a progress task for tracking
            task = progress.add_task("[green]Running checks", total=total_checks)
            # run each of the checks
            for check in checks:
                result = None
                command_ran = None
                if isinstance(check, ShellCheck):
                    result = _run_shell_check(check)
                    command_ran = check.command
                    result.run_command = command_ran
                # run a check that GatorGrader implements
                elif isinstance(check, GatorGraderCheck):
                    result = _run_gg_check(check)
                    # check to see if there was a command in the
                    # GatorGraderCheck. This code finds the index of the
                    # word "--command" in the check.gg_args list if it
                    # is available (it is not available for all of
                    # the various types of GatorGraderCheck instances),
                    # and then it adds 1 to that index to get the actual
                    # command run and then stores that command in the
                    # result.run_command field that is initialized to
                    # an empty string in the constructor for CheckResult
                    if "--command" in check.gg_args:
                        index_of_command = check.gg_args.index("--command")
                        index_of_new_command = int(index_of_command) + 1
                        result.run_command = check.gg_args[index_of_new_command]
                # there were results from running checks
                # and thus they must be displayed
                if result is not None:
                    result.print()
                    results.append(result)
                # update progress based on running_mode
                if running_mode:
                    progress.update(task, advance=1)
                else:
                    if result and result.passed:
                        progress.update(task, advance=1)
    # determine if there are failures and then display them
    failed_results = list(filter(lambda result: not result.passed, results))
    # print failures list if there are failures to print
    # and print what ShellCheck command that Gatorgrade ran
    if len(failed_results) > 0:
        print("\n-~-  FAILURES  -~-\n")
        for result in failed_results:
            # main.console.print("This is a result")
            # main.console.print(result)
            result.print(show_diagnostic=True)
            # this result is an instance of CheckResult
            # that has a run_command field that is some
            # value that is not the default of an empty
            # string and thus it should be displayed;
            # the idea is that displaying this run_command
            # will give the person using Gatorgrade a way
            # to quickly run the command that failed
            if result.run_command != "":
                rich.print(f"[blue]   → Run this command: [green]{result.run_command}")
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
    # compute summary results and display them in the console using the Panel
    # provided by Rich; this enables a border that resizes with the terminal;
    # note that there is one blank line between the prior output and the Panel
    summary = f"Passed {passed_count}/{len(results)} ({percent}%) of checks for {Path.cwd().name}!"
    summary_color = "green" if passed_count == len(results) else "bright_red"
    rich.print("")
    rich.print(Panel(summary, expand=False, title=None, style=summary_color))
    # determine whether or not the run was a success or not:
    # if all of the tests pass then the function returns True;
    # otherwise the function must return False
    summary_status = True if passed_count == len(results) else False
    return summary_status
