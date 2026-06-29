"""Run checks and display whether each has passed or failed."""

import datetime
import json as json_module
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
CHECKS_LABEL = "Checks"
FAILING_CHECKS_LABEL = "Failing Check(s)"
POINTS_LABEL = "Points"
PROJECT_LABEL = "Project"
REPORT_LABEL = "Report"
RUNNING_CHECKS_LABEL = "Running checks"
RUNNING_CHECKS_RULE_LABEL = "Running Check(s)"
WEIGHT_LABEL = "Weight"
RUN_COMMAND_LABEL = "Run this command"

# format strings for diagnostic truncation
TRUNCATED_MSG = "\n   ... (output truncated from {} to {} line(s))"
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
VERSION_INFO_KEY = "version_info"
REPORT_TIME_KEY = "report_time"
CHECKS_KEY = "checks"
STATUS_KEY = "status"
PATH_KEY = "path"
DIAGNOSTIC_KEY = "diagnostic"
WEIGHT_KEY = "weight"
OUTPUTLIMIT_KEY = "outputlimit"
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
# (uppercase is now canonical,
# but lowercase accepted for backward compatability)
REPORT_TYPE_JSON = "JSON"
REPORT_TYPE_MD = "MD"
REPORT_FORMAT_FILE = "FILE"
REPORT_FORMAT_ENV = "ENV"
GITHUB_STEP_SUMMARY_VAR = "GITHUB_STEP_SUMMARY"
GITHUB_ENV_VAR = "GITHUB_ENV"
JSON_REPORT_KEY = "JSON_REPORT"

# file operation constants
FILE_MODE_WRITE = "w"
FILE_ENCODING = "utf-8"
INDENT_JSON = 4

# path eliding constants for report display
MAX_REPORT_PATH_LENGTH = 50
MIN_PATH_PARTS = 2
KEEP_ABSOLUTE_PARTS = 3
KEEP_RELATIVE_PARTS = 2
PATH_ELLIPSIS = "..."

# markdown template strings
MD_HEADER = "# Gatorgrade Report\n\n"
MD_PASSING_HEADER = "\n## Passing Checks\n"
MD_FAILING_HEADER = "\n\n## Failing Checks\n"
MD_PASSING_ITEM = "\n- [x] {}"
MD_FAILING_ITEM = "\n- [ ] {}"
MD_CODE_BLOCK_FMT = "\n## {}\n\n```json\n{}\n```"
MD_LIST_INDENT = SPACE + SPACE
MD_DIAG_OPEN = "````text"
MD_DIAG_CLOSE = "````"
MD_CLI_ARGS_HEADING = "Command-Line Arguments"
MD_VERSION_INFO_HEADING = "Version Information"

# error message strings
FILE_WRITE_ERR = (
    "Can't open or write the target file, check if you provide a valid path"
)

# empty dict for CLI args default
EMPTY_CLI_ARGS: dict = {}


def _elide_report_path(path_str: str) -> str:
    """Elide the middle of a long path, keeping the start and filename."""
    if len(path_str) <= MAX_REPORT_PATH_LENGTH:
        return path_str
    path = Path(path_str)
    parts = path.parts
    if len(parts) <= MIN_PATH_PARTS:
        return path_str
    if path.root:
        kept_start = parts[0] + os.sep.join(parts[1:KEEP_ABSOLUTE_PARTS])
    else:
        kept_start = os.sep.join(parts[:KEEP_RELATIVE_PARTS])
    kept_end = parts[-1]
    elided = f"{kept_start}{os.sep}{PATH_ELLIPSIS}{os.sep}{kept_end}"
    if len(elided) < len(path_str):
        return elided
    return path_str


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
    total = len(lines)
    truncated = lines[:limit]
    return NEWLINE.join(truncated) + TRUNCATED_MSG.format(total, limit)


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
        outputlimit=limit,
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
                # confirm that all of the parameters are
                # available and then extract them from the
                # list of the GatorGrader arguments
                if i + 3 < len(check.gg_args):
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
        outputlimit=limit,
    )


