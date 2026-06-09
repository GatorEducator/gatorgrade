"""Run checks and display whether each has passed or failed."""

import datetime
import json
import os
import subprocess
from pathlib import Path
from typing import Any, List, Tuple, Union

import gator
import rich
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn
from rich.rule import Rule

from gatorgrade.input.checks import GatorGraderCheck, ShellCheck
from gatorgrade.output.check_result import CheckResult

# disable rich's default highlight to stop number coloring
rich.reconfigure(highlight=False)

# basic string constants
EMPTY = ""
NEWLINE = "\n"
SPACE = " "

# output labels
FAILING_CHECKS_LABEL = "Failing Checks"
PROJECT_LABEL = "Project"
RUNNING_CHECKS_LABEL = "Running checks"
WEIGHT_LABEL = "Weight"
RUN_COMMAND_LABEL = "Run this command"

# format strings for diagnostic truncation
TRUNCATED_MSG = "\n   ... (output truncated to {} line(s))"
DIAGNOSTIC_INDENT = "\n     "

# argument strings used in GatorGrader checks
GG_DIRECTORY_ARG = "--directory"
GG_COMMAND_ARG = "--command"
GG_PATH_SEPARATOR = "/"
INVALID_GG_CHECK_FMT = 'Invalid GatorGrader check: "{}"'
GG_ERROR_FMT = '"{}" thrown by GatorGrader'

# JSON report key constants
AMOUNT_CORRECT_KEY = "amount_correct"
PERCENTAGE_SCORE_KEY = "percentage_score"
WEIGHTED_AMOUNT_CORRECT_KEY = "weighted_amount_correct"
WEIGHTED_TOTAL_KEY = "weighted_total"
WEIGHTED_PERCENTAGE_KEY = "weighted_percentage_score"
CLI_ARGS_KEY = "cli_args"
REPORT_TIME_KEY = "report_time"
CHECKS_KEY = "checks"
STATUS_KEY = "status"
PATH_KEY = "path"
DIAGNOSTIC_KEY = "diagnostic"
DATETIME_FMT = "%Y-%m-%d %H:%M:%S"

# JSON key constants used in check results
DESCRIPTION_KEY = "description"
CHECK_KEY = "check"
OPTIONS_KEY = "options"
COMMAND_KEY = "command"
FRAGMENT_KEY = "fragment"
TAG_KEY = "tag"
COUNT_KEY = "count"
DIRECTORY_KEY = "directory"
FILE_KEY = "file"

# report format strings
REPORT_TYPE_JSON = "json"
REPORT_TYPE_MD = "md"
REPORT_FORMAT_FILE = "file"
REPORT_FORMAT_ENV = "env"
GITHUB_STEP_SUMMARY_VAR = "GITHUB_STEP_SUMMARY"
GITHUB_ENV_VAR = "GITHUB_ENV"
JSON_REPORT_KEY = "JSON_REPORT"

# file operation constants
FILE_MODE_WRITE = "w"
FILE_ENCODING = "utf-8"
INDENT_JSON = 4

# markdown template strings
MD_HEADER = "# Gatorgrade Insights\n\n"
MD_PASSING_HEADER = "\n## Passing Checks\n"
MD_FAILING_HEADER = "\n\n## Failing Checks\n"
MD_PASSING_ITEM = "\n- [x] {}"
MD_FAILING_ITEM = "\n- [ ] {}"
MD_OPTION_CMD_FMT = "\n\t- **{}** {}"
MD_OPTION_FMT = "\n\t- **{}:** {}"
MD_TOP_CMD_FMT = "\n\t- **command:** {}"
MD_DIAGNOSTIC_LABEL = "\n\t- **diagnostic:** {}"

# error message strings
REPORT_TYPE_ERR = (
    "\n[red]The second argument of report has to be 'md' or 'json' "
)
REPORT_FORMAT_ERR = (
    "\n[red]The first argument of report has to be 'env' or 'file' "
)
FILE_WRITE_ERR = "\n[red]Can't open or write the target file, check if you provide a valid path"

