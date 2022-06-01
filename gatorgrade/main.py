"""Use Typer to run gatorgrade to run the checks and generate the yml file."""

from typing import List
from pathlib import Path

import glob
import typer

from gatorgrade.input.parse_config import parse_config
from gatorgrade.output.output_functions import run_and_display_command_checks
from gatorgrade.generate.generate import generate_config

app = typer.Typer(add_completion=False)
FILE = "gatorgrade.yml"


@app.callback(invoke_without_command=True)
def gatorgrade(
    ctx: typer.Context,
    filename: Path = typer.Option(FILE, "--config", "-c", help="Name of the yml file."),
):
    """Run the GatorGrader checks in the gatorgrade.yml file."""
    # check if ctx.subcommand is none
    if ctx.invoked_subcommand is None:
        checks = parse_config(filename)
        run_and_display_command_checks(checks)


@app.command()
def generate(
    root: Path = typer.Argument(
        Path("."),
        help="Root directory of the assignment",
        exists=True,
        dir_okay=True,
        writable=True,
    ),
    paths: List[Path] = typer.Option(
        ["*"],
        help="Paths to recurse through and generate checks for",
        exists=False,
    ),
):
    """Generate a gatorgrade.yml file."""
    targets = []
    for path in paths:
        targets.extend(glob.iglob(path.as_posix(), recursive=True))
    generate_config(targets, root.as_posix())


if __name__ == "__main__":
    app()
