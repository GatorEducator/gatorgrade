"""Check that the GatorGrade version in main.py matches the version in pyproject.toml.

Uses Tree-sitter to parse gatorgrade/main.py into a Concrete Syntax Tree
to extract the GATORGRADE_VERSION constant, and uses the toml library to
read the project version from pyproject.toml. Exits with code 0 when the
two versions match, and code 1 when they differ.

Run with:
uv run -m scripts.vsc check
uv run -m scripts.vsc fix
uv run task vsc
"""

from pathlib import Path

import toml
import tree_sitter_python as tspython
import typer
from rich.console import Console
from tree_sitter import Language, Node, Parser

VERSION_VAR = "GATORGRADE_VERSION"
PY_LANGUAGE = Language(tspython.language())

console = Console(stderr=False)
err_console = Console(stderr=True)

app = typer.Typer(
    name="version-check",
    help=(
        "Check that the GATORGRADE_VERSION in main.py matches the "
        "project version in pyproject.toml."
    ),
)


def _extract_version_from_main(main_path: Path, parser: Parser) -> str | None:
    """Return the string assigned to GATORGRADE_VERSION in main_path, or None."""
    source = main_path.read_bytes()
    tree = parser.parse(source)
    found: list[str] = []

    def walk(node: Node) -> None:
        MIN_CHILDREN = 3
        if (
            node.type == "assignment"
            and len(node.children) >= MIN_CHILDREN
            and node.children[0].type == "identifier"
            and node.children[0].text is not None
            and node.children[0].text.decode("utf-8") == VERSION_VAR
            and node.children[2].type == "string"
            and node.children[2].text is not None
        ):
            raw = node.children[2].text.decode("utf-8")
            found.append(_unquote_string(raw))
            return
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return found[0] if found else None


def _unquote_string(raw: str) -> str:
    """Strip matching single or double quotes from a Python string literal."""
    MIN_ROWS = 2
    if len(raw) >= MIN_ROWS and raw[0] == raw[-1] and raw[0] in ("'", '"'):
        return raw[1:-1]
    return raw


def _extract_version_from_pyproject(pyproject_path: Path) -> str | None:
    """Return the project version from pyproject.toml, or None if missing."""
    data = toml.loads(pyproject_path.read_text(encoding="utf-8"))
    project = data.get("project", {})
    version = project.get("version")
    return str(version) if version is not None else None


@app.command()
def check() -> None:
    """Check that the versions in main.py and pyproject.toml match."""
    main_path = Path("gatorgrade/main.py")
    pyproject_path = Path("pyproject.toml")
    parser = Parser(PY_LANGUAGE)
    main_version = _extract_version_from_main(main_path, parser)
    pyproject_version = _extract_version_from_pyproject(pyproject_path)
    if main_version is None:
        err_console.print(
            f"[red]Could not find {VERSION_VAR} in {main_path}[/red]"
        )
        raise typer.Exit(code=1)
    if pyproject_version is None:
        err_console.print(
            f"[red]Could not find project version in {pyproject_path}[/red]"
        )
        raise typer.Exit(code=1)
    if main_version == pyproject_version:
        console.print(f"[green]Versions match:[/green] {main_version}")
        raise typer.Exit(code=0)
    err_console.print(
        f"[red]Version mismatch:[/red] "
        f"{VERSION_VAR}={main_version!r} in {main_path} "
        f"vs version={pyproject_version!r} in {pyproject_path}"
    )
    raise typer.Exit(code=1)


def _update_version_in_main(main_path: Path, new_version: str) -> bool:
    """Update the GATORGRADE_VERSION string in main_path. Return True if changed."""
    text = main_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    changed = False
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith(f"{VERSION_VAR} ="):
            prefix = line[: len(line) - len(stripped)]
            lines[index] = f'{prefix}{VERSION_VAR} = "{new_version}"\n'
            changed = True
            break
    if changed:
        main_path.write_text("".join(lines), encoding="utf-8")
    return changed


@app.command()
def fix() -> None:
    """Update main.py so GATORGRADE_VERSION matches the pyproject.toml version."""
    main_path = Path("gatorgrade/main.py")
    pyproject_path = Path("pyproject.toml")
    pyproject_version = _extract_version_from_pyproject(pyproject_path)
    if pyproject_version is None:
        err_console.print(
            f"[red]Could not find project version in {pyproject_path}[/red]"
        )
        raise typer.Exit(code=1)
    parser = Parser(PY_LANGUAGE)
    main_version = _extract_version_from_main(main_path, parser)
    if main_version == pyproject_version:
        console.print(f"[green]Versions already match:[/green] {main_version}")
        raise typer.Exit(code=0)
    if main_version is None:
        err_console.print(
            f"[red]Could not find {VERSION_VAR} in {main_path}[/red]"
        )
        raise typer.Exit(code=1)
    if _update_version_in_main(main_path, pyproject_version):
        console.print(
            f"[green]Updated[/green] {VERSION_VAR} in {main_path} "
            f"from {main_version!r} to {pyproject_version!r}"
        )
        raise typer.Exit(code=0)
    err_console.print(
        f"[red]Could not update {VERSION_VAR} in {main_path}[/red]"
    )
    raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