# empty dict for CLI args default
EMPTY_CLI_ARGS: dict = {}


def _truncate_diagnostic(diagnostic: str, limit: int | None) -> str:
    """Truncate diagnostic output to a maximum number of lines.

    Args:
        diagnostic: The raw diagnostic output.
        limit: The maximum number of lines to keep.

    Returns:
        The truncated diagnostic string.

    """
    if limit is None or limit <= 0:
        return diagnostic
    lines = diagnostic.splitlines()
    if len(lines) <= limit:
        return diagnostic
    truncated = lines[:limit]
    return NEWLINE.join(truncated) + TRUNCATED_MSG.format(limit)


def _run_shell_check(
    check: ShellCheck, output_limit: int | None = None
) -> CheckResult:
    """Run a shell check.

    Args:
        check: The shell check to run.
        output_limit: The maximum number of diagnostic lines to display.

    Returns:
        The result of running the shell check as a CheckResult.

    """
    result = subprocess.run(
        check.command,
        shell=True,
        check=False,
        timeout=300,
        stdout=subprocess.PIPE,
        # redirect STDERR to STDOUT so STDOUT and STDERR can be captured
        # together as diagnostic
        stderr=subprocess.STDOUT,
    )
    passed = result.returncode == 0
    # add spaces after each newline to indent all lines of diagnostic
    raw_diagnostic = (
        ""
        if passed
        else result.stdout.decode().strip().replace("\n", DIAGNOSTIC_INDENT)
    )
    limit = (
        check.outputlimit if check.outputlimit is not None else output_limit
    )
    diagnostic = _truncate_diagnostic(raw_diagnostic, limit)
    return CheckResult(
        passed=passed,
        description=check.description,
        json_info=check.json_info,
        diagnostic=diagnostic,
        weight=check.weight,
    )


def _run_gg_check(
    check: GatorGraderCheck, output_limit: int | None = None
) -> CheckResult:
    """Run a GatorGrader check.

    Args:
        check: The GatorGrader check to run.
        output_limit: The maximum number of diagnostic lines to display.

    Returns:
        The result of running the GatorGrader check as a CheckResult.

    """
    try:
        result = gator.grader(check.gg_args)
        passed = result[1]
        description = result[0]
        diagnostic = result[2]
        # fetch the path from gatorgrade arguments
        # the path pattern are 4 consistent string in the list
        # --dir `dir_name` --file `file_name`
        file_path = None
        for i in range(len(check.gg_args)):
            if check.gg_args[i] == GG_DIRECTORY_ARG:
                dir_name = check.gg_args[i + 1]
                file_name = check.gg_args[i + 3]
                file_path = dir_name + GG_PATH_SEPARATOR + file_name
                break
    # if arguments are formatted incorrectly, catch the exception and
    # return it as the diagnostic message
    # disable pylint to catch any type of exception thrown by GatorGrader
    except Exception as command_exception:  # pylint: disable=W0703
        passed = False
        check_args_str = SPACE.join(check.gg_args)
        description = INVALID_GG_CHECK_FMT.format(check_args_str)
        diagnostic = GG_ERROR_FMT.format(command_exception.__class__)
        file_path = None
    limit = (
        check.outputlimit if check.outputlimit is not None else output_limit
    )
    diagnostic = _truncate_diagnostic(diagnostic, limit)
    return CheckResult(
        passed=passed,
        description=description,
        json_info=check.json_info,
        diagnostic=diagnostic,
        path=file_path,
        weight=check.weight,
    )


