import typer
from pathlib import Path

app = typer.Typer(add_completion=False)
FILE_DIR = "config"
FILE = "gatorgrade.yml"


@app.callback(invoke_without_command=True)
def gatorgrade(file_dir: Path = typer.Option(f"{FILE_DIR}/{FILE}")):
    """Runs the GatorGrader checks that are defined in the gatorgrade.yml file."""


@app.command()
def generate(force: bool = typer.Option(False, "--force", "-f")):
    """Generates a gatorgrade.yml file based on the folers/files in the current directory."""


if __name__ == "__main__":
    app()
