import sys
from pathlib import Path
from typing import Tuple

import typer
from rich.console import Console

from gatorgrade.input.parse_config import parse_config
from gatorgrade.output.output import run_checks

# create an app for the Typer-based CLI

gatorgrade_emoji = "🐊"

app = typer.Typer(
    add_completion=False,
    help=f"{gatorgrade_emoji} Run the GatorGrader checks in the specified gatorgrade.yml file.",
)

console = Console()
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
    ),
    show_failures: bool = typer.Option(
        False,
        "--show-failures",
        "-f",
        help="Only show the failed checks.",
    ),
):
    """Run the GatorGrader checks in the specified gatorgrade.yml file."""
    if ctx.invoked_subcommand is None:
        (checks, match) = parse_config(filename, check_include, check_exclude)

        if len(checks) > 0:
            checks_status = run_checks(
                checks, report, output_limit, check_status, show_failures
            )
        else:
            checks_status = False
            console.print()
            if match is False:
                if check_include:
                    console.print(
                        f"The check {check_include} does not exist in the file {filename}."
                    )
                if check_exclude:
                    console.print(
                        f"The check {check_exclude} does not exist in the file {filename}."
                    )
            else:
                console.print(
                    f"The file {filename} either does not exist or is not valid."
                )
            console.print("Exiting now!")
            console.print()

        if checks_status is not True:
            sys.exit(FAILURE)


if __name__ == "__main__":
    app()