def create_report_json(
    passed_count: int,
    checkResults: List[CheckResult],
    percent_passed: int,
    weighted_percent: int = 0,
    cli_args: dict | None = None,
) -> dict:
    """Take checks and put them into json format in a dictionary.

    Args:
        passed_count: the number of checks that passed
        check_information: the basic information about checks and their params
        checkResults: the list of check results that will be put in json
        percent_passed: the percentage of checks that passed
        weighted_percent: the weighted percentage of checks that passed
        cli_args: the command-line arguments to include in the report

    """
    # compute weighted totals from check results
    total_weight = sum(r.weight for r in checkResults)
    passed_weight = sum(r.weight for r in checkResults if r.passed)
    # create list to hold the key values for the dictionary that
    # will be converted into json
    overall_key_list = [
        AMOUNT_CORRECT_KEY,
        PERCENTAGE_SCORE_KEY,
        WEIGHTED_AMOUNT_CORRECT_KEY,
        WEIGHTED_TOTAL_KEY,
        WEIGHTED_PERCENTAGE_KEY,
        CLI_ARGS_KEY,
        REPORT_TIME_KEY,
        CHECKS_KEY,
    ]
    checks_list = []
    # extract the date and time from the report generation time
    report_generation_time = datetime.datetime.now()
    formatted_time = report_generation_time.strftime(DATETIME_FMT)
    # for each check, perform the following steps
    for i in range(len(checkResults)):
        # grab all of the information in it and add it to the checks list
        results_json = checkResults[i].json_info
        # confirm that the json_info field of the check result is a dictionary
        # and then add the status, path, and diagnostic information to that dictionary
        if isinstance(results_json, dict):
            results_json[STATUS_KEY] = checkResults[i].passed
            if checkResults[i].path:
                results_json[PATH_KEY] = checkResults[i].path
            if not checkResults[i].passed:
                results_json[DIAGNOSTIC_KEY] = checkResults[i].diagnostic
        checks_list.append(results_json)
    # create the dictionary for all of the check information
    overall_dict = dict(
        zip(
            overall_key_list,
            [
                passed_count,
                percent_passed,
                passed_weight,
                total_weight,
                weighted_percent,
                cli_args if cli_args is not None else EMPTY_CLI_ARGS,
                formatted_time,
                checks_list,
            ],
        )
    )
    return overall_dict


