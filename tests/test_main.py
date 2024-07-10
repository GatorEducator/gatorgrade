"""Tests for the main file of the project.

In the tests below, print statements that print Typer's captured stdout will
only display output when tests fail. These print statements are required
because disabling output capture through pytest does not disable Typer's output
capturing.
"""

import builtins
import io
import os
import subprocess
import sys
from unittest.mock import patch

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


# def test_generate_creates_valid_yml():
#     """Ensure that the generate command creates the .yml file correctly."""
#     result = runner.invoke(main.app, ["generate"])
#     print(result.stdout)
#     assert result.exit_code == 0


# def test_generate_fails_with_existing_yml():
#     """Ensure that a second yml file isn't generated without the force command."""
#     result = runner.invoke(main.app, ["generate"])
#     print(result.stdout)
#     assert result.exit_code == 0


# def test_generate_force_option_creates_yml():
#     """Ensure that the force command works correctly."""
#     result = runner.invoke(main.app, ["generate"])
#     print(result.stdout)
#     assert result.exit_code == 0


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
    assignment_path, expected_output_and_freqs, chdir
):
    """Tests full integration pipeline to ensure input assignments give the correct output."""
    chdir(assignment_path)
    result = runner.invoke(main.app)

    assert result.exit_code == 0
    for output, freq in expected_output_and_freqs:
        assert result.stdout.count(output) == freq


def test_no_invoked_subcommand_invalid_checks():
    """Test with a valid configuration file that produces invalid checks."""
    result = runner.invoke(main.app)
    assert result.exit_code == 1


# def test_entry_point(chdir):
#     """Test the entry point of the script to ensure it runs as expected."""
#     chdir(os.path.join(os.path.dirname(__file__), '../gatorgrade/'))
#     result = subprocess.run([sys.executable, "main.py"], capture_output=True, text=True)

#     assert result.returncode == 1


if __name__ == "__main__":
    pytest.main()
