"""Set-up the shell commands."""

import subprocess
from typing import Any, Dict

import rich
import typer
from rich.rule import Rule

# constants used in setup command execution
SETUP_KEY = "setup"
SETUP_RULE_TITLE = "Running Set Up Commands"
GREEN_STYLE = "green"
TIMEOUT_SECONDS = 300
SETUP_DONE_MSG = "Finished!\n"
EXIT_FAILURE = 1
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
        rich.print()
        rich.print(Rule(SETUP_RULE_TITLE, style=GREEN_STYLE))
        rich.print()
        for line in setup.splitlines():
            # trims the blank space
            command = line.strip()
            # executes the command
            proc = subprocess.run(
                command, shell=True, check=False, timeout=TIMEOUT_SECONDS
            )
            # if the exit code tells it was unsuccessful and did not return 0
            if proc.returncode != 0:
                typer.secho(
                    SETUP_FAILURE_FMT.format(command),
                    err=True,
                    fg=typer.colors.RED,
                )
                rich.print()
                # if a set up command failed, exit the execution
                # because environment was not set up correctly.
                rich.print(Rule(style=GREEN_STYLE))
                raise typer.Exit(EXIT_FAILURE)

        typer.echo(SETUP_DONE_MSG)
        rich.print(Rule(style=GREEN_STYLE))