def create_markdown_report_file(json: dict) -> str:  # noqa: PLR0912
    """Create a markdown file using the created json to use in GitHub actions summary, among other places.

    Args:
        json: a dictionary containing the json that should be converted to markdown

    """
    markdown_contents = ""
    passing_checks = []
    failing_checks = []
    num_checks = len(json.get(CHECKS_KEY))  # type: ignore
    # write the total, amt correct and percentage score to md file
    weighted_score = json.get(WEIGHTED_PERCENTAGE_KEY, 0)
    weighted_amount = json.get(WEIGHTED_AMOUNT_CORRECT_KEY, 0)
    weighted_total = json.get(WEIGHTED_TOTAL_KEY, 0)
    markdown_contents += (
        f"{MD_HEADER}"
        f"**Project Name:** {Path.cwd().name}\n"
        f"**Amount Correct:** {json.get(AMOUNT_CORRECT_KEY)}/{num_checks} "
        f"({json.get(PERCENTAGE_SCORE_KEY)}%)\n"
        f"**Points:** {weighted_amount}/{weighted_total} "
        f"({weighted_score}%)\n"
    )
    # split checks into passing and not passing
    for check in json.get(CHECKS_KEY):  # type: ignore
        # if the check is passing
        if check[STATUS_KEY]:
            passing_checks.append(check)
        # if the check is failing
        else:
            failing_checks.append(check)
    # give short info about passing checks
    markdown_contents += MD_PASSING_HEADER
    for check in passing_checks:
        if DESCRIPTION_KEY in check:
            markdown_contents += MD_PASSING_ITEM.format(check[DESCRIPTION_KEY])
        else:
            markdown_contents += MD_PASSING_ITEM.format(check[CHECK_KEY])
    # give extended information about failing checks
    markdown_contents += MD_FAILING_HEADER
    # for each failing check, print out all related information
    for check in failing_checks:
        # for each key val pair in the check dictionary
        if DESCRIPTION_KEY in check:
            markdown_contents += MD_FAILING_ITEM.format(check[DESCRIPTION_KEY])
        else:
            markdown_contents += MD_FAILING_ITEM.format(check[CHECK_KEY])
        if OPTIONS_KEY in check:
            for i in check.get(OPTIONS_KEY):
                if COMMAND_KEY == i:
                    val = check[OPTIONS_KEY][COMMAND_KEY]
                    markdown_contents += MD_OPTION_CMD_FMT.format(
                        COMMAND_KEY, val
                    )
                if FRAGMENT_KEY == i:
                    val = check[OPTIONS_KEY][FRAGMENT_KEY]
                    markdown_contents += MD_OPTION_FMT.format(
                        FRAGMENT_KEY, val
                    )
                if TAG_KEY == i:
                    val = check[OPTIONS_KEY][TAG_KEY]
                    markdown_contents += MD_OPTION_FMT.format(TAG_KEY, val)
                if COUNT_KEY == i:
                    val = check[OPTIONS_KEY][COUNT_KEY]
                    markdown_contents += MD_OPTION_FMT.format(COUNT_KEY, val)
                if DIRECTORY_KEY == i:
                    val = check[OPTIONS_KEY][DIRECTORY_KEY]
                    markdown_contents += MD_OPTION_FMT.format(
                        DIRECTORY_KEY, val
                    )
                if FILE_KEY == i:
                    val = check[OPTIONS_KEY][FILE_KEY]
                    markdown_contents += MD_OPTION_FMT.format(FILE_KEY, val)
        elif COMMAND_KEY in check:
            val = check[COMMAND_KEY]
            markdown_contents += MD_TOP_CMD_FMT.format(val)
        if DIAGNOSTIC_KEY in check:
            markdown_contents += MD_DIAGNOSTIC_LABEL.format(
                check[DIAGNOSTIC_KEY]
            )
        markdown_contents += NEWLINE
    return markdown_contents


def configure_report(
    report_params: Tuple[str, str, str], report_output_data_json: dict
) -> None:
    """Put together the contents of the report depending on the inputs of the user.

    Args:
        report_params: The details of what the user wants the report to
            look like.
            report_params[0]: file or env
            report_params[1]: json or md
            report_params[2]: name of the file or env
        report_output_data_json: The json dictionary that will be used
            or converted to md.

    """
    report_format = report_params[0]
    report_type = report_params[1]
    report_name = report_params[2]
    if report_type not in (REPORT_TYPE_JSON, REPORT_TYPE_MD):
        raise ValueError(REPORT_TYPE_ERR)
    # if the user wants markdown, get markdown content based on json
    if report_type == REPORT_TYPE_MD:
        report_output_data_md = create_markdown_report_file(
            report_output_data_json
        )
    # if the user wants the data stored in a file
    if report_format == REPORT_FORMAT_FILE:
        if report_type == REPORT_TYPE_MD:
            write_json_or_md_file(
                report_name, report_type, report_output_data_md
            )
        else:
            write_json_or_md_file(
                report_name, report_type, report_output_data_json
            )
    # the user wants the data stored in an environment variable; do not attempt
    # to save to the environment variable if it does not exist in the environment
    elif report_format == REPORT_FORMAT_ENV:
        if report_name == GITHUB_STEP_SUMMARY_VAR:
            env_file = os.getenv(GITHUB_STEP_SUMMARY_VAR, None)
            if env_file is not None:
                if report_type == REPORT_TYPE_MD:
                    write_json_or_md_file(
                        env_file, report_type, report_output_data_md
                    )
                else:
                    write_json_or_md_file(
                        env_file, report_type, report_output_data_json
                    )
        json_string = json.dumps(report_output_data_json)
        env_file = os.getenv(GITHUB_ENV_VAR, None)
        if env_file is not None:
            with open(os.environ[GITHUB_ENV_VAR], "a") as env_file_handle:
                env_file_handle.write(f"{JSON_REPORT_KEY}={json_string}\n")
    else:
        raise ValueError(REPORT_FORMAT_ERR)


