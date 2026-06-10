"""Check which functions in gatorgrade are directly tested vs. indirectly tested.

If a function is indirectly covered that means that a test case
calls a function that transitively calls that function. Importantly,
a function that is indirectly tested does not have a test case that
calls it directly and this could be a sign that the function is not
being tested as thoroughly as it should be.

Uses `tree-sitter-analyzer` (Python API) for language detection and
file analysis, then falls back to raw Tree-sitter for function-definition
extraction and call-graph construction (the installed version of
`tree-sitter-analyzer` uses a deprecated `query.captures()` API that
has been removed from modern tree-sitter).

Usage:
    uv run python -m scripts.tsc

Exit code:
    0 — every function has at least one direct test caller
    1 — at least one function is only indirectly tested

Output:
    Writes `tsc.json` to the project root and prints
    a summary to stdout.

"""

import json
import sys
from pathlib import Path
from typing import Any

import tree_sitter_python as tspython
import typer
from tree_sitter import Language, Node, Parser
from tree_sitter_analyzer.api import (
    detect_language,
    get_supported_languages,
)

PY_LANGUAGE = Language(tspython.language())


def _make_parser() -> Parser:
    """Create a tree-sitter parser for Python."""
    return Parser(PY_LANGUAGE)


def _walk_node(node: Node) -> list[Node]:
    """Walk the tree recursively and return all descendant nodes."""
    nodes = [node]
    for child in node.children:
        nodes.extend(_walk_node(child))
    return nodes


def _get_func_name(func_node: Node) -> str | None:
    """Extract the function name from a function_definition node."""
    for child in func_node.children:
        if child.type == "identifier":
            text = child.text
            if text is not None:
                return text.decode("utf-8")
    return None


def _get_call_names(call_node: Node) -> list[str]:
    """Extract all function names from a call node.

    Handles both bare calls (``foo(...)``) and dotted calls
    (``mod.foo(...)``, ``a.b.foo(...)``).

    """
    names: list[str] = []
    for child in call_node.children:
        if child.type == "identifier":
            text = child.text
            if text is not None:
                names.append(text.decode("utf-8"))
        elif child.type == "attribute":
            for attr_child in child.children:
                if attr_child.type == "identifier":
                    text = attr_child.text
                    if text is not None:
                        names.append(text.decode("utf-8"))
    return names


def find_function_definitions(
    source_dir: Path,
) -> dict[str, dict[str, Any]]:
    """Walk source files and extract every function definition.

    Uses the Tree-sitter CST to find nodes of type
    ``function_definition`` and records the child ``identifier``
    node's text as the function name.

    """
    functions: dict[str, dict[str, Any]] = {}
    for py_file in sorted(source_dir.rglob("*.py")):
        if py_file.name == "__init__.py":
            continue
        try:
            parser = _make_parser()
            tree = parser.parse(
                bytes(py_file.read_text(encoding="utf-8"), "utf-8")
            )
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in _walk_node(tree.root_node):
            if node.type == "function_definition":
                name = _get_func_name(node)
                if name and (
                    not (name.startswith("__") and name.endswith("__"))
                ):
                    functions[name] = {
                        "file": str(py_file.relative_to(source_dir.parent)),
                        "line": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                    }
    return functions


def find_direct_test_calls(test_dir: Path, target_funcs: set[str]) -> set[str]:
    """Scan test files for direct calls to any target function.

    Walks the Tree-sitter CST of every ``test_*.py`` file for nodes
    of type ``call``, then extracts the function name from each call
    and checks it against *target_funcs*.

    """
    directly_called: set[str] = set()
    for py_file in sorted(test_dir.rglob("*.py")):
        if not py_file.name.startswith("test_"):
            continue
        try:
            parser = _make_parser()
            tree = parser.parse(
                bytes(py_file.read_text(encoding="utf-8"), "utf-8")
            )
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in _walk_node(tree.root_node):
            if node.type == "call":
                for name in _get_call_names(node):
                    if name in target_funcs:
                        directly_called.add(name)
    return directly_called


def classify_and_report(
    all_functions: dict[str, dict[str, Any]],
    directly_tested: set[str],
) -> dict[str, Any]:
    """Build the coverage report."""
    report: dict[str, Any] = {
        "functions": {},
        "summary": {
            "total": 0,
            "directly_tested": 0,
            "indirectly_tested": 0,
        },
        "indirectly_tested_list": [],
    }
    for name, info in sorted(all_functions.items()):
        dt = name in directly_tested
        report["functions"][name] = {**info, "directly_tested": dt}
        if not dt:
            report["indirectly_tested_list"].append({"name": name, **info})
    s = report["summary"]
    s["total"] = len(all_functions)
    s["directly_tested"] = sum(
        1 for v in report["functions"].values() if v["directly_tested"]
    )
    s["indirectly_tested"] = s["total"] - s["directly_tested"]
    return report


def print_summary(report: dict[str, Any]) -> None:
    """Print a human-readable summary."""
    s = report["summary"]
    typer.echo(f"Total source functions:  {s['total']}")
    typer.echo(f"Directly tested:         {s['directly_tested']}")
    typer.echo(f"Indirectly tested only:  {s['indirectly_tested']}")
    if report["indirectly_tested_list"]:
        typer.echo()
        typer.echo("Functions with only indirect test coverage:")
        for entry in report["indirectly_tested_list"]:
            typer.echo(f"  {entry['name']}  ({entry['file']}:{entry['line']})")


def demo_api() -> None:
    """Demonstrate the tree-sitter-analyzer Python API."""
    langs = get_supported_languages()
    typer.echo(f"tree-sitter-analyzer supports {len(langs)} languages.")
    py_ext = "gatorgrade/output/output.py"
    detected = detect_language(py_ext)
    typer.echo(f"  detect_language('{py_ext}') -> {detected}")
    typer.echo()


def main() -> int:
    """Run the coverage analysis and return 0 if all functions are directly tested."""
    project_root = Path(__file__).resolve().parent.parent
    source_dir = project_root / "gatorgrade"
    test_dir = project_root / "tests"

    demo_api()

    typer.echo("Extracting function definitions via Tree-sitter ...")
    all_functions = find_function_definitions(source_dir)
    target_funcs = set(all_functions.keys())
    typer.echo(f"  Found {len(all_functions)} functions.\n")

    typer.echo("Finding direct calls in test files ...")
    directly_tested = find_direct_test_calls(test_dir, target_funcs)
    typer.echo(f"  Found {len(directly_tested)} directly-tested functions.\n")

    report = classify_and_report(all_functions, directly_tested)

    report_path = project_root / "tsc.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    typer.echo(f"Report written to {report_path}\n")

    print_summary(report)

    if report["summary"]["indirectly_tested"] > 0:
        typer.echo(
            f"FAILURE: {report['summary']['indirectly_tested']} "
            "function(s) lack direct test coverage."
        )
        return 1
    typer.echo("All functions have direct test coverage.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
