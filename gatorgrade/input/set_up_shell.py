"""Set-up the shell commands."""

import subprocess
import sys
from typing import Any, Dict

import rich
import typer
from rich.rule import Rule

from gatorgrade.input.checks import validate_positive_nonzero_int
from gatorgrade.shell_runner import DEFAULT_TIMEOUT_SECONDS

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


def run_setup(front_matter: Dict[str, Any]) -> None:  # noqa: PLR0912
    """Run the shell set up commands and exit the program if a command fails.

    Args:
        front_matter: A dictionary whose 'setup' key contains the set up commands
        as a multi-line string.

    """
    setup = front_matter.get(SETUP_KEY)
    if setup:
        timeout = front_matter.get(SETUP_TIMEOUT_KEY, DEFAULT_TIMEOUT_SECONDS)
        error = validate_positive_nonzero_int(timeout, SETUP_TIMEOUT_KEY)
        if error:
            raise ValueError(error)

        failure_command = None
        timed_out = False
        captured_output = ""

        for line in setup.splitlines():
            command = line.strip()
            if not command:
                continue
            try:
                proc = subprocess.run(
                    command,
                    shell=True,
                    check=False,
                    timeout=timeout,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            except subprocess.TimeoutExpired as exc:
                failure_command = command
                timed_out = True
                if exc.stdout:
                    captured_output += exc.stdout.decode(errors="replace")
                if exc.stderr:
                    captured_output += exc.stderr.decode(errors="replace")
                break

            if proc.stdout:
                captured_output += proc.stdout.decode(errors="replace")
            if proc.stderr:
                captured_output += proc.stderr.decode(errors="replace")
            if proc.returncode != EXIT_SUCCESS:
                failure_command = command
                break

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
