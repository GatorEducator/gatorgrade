"""Use Typer to run gatorgrade to run the checks and generate the yml file."""

import sys
from pathlib import Path
from typing import Tuple

import typer
from rich.console import Console

from gatorgrade.input.parse_config import parse_config
from gatorgrade.output.output import run_checks

# create an app for the Typer-based CLI

# define the emoji that will be prepended to the help message
gatorgrade_emoji = "🐊"

# create a Typer app that
# --> does not support completion
# --> has a specified help message with an emoji
app = typer.Typer(
    add_completion=False,
    help=f"{gatorgrade_emoji} Run the GatorGrader checks in the specified gatorgrade.yml file.",
)

# create a default console for printing with rich
console = Console()

# define constants used in this module
FILE = "gatorgrade.yml"
FAILURE = 1


@app.callback(invoke_without_command=True)
def gatorgrade(
    ctx: typer.Context,
    filename: Path = typer.Option(FILE, "--config", "-c", help="Name of the yml file."),
    report: Tuple[str, str, str] = typer.Option(
        (None, None, None),
        "--report",
        "-r",
        help="A tuple containing the following REQUIRED values: \
            1. The destination of the report (either file or env) \
            2. The format of the report (either json or md) \
            3. the name of the file or environment variable\
            4. use 'env md GITHUB_STEP_SUMMARY' to create GitHub job summary in GitHub Action",
    ),
    output_limit: int = typer.Option(
        None,
        "--output-limit",
        "-l",
        help="The maximum number of lines to store in an environment variable. Example: '--output-limit 1000'",
    ),
    check_include: str = typer.Option(
        None,
        "--check-include",
        "-i",
        help="Description of the checks to include. Example: '--check-include \"Complete all TODOs\"'",
    ),
    check_exclude: str = typer.Option(
        None,
        "--check-exclude",
        "-e",
        help="Description of the checks to exclude. Example: '--check-exclude \"Complete all TODOs\"'",
    ),
    check_status: str = typer.Option(
        None,
        "--check-status",
        "-s",
        help="Filter checks by their status (pass or fail). Example: '--check-status pass'",
    )
):
    if check_include:
        typer.echo(f"Included checks: {check_include}")
    if check_exclude:
        typer.echo(f"Excluded checks: {check_exclude}")
    if check_status:
        typer.echo(f"Filter checks by status: {check_status}")
    """Run the GatorGrader checks in the specified gatorgrade.yml file."""
    # if ctx.subcommand is None then this means
    # that, by default, gatorgrade should run in checking mode
    if ctx.invoked_subcommand is None:
        # parse the provided configuration file
        (checks, match) = parse_config(filename, check_include, check_exclude)
        # there are valid checks and thus the
        # tool should run them with run_checks
        if len(checks) > 0:
            checks_status = run_checks(checks, report, output_limit, check_status)
        # no checks were created and this means
        # that, most likely, the file was not
        # valid and thus the tool cannot run checks
        else:
            checks_status = False
            console.print()         
            if match is False:   
                if check_include:
                    console.print(f"The check {check_include} does not exist in the file {filename}.")
                if check_exclude:
                    console.print(f"The check {check_exclude} does not exist in the file {filename}.")
            else:
                console.print(f"The file {filename} either does not exist or is not valid.")
            console.print("Exiting now!")
            console.print()
        # at least one of the checks did not pass or
        # the provided file was not valid and thus
        # the tool should return a non-zero exit
        # code to designate some type of failure
        if checks_status is not True:
            sys.exit(FAILURE)


# @app.command()
# def generate(
#     root: Path = typer.Argument(
#         Path("."),
#         help="Root directory of the assignment",
#         exists=True,
#         dir_okay=True,
#         writable=True,
#     ),
#     paths: List[Path] = typer.Option(
#         ["*"],
#         help="Paths to recurse through and generate checks for",
#         exists=False,
#     ),
# ):
#     """Generate a gatorgrade.yml file."""
#     targets = []
#     for path in paths:
#         targets.extend(glob.iglob(path.as_posix(), recursive=True))
#     generate_config(targets, root.as_posix())


if __name__ == "__main__":
    app()
