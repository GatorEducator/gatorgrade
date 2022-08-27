"""Run checks and display whether each has passed or failed."""

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


def run_checks(checks: List[Union[ShellCheck, GatorGraderCheck]]) -> bool:
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
