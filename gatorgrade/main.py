"""Use Typer to run gatorgrade to run the checks and generate the yml file."""

import sys
from pathlib import Path

import typer
from rich.console import Console

from gatorgrade import version
from gatorgrade.input.parse_config import parse_config
from gatorgrade.output.output import run_checks

# create an app for the Typer-based CLI

# define the emoji that will be prepended to the help message
gatorgrade_emoji = "🐊"

# define the current version of GatorGrade
gatorgrade_version = version.get_gatorgrade_version()

# define the GitHub repository URL for GatorGrade
gatorgrade_github = "https://github.com/GatorEducator/gatorgrade"

# define the current version of GatorGrader
gatorgrader_version = version.get_gatorgrader_version()

# define the GitHub repository URL for GatorGrader
gatorgrader_github = "https://github.com/GatorEducator/gatorgrader"

# define the overall help message
help_message = (
    f"{gatorgrade_emoji} Run the GatorGrader checks in the specified gatorgrade.yml file."
    f"\n\n\t   GatorGrade Version: {gatorgrade_version}"
)

help_message = f"""
    :crocodile: Run the GatorGrader checks in the specified configuration file.

    * GatorGrade version: {gatorgrade_version}

    * GatorGrader version: {gatorgrader_version}
    """

epilog_message = f"""
    :tada: Want to contribute to this project? Check these GitHub sites!

    * GatorGrade: {gatorgrade_github}

    * GatorGrader: {gatorgrader_github}
    """

# create a Typer app that
# --> does not support completion
# --> has a specified help message with an emoji
app = typer.Typer(
    add_completion=False,
    epilog=epilog_message,
    help=help_message,
    rich_markup_mode="markdown",
)

# create a default console for printing with rich
console = Console()

# define constants used in this module
FILE = "gatorgrade.yml"
FAILURE = 1


@app.callback(invoke_without_command=True)
def gatorgrade(
    ctx: typer.Context,
    filename: Path = typer.Option(FILE, "--config", "-c", help="Name of the YML file."),
):
    """Run the GatorGrader checks in the specified configuration file."""
    # if ctx.subcommand is None then this means
    # that, by default, gatorgrade should run in checking mode
    if ctx.invoked_subcommand is None:
        # parse the provided configuration file
        checks = parse_config(filename)
        # there are valid checks and thus the
        # tool should run them with run_checks
        if len(checks) > 0:
            checks_status = run_checks(checks)
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
