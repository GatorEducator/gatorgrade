"""Use Typer to run gatorgrade to run the checks and generate the yml file."""
from pathlib import Path
import typer
from typing import List
from gatorgrade.input.in_file_path import parse_config
from gatorgrade.output.output_functions import run_and_display_command_checks

app = typer.Typer(add_completion=False)
FILE = "gatorgrade.yml"


@app.callback(invoke_without_command=True)
def gatorgrade(
    ctx: typer.Context,
    filename: Path = typer.Option(
        FILE, "--config", "-c", help="Name of the yml file."
    ),
):
    """Run the GatorGrader checks in the gatorgrade.yml file."""
    # check if ctx.subcommand is none
    if ctx.invoked_subcommand is None:
        checks = parse_config(filename)
        run_and_display_command_checks(checks)


@app.command()
def generate(target_path_list: List[str]):
    """Generate a gatorgrade.yml file."""
    pass


if __name__ == "__main__":
    app()
