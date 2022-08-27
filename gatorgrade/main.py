"""Use Typer to run gatorgrade to run the checks and generate the yml file."""

import glob
import sys
from pathlib import Path
from typing import List

import typer

from gatorgrade.generate.generate import generate_config
from gatorgrade.input.parse_config import parse_config
from gatorgrade.output.output import run_checks

app = typer.Typer(add_completion=False)

FILE = "gatorgrade.yml"
FAILURE = 1


@app.callback(invoke_without_command=True)
def gatorgrade(
    ctx: typer.Context,
    filename: Path = typer.Option(FILE, "--config", "-c", help="Name of the yml file."),
):
    """Run the GatorGrader checks in the gatorgrade.yml file."""
    # check if ctx.subcommand is none
    if ctx.invoked_subcommand is None:
        checks = parse_config(filename)
        checks_status = run_checks(checks)
        if checks_status is not True:
            sys.exit(FAILURE)


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
