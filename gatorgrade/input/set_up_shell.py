"""Set-up the shell commands."""

import subprocess
import sys
from typing import Any, Dict

import rich
import typer
from rich.rule import Rule

# define the exit codes for the individual
# and overall setup commands
EXIT_FAILURE = 1
EXIT_SUCCESS = 0

# define constants used in setup command execution
SETUP_KEY = "setup"
SETUP_RULE_TITLE = "Running Set Up Commands"
GREEN_STYLE = "green"
BRIGHT_RED_STYLE = "bright_red"
TIMEOUT_SECONDS = 300
SETUP_DONE_MSG = "Finished!\n"
SETUP_FAILURE_FMT = 'The set up command "{}" failed.\nExiting GatorGrade.'


def run_setup(front_matter: Dict[str, Any]) -> None:
    """Run the shell set up commands and exit the program if a command fails.

    Args:
        front_matter: A dictionary whose 'setup' key contains the set up commands
        as a multi-line string.

    """
    # if setup exists in the front matter
    setup = front_matter.get(SETUP_KEY)
    if setup:
        # run commands first, capturing all output and tracking the first failure
        failure_command = None
        captured_output = ""
        for line in setup.splitlines():
            command = line.strip()
            proc = subprocess.run(
                command,
                shell=True,
                check=False,
                timeout=TIMEOUT_SECONDS,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if proc.stdout:
                captured_output += proc.stdout.decode(errors="replace")
            if proc.stderr:
                captured_output += proc.stderr.decode(errors="replace")
            if proc.returncode != EXIT_SUCCESS:
                failure_command = command
                break
        # display results with appropriate rule colors
        if failure_command is not None:
            rule_style = BRIGHT_RED_STYLE
            rich.print()
            rich.print(Rule(SETUP_RULE_TITLE, style=rule_style))
            rich.print()
            if captured_output:
                sys.stdout.write(captured_output)
            rich.print(
                f"[red]{SETUP_FAILURE_FMT.format(failure_command)}[/red]"
            )
            rich.print()
            rich.print(Rule(style=rule_style))
            raise typer.Exit(EXIT_FAILURE)
        else:
            rich.print()
            rich.print(Rule(SETUP_RULE_TITLE, style=GREEN_STYLE))
            rich.print()
            if captured_output:
                sys.stdout.write(captured_output)
            typer.echo(SETUP_DONE_MSG)
            rich.print(Rule(style=GREEN_STYLE))
