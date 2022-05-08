"""Use Typer to run gatorgrade to run the checks and generate the yml file."""
from pathlib import Path
import typer

app = typer.Typer(add_completion=False)
FILE = "gatorgrade.yml"


@app.callback(invoke_without_command=True)
def gatorgrade(
    ctx: typer.Context,
    filename: Path = typer.Option(
        "FILE", "--config", "-c", help="Name of the yml file."
    ),
):
    """Run the GatorGrader checks in the gatorgrade.yml file."""
    # check if ctx.subcommand is none
    if ctx.invoked_subcommand is None:
        if filename.suffix == "yml":
            pass


@app.command()
def generate(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force gatorgrade to overwrite an existing yml file.",
    )
):
    """Generate a gatorgrade.yml file."""
    if force is False:
        pass


if __name__ == "__main__":
    app()
