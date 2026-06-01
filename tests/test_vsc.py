"""Tests for the scripts.vsc module."""

from pathlib import Path

import pytest
import tree_sitter_python as tspython
from tree_sitter import Language, Parser
from typer.testing import CliRunner

from scripts.vsc import (
    VERSION_VAR,
    _extract_version_from_main,
    _extract_version_from_pyproject,
    _unquote_string,
    _update_version_in_main,
    app,
)

PY_LANGUAGE = Language(tspython.language())


def _make_parser() -> Parser:
    """Create a fresh Tree-sitter parser for Python."""
    return Parser(PY_LANGUAGE)


def test_unquote_string_strips_double_quotes() -> None:
    """Strip matching double quotes from a Python string literal."""
    assert _unquote_string('"0.8.3"') == "0.8.3"


def test_unquote_string_strips_single_quotes() -> None:
    """Strip matching single quotes from a Python string literal."""
    assert _unquote_string("'0.8.3'") == "0.8.3"


def test_unquote_string_preserves_unmatched_quotes() -> None:
    """Return the raw string unchanged when quotes do not match."""
    assert _unquote_string('"0.8.3') == '"0.8.3'
    assert _unquote_string('0.8.3"') == '0.8.3"'
    assert _unquote_string("0.8.3") == "0.8.3"
    assert _unquote_string("") == ""


def test_extract_version_from_main_returns_assigned_value(
    tmp_path: Path,
) -> None:
    """Return the string assigned to GATORGRADE_VERSION in a Python file."""
    main_file = tmp_path / "main.py"
    main_file.write_text(
        f'"""Module docstring."""\n{VERSION_VAR} = "1.2.3"\nimport os\n'
    )
    assert _extract_version_from_main(main_file, _make_parser()) == "1.2.3"


def test_extract_version_from_main_returns_none_when_missing(
    tmp_path: Path,
) -> None:
    """Return None when the file does not define GATORGRADE_VERSION."""
    main_file = tmp_path / "main.py"
    main_file.write_text("import os\n")
    assert _extract_version_from_main(main_file, _make_parser()) is None


def test_extract_version_from_pyproject_returns_project_version(
    tmp_path: Path,
) -> None:
    """Return the project version key from pyproject.toml."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "gatorgrade"\nversion = "2.0.0"\n')
    assert _extract_version_from_pyproject(pyproject) == "2.0.0"


def test_extract_version_from_pyproject_returns_none_when_missing(
    tmp_path: Path,
) -> None:
    """Return None when the project table has no version key."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "gatorgrade"\n')
    assert _extract_version_from_pyproject(pyproject) is None


def test_extract_version_from_pyproject_returns_none_when_no_project(
    tmp_path: Path,
) -> None:
    """Return None when pyproject.toml has no project table."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.ruff]\nline-length = 79\n")
    assert _extract_version_from_pyproject(pyproject) is None


def test_update_version_in_main_replaces_assigned_value(
    tmp_path: Path,
) -> None:
    """Replace the GATORGRADE_VERSION string and write the file back."""
    main_file = tmp_path / "main.py"
    main_file.write_text(
        f'"""Module."""\n{VERSION_VAR} = "0.1.0"\nimport os\n'
    )
    changed = _update_version_in_main(main_file, "0.2.0")
    assert changed is True
    assert f'{VERSION_VAR} = "0.2.0"' in main_file.read_text()


def test_update_version_in_main_returns_false_when_missing(
    tmp_path: Path,
) -> None:
    """Return False when the file does not define GATORGRADE_VERSION."""
    main_file = tmp_path / "main.py"
    main_file.write_text("import os\n")
    changed = _update_version_in_main(main_file, "0.2.0")
    assert changed is False


def test_update_version_in_main_preserves_indentation(
    tmp_path: Path,
) -> None:
    """Preserve the original indentation when updating the version line."""
    main_file = tmp_path / "main.py"
    main_file.write_text(
        f'def f() -> None:\n    {VERSION_VAR} = "0.1.0"\n    return None\n'
    )
    _update_version_in_main(main_file, "0.2.0")
    lines = main_file.read_text().splitlines()
    assert lines[1] == f'    {VERSION_VAR} = "0.2.0"'


@pytest.fixture
def project_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a temporary gatorgrade/main.py and pyproject.toml and chdir into tmp_path."""
    main_dir = tmp_path / "gatorgrade"
    main_dir.mkdir(parents=True, exist_ok=True)
    main_file = main_dir / "main.py"
    main_file.write_text(f'"""Module."""\n{VERSION_VAR} = "9.9.9"\n')
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "gatorgrade"\nversion = "9.9.9"\n')
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_check_exits_zero_when_versions_match(
    project_files: Path,
) -> None:
    """Exit 0 and print a success message when versions match."""
    runner = CliRunner()
    result = runner.invoke(app, ["check"])
    assert result.exit_code == 0
    assert "Versions match" in result.stdout


