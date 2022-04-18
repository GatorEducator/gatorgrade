import typer
"""The useage of typer to properly run gatorgrade by running the checks and generating the yml file."""

app = typer.Typer(add_completion=False)
FILE = "gatorgrade.yml"


@app.callback(invoke_without_command=True)
def gatorgrade():
    """Runs the GatorGrader checks that are defined in the gatorgrade.yml file."""


@app.command()
def generate(force: bool = typer.Option(False, "--force", "-f")):
    """Generates a gatorgrade.yml file based on the folers/files in the current directory."""


if __name__ == "__main__":
    app()
