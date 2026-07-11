"""Run checks and display whether each has passed or failed."""

import datetime
import json as json_module
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, List, Tuple, Union

import gator
import rich
from rich.progress import (
    BarColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
)
from rich.rule import Rule

from gatorgrade.input.checks import GatorGraderCheck, ShellCheck
from gatorgrade.output.check_result import CheckResult
from gatorgrade.track import append_track_entry, build_track_entry

# disable rich's default highlight to stop number coloring
rich.reconfigure(highlight=False)

# basic string constants
EMPTY = ""
NEWLINE = "\n"
SPACE = " "

# output labels
CHECKS_LABEL = "Checks"
FAILING_CHECKS_LABEL = "Failing Check(s)"
OVERDUE_LABEL = "Overdue"
POINTS_LABEL = "Points"
PROJECT_LABEL = "Project"
REPORT_LABEL = "Report"
GITHUB_ENV_LABEL = "GitHub Environment"
DUE_DATE_LABEL = "Due Date"
REMAINING_LABEL = "remaining"
LESS_THAN_ONE_MINUTE = "Less than 1 minute"
SECONDS_PER_HOUR = 3600
SECONDS_PER_MINUTE = 60
TIME_REMAINING_GREEN = "green"
TIME_REMAINING_YELLOW = "yellow"
TIME_REMAINING_SOON = "bright_yellow"
TIME_REMAINING_OVERDUE = "red"
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
DETAILS_ITEM_FMT = "[italic]{}[/]: {}"

# JSON report key constants
AMOUNT_CORRECT_KEY = "amount_correct"
PERCENTAGE_SCORE_KEY = "percentage_score"
WEIGHTED_AMOUNT_CORRECT_KEY = "weighted_amount_correct"
WEIGHTED_TOTAL_KEY = "weighted_total"
WEIGHTED_PERCENTAGE_KEY = "weighted_percentage_score"
CLI_ARGS_KEY = "cli_args"
VERSION_INFO_KEY = "version_info"
REPORT_TIME_KEY = "report_time"
PROJECT_NAME_KEY = "project_name"
DUE_DATE_KEY = "due_date"
CHECKS_KEY = "checks"
STATUS_KEY = "status"
PATH_KEY = "path"
DIAGNOSTIC_KEY = "diagnostic"
HINT_KEY = "hint"
WEIGHT_KEY = "weight"
OUTPUTLIMIT_KEY = "outputlimit"
CHECK_ID_KEY = "check_id"
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
MD_PROJECT_NAME_LABEL = "**Project Name:**"
MD_AMOUNT_CORRECT_LABEL = "**Amount Correct:**"
MD_POINTS_LABEL = "**Points:**"
MD_REPORT_TIME_LABEL = "**Report Time:**"
MD_OPTIONS_LABEL = "**options:**"
MD_DIAGNOSTIC_LABEL = "**diagnostic:**"
MD_DUE_DATE_LABEL = "**Due Date:**"

# error message strings
FILE_WRITE_ERR = (
    "Can't open or write the target file, check if you provide a valid path"
)

# empty dict for CLI args default
EMPTY_CLI_ARGS: dict = {}

# default value for the auto-hint generation
# maximum step value (used to mimic other progress bars)
AUTO_HINT_STEPS = 100
AUTO_HINT_SLEEP_TIME = 0.15


def _elide_report_path(path_str: str) -> str:
    """Elide the middle of a long file/directory path, keeping the start and filename."""
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
    # run the shell command and capture its output and return code
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
        EMPTY
        if passed
        else result.stdout.decode().strip().replace(NEWLINE, DIAGNOSTIC_INDENT)
    )
    limit = (
        check.outputlimit if check.outputlimit is not None else output_limit
    )
    # truncate the diagnostic message if it is too long (note that this
    # limit can be specified on a per-check basis or, alternatively, it
    # can be provided by the person running gatorgrade on the command-line)
    diagnostic = _truncate_diagnostic(raw_diagnostic, limit)
    # create and return the CheckResult arising from the
    # execution of the shell check
    return CheckResult(
        passed=passed,
        description=check.description,
        json_info=check.json_info,
        diagnostic=diagnostic,
        weight=check.weight,
        outputlimit=limit,
        hint=check.hint,
        raw_diagnostic=raw_diagnostic,
        check_id=check.check_id,
    )


