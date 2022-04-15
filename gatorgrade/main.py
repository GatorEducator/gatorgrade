import typer

app = typer.Typer()
file = "gatorgrade.yml"


@app.command()
def generate(force: bool = False):
    """Generates a gatorgrade.yml file based on the folers/files in the current directory."""
    if (force == False) & (file.exists == True):
        print("A gatorgrade.yml file already exists.")


if __name__ == "__main__":
    app()
