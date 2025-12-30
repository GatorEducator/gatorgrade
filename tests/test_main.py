"""Tests for the main file of the project."""

import builtins
import io
import os

import pytest
from typer.testing import CliRunner

from gatorgrade import main

runner = CliRunner()


def patch_open(open_func, files):
    """Create a patch to for file opening to track and later delete opened files."""

    def open_patched(
        path,
        mode="r",
        buffering=-1,
        encoding=None,
        errors=None,
        newline=None,
        closefd=True,
        opener=None,
    ):
        if "w" in mode and not os.path.isfile(path):
            files.append(path)
        return open_func(
            path,
            mode=mode,
            buffering=buffering,
            encoding=encoding,
            errors=errors,
            newline=newline,
            closefd=closefd,
            opener=opener,
        )

    return open_patched


@pytest.fixture(autouse=True)
def cleanup_files(monkeypatch):
    """Cleanup any files that are created by the tests in this test suite."""
    files = []
    monkeypatch.setattr(builtins, "open", patch_open(builtins.open, files))
    monkeypatch.setattr(io, "open", patch_open(io.open, files))
    yield
    for file in files:
        os.remove(file)


@pytest.mark.parametrize(
    "assignment_path,expected_output_and_freqs",
    [
        (
            "tests/test_assignment",
            [
                ("Complete all TODOs", 2),
                ("Use an if statement", 1),
                ("✓", 3),
                ("✕", 0),
                ("Passed 3/3 (100%) of checks", 1),
            ],
        )
    ],
)
def test_full_integration_creates_valid_output(
    assignment_path, expected_output_and_freqs, chdir, capsys
):
    """Tests full integration pipeline to ensure input assignments give the correct output."""
    # the assignment path is:
    # tests/test_assignment
    chdir(assignment_path)
    # result is the following information:
    # ✓  Complete all TODOs
    # ✓  Use an if statement
    # ✓  Complete all TODOs
    result = runner.invoke(main.app)
    capsys.readouterr()
    print(result.stdout)
    assert result.exit_code == 0
    for output, freq in expected_output_and_freqs:
        assert result.stdout.count(output) == freq


def test_gatorgrade_with_nonexistent_file(chdir, capsys):
    """Test that gatorgrade exits with error when config file doesn't exist."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--config", "nonexistent.yml"])
    capsys.readouterr()
    print(result.stdout)
    assert result.exit_code == 1
    assert "either does not exist or is not valid" in result.stdout
    assert "Exiting now!" in result.stdout


def test_gatorgrade_with_custom_config_name(chdir, capsys):
    """Test that gatorgrade works with custom config file name."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--config", "gatorgrade.yml"])
    capsys.readouterr()
    print(result.stdout)
    assert result.exit_code == 0
    assert "Passed 3/3 (100%) of checks" in result.stdout


def test_gatorgrade_with_report_option(chdir, tmp_path, capsys):
    """Test that gatorgrade works with report option."""
    chdir("tests/test_assignment")
    report_file = tmp_path / "report.json"
    result = runner.invoke(main.app, ["--report", "file", "json", str(report_file)])
    capsys.readouterr()
    print(result.stdout)
    assert result.exit_code == 0
    assert report_file.exists()


def test_gatorgrade_with_status_bar(chdir, capsys):
    """Test that gatorgrade works with status bar enabled."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--status-bar"])
    capsys.readouterr()
    print(result.stdout)
    assert result.exit_code == 0
    assert "Passed 3/3 (100%) of checks" in result.stdout


def test_gatorgrade_with_no_status_bar(chdir, capsys):
    """Test that gatorgrade works with no status bar."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--no-status-bar"])
    capsys.readouterr()
    print(result.stdout)
    assert result.exit_code == 0
    assert "Passed 3/3 (100%) of checks" in result.stdout
