"""Check which functions in gatorgrade are directly tested vs. indirectly tested.

If a function is indirectly covered that means that a test case
calls a function that transitively calls that function. Importantly,
a function that is indirectly tested does not have a test case that
calls it directly and this could be a sign that the function is not
being tested as thoroughly as it should be.

Uses tree-sitter-analyzer (Python API) for language detection and
file analysis, then falls back to raw Tree-sitter for function-definition
extraction and call-graph construction (the installed version of
tree-sitter-analyzer uses a deprecated query.captures() API that
has been removed from modern tree-sitter).

Usage:
    uv run python -m scripts.tsc [OPTIONS]

Options:
    --threshold, -t INT  Minimum percentage of directly tested functions
                         required (default 100).
    --output, -o PATH    Path for the JSON report file (default tsc.json).
    --verbose, --no-verbose
                         Show detailed coverage analysis output (default:
                         no-verbose).

Exit code:
    0 — at least THRESHOLD% of functions are directly tested
    1 — fewer than THRESHOLD% of functions are directly tested

Output:
    Writes a JSON report and prints a color-coded summary to stdout.

"""

import json
from pathlib import Path
from typing import Any

import tree_sitter_python as tspython
import typer
from rich import box
from rich.console import Console
from rich.rule import Rule
from rich.style import Style
from rich.table import Table
from tree_sitter import Language, Node, Parser
from tree_sitter_analyzer.api import (
    detect_language,
    get_supported_languages,
)

PY_LANGUAGE = Language(tspython.language())
CONSOLE = Console()


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

    Handles both bare calls (foo(...)) and dotted calls
    (mod.foo(...), a.b.foo(...)).

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
    function_definition and records the child identifier
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


def find_direct_test_calls(
    test_dir: Path, target_funcs: set[str]
) -> tuple[set[str], dict[str, list[dict[str, Any]]]]:
    """Scan test files for direct calls to any target function.

    Walks the Tree-sitter CST of every test_*.py file, tracking
    the enclosing test-function scope, and records which test function
    calls which target function directly, along with the test's file
    and line-number range.

    Returns a tuple of:
    - set of directly-called function names
    - dict mapping each directly-called function to a list of test
      detail dicts with keys test_name, test_file,
      test_start_line, test_end_line

    """
    directly_called: set[str] = set()
    func_to_test_details: dict[str, list[dict[str, Any]]] = {}
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

        def _walk_scope(
            node: Node,
            current_test: str | None,
            test_start: int | None,
            test_end: int | None,
        ) -> None:
            for child in node.children:
                if child.type == "function_definition":
                    test_name = _get_func_name(child)
                    if test_name and test_name.startswith("test_"):
                        _walk_scope(
                            child,
                            test_name,
                            child.start_point[0] + 1,
                            child.end_point[0] + 1,
                        )
                    else:
                        _walk_scope(child, current_test, test_start, test_end)
                elif child.type == "call" and current_test is not None:
                    for name in _get_call_names(child):
                        if name in target_funcs:
                            directly_called.add(name)
                            detail = {
                                "test_name": current_test,
                                "test_file": str(py_file),
                                "test_start_line": test_start,
                                "test_end_line": test_end,
                            }
                            if name not in func_to_test_details:
                                func_to_test_details[name] = []
                            if detail not in func_to_test_details[name]:
                                func_to_test_details[name].append(detail)
                    _walk_scope(child, current_test, test_start, test_end)
                else:
                    _walk_scope(child, current_test, test_start, test_end)

        _walk_scope(tree.root_node, None, None, None)
    return directly_called, func_to_test_details


def build_call_graph(
    source_dir: Path, target_funcs: set[str]
) -> dict[str, set[str]]:
    """Build a call graph of which source functions call which others.

    Parses every source file and tracks which function body contains
    each call node. Returns a dict mapping each caller to the set
    of callees (functions in target_funcs) it invokes.

    """
    call_graph: dict[str, set[str]] = {f: set() for f in target_funcs}
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

        def _walk_scope(node: Node, current_func: str | None) -> None:
            for child in node.children:
                if child.type == "function_definition":
                    func_name = _get_func_name(child)
                    if func_name and func_name in target_funcs:
                        _walk_scope(child, func_name)
                    else:
                        _walk_scope(child, current_func)
                elif child.type == "call" and current_func is not None:
                    for name in _get_call_names(child):
                        if name in target_funcs and name != current_func:
                            call_graph[current_func].add(name)
                    _walk_scope(child, current_func)
                else:
                    _walk_scope(child, current_func)

        _walk_scope(tree.root_node, None)
    return call_graph


