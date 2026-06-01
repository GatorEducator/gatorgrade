"""Tests for the scripts.ccl module."""

import re
from pathlib import Path

import pytest
import tree_sitter_python as tspython
from tree_sitter import Language, Parser
from typer.testing import CliRunner

from scripts.ccl import (
    PROPER_NOUNS,
    CommentError,
    _find_errors,
    _fix_comment_text,
    _scan_files,
    app,
)

PY_LANGUAGE = Language(tspython.language())

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text so substring checks are robust."""
    return ANSI_ESCAPE_RE.sub("", text)


def _make_parser() -> Parser:
    """Create a fresh Tree-sitter parser for Python."""
    return Parser(PY_LANGUAGE)


def _write_py(tmp_path: Path, name: str, content: str) -> Path:
    """Write a Python file with the given content and return its path."""
    filepath = tmp_path / name
    filepath.write_text(content, encoding="utf-8")
    return filepath


def test_comment_error_str_includes_location_and_message() -> None:
    """Format the error as filepath:line:col: comment-starts-with-uppercase."""
    error = CommentError(Path("a.py"), 3, 5, "# Bad comment")
    assert str(error) == "a.py:3:5: comment-starts-with-uppercase"


def test_comment_error_stores_all_fields() -> None:
    """Store filepath, line, col, and text on the CommentError instance."""
    error = CommentError(Path("a.py"), 1, 2, "# Hello")
    assert error.filepath == Path("a.py")
    assert error.line == 1
    assert error.col == 2  # noqa: PLR2004
    assert error.text == "# Hello"


def test_find_errors_returns_empty_for_lowercase_comments(
    tmp_path: Path,
) -> None:
    """Return no errors when every comment starts with a lowercase letter."""
    py_file = _write_py(tmp_path, "good.py", "# this is fine\nx = 1\n")
    assert _find_errors(py_file, _make_parser()) == []


def test_find_errors_reports_uppercase_comment(
    tmp_path: Path,
) -> None:
    """Report a single error for a comment starting with an uppercase letter."""
    py_file = _write_py(tmp_path, "bad.py", "# Bad comment\nx = 1\n")
    errors = _find_errors(py_file, _make_parser())
    assert len(errors) == 1
    assert errors[0].filepath == py_file
    assert errors[0].line == 1
    assert errors[0].col == 1
    assert errors[0].text == "# Bad comment"


def test_find_errors_allows_proper_noun(tmp_path: Path) -> None:
    """Skip comments whose first word is a known proper noun."""
    py_file = _write_py(tmp_path, "ok.py", "# GatorGrader is cool\n")
    assert _find_errors(py_file, _make_parser()) == []


def test_find_errors_allows_github_env(tmp_path: Path) -> None:
    """Skip comments starting with the GITHUB_ENV identifier."""
    py_file = _write_py(tmp_path, "ok.py", "# GITHUB_ENV is set by Actions\n")
    assert _find_errors(py_file, _make_parser()) == []


def test_find_errors_handles_indented_comment(
    tmp_path: Path,
) -> None:
    """Detect uppercase comments that are indented in a function body."""
    py_file = _write_py(
        tmp_path,
        "indented.py",
        "def f() -> None:\n    # Indented bad comment\n    return None\n",
    )
    errors = _find_errors(py_file, _make_parser())
    assert len(errors) == 1
    assert errors[0].line == 2  # noqa: PLR2004


def test_find_errors_handles_multiple_comments(
    tmp_path: Path,
) -> None:
    """Collect one error per offending comment across the file."""
    py_file = _write_py(
        tmp_path,
        "many.py",
        "# First bad\nx = 1\n# good line\n# Second bad\n",
    )
    errors = _find_errors(py_file, _make_parser())
    assert len(errors) == 2  # noqa: PLR2004
    assert errors[0].line == 1
    assert errors[1].line == 4  # noqa: PLR2004


def test_find_errors_strips_trailing_punctuation_before_checking_noun(
    tmp_path: Path,
) -> None:
    """Treat 'GatorGrader,' as the proper noun GatorGrader."""
    py_file = _write_py(tmp_path, "ok.py", "# GatorGrader, is cool.\n")
    assert _find_errors(py_file, _make_parser()) == []


def test_find_errors_skips_empty_comment(tmp_path: Path) -> None:
    """Not report an error for a comment that is just a hash with no content."""
    py_file = _write_py(tmp_path, "empty.py", "#\n#\n")
    assert _find_errors(py_file, _make_parser()) == []


def test_find_errors_skips_comment_starting_with_digit(
    tmp_path: Path,
) -> None:
    """Not report an error for a comment whose first content character is a digit."""
    py_file = _write_py(tmp_path, "digit.py", "# 1 thing\n")
    assert _find_errors(py_file, _make_parser()) == []


def test_scan_files_with_explicit_paths(
    tmp_path: Path,
) -> None:
    """Scan only the explicitly provided paths and return the files scanned."""
    good = _write_py(tmp_path, "good.py", "# fine\n")
    bad = _write_py(tmp_path, "bad.py", "# Bad\n")
    files, errors = _scan_files([bad, good])
    assert files == [bad, good]
    assert len(errors) == 1
    assert errors[0].filepath == bad


def test_scan_files_skips_pycache(tmp_path: Path) -> None:
    """Filter out __pycache__ directories from the default glob."""
    cache_dir = tmp_path / "gatorgrade" / "__pycache__"
    cache_dir.mkdir(parents=True)
    _write_py(cache_dir, "ignored.py", "# Bad\n")
    live = tmp_path / "gatorgrade"
    live.mkdir(parents=True, exist_ok=True)
    _write_py(live, "good.py", "# fine\n")
    monkeypatch_cwd = pytest.MonkeyPatch()
    monkeypatch_cwd.chdir(tmp_path)
    try:
        files, _ = _scan_files()
    finally:
        monkeypatch_cwd.undo()
    assert all("__pycache__" not in str(f) for f in files)


def test_scan_files_uses_default_glob_when_no_paths(
    tmp_path: Path,
) -> None:
    """Fall back to gatorgrade/ and tests/ globs when no paths are given."""
    gator_dir = tmp_path / "gatorgrade"
    gator_dir.mkdir()
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    _write_py(gator_dir, "mod.py", "# fine\n")
    _write_py(tests_dir, "test_x.py", "# Bad\n")
    monkeypatch_cwd = pytest.MonkeyPatch()
    monkeypatch_cwd.chdir(tmp_path)
    try:
        files, errors = _scan_files()
    finally:
        monkeypatch_cwd.undo()
    assert len(files) == 2  # noqa: PLR2004
    assert len(errors) == 1
    assert errors[0].filepath.name == "test_x.py"


def test_fix_comment_text_lowercases_first_letter() -> None:
    """Lowercase the first letter of a comment that starts with an uppercase word."""
    assert _fix_comment_text("# Bad comment") == "# bad comment"


def test_fix_comment_text_keeps_proper_noun_unchanged() -> None:
    """Leave a comment that starts with a proper noun unchanged."""
    assert (
        _fix_comment_text("# GatorGrader is cool") == "# GatorGrader is cool"
    )


def test_fix_comment_text_preserves_leading_whitespace() -> None:
    """Preserve leading whitespace and the single hash followed by a space."""
    assert _fix_comment_text("    # Bad") == "    # bad"


def test_fix_comment_text_handles_already_lowercase() -> None:
    """Return the comment unchanged when it already starts with a lowercase letter."""
    assert _fix_comment_text("# fine") == "# fine"


def test_fix_comment_text_handles_empty_comment() -> None:
    """Return an empty comment unchanged."""
    assert _fix_comment_text("#") == "# "


def test_fix_comment_text_handles_trailing_punctuation() -> None:
    """Lowercase the first letter even when followed by trailing punctuation."""
    assert _fix_comment_text("# Bad!") == "# bad!"


def test_check_exits_zero_when_no_errors(
    tmp_path: Path,
) -> None:
    """Exit 0 and print a success message when no comments are uppercase."""
    _write_py(tmp_path, "good.py", "# fine\n")
    runner = CliRunner()
    result = runner.invoke(app, ["check", str(tmp_path / "good.py")])
    assert result.exit_code == 0


def test_check_exits_one_when_errors_found(
    tmp_path: Path,
) -> None:
    """Exit 1 and report the number of errors found."""
    _write_py(tmp_path, "bad.py", "# Bad comment\n")
    runner = CliRunner()
    result = runner.invoke(app, ["check", str(tmp_path / "bad.py")])
    assert result.exit_code == 1


def test_check_reports_filepath_and_line(
    tmp_path: Path,
) -> None:
    """Include the filepath and line number in the error output."""
    bad = _write_py(tmp_path, "bad.py", "# Bad\nx = 1\n# Another bad\n")
    runner = CliRunner()
    result = runner.invoke(app, ["check", str(bad)])
    combined = _strip_ansi(result.stdout + (result.stderr or ""))
    assert "bad.py:1" in combined
    assert "bad.py:3" in combined


def test_check_suggests_fix_in_output(
    tmp_path: Path,
) -> None:
    """Show the auto-fixed version of each offending comment in the output."""
    _write_py(tmp_path, "bad.py", "# Bad\n")
    runner = CliRunner()
    result = runner.invoke(app, ["check", str(tmp_path / "bad.py")])
    combined = _strip_ansi(result.stdout + (result.stderr or ""))
    assert "# bad" in combined


def test_fix_writes_corrected_file(
    tmp_path: Path,
) -> None:
    """Rewrite the file in place so the offending comment is lowercased."""
    py_file = _write_py(tmp_path, "bad.py", "# Bad comment\nx = 1\n")
    runner = CliRunner()
    result = runner.invoke(app, ["fix", str(py_file)])
    assert result.exit_code == 0
    assert py_file.read_text() == "# bad comment\nx = 1\n"


def test_fix_preserves_indentation(
    tmp_path: Path,
) -> None:
    """Preserve the original indentation when fixing an indented comment."""
    py_file = _write_py(
        tmp_path,
        "indented.py",
        "def f() -> None:\n    # Bad\n    return None\n",
    )
    runner = CliRunner()
    runner.invoke(app, ["fix", str(py_file)])
    assert py_file.read_text() == (
        "def f() -> None:\n    # bad\n    return None\n"
    )


def test_fix_preserves_proper_noun(
    tmp_path: Path,
) -> None:
    """Leave a comment that starts with a proper noun unchanged."""
    py_file = _write_py(tmp_path, "ok.py", "# GatorGrader is cool\n")
    original = py_file.read_text()
    runner = CliRunner()
    runner.invoke(app, ["fix", str(py_file)])
    assert py_file.read_text() == original


def test_fix_skips_non_comment_lines(
    tmp_path: Path,
) -> None:
    """Not modify lines that are not comments, even if they start uppercase."""
    py_file = _write_py(tmp_path, "code.py", "X = 1\n# Bad\n")
    runner = CliRunner()
    runner.invoke(app, ["fix", str(py_file)])
    assert py_file.read_text() == "X = 1\n# bad\n"


def test_fix_reports_no_changes_when_already_correct(
    tmp_path: Path,
) -> None:
    """Print a success message and exit 0 when no fixes are needed."""
    py_file = _write_py(tmp_path, "good.py", "# fine\n")
    runner = CliRunner()
    result = runner.invoke(app, ["fix", str(py_file)])
    assert result.exit_code == 0
    assert py_file.read_text() == "# fine\n"


def test_fix_handles_multiple_files(
    tmp_path: Path,
) -> None:
    """Fix uppercase comments in every provided file and track the count."""
    a = _write_py(tmp_path, "a.py", "# Bad\n")
    b = _write_py(tmp_path, "b.py", "# Also bad\n# fine\n")
    runner = CliRunner()
    result = runner.invoke(app, ["fix", str(a), str(b)])
    assert result.exit_code == 0
    assert a.read_text() == "# bad\n"
    assert b.read_text() == "# also bad\n# fine\n"


def test_proper_nouns_contains_expected_entries() -> None:
    """Include the well-known proper nouns in the PROPER_NOUNS set."""
    for noun in (
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
        "CountCommits",
    ):
        assert noun in PROPER_NOUNS