def test_check_exits_one_when_versions_differ(
    project_files: Path,
) -> None:
    """Exit 1 and report the mismatch when versions differ."""
    main_file = project_files / "gatorgrade" / "main.py"
    main_file.write_text(f'"""Module."""\n{VERSION_VAR} = "0.0.1"\n')
    runner = CliRunner()
    result = runner.invoke(app, ["check"])
    assert result.exit_code == 1
    assert "Version mismatch" in (result.stdout + result.stderr)


def test_check_exits_one_when_main_version_missing(
    project_files: Path,
) -> None:
    """Exit 1 when main.py does not define GATORGRADE_VERSION."""
    main_file = project_files / "gatorgrade" / "main.py"
    main_file.write_text('"""Module."""\nimport os\n')
    runner = CliRunner()
    result = runner.invoke(app, ["check"])
    assert result.exit_code == 1


def test_check_exits_one_when_pyproject_version_missing(
    project_files: Path,
) -> None:
    """Exit 1 when pyproject.toml has no project version."""
    pyproject = project_files / "pyproject.toml"
    pyproject.write_text('[project]\nname = "gatorgrade"\n')
    runner = CliRunner()
    result = runner.invoke(app, ["check"])
    assert result.exit_code == 1


def test_fix_updates_main_when_versions_differ(
    project_files: Path,
) -> None:
    """Update main.py to match pyproject.toml when they differ."""
    main_file = project_files / "gatorgrade" / "main.py"
    main_file.write_text(f'"""Module."""\n{VERSION_VAR} = "0.0.1"\n')
    runner = CliRunner()
    result = runner.invoke(app, ["fix"])
    assert result.exit_code == 0
    assert f'{VERSION_VAR} = "9.9.9"' in main_file.read_text()


def test_fix_is_noop_when_versions_already_match(
    project_files: Path,
) -> None:
    """Exit 0 without changes when versions already match."""
    main_file = project_files / "gatorgrade" / "main.py"
    before = main_file.read_text()
    runner = CliRunner()
    result = runner.invoke(app, ["fix"])
    assert result.exit_code == 0
    assert main_file.read_text() == before


def test_fix_exits_one_when_main_version_missing(
    project_files: Path,
) -> None:
    """Exit 1 when main.py does not define GATORGRADE_VERSION."""
    main_file = project_files / "gatorgrade" / "main.py"
    main_file.write_text('"""Module."""\nimport os\n')
    runner = CliRunner()
    result = runner.invoke(app, ["fix"])
    assert result.exit_code == 1


def test_fix_exits_one_when_pyproject_version_missing(
    project_files: Path,
) -> None:
    """Exit 1 when pyproject.toml has no project version."""
    pyproject = project_files / "pyproject.toml"
    pyproject.write_text('[project]\nname = "gatorgrade"\n')
    runner = CliRunner()
    result = runner.invoke(app, ["fix"])
    assert result.exit_code == 1
