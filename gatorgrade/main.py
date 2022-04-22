"""Use Typer to run gatorgrade to run the checks and generate the yml file."""
import typer
from pathlib import Path

app = typer.Typer(add_completion=False)
FILE = "gatorgrade.yml"


@app.callback(invoke_without_command=True)
def gatorgrade(
    filepath: Path = typer.Option(
        f"{FILE}", "--config", "-c", help="Filepath to the yml file."
    )
):
    """Runs the GatorGrader checks that are defined in the gatorgrade.yml file."""


@app.command()
def generate(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force gatorgrade to overwrite an existing yml file.",
    )
):
    """Generates a gatorgrade.yml file based on the folders and files in the current directory."""


if __name__ == "__main__":
    app()