def _build_gg_check_details(check: GatorGraderCheck) -> str:
    """Build a details string from the check's configuration.

    Extracts the check name and options from json_info and
    formats them into a compact, readable string that is appended
    to the diagnostic output.

    Args:
        check: The GatorGrader check to extract details from.

    Returns:
        A formatted details string, or an empty string if no
        options are present.

    """
    info = check.json_info
    if not isinstance(info, dict):
        return EMPTY
    check_name = info.get("check", "")
    options = info.get("options", {})
    if not isinstance(options, dict):
        return EMPTY
    # build a list of labeled items, each with the label in italic
    parts = []
    if check_name:
        parts.append(DETAILS_ITEM_FMT.format("check", check_name))
    if isinstance(options, dict):
        for key, value in options.items():
            if key == COMMAND_KEY:
                # command is already shown as "Run this command"
                continue
            parts.append(DETAILS_ITEM_FMT.format(key, value))
    return ", ".join(parts)


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
    raw_diagnostic = diagnostic
    # extract the structured check details for GatorGrader checks
    details = _build_gg_check_details(check)
    diagnostic = _truncate_diagnostic(diagnostic, limit)
    return CheckResult(
        passed=passed,
        description=description,
        json_info=check.json_info,
        diagnostic=diagnostic,
        path=file_path,
        weight=check.weight,
        outputlimit=limit,
        hint=check.hint,
        raw_diagnostic=raw_diagnostic,
        details=details,
        check_id=check.check_id,
    )


