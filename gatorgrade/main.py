import typer

app = typer.Typer(add_completion=False)
file = "gatorgrade.yml"


@app.callback(invoke_without_command=True)
def foo(file):
    """Runs the GatorGrader checks that are defined in the gatorgrade.yml file."""


@app.command()
def generate(force: bool = False):
    """Generates a gatorgrade.yml file based on the folers/files in the current directory."""
    if (force == False) & (file.exists == True):
        print("A gatorgrade.yml file already exists.")


if __name__ == "__main__":
    app()