def create_report_json(  # noqa: PLR0913
    passed_count: int,
    checkResults: List[CheckResult],
    percent_passed: int,
    weighted_percent: int = 0,
    cli_args: dict | None = None,
    version_info: dict | None = None,
) -> dict:
    """Take checks and put them into json format in a dictionary.

    Args:
        passed_count: the number of checks that passed
        checkResults: the list of check results that will be put in json
        percent_passed: the percentage of checks that passed
        weighted_percent: the weighted percentage of checks that passed
        cli_args: the command-line arguments to include in the report
        version_info: the version and platform information to include in the report

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
        VERSION_INFO_KEY,
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
            results_json[WEIGHT_KEY] = checkResults[i].weight
            results_json[OUTPUTLIMIT_KEY] = checkResults[i].outputlimit
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
                version_info if version_info is not None else EMPTY_CLI_ARGS,
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
    passing_checks: list[dict] = []
    failing_checks: list[dict] = []
    num_checks = len(json.get(CHECKS_KEY))  # type: ignore
    # write the total, amt correct and percentage score to md file
    weighted_score = json.get(WEIGHTED_PERCENTAGE_KEY, 0)
    weighted_amount = json.get(WEIGHTED_AMOUNT_CORRECT_KEY, 0)
    weighted_total = json.get(WEIGHTED_TOTAL_KEY, 0)
    markdown_contents += (
        f"{MD_HEADER}"
        f"- **Project Name:** {Path.cwd().name}{NEWLINE}"
        f"- **Amount Correct:** {json.get(AMOUNT_CORRECT_KEY)}/{num_checks} "
        f"({json.get(PERCENTAGE_SCORE_KEY)}%){NEWLINE}"
        f"- **Points:** {weighted_amount}/{weighted_total} "
        f"({weighted_score}%){NEWLINE}"
    )
    # report time
    if REPORT_TIME_KEY in json:
        markdown_contents += (
            f"- **Report Time:** {json[REPORT_TIME_KEY]}{NEWLINE}"
        )
    # fenced code block for cli arguments
    cli_args = json.get(CLI_ARGS_KEY, {})
    if cli_args:
        cli_args_json = json_module.dumps(cli_args, indent=INDENT_JSON)
        markdown_contents += MD_CODE_BLOCK_FMT.format(
            MD_CLI_ARGS_HEADING, cli_args_json
        )
    # fenced code block for version information
    version_info = json.get(VERSION_INFO_KEY, {})
    if version_info:
        version_json = json_module.dumps(version_info, indent=INDENT_JSON)
        markdown_contents += MD_CODE_BLOCK_FMT.format(
            MD_VERSION_INFO_HEADING, version_json
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
        # show all keys except status and description
        for key, value in check.items():
            if key in (STATUS_KEY, DESCRIPTION_KEY, CHECK_KEY):
                continue
            if key == OPTIONS_KEY and value:
                markdown_contents += f"{NEWLINE}{MD_LIST_INDENT}- **options:**"
                for opt_key, opt_val in value.items():
                    markdown_contents += (
                        f"{NEWLINE}{MD_LIST_INDENT}{MD_LIST_INDENT}"
                        f"- **{opt_key}:** {opt_val}"
                    )
            elif key == DIAGNOSTIC_KEY:
                markdown_contents += (
                    f"{NEWLINE}{MD_LIST_INDENT}- **diagnostic:**"
                    f"{NEWLINE}{NEWLINE}{MD_LIST_INDENT}{MD_LIST_INDENT}"
                    f"{MD_DIAG_OPEN}{NEWLINE}"
                )
                for value_line in value.splitlines():
                    markdown_contents += (
                        f"{MD_LIST_INDENT}{MD_LIST_INDENT}"
                        f"{value_line}{NEWLINE}"
                    )
                markdown_contents += (
                    f"{MD_LIST_INDENT}{MD_LIST_INDENT}{MD_DIAG_CLOSE}"
                )
            else:
                markdown_contents += (
                    f"{NEWLINE}{MD_LIST_INDENT}- **{key}:** {value}"
                )
        markdown_contents += NEWLINE
    return markdown_contents


def configure_report(
    report_params: Tuple[str, str, str], report_output_data_json: dict
) -> None:
    """Write the report based on the user's destination and format.

    When the destination is FILE, the report is written directly to the
    specified file path in the requested format.

    When the destination is ENV, the report_name is treated as an environment
    variable name. If that variable exists, its value is used as a file path
    and the report is written there. This works for any environment variable,
    including GitHub Actions variables like GITHUB_STEP_SUMMARY.

    Additionally, when the GITHUB_ENV environment variable is set, the full
    JSON report is always appended as JSON_REPORT=<json> to that file. This
    behavior is designed for GitHub Actions, where GITHUB_ENV is a special
    file that sets environment variables for downstream steps.

    Args:
        report_params: The details of what the user wants the report to
            look like.
            report_params[0]: FILE or ENV (lowercase also accepted)
            report_params[1]: JSON or MD (lowercase also accepted)
            report_params[2]: name of the file or environment variable
        report_output_data_json: The JSON dictionary that will be used
            or converted to markdown.

    """
    # normalize to uppercase for case-insensitive matching
    # as the tool expects capitalized versions of these fields
    # as in "JSON" or "MD". With that said, a prior version of the
    # tool also supported lowercase versions of these fields
    # as in "json" or "md". The command-line interface only
    # advertisies the capitalized versions, but lowercasing them
    # here will ensure that this is backwards compatible
    report_format = report_params[0].upper()
    report_type = report_params[1].upper()
    # the report name is not normalized to uppercase because
    # it could be a file name or environment variable name that
    # is case-sensitive, which is the same as in prior versions
    report_name = report_params[2]
    # if the user wants markdown, get markdown content based on json
    if report_type == REPORT_TYPE_MD:
        report_output_data_md = create_markdown_report_file(
            report_output_data_json
        )
    # if the user wants the data stored in a file
    if report_format == REPORT_FORMAT_FILE:
        # save a markdown file for the report
        if report_type == REPORT_TYPE_MD:
            write_json_or_md_file(
                report_name, report_type, report_output_data_md
            )
        # save a JSON file for the report
        else:
            write_json_or_md_file(
                report_name, report_type, report_output_data_json
            )
    # the user wants the data stored in an environment variable; do not attempt
    # to save to the environment variable if it does not exist in the environment
    elif report_format == REPORT_FORMAT_ENV:
        # do not write the raw report to GITHUB_ENV because that file is a
        # special GitHub Actions workflow file for setting environment
        # variables; writing raw JSON to it would corrupt the file format
        if report_name != GITHUB_ENV_VAR:
            report_dest_path = os.getenv(report_name)
            if report_dest_path is not None:
                if report_type == REPORT_TYPE_MD:
                    write_json_or_md_file(
                        report_dest_path, report_type, report_output_data_md
                    )
                else:
                    write_json_or_md_file(
                        report_dest_path, report_type, report_output_data_json
                    )
    # if running in GitHub Actions, always append the JSON report to the
    # GITHUB_ENV file so that downstream steps can access it, regardless
    # of the report format chosen by the user. References:
    # https://docs.github.com/en/actions/reference/workflows-and-actions/variables
    # https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands
    github_env_path = os.getenv(GITHUB_ENV_VAR)
    if github_env_path is not None:
        json_string = json_module.dumps(report_output_data_json)
        with open(
            github_env_path, "a", encoding=FILE_ENCODING
        ) as env_file_handle:
            env_file_handle.write(f"{JSON_REPORT_KEY}={json_string}\n")


def write_json_or_md_file(
    file_name: Union[str, Path], content_type: str, content: Any
) -> bool:
    """Write a Markdown or JSON file."""
    # try to store content in a file with user chosen format
    # normalize content_type to uppercase for case-insensitive matching
    normalized_type = content_type.upper()
    try:
        # second argument has to be either json or md
        with open(file_name, FILE_MODE_WRITE, encoding=FILE_ENCODING) as file:
            if normalized_type == REPORT_TYPE_JSON:
                json_module.dump(content, file, indent=INDENT_JSON)
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
    version_info: dict | None = None,
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
        version_info: Version and platform information to include in the report.

    """
    results: List[CheckResult] = []
    # run each of the checks
    # check how many tests are being ran
    total_checks = len(checks)
    # run checks with no progress bar
    if no_progress_bar:
        rich.print()
        rich.print(Rule(RUNNING_CHECKS_RULE_LABEL))
        rich.print()
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
        rich.print()
        rich.print(Rule(RUNNING_CHECKS_RULE_LABEL))
        rich.print()
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
                # update progress for every check
                if result:
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
    report_display_name = None
    if all(report):
        report_output_data = create_report_json(
            passed_count,
            results,
            percent,
            weighted_percent,
            cli_args,
            version_info,
        )
        configure_report(report, report_output_data)
        if report[0].upper() == REPORT_FORMAT_FILE:
            report_display_name = _elide_report_path(report[2])
        else:
            report_display_name = report[2]
    # compute the summary color based on pass/fail status
    summary_color = "green" if passed_count == len(results) else "bright_red"
    # print failures list if there are failures to print
    # and print what ShellCheck command that Gatorgrade ran
    if len(failed_results) > 0:
        # close the running checks section with an outcome-colored rule
        rich.print()
        rich.print(Rule(style=summary_color))
        # failing checks section (with its own red rules)
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
            f"[bold]- {CHECKS_LABEL}:[/] {passed_count}/{len(results)} "
            f"[{summary_color}]({percent}%)[/]"
        )
        rich.print(
            f"[bold]- {POINTS_LABEL}:[/] {passed_weight}/{total_weight} "
            f"[{summary_color}]({weighted_percent}%)[/]"
        )
        if report_display_name is not None:
            rich.print(f"[bold]- {REPORT_LABEL}:[/] {report_display_name}")
        rich.print(EMPTY)
        rich.print(Rule(style="bright_red"))
    # all of the checks passed and thus the color highlights
    # are green instead of bright red; however, the same three
    # scores are displayed as in the failure case
    else:
        rich.print("")
        rich.print(f"[bold]- {PROJECT_LABEL}:[/] {Path.cwd().name}")
        rich.print(
            f"[bold]- {CHECKS_LABEL}:[/] {passed_count}/{len(results)} "
            f"[{summary_color}]({percent}%)[/]"
        )
        rich.print(
            f"[bold]- {POINTS_LABEL}:[/] {passed_weight}/{total_weight} "
            f"[{summary_color}]({weighted_percent}%)[/]"
        )
        if report_display_name is not None:
            rich.print(f"[bold]- {REPORT_LABEL}:[/] {report_display_name}")
        # close the running checks section with an outcome-colored rule
        rich.print()
        rich.print(Rule(style=summary_color))
    # determine whether or not the run was a success or not:
    # if all of the tests pass then the function returns True;
    # otherwise the function must return False since run did not pass
    summary_status = True if passed_count == len(results) else False
    return summary_status