def write_json_or_md_file(
    file_name: Union[str, Path], content_type: str, content: Any
) -> bool:
    """Write a markdown or json file."""
    # try to store content in a file with user chosen format
    try:
        # second argument has to be either json or md
        with open(file_name, FILE_MODE_WRITE, encoding=FILE_ENCODING) as file:
            if content_type == REPORT_TYPE_JSON:
                json.dump(content, file, indent=INDENT_JSON)
            else:
                file.write(str(content))
        return True
    except Exception as e:
        raise ValueError(FILE_WRITE_ERR) from e


def run_checks(  # noqa: PLR0912, PLR0913, PLR0915
    checks: List[Union[ShellCheck, GatorGraderCheck]],
    report: Tuple[str, str, str],
    no_progress_bar: bool = False,
    show_diagnostics: bool = True,
    output_limit: int | None = None,
    cli_args: dict | None = None,
) -> bool:
    """Run shell and GatorGrader checks and display whether each has passed or failed.

        Also, print a list of all failed checks with their diagnostics and a summary message that
        shows the overall fraction of passed checks.

    Args:
        checks: The list of shell and GatorGrader checks to run.
        report: The tuple specifying the report format, type, and name.
        no_progress_bar: Disable the progress bar (shown by default).
        show_diagnostics: Show diagnostic details for failing checks.
        output_limit: The maximum number of diagnostic lines to display
            for each check.
        cli_args: The command-line arguments to include in the report.

    """
    results: List[CheckResult] = []
    # run each of the checks
    # check how many tests are being ran
    total_checks = len(checks)
    # run checks with no progress bar
    if no_progress_bar:
        for check in checks:
            result = None
            # command_ran = None
            # run a shell check; this means
            # that it is going to run a command
            # in the shell as a part of a check;
            # store the command that ran in the
            # field called run_command that is
            # inside of a CheckResult object but
            # not initialized in the constructor
            if isinstance(check, ShellCheck):
                result = _run_shell_check(check, output_limit)
                command_ran = check.command
                result.run_command = command_ran
            # run a check that GatorGrader implements
            elif isinstance(check, GatorGraderCheck):
                result = _run_gg_check(check, output_limit)
                # check to see if there was a command in the
                # GatorGraderCheck. This code finds the index of the
                # word "--command" in the check.gg_args list if it
                # is available (it is not available for all of
                # the various types of GatorGraderCheck instances),
                # and then it adds 1 to that index to get the actual
                # command run and then stores that command in the
                # result.run_command field that is initialized to
                # an empty string in the constructor for CheckResult
                if GG_COMMAND_ARG in check.gg_args:
                    index_of_command = check.gg_args.index(GG_COMMAND_ARG)
                    index_of_new_command = index_of_command + 1
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
            TextColumn("[green]({task.completed}/{task.total})[/green]"),
            TimeElapsedColumn(),
        ) as progress:
            # add a progress task for tracking
            task = progress.add_task(
                f"[green]{RUNNING_CHECKS_LABEL}", total=total_checks
            )
            # run each of the checks
            for check in checks:
                result = None
                # command_ran = None
                if isinstance(check, ShellCheck):
                    result = _run_shell_check(check, output_limit)
                    command_ran = check.command
                    result.run_command = command_ran
                # run a check that GatorGrader implements
                elif isinstance(check, GatorGraderCheck):
                    result = _run_gg_check(check, output_limit)
                    # check to see if there was a command in the
                    # GatorGraderCheck. This code finds the index of the
                    # word "--command" in the check.gg_args list if it
                    # is available (it is not available for all of
                    # the various types of GatorGraderCheck instances),
                    # and then it adds 1 to that index to get the actual
                    # command run and then stores that command in the
                    # result.run_command field that is initialized to
                    # an empty string in the constructor for CheckResult
                    if GG_COMMAND_ARG in check.gg_args:
                        index_of_command = check.gg_args.index(GG_COMMAND_ARG)
                        # index_of_new_command = int(index_of_command) + 1
                        index_of_new_command = index_of_command + 1
                        result.run_command = check.gg_args[
                            index_of_new_command
                        ]
                # there were results from running checks
                # and thus they must be displayed
                if result is not None:
                    result.print()
                    results.append(result)
                # update progress on passing checks
                if result and result.passed:
                    progress.update(task, advance=1)
    # determine if there are failures and then display them
    failed_results = list(filter(lambda result: not result.passed, results))
    # determine how many of the checks passed and then
    # compute the total percentage of checks passed
    passed_count = len(results) - len(failed_results)
    # prevent division by zero if no results
    if len(results) == 0:
        percent = 0
    else:
        percent = round(passed_count / len(results) * 100)
    # compute the weighted percentage of checks passed
    total_weight = sum(result.weight for result in results)
    passed_weight = sum(result.weight for result in results if result.passed)
    if total_weight == 0:
        weighted_percent = 0
    else:
        weighted_percent = round(passed_weight / total_weight * 100)
    # if the report is wanted, create output in line with their specifications
    if all(report):
        report_output_data = create_report_json(
            passed_count, results, percent, weighted_percent, cli_args
        )
        configure_report(report, report_output_data)
    # compute the summary color based on pass/fail status
    summary_color = "green" if passed_count == len(results) else "bright_red"
    # print failures list if there are failures to print
    # and print what ShellCheck command that Gatorgrade ran
    if len(failed_results) > 0:
        rich.print("")
        rich.print(Rule(f"{FAILING_CHECKS_LABEL}", style="bright_red"))
        rich.print("")
        for result in failed_results:
            result.print(show_diagnostic=show_diagnostics)
            if show_diagnostics:
                # display the weight of the check so that the
                # person using gatorgrade understands the impact
                # of this check on the overall score
                rich.print(
                    f"[blue]   → {WEIGHT_LABEL}: [green]{result.weight}"
                )
                # this result is an instance of CheckResult
                # that has a run_command field that is some
                # value that is not the default of an empty
                # string and thus it should be displayed;
                # the idea is that displaying this run_command
                # will give the person using Gatorgrade a way
                # to quickly run the command that failed
                if result.run_command != EMPTY:
                    rich.print(
                        f"[blue]   → {RUN_COMMAND_LABEL}: [green]{result.run_command}"
                    )
        rich.print("")
        rich.print(f"[bold]- {PROJECT_LABEL}:[/] {Path.cwd().name}")
        rich.print(
            f"[bold]- Checks:[/] {passed_count}/{len(results)} "
            f"[{summary_color}]({percent}%)[/]"
        )
        rich.print(
            f"[bold]- Points:[/] {passed_weight}/{total_weight} "
            f"[{summary_color}]({weighted_percent}%)[/]"
        )
        rich.print("")
        rich.print(Rule(style="bright_red"))
    # all of the checks passed and thus the color highlights
    # are green instead of bright red; however, the same three
    # scores are displayed as in the failure case
    else:
        rich.print("")
        rich.print(f"[bold]- Project:[/] {Path.cwd().name}")
        rich.print(
            f"[bold]- Checks:[/] {passed_count}/{len(results)} "
            f"[{summary_color}]({percent}%)[/]"
        )
        rich.print(
            f"[bold]- Points:[/] {passed_weight}/{total_weight} "
            f"[{summary_color}]({weighted_percent}%)[/]"
        )
    # determine whether or not the run was a success or not:
    # if all of the tests pass then the function returns True;
    # otherwise the function must return False since run did not pass
    summary_status = True if passed_count == len(results) else False
    return summary_status
