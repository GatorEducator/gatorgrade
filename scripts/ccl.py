"""Check that Python comments start with a lowercase letter.

Uses Tree-sitter to parse Python files into a Concrete Syntax Tree,
which preserves comment nodes that are stripped by AST parsers.

Exceptions are made for proper nouns (GatorGrader, GitHub, etc.)
and identifiers that must start with a capital letter (GITHUB_ENV).

Run with:
uv run -m scripts.ccl check
uv run -m scripts.ccl fix
uv run task comments
"""

from pathlib import Path

import tree_sitter_python as tspython
import typer
from rich.console import Console
from rich.panel import Panel
from tree_sitter import Language, Node, Parser

PROPER_NOUNS = frozenset(
    {
        "CountCommits",
        "GatorGrade",
        "GatorGrader",
        "GatorGraderCheck",
        "GITHUB_ENV",
        "GITHUB_STEP_SUMMARY",
        "JSON",
        "MatchFileFragment",
        "ShellCheck",
        "STDOUT",
        "STDERR",
        "TODO",
        "FIXME",
        "NOTE",
    }
)

PY_LANGUAGE = Language(tspython.language())

DEFAULT_DIRS = ["gatorgrade", "tests", "scripts"]

console = Console(stderr=True)
err_console = Console(stderr=True)

app = typer.Typer(
    name="ccl",
    help="Check that Python comments start with a lowercase letter.",
)


class CommentError:
    """Represent a comment that starts with an uppercase letter."""

    def __init__(self, filepath: Path, line: int, col: int, text: str) -> None:
        """Construct a CommentError with file location and text."""
        self.filepath = filepath
        self.line = line
        self.col = col
        self.text = text

    def __str__(self) -> str:
        """Return a string representation of the error."""
        return (
            f"{self.filepath}:{self.line}:{self.col}: "
            f"comment-starts-with-uppercase"
        )


def _find_errors(filepath: Path, parser: Parser) -> list[CommentError]:
    """Find comment-case errors in a Python file.

    Walks the Tree-sitter CST looking for comment nodes, then checks
    whether each non-empty comment starts with a lowercase letter
    (allowing proper nouns).

    """
    errors = []
    source = filepath.read_bytes()
    tree = parser.parse(source)

    def walk(node: Node) -> None:
        if node.type == "comment":
            node_text = node.text
            if node_text is None:
                return
            text = node_text.decode("utf-8")
            content = text.lstrip("#").lstrip()
            if content and content[0].isupper():
                first_word = content.split()[0].rstrip(",:;.!?")
                if first_word not in PROPER_NOUNS:
                    line = node.start_point[0] + 1
                    col = node.start_point[1] + 1
                    errors.append(
                        CommentError(filepath, line, col, text.strip())
                    )
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return errors


def _scan_files(
    paths: list[Path] | None = None,
) -> tuple[list[Path], list[CommentError]]:
    """Scan Python files for comment-case errors.

    Finds all .py files under the given paths (or the
    default directories gatorgrade/, tests/, scripts/),
    then checks each one for comments that start with
    an uppercase letter.

    Returns a tuple of (all_matched_files, errors_found).

    """
    parser = Parser(PY_LANGUAGE)
    root = Path(".")
    if paths:
        py_files = sorted(
            f
            for p in paths
            for f in (p.glob("**/*.py") if p.is_dir() else [p])
            if "__pycache__" not in str(f)
        )
    else:
        py_files = sorted(
            f
            for d in DEFAULT_DIRS
            for f in root.glob(f"{d}/**/*.py")
            if "__pycache__" not in str(f)
        )
    all_errors = []
    for py_file in py_files:
        all_errors.extend(_find_errors(py_file, parser))
    return py_files, all_errors


@app.command()
def check(
    paths: list[Path] | None = typer.Argument(
        None,
        help="Paths to scan. Defaults to gatorgrade/, tests/, and scripts/.",
    ),
) -> None:
    """Check that comments start with a lowercase letter."""
    py_files, errors = _scan_files(paths)
    if not errors:
        console.print(
            "[green]All comments start with lowercase "
            "(or are proper nouns).[/green]"
        )
        raise typer.Exit(code=0)
    err_console.print(
        f"[red]Found {len(errors)} error(s)[/red] "
        f"across {len(py_files)} file(s).\n"
    )
    for error in errors:
        err_console.print(
            f"[bold]{error.filepath}[/bold]:{error.line}:{error.col} "
            f"[red]comment-starts-with-uppercase[/red]"
        )
        err_console.print(f"  {error.text}")
        fixed = _fix_comment_text(error.text)
        err_console.print(f"  [green]{fixed}[/green]\n")
    err_console.print(
        Panel(
            f"[bold]Summary:[/bold] {len(errors)} comment(s) "
            f"starting with uppercase found.\n"
            f"Run [bold]uv run -m scripts.ccl fix[/bold] to auto-fix.",
            title="[bold]Check Comments[/bold]",
            border_style="red",
        )
    )
    raise typer.Exit(code=1)


def _fix_comment_text(text: str) -> str:
    """Fix a comment line by lowercasing the first letter."""
    stripped = text.lstrip()
    hash_prefix = text[: len(text) - len(stripped)]
    content = stripped.lstrip("#").lstrip()
    if content and content[0].isupper():
        first_word = content.split()[0].rstrip(",:;.!?")
        if first_word not in PROPER_NOUNS:
            content = content[0].lower() + content[1:]
    return f"{hash_prefix}# {content}"


@app.command()
def fix(
    paths: list[Path] | None = typer.Argument(
        None,
        help="Paths to fix. Defaults to gatorgrade/, tests/, and scripts/.",
    ),
) -> None:
    """Auto-fix comments that start with an uppercase letter."""
    root = Path(".")
    if paths:
        py_files = sorted(
            f
            for p in paths
            for f in (p.glob("**/*.py") if p.is_dir() else [p])
            if "__pycache__" not in str(f)
        )
    else:
        py_files = sorted(
            f
            for d in DEFAULT_DIRS
            for f in root.glob(f"{d}/**/*.py")
            if "__pycache__" not in str(f)
        )
    total_fixed = 0
    files_fixed = 0
    for py_file in py_files:
        lines = py_file.read_text(encoding="utf-8").splitlines()
        new_lines = []
        file_changed = False
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith("#"):
                content = stripped.lstrip("#").lstrip()
                if content and content[0].isupper():
                    first_word = content.split()[0].rstrip(",:;.!?")
                    if first_word not in PROPER_NOUNS:
                        indent = line[: len(line) - len(stripped)]
                        new_content = content[0].lower() + content[1:]
                        new_line = f"{indent}# {new_content}"
                        new_lines.append(new_line)
                        file_changed = True
                        total_fixed += 1
                        continue
            new_lines.append(line)
        if file_changed:
            py_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            files_fixed += 1
            console.print(f"[green]Fixed[/green] {py_file}")
    if total_fixed == 0:
        console.print(
            "[green]All comments already start with lowercase "
            "(or are proper nouns).[/green]"
        )
    else:
        console.print(
            f"\n[bold green]Fixed {total_fixed} comment(s) "
            f"in {files_fixed} file(s).[/bold green]"
        )
    raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