def compute_coverage_status(
    all_functions: dict[str, dict[str, Any]],
    directly_tested: set[str],
    call_graph: dict[str, set[str]],
) -> dict[str, str]:
    """Determine test status for every function.

    Returns a dict mapping each function name to one of:
    - "direct" — called directly by at least one test
    - "indirect" — not called directly, but reachable via the
      call graph from a directly-tested function
    - "none" — no test coverage (direct or indirect)

    """
    status: dict[str, str] = {}
    for name in all_functions:
        status[name] = "direct" if name in directly_tested else "unknown"
    # BFS through the call graph starting from directly-tested functions
    queue = list(directly_tested)
    while queue:
        caller = queue.pop(0)
        for callee in call_graph.get(caller, []):
            if status[callee] == "unknown":
                status[callee] = "indirect"
                queue.append(callee)
    # remaining unknown functions have no coverage at all
    for name in all_functions:
        if status[name] == "unknown":
            status[name] = "none"
    return status


def compute_indirect_paths(
    call_graph: dict[str, set[str]],
    directly_tested: set[str],
    func_to_test_details: dict[str, list[dict[str, Any]]],
    all_functions: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Find every call chain from a test to each indirectly-tested function.

    For each directly-tested function, performs a BFS through the call
    graph.  Whenever a function not in *directly_tested* is reached, a
    path entry is recorded showing which test invoked it, through
    which chain of production-function calls, and the file/line
    location of every step.

    Returns a dict mapping each indirectly-tested function to a list
    of path entries, each with test and chain keys.  Every
    chain element contains name, file, start_line, and
    end_line.

    """
    indirect_info: dict[str, list[dict[str, Any]]] = {}
    for func in sorted(directly_tested):
        for test_detail in func_to_test_details.get(func, []):
            queue: list[tuple[str, list[str]]] = [(func, [func])]
            visited: set[str] = {func}
            while queue:
                current, path = queue.pop(0)
                for callee in sorted(call_graph.get(current, set())):
                    if callee not in visited and callee not in directly_tested:
                        new_path = [*path, callee]
                        if callee not in indirect_info:
                            indirect_info[callee] = []
                        chain = [
                            {
                                "name": fn,
                                "file": all_functions.get(fn, {}).get(
                                    "file", ""
                                ),
                                "start_line": all_functions.get(fn, {}).get(
                                    "line", 0
                                ),
                                "end_line": all_functions.get(fn, {}).get(
                                    "end_line", 0
                                ),
                            }
                            for fn in new_path
                        ]
                        indirect_info[callee].append(
                            {
                                "test": {
                                    "name": test_detail["test_name"],
                                    "file": test_detail["test_file"],
                                    "start_line": test_detail[
                                        "test_start_line"
                                    ],
                                    "end_line": test_detail["test_end_line"],
                                },
                                "chain": chain,
                            }
                        )
                        visited.add(callee)
                        queue.append((callee, new_path))
    return indirect_info


def classify_and_report(
    all_functions: dict[str, dict[str, Any]],
    directly_tested: set[str],
    call_graph: dict[str, set[str]],
    func_to_test_details: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Build the coverage report."""
    coverage = compute_coverage_status(
        all_functions, directly_tested, call_graph
    )
    indirect_paths = compute_indirect_paths(
        call_graph,
        directly_tested,
        func_to_test_details,
        all_functions,
    )
    report: dict[str, Any] = {
        "functions": {},
        "summary": {
            "total": 0,
            "directly_tested": 0,
            "indirectly_tested": 0,
            "untested": 0,
        },
        "indirectly_tested_list": [],
        "directly_tested_list": [],
        "untested_list": [],
    }
    for name, info in sorted(all_functions.items()):
        entry: dict[str, Any] = {
            **info,
            "test_status": coverage[name],
            "directly_tested": coverage[name] == "direct",
        }
        report["functions"][name] = entry
        if coverage[name] == "direct":
            test_details = func_to_test_details.get(name, [])
            report["directly_tested_list"].append(
                {
                    "name": name,
                    **info,
                    "direct_calls_by_tests": test_details,
                }
            )
        elif coverage[name] == "indirect":
            paths = indirect_paths.get(name, [])
            report["indirectly_tested_list"].append(
                {"name": name, **info, "indirect_paths": paths}
            )
        elif coverage[name] == "none":
            report["untested_list"].append({"name": name, **info})
    s = report["summary"]
    s["total"] = len(all_functions)
    s["directly_tested"] = sum(
        1 for v in report["functions"].values() if v["directly_tested"]
    )
    s["indirectly_tested"] = sum(
        1
        for v in report["functions"].values()
        if v["test_status"] == "indirect"
    )
    s["untested"] = sum(
        1 for v in report["functions"].values() if v["test_status"] == "none"
    )
    return report


def print_summary(report: dict[str, Any]) -> None:
    """Print a human-readable summary using rich formatting."""
    s = report["summary"]
    table = Table(
        title="Function Coverage Summary",
        box=box.SIMPLE,
        title_style=Style(bold=True),
        header_style=Style(bold=True),
    )
    table.add_column("Status", style="bold")
    table.add_column("Count", justify="right")
    table.add_column("Percent", justify="right")
    total = s["total"] or 1
    table.add_row(
        "Directly tested",
        str(s["directly_tested"]),
        f"{s['directly_tested'] / total * 100:.1f}%",
    )
    table.add_row(
        "Indirectly tested only",
        str(s["indirectly_tested"]),
        f"{s['indirectly_tested'] / total * 100:.1f}%",
    )
    table.add_row(
        "Untested",
        str(s["untested"]),
        f"{s['untested'] / total * 100:.1f}%",
    )
    CONSOLE.print(table)
    if report["indirectly_tested_list"]:
        CONSOLE.print(Rule("Indirectly Tested Functions", style="yellow"))
        CONSOLE.print()
        for entry in report["indirectly_tested_list"]:
            CONSOLE.print(
                f"  {entry['name']}  ({entry['file']}:{entry['line']})"
            )
    if report["untested_list"]:
        CONSOLE.print()
        CONSOLE.print(Rule("Not Tested Functions", style="red"))
        CONSOLE.print()
        for entry in report["untested_list"]:
            CONSOLE.print(
                f"  {entry['name']}  ({entry['file']}:{entry['line']})"
            )


def demo_api() -> list[str]:
    """Demonstrate the tree-sitter-analyzer Python API and return lines."""
    lines: list[str] = []
    langs = get_supported_languages()
    lines.append(f"tree-sitter-analyzer supports {len(langs)} languages.")
    py_ext = "gatorgrade/output/output.py"
    detected = detect_language(py_ext)
    lines.append(f"  detect_language('{py_ext}') -> {detected}")
    return lines


def main(  # noqa: PLR0915
    threshold: int = typer.Option(
        100,
        "--threshold",
        "-t",
        help="Minimum percentage of directly tested functions required.",
    ),
    output: Path = typer.Option(
        "tsc.json",
        "--output",
        "-o",
        help="Path for the JSON report file.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose/--no-verbose",
        help="Show detailed coverage analysis output.",
    ),
) -> None:
    """Run the coverage analysis and check against a direct-test threshold."""
    project_root = Path(__file__).resolve().parent.parent
    source_dir = project_root / "gatorgrade"
    test_dir = project_root / "tests"
    report_path = Path(output)
    if not report_path.is_absolute():
        report_path = project_root / report_path
    # Analysis phase
    analysis_lines: list[str] = []
    for line in demo_api():
        analysis_lines.append(line)
    analysis_lines.append("")
    analysis_lines.append(
        "Extracting function definitions via Tree-sitter ..."
    )
    all_functions = find_function_definitions(source_dir)
    target_funcs = set(all_functions.keys())
    analysis_lines.append(f"  Found {len(all_functions)} functions.")
    analysis_lines.append("")
    analysis_lines.append("Searching for direct calls in test files ...")
    directly_tested, func_to_test_details = find_direct_test_calls(
        test_dir, target_funcs
    )
    analysis_lines.append(
        f"  Found {len(directly_tested)} directly-tested functions."
    )
    analysis_lines.append("")
    analysis_lines.append("Building internal call graph ...")
    call_graph = build_call_graph(source_dir, target_funcs)
    total_edges = sum(len(v) for v in call_graph.values())
    analysis_lines.append(f"  Found {total_edges} internal call edges.")
    analysis_lines.append("")
    analysis_lines.append(f"Report written to {report_path}")
    if verbose:
        CONSOLE.print()
        CONSOLE.print(Rule("Coverage Analysis", style="blue"))
        CONSOLE.print()
        for line in analysis_lines:
            CONSOLE.print(line)
    # Build report
    report = classify_and_report(
        all_functions,
        directly_tested,
        call_graph,
        func_to_test_details,
    )
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if verbose:
        CONSOLE.print()
        CONSOLE.print(Rule("Coverage Results", style="dim"))
        CONSOLE.print()
        print_summary(report)
        CONSOLE.print()
    # threshold check
    s = report["summary"]
    total = s["total"]
    direct_count = s["directly_tested"]
    pct = (direct_count / total * 100) if total > 0 else 100.0
    if pct < threshold:
        if verbose:
            CONSOLE.print()
        CONSOLE.print(Rule("Failure", style="red"))
        CONSOLE.print()
        CONSOLE.print(
            f"Only {pct:.1f}% of functions are directly tested "
            f"(threshold: {threshold}%)."
        )
        if not verbose:
            for entry in report["indirectly_tested_list"]:
                CONSOLE.print(
                    f"  {entry['name']}  ({entry['file']}:{entry['line']})"
                )
            for entry in report["untested_list"]:
                CONSOLE.print(
                    f"  {entry['name']}  ({entry['file']}:{entry['line']})"
                )
        raise typer.Exit(code=1)
    if verbose:
        CONSOLE.print()
        CONSOLE.print(Rule("Pass", style="green"))
        CONSOLE.print(
            f"All functions have sufficient direct test coverage "
            f"({pct:.1f}% >= {threshold}%)."
        )


if __name__ == "__main__":
    typer.run(main)
