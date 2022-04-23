"""Use Typer to run gatorgrade to run the checks and generate the yml file."""
from pathlib import Path
import typer

app = typer.Typer(add_completion=False)
FILE = "gatorgrade.yml"


@app.callback(invoke_without_command=True)
def gatorgrade(
    filename: Path = typer.Option(
        f"{FILE}", "--config", "-c", help="Name of the yml file."
    )
):
    """Runs the GatorGrader checks that are defined
    in the gatorgrade.yml file."""

    if filename.contains(".yml"):
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
    """Generates a gatorgrade.yml file based on the folders and files
    in the current directory."""
    if force is False:
        pass


if __name__ == "__main__":
    app()
