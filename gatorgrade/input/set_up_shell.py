"""Set-up the shell commands."""

import subprocess

import typer


def run_setup(front_matter):
    """Run the shell set up commands and exit the program if a command fails.

    Args:
        front_matter: A dictionary whose 'setup' key contains the set up commands
        as a multi-line string.

    """
    # If setup exists in the front matter
    setup = front_matter.get("setup")
    if setup:
        typer.echo("Running set up commands...")
        for line in setup.splitlines():
            # Trims the white space
            command = line.strip()
            # Executes the command
            proc = subprocess.run(command, shell=True, check=False, timeout=300)
            # If the exit code tells it was unsuccessful and did not return 0
            if proc.returncode != 0:
                typer.secho(
                    f'The set up command "{command}" failed.\
                Exiting GatorGrade.',
                    err=True,
                    fg=typer.colors.RED,
                )
                # If a set up command failed, exit the execution
                # because environment was not set up correctly.
                raise typer.Exit(1)
        typer.echo("Finished!\n")
