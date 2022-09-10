"""Use Typer to run gatorgrade to run the checks and generate the yml file."""

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown

from gatorgrade.input.parse_config import parse_config
from gatorgrade.output.output import run_checks
from gatorgrade.util import github
from gatorgrade.util import versions

# define constants used in this module
DEFAULT_VERSION = False
GATORGRADE_EMOJI = "🐊"
GATORGRADE_EMOJI_RICH = ":crocodile:"
FILE = "gatorgrade.yml"
FAILURE = 1

# define the message about GitHub repositories
github_message = github.get_github_projects()

# define the version message with markdown formatting
project_version_str = versions.get_project_versions()
version_label = ":wrench: Version information:"
version_info_markdown = f"""
    {version_label}

    {project_version_str}
"""

# define the overall help message
help_message_markdown = f"""
{GATORGRADE_EMOJI_RICH} GatorGrade runs the GatorGrader checks in a specified configuration file.
"""

# define the epilog that appears after the help details
epilog_message_markdown = f"""
{version_info_markdown}


    :tada: Want to contribute to this project? Check these GitHub sites!

    {github_message}
"""

# create a Typer app that
# --> does not support completion
# --> has an epilog with version information and contact
# --> has a specified help message with an emoji for tagline
# --> uses "markdown" mode so that markdown and emojis work
app = typer.Typer(
    add_completion=False,
    epilog=epilog_message_markdown,
    help=help_message_markdown,
    rich_markup_mode="markdown",
)

# create a default console for printing with rich
console = Console()


@app.callback(invoke_without_command=True)
def gatorgrade(
    ctx: typer.Context,
    filename: Path = typer.Option(FILE, "--config", "-c", help="Name of the YML file."),
    version: bool = typer.Option(
        DEFAULT_VERSION, "--version", "-v", help="Display version information."
    ),
):
    """Run the GatorGrader checks in the specified configuration file."""
    # if ctx.subcommand is None then this means
    # that, by default, gatorgrade should run in checking mode
    if ctx.invoked_subcommand is None:
        # requesting version information overrides all other commands;
        # if the version details are requested, print them and exit
        if version:
            console.print(help_message_markdown)
            console.print(version_label)
            console.print(Markdown(versions.get_project_versions()))
            console.print()
        else:
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
                console.print(
                    f"The file {filename} either does not exist or is not valid."
                )
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