def create_report_json(  # noqa: PLR0913
    passed_count: int,
    checkResults: List[CheckResult],
    percent_passed: int,
    weighted_percent: int = 0,
    cli_args: dict | None = None,
    version_info: dict | None = None,
    project_name: str | None = None,
    due_date: datetime.datetime | None = None,
) -> dict:
    """Take checks and put them into json format in a dictionary.

    Args:
        passed_count: the number of checks that passed
        checkResults: the list of check results that will be put in json
        percent_passed: the percentage of checks that passed
        weighted_percent: the weighted percentage of checks that passed
        cli_args: the command-line arguments to include in the report
        version_info: the version and platform information to include in the report
        project_name: optional custom project name from the config file
        due_date: optional due date from the config file

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
        PROJECT_NAME_KEY,
        DUE_DATE_KEY,
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
            if checkResults[i].hint:
                results_json[HINT_KEY] = checkResults[i].hint
            if checkResults[i].check_id:
                results_json[CHECK_ID_KEY] = checkResults[i].check_id
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
                project_name if project_name is not None else EMPTY,
                due_date.strftime("%Y-%m-%d %H:%M")
                if due_date is not None
                else EMPTY,
                cli_args if cli_args is not None else EMPTY_CLI_ARGS,
                version_info if version_info is not None else EMPTY_CLI_ARGS,
                formatted_time,
                checks_list,
            ],
        )
    )
    return overall_dict


def create_markdown_report_file(  # noqa: PLR0912, PLR0915
    json: dict,
    project_name: str | None = None,
    due_date: datetime.datetime | None = None,
) -> str:
    """Create a markdown file using the created json to use in GitHub actions summary, among other places.

    Args:
        json: a dictionary containing the json that should be converted to markdown
        project_name: optional custom project name from the config file
        due_date: optional due date from the config file

    """
    markdown_contents = EMPTY
    display_project_name = project_name or Path.cwd().name
    passing_checks: list[dict] = []
    failing_checks: list[dict] = []
    num_checks = len(json.get(CHECKS_KEY))  # type: ignore
    # write the total, amt correct and percentage score to md file
    weighted_score = json.get(WEIGHTED_PERCENTAGE_KEY, 0)
    weighted_amount = json.get(WEIGHTED_AMOUNT_CORRECT_KEY, 0)
    weighted_total = json.get(WEIGHTED_TOTAL_KEY, 0)
    markdown_contents += (
        f"{MD_HEADER}- {MD_PROJECT_NAME_LABEL} {display_project_name}{NEWLINE}"
    )
    if due_date is not None:
        due_date_str = due_date.strftime("%Y-%m-%d %H:%M")
        time_str, _ = _format_remaining_time(due_date)
        markdown_contents += (
            f"- {MD_DUE_DATE_LABEL} {due_date_str} ({time_str}){NEWLINE}"
        )
    markdown_contents += (
        f"- {MD_AMOUNT_CORRECT_LABEL} {json.get(AMOUNT_CORRECT_KEY)}/{num_checks} "
        f"({json.get(PERCENTAGE_SCORE_KEY)}%){NEWLINE}"
        f"- {MD_POINTS_LABEL} {weighted_amount}/{weighted_total} "
        f"({weighted_score}%){NEWLINE}"
    )
    # report time
    if REPORT_TIME_KEY in json:
        markdown_contents += (
            f"- {MD_REPORT_TIME_LABEL} {json[REPORT_TIME_KEY]}{NEWLINE}"
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
        # for each key-value pair in the check dictionary
        if DESCRIPTION_KEY in check:
            markdown_contents += MD_FAILING_ITEM.format(check[DESCRIPTION_KEY])
        else:
            markdown_contents += MD_FAILING_ITEM.format(check[CHECK_KEY])
        # show all keys except status and description
        for key, value in check.items():
            if key in (STATUS_KEY, DESCRIPTION_KEY, CHECK_KEY):
                continue
            if key == OPTIONS_KEY and value:
                markdown_contents += (
                    f"{NEWLINE}{MD_LIST_INDENT}- {MD_OPTIONS_LABEL}"
                )
                for opt_key, opt_val in value.items():
                    markdown_contents += (
                        f"{NEWLINE}{MD_LIST_INDENT}{MD_LIST_INDENT}"
                        f"- **{opt_key}:** {opt_val}"
                    )
            elif key == DIAGNOSTIC_KEY:
                markdown_contents += (
                    f"{NEWLINE}{MD_LIST_INDENT}- {MD_DIAGNOSTIC_LABEL}"
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
    report_params: Tuple[str, str, str],
    report_output_data_json: dict,
    project_name: str | None = None,
    due_date: datetime.datetime | None = None,
) -> None:
    """Write the report based on the user's destination and format.

    When the destination is FILE, the report is written directly to the
    specified file path in the requested format.

    When the destination is ENV, the report_name is treated as an environment
    variable name. If that variable exists, its value is used as a file path
    and the report is written there. This works for any environment variable,
    including GitHub Actions variables like GITHUB_STEP_SUMMARY.

    Writing report data to the GITHUB_ENV file for GitHub Actions is now
    handled by the standalone --github-env CLI flag. See write_github_env()
    for details.

    Args:
        report_params: The details of what the user wants the report to
            look like.
            report_params[0]: FILE or ENV (lowercase also accepted)
            report_params[1]: JSON or MD (lowercase also accepted)
            report_params[2]: name of the file or environment variable
        report_output_data_json: The JSON dictionary that will be used
            or converted to markdown.
        project_name: Optional custom project name from the config file.
        due_date: Optional due date from the config file.

    """
    # normalize to uppercase for case-insensitive matching
    # as the tool expects capitalized versions of these fields
    # as in "JSON" or "MD". With that said, a prior version of the
    # tool also supported lowercase versions of these fields
    # as in "json" or "md". The command-line interface only
    # advertisies the capitalized versions, but uppercasing them
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
            report_output_data_json, project_name, due_date
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


def write_github_env(
    github_env: Tuple[str | None, str | None],
    report_output_data_json: dict,
    project_name: str | None = None,
    due_date: datetime.datetime | None = None,
) -> bool:
    """Write report data to the GITHUB_ENV environment file.

    When the GITHUB_ENV environment variable is set, this function
    appends the report data as an environment variable assignment to
    that file and returns True.

    Args:
        github_env: Tuple of (format, environment variable name).
            Format is "JSON" or "MD" (case-insensitive).
        report_output_data_json: The full JSON report data.
        project_name: Optional custom project name from the config file.
        due_date: Optional due date from the config file.

    Returns:
        True if data was written to GITHUB_ENV, False if skipped
        because GITHUB_ENV was not set.

    """
    github_env_path = os.getenv(GITHUB_ENV_VAR)
    if github_env_path is None:
        return False
    # both values are guaranteed non-None by the caller
    fmt: str = github_env[0] if github_env[0] is not None else EMPTY
    fmt = fmt.upper()
    key: str = github_env[1] if github_env[1] is not None else EMPTY
    if fmt == REPORT_TYPE_MD:
        content = create_markdown_report_file(
            report_output_data_json, project_name, due_date
        )
    else:
        content = json_module.dumps(report_output_data_json)
    # use multiline delimiter syntax for content with newlines,
    # simple KEY=VALUE format for single-line content (compact JSON)
    # reference: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands#multiline-strings
    if NEWLINE in content:
        delimiter = f"GATORGRADE_{os.urandom(8).hex()}"
        # keep randomly generating a new delimeter for the
        # content if the delimeter is found inside of the content
        while delimiter in content:
            delimiter = f"GATORGRADE_{os.urandom(8).hex()}"
        with open(github_env_path, "a", encoding=FILE_ENCODING) as f:
            f.write(f"{key}<<{delimiter}\n{content}\n{delimiter}\n")
    else:
        with open(github_env_path, "a", encoding=FILE_ENCODING) as f:
            f.write(f"{key}={content}\n")
    return True


def write_json_or_md_file(
    file_name: Union[str, Path], content_type: str, content: Any
) -> bool:
    """Write a Markdown or JSON file."""
    # try to store content in a file with the user's chosen format
    # normalize content_type to uppercase for case-insensitive matching
    normalized_type = content_type.upper()
    try:
        # second argument, originally stored in the content_type parameter
        # and now stored in the normalized type, has to be either JSON or MD
        with open(file_name, FILE_MODE_WRITE, encoding=FILE_ENCODING) as file:
            if normalized_type == REPORT_TYPE_JSON:
                json_module.dump(content, file, indent=INDENT_JSON)
            else:
                file.write(str(content))
        return True
    except Exception as e:
        raise ValueError(FILE_WRITE_ERR) from e


def _format_remaining_time(due_date: datetime.datetime) -> tuple[str, str]:
    """Format the time remaining until (or past) a due date.

    Args:
        due_date: The due date and time.

    Returns:
        A tuple of (formatted_string, color_name). The color is "green"
        when there is plenty of time, "yellow" when less than 24 hours
        remain, and "red" when the due date has passed. Importantly, all
        of these colors are specified using rich and only defined in the
        terminal window of the person who ran the gatorgrade tool.

    """
    # determine the current time and then produce a diagnostic based
    # on the connection between the due date and the current time
    now = datetime.datetime.now()
    seconds = int((due_date - now).total_seconds())
    if seconds >= 0:
        remaining = datetime.timedelta(seconds=seconds)
        days = remaining.days
        hours = remaining.seconds // SECONDS_PER_HOUR
        minutes = (remaining.seconds % SECONDS_PER_HOUR) // SECONDS_PER_MINUTE
        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0 and days == 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if not parts:
            parts.append(LESS_THAN_ONE_MINUTE)
        time_str = ", ".join(parts)
        if days > 0:
            color = TIME_REMAINING_GREEN
        elif hours > 0:
            color = TIME_REMAINING_YELLOW
        else:
            color = TIME_REMAINING_SOON
        return f"{time_str} {REMAINING_LABEL}", color
    overdue = datetime.timedelta(seconds=-seconds)
    days = overdue.days
    hours = overdue.seconds // SECONDS_PER_HOUR
    minutes = (overdue.seconds % SECONDS_PER_HOUR) // SECONDS_PER_MINUTE
    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0 and days == 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if not parts:
        parts.append(LESS_THAN_ONE_MINUTE)
    time_str = ", ".join(parts)
    return f"{OVERDUE_LABEL} by {time_str}", TIME_REMAINING_OVERDUE


def run_checks(  # noqa: PLR0912, PLR0913, PLR0915
    checks: List[Union[ShellCheck, GatorGraderCheck]],
    report: Tuple[str, str, str],
    no_progress_bar: bool = False,
    show_diagnostics: bool = True,
    output_limit: int | None = None,
    cli_args: dict | None = None,
    version_info: dict | None = None,
    github_env: Tuple[str | None, str | None] = (None, None),
    project_name: str | None = None,
    due_date: datetime.datetime | None = None,
    auto_hint_engine: Any = None,
    auto_hint_url: str | None = None,
    auto_hint_track: bool = False,
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
        github_env: Optional tuple of (format, key) for writing report data
            to the GITHUB_ENV file in GitHub Actions.
        project_name: Optional custom project name from the config file.
            If not provided, the current directory name is used.
        due_date: Optional due date from the config file for deadline display.
        auto_hint_engine: Optional engine for generating hints for failing
            checks. If provided, hints are generated lazily.
        auto_hint_url: URL of the remote auto-hint server, if any.
            Displayed in the summary when remote hints were used.
        auto_hint_track: Whether to write tracking data to
            autohints.json in the current working directory.

    """

    def _generate_hint(result: CheckResult) -> None:
        """Generate a hint for a failing check if the engine is available.

        Does not overwrite hints that were explicitly provided via the
        configuration file.

        """
        if auto_hint_engine is None or result.passed:
            return
        if result.hint is not None:
            # do not overwrite an explicit hint from the config file.
            return
        # read the relevant file content if the check has a file path.
        file_content = ""
        if result.path is not None:
            try:
                with open(result.path, "r", encoding="utf-8") as f:
                    file_content = f.read()
            except (OSError, IOError):
                file_content = ""
        hint, is_low_quality = auto_hint_engine.generate_hint(
            description=result.description,
            diagnostic=result.raw_diagnostic,
            command=result.run_command,
            file_content=file_content,
            details=result.details,
        )
        if hint is not None:
            result.hint = hint
            result.is_auto_hint = True
            result.is_low_quality = is_low_quality

    results: List[CheckResult] = []
    # use the configured project name, falling back to directory name
    display_project_name = project_name or Path.cwd().name
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
                # and thus they must be displayed; use the progress
                # bar's print method so each check appears above
                # the progress bar as it completes
                if result is not None:
                    results.append(result)
                    progress.print(result.display_result())
                    # if result:
                    progress.update(task, advance=1)
    # determine if there are failures and then display them
    failed_results = list(filter(lambda result: not result.passed, results))
    # generate auto-hints for failing checks with a progress bar
    if auto_hint_engine is not None and failed_results:
        # if the model has not been loaded yet, show a dedicated
        # progress bar for the download / load phase so the user
        # understands why the first hint is taking longer
        if not auto_hint_engine.is_loaded:
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(
                    bar_width=40,
                    style="red",
                    complete_style="green",
                    finished_style="green",
                ),
                TimeElapsedColumn(),
            ) as load_progress:
                task_id = load_progress.add_task(
                    "[green]Loading auto-hinter",
                    total=AUTO_HINT_STEPS,
                )
                load_progress.update(
                    task_id,
                    completed=0,
                )

                # use a daemon thread to advance the bar so it animates
                # while the model is being loaded, then mark it complete
                # in green once loading finishes
                def _advance_bar() -> None:
                    for _ in range(AUTO_HINT_STEPS - 1):
                        time.sleep(AUTO_HINT_SLEEP_TIME)
                        load_progress.update(task_id, advance=1)

                thread = threading.Thread(target=_advance_bar, daemon=True)
                thread.start()
                load_error: str | None = None
                try:
                    auto_hint_engine.ensure_loaded()
                except Exception as exc:  # pylint: disable=broad-except
                    load_error = str(exc)[:300]
                load_progress.update(task_id, completed=100)
                if load_error is not None:
                    rich.print()
                    rich.print(
                        "[yellow]Warning: Could not load the auto-hint"
                        f" model: {load_error}"
                        "[/]"
                    )
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
            task = progress.add_task(
                "[green]Generating auto-hints",
                total=len(failed_results),
            )
            for result in failed_results:
                _generate_hint(result)
                progress.update(task, advance=1)
        # if no hints were generated despite having an engine,
        # print a diagnostic message to explain why
        if not any(r.is_auto_hint for r in failed_results):
            last_err = getattr(auto_hint_engine, "last_error", None)
            if last_err:
                rich.print()
                rich.print(
                    "[yellow]Warning: Auto-hints could not be generated:"
                    f" {last_err}[/]"
                )
            else:
                rich.print()
                rich.print(
                    "[yellow]Warning: Auto-hints could not be generated."
                    " Check your network connection and model"
                    " availability.[/]"
                )
    # write tracking data to autohints.json if enabled and
    # at least one auto-hint was generated for failing checks
    if auto_hint_track and auto_hint_engine is not None:
        hinted_results = [r for r in failed_results if r.is_auto_hint]
        if hinted_results:
            track_entry = build_track_entry(
                failed_results,
                project_name=display_project_name,
                due_date=due_date,
                version_info=version_info,
                cli_args=cli_args,
            )
            if track_entry:
                append_track_entry(track_entry)

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
    # if the report or github-env is wanted, create the JSON report data
    report_display_name = None
    need_report_data = all(report) or all(github_env)
    if need_report_data:
        report_output_data = create_report_json(
            passed_count,
            results,
            percent,
            weighted_percent,
            cli_args,
            version_info,
            display_project_name,
            due_date,
        )
    # track report format for summary display
    report_type_str = None
    if all(report):
        # pass along all relevent details for the report so as
        # to ensure that when content is displayed or saved that
        # there is enough information to debug the failing checks
        configure_report(
            report, report_output_data, display_project_name, due_date
        )
        report_type_str = report[1].upper()
        if report[0].upper() == REPORT_FORMAT_FILE:
            report_display_name = _elide_report_path(report[2])
        else:
            report_display_name = report[2]
    # track github-env details for summary display
    github_env_written = False
    github_env_type_str = None
    github_env_key = None
    if all(github_env):
        # both values are guaranteed non-None by the all() check
        assert github_env[0] is not None
        assert github_env[1] is not None
        github_env_written = write_github_env(
            github_env, report_output_data, display_project_name, due_date
        )
        github_env_type_str = github_env[0].upper()
        github_env_key = github_env[1]
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
        # add labels to the top of the summary section
        # --> display the name of the project
        rich.print(f"[bold]- {PROJECT_LABEL}:[/] {display_project_name}")
        # --> if a due date was specified, display it and the time remaining
        if due_date is not None:
            due_date_str = due_date.strftime("%Y-%m-%d %H:%M")
            time_str, time_color = _format_remaining_time(due_date)
            rich.print(
                f"[bold]- {DUE_DATE_LABEL}:[/] "
                f"{due_date_str} [{time_color}]({time_str})[/]"
            )
        # --> display the number of checks and the percentage of passed checks
        rich.print(
            f"[bold]- {CHECKS_LABEL}:[/] {passed_count}/{len(results)} "
            f"[{summary_color}]({percent}%)[/]"
        )
        # --> display the number of points and the percentage of points
        rich.print(
            f"[bold]- {POINTS_LABEL}:[/] {passed_weight}/{total_weight} "
            f"[{summary_color}]({weighted_percent}%)[/]"
        )
        # --> if a report was specified, display it and the type
        if report_display_name is not None and report_type_str is not None:
            rich.print(
                f"[bold]- {REPORT_LABEL}:[/] "
                f"{report_display_name} ({report_type_str})"
            )
        if github_env_written:
            rich.print(
                f"[bold]- {GITHUB_ENV_LABEL}:[/] "
                f"{github_env_key} ({github_env_type_str})"
            )
        # add reminder about auto-hints at the very bottom
        # (after all other summary lines) so they appear as a
        # separate dimmed section below the main summary group
        if auto_hint_engine is not None and any(
            r.is_auto_hint for r in failed_results
        ):
            has_fallback = getattr(auto_hint_engine, "has_fallback", False)
            local_fallback = has_fallback and not getattr(
                auto_hint_engine, "remote_url", None
            )
            remote_fallback = has_fallback and getattr(
                auto_hint_engine, "remote_url", None
            )
            if remote_fallback:
                rich.print(
                    f"\n[dim]→ Use auto-hints generated by "
                    f"{auto_hint_engine.model_id} "
                    f"to spark ideas.\n"
                    f"  Failed to use remote server at"
                    f" {auto_hint_engine.remote_url}.[/]"
                )
            elif local_fallback:
                primary_model = getattr(
                    auto_hint_engine,
                    "primary_model_id",
                    "unknown",
                )
                rich.print(
                    f"\n[dim]→ Use auto-hints generated by "
                    f"{auto_hint_engine.model_id} "
                    f"to spark ideas.\n"
                    f"  The specified local model"
                    f" ({primary_model}) was not available;"
                    f" using the default model.[/]"
                )
            elif auto_hint_url:
                rich.print(
                    f"\n[dim]→ Use auto-hints generated by "
                    f"{auto_hint_engine.model_id}"
                    f" from {auto_hint_url} to spark ideas.[/]"
                )
            else:
                rich.print(
                    f"\n[dim]→ Use auto-hints generated by "
                    f"{auto_hint_engine.model_id}"
                    f" to spark ideas.[/]"
                )
            # add a note about lower-quality hints (dimmed/italic/grey)
            if any(r.is_low_quality for r in failed_results):
                rich.print(
                    "[dim]  Hints shown in "
                    "[dim][italic][bright_black]dimmed, grey, italic[/][/]"
                    "[dim] text may be of lower quality. "
                    "Use your judgment when following them![/]"
                )
        rich.print(EMPTY)
        rich.print(Rule(style="bright_red"))
    # all of the checks passed and thus the color highlights
    # are green instead of bright red; however, the same three
    # scores are displayed as in the failure case
    else:
        rich.print("")
        rich.print(f"[bold]- {PROJECT_LABEL}:[/] {display_project_name}")
        if due_date is not None:
            due_date_str = due_date.strftime("%Y-%m-%d %H:%M")
            time_str, time_color = _format_remaining_time(due_date)
            rich.print(
                f"[bold]- {DUE_DATE_LABEL}:[/] "
                f"{due_date_str} [{time_color}]({time_str})[/]"
            )
        rich.print(
            f"[bold]- {CHECKS_LABEL}:[/] {passed_count}/{len(results)} "
            f"[{summary_color}]({percent}%)[/]"
        )
        rich.print(
            f"[bold]- {POINTS_LABEL}:[/] {passed_weight}/{total_weight} "
            f"[{summary_color}]({weighted_percent}%)[/]"
        )
        if report_display_name is not None and report_type_str is not None:
            rich.print(
                f"[bold]- {REPORT_LABEL}:[/] "
                f"{report_display_name} in {report_type_str} format"
            )
        if github_env_written:
            rich.print(
                f"[bold]- {GITHUB_ENV_LABEL}:[/] "
                f"{github_env_key} in {github_env_type_str} format"
            )
        # add reminder about auto-hints at the very bottom
        # (after all other summary lines) so it appears as a
        # separate dimmed line below the main summary group
        if auto_hint_engine is not None:
            rich.print(
                f"[dim]Reminder: Auto-hints would have been generated by "
                f"{auto_hint_engine.model_id} if any checks failed[/]"
            )
        # close the running checks section with an outcome-colored rule
        rich.print()
        rich.print(Rule(style=summary_color))
    # determine whether or not the run was a success or not:
    # if all of the tests pass then the function returns True;
    # otherwise the function must return False since run did not pass
    summary_status = True if passed_count == len(results) else False
    return summary_status
