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


def truncate_report(report_output_data_json: dict, output_limit: int = None) -> str:
    """Truncate the json report to the maximum number of lines allowed.

    Args:
        report_output_data_json: the json dictionary that will be used or converted to md
        output_limit: the maximum number of lines to display in the output
    """
    # Convert the JSON dictionary to a formatted string
    report_str = json.dumps(report_output_data_json, indent=4)

    # Split the string into lines
    report_lines = report_str.split("\n")

    # If the number of lines is within the limit, return the full report
    if output_limit is None or len(report_lines) <= output_limit:
        return report_str

    # Otherwise, truncate the report to the maximum number of lines
    truncated_report_lines = report_lines[:output_limit]

    # Convert the truncated report back to a JSON string
    truncated_report_str = "\n".join(truncated_report_lines)

    # Add a trailing ellipsis to indicate the report was truncated
    truncated_report_str += "\n..."

    return truncated_report_str


def configure_report(
    report_params: Tuple[str, str, str],
    report_output_data_json: dict,
    output_limit: int = None,
):
    """Put together the contents of the report depending on the inputs of the user.

    Args:
        report_params: The details of what the user wants the report to look like
            report_params[0]: file or env
            report_params[1]: json or md
            report_params[2]: name of the file or env
        report_output_data: the json dictionary that will be used or converted to md
        output_limit: the maximum number of characters to display in the output
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
    output_limit: int = None,
    check_status: str = None,
    show_failures: bool = False,
    check_include: str = None,
    check_exclude: str = None,
) -> bool:
    results = []

    # Run checks and gather results
    for check in checks:
        result = None
        command_ran = None

        # Run shell or GatorGrader checks
        if isinstance(check, ShellCheck):
            result = _run_shell_check(check)
            command_ran = check.command
            result.run_command = command_ran
        elif isinstance(check, GatorGraderCheck):
            result = _run_gg_check(check)
            if "--command" in check.gg_args:
                index_of_command = check.gg_args.index("--command")
                index_of_new_command = index_of_command + 1
                result.run_command = check.gg_args[index_of_new_command]

        if result:
            # Filter checks by status if specified
            if check_status == "pass" and result.passed:
                results.append(result)
            elif check_status == "fail" and not result.passed:
                results.append(result)
            elif not check_status:  # No specific status filter
                results.append(result)

    # Filter by include/exclude criteria
    filtered_results = results
    if check_include:
        filtered_results = [
            r for r in filtered_results if check_include in r.description
        ]

    if check_exclude:
        filtered_results = [
            r for r in filtered_results if check_exclude not in r.description
        ]

    # Print results based on the filtered results
    if show_failures:
        # Print only failures
        for result in filtered_results:
            if not result.passed:
                result.print(show_diagnostic=True)
                if result.run_command:
                    rich.print(
                        f"[blue]   → Run this command: [green]{result.run_command}\n"
                    )
    else:
        # Print all results
        for result in filtered_results:
            if not result.passed:
                result.print(show_diagnostic=True)
                if result.run_command:
                    rich.print(
                        f"[blue]   → Run this command: [green]{result.run_command}\n"
                    )
            else:
                result.print()  # Print normally for passing checks

    # Generate summary
    failed_results = [r for r in results if not r.passed]
    passed_count = len(results) - len(failed_results)
    percent = round(passed_count / len(results) * 100) if results else 0

    if all(report):
        report_output_data = create_report_json(passed_count, results, percent)
        configure_report(report, report_output_data)

    summary = f"Passed {passed_count}/{len(results)} ({percent}%) of checks for {Path.cwd().name}!"
    summary_color = "green" if passed_count == len(results) else "bright white"
    print_with_border(summary, summary_color)

    return passed_count == len(results)


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
    downright = "\u251b"
    # Lower right corner
    vert = "\u2503"
    # Vertical line
    horz = "\u2501"
    # Horizontal line
    line = horz * (len(text) + 2)
    rich.print(f"[{rich_color}]\n\t{upleft}{line}{upright}")
    rich.print(f"[{rich_color}]\t{vert} {text} {vert}")
    rich.print(f"[{rich_color}]\t{downleft}{line}{downright}\n")
