"""Set-up the shell commands."""

import subprocess
from typing import Any, Dict

import rich
import typer
from rich.rule import Rule


def run_setup(front_matter: Dict[str, Any]) -> None:
    """Run the shell set up commands and exit the program if a command fails.

    Args:
        front_matter: A dictionary whose 'setup' key contains the set up commands
        as a multi-line string.

    """
    # if setup exists in the front matter
    setup = front_matter.get("setup")
    if setup:
        rich.print()
        rich.print(Rule("Running Set Up Commands", style="green"))
        rich.print()
        for line in setup.splitlines():
            # trims the blank space
            command = line.strip()
            # executes the command
            proc = subprocess.run(
                command, shell=True, check=False, timeout=300
            )
            # if the exit code tells it was unsuccessful and did not return 0
            if proc.returncode != 0:
                typer.secho(
                    f'The set up command "{command}" failed.\
                Exiting GatorGrade.',
                    err=True,
                    fg=typer.colors.RED,
                )
                # if a set up command failed, exit the execution
                # because environment was not set up correctly.
                raise typer.Exit(1)
        typer.echo("Finished!\n")
        rich.print(Rule(style="green"))
