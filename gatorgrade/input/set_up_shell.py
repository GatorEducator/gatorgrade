"""Set-up the shell commands."""

import sys
from typing import Any, Dict

import rich
import typer
from rich.rule import Rule

from gatorgrade.input.checks import validate_positive_nonzero_int
from gatorgrade.shell_runner import DEFAULT_TIMEOUT_SECONDS, run_shell_command

# define the exit codes for the individual
# and overall setup commands
EXIT_FAILURE = 1
EXIT_SUCCESS = 0

# define constants used in setup command execution
SETUP_KEY = "setup"
SETUP_TIMEOUT_KEY = "setup_timeout"
SETUP_RULE_TITLE = "Running Set Up Command(s)"
GREEN_STYLE = "green"
BRIGHT_RED_STYLE = "bright_red"
SETUP_DONE_MSG = "Finished!\n"
SETUP_FAILURE_FMT = 'The set up command "{}" failed.\nExiting GatorGrade.'
SETUP_TIMEOUT_FMT = 'The set up command "{}" timed out after {} second(s).'


def run_setup(front_matter: Dict[str, Any]) -> None:
    """Run the shell set up commands and exit the program if a command fails.

    Args:
        front_matter: A dictionary whose 'setup' key contains the set up commands
        as a multi-line string.

    """
    # if setup exists in the front matter
    setup = front_matter.get(SETUP_KEY)
    if setup:
        # every setup command uses the front matter timeout, falling back
        # to the same default that shell checks use
        timeout = front_matter.get(SETUP_TIMEOUT_KEY, DEFAULT_TIMEOUT_SECONDS)
        error = validate_positive_nonzero_int(timeout, SETUP_TIMEOUT_KEY)
        if error:
            raise ValueError(error)
        # run commands first, capturing all output and tracking the first failure
        failure_command = None
        timed_out = False
        captured_output = ""
        for line in setup.splitlines():
            command = line.strip()
            if not command:
                continue
            # the shared runner kills the whole process tree on a timeout and
            # returns any partial output instead of raising an exception
            outcome = run_shell_command(
                command, timeout=timeout, merge_stderr=False
            )
            captured_output += outcome.stdout + outcome.stderr
            if outcome.timed_out or outcome.returncode != EXIT_SUCCESS:
                failure_command = command
                timed_out = outcome.timed_out
                break
        # display results with appropriate rule colors
        if failure_command is not None:
            rule_style = BRIGHT_RED_STYLE
            rich.print()
            rich.print(Rule(SETUP_RULE_TITLE, style=rule_style))
            rich.print()
            if captured_output:
                sys.stdout.write(captured_output)
            message = (
                SETUP_TIMEOUT_FMT.format(failure_command, timeout)
                if timed_out
                else SETUP_FAILURE_FMT.format(failure_command)
            )
            rich.print(f"[red]{message}[/red]")
            rich.print()
            rich.print(Rule(style=rule_style))
            raise typer.Exit(EXIT_FAILURE)
        rich.print()
        rich.print(Rule(SETUP_RULE_TITLE, style=GREEN_STYLE))
        rich.print()
        if captured_output:
            sys.stdout.write(captured_output)
        typer.echo(SETUP_DONE_MSG)
        rich.print(Rule(style=GREEN_STYLE))
