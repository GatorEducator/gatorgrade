"""Use Typer to run gatorgrade to run the checks and generate the yml file."""

import sys
from pathlib import Path
from typing import Tuple

import typer
from rich.console import Console
from rich.emoji import Emoji

from gatorgrade.input.parse_config import parse_config
from gatorgrade.output.output import run_checks

# create an app for the Typer-based CLI

# define the emoji that will be prepended to the help message;
# note that this uses a Rich emoji so that it is as platform-
# independent as possible, across three major operating systems
gatorgrade_emoji = Emoji.replace(":crocodile:")

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
    run_status_bar: bool = typer.Option(
        False,
        "--status-bar",
        help="Enable a progress bar for checks running/not running.",
    ),
    no_status_bar: bool = typer.Option(
        False, "--no-status-bar", help="Disable the progress bar entirely."
    ),
):
    """Run the GatorGrader checks in the specified gatorgrade.yml file."""
    # if ctx.subcommand is None then this means
    # that, by default, gatorgrade should run in checking mode
    if ctx.invoked_subcommand is None:
        # parse the provided configuration file
        checks = parse_config(filename)
        # there are valid checks and thus the
        # tool should run them with run_checks
        if len(checks) > 0:
            checks_status = run_checks(checks, report, run_status_bar, no_status_bar)
        # no checks were created and this means
        # that, most likely, the file was not
        # valid and thus the tool cannot run checks
        else:
            checks_status = False
            console.print()
            console.print(f"The file {filename} either does not exist or is not valid.")
            console.print("Exiting now!")
            console.print()
        # at least one of the checks did not pass or
        # the provided file was not valid and thus
        # the tool should return a non-zero exit
        # code to designate some type of failure
        if checks_status is not True:
            sys.exit(FAILURE)


if __name__ == "__main__":
    app()
