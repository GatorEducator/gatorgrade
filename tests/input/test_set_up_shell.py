"""Test suite for set_up_shell.py."""

import pytest
from typer import Exit

from gatorgrade.input.set_up_shell import run_setup


def test_run_setup_with_no_setup_commands():
    """Test run_setup with empty front matter."""
    front_matter = {}
    result = run_setup(front_matter)
    assert result is None


def test_run_setup_with_successful_commands():
    """Test run_setup with successful shell commands."""
    front_matter = {"setup": "echo 'Hello World'\necho 'Test Command'"}
    result = run_setup(front_matter)
    assert result is None


def test_run_setup_with_failing_command():
    """Test run_setup with a failing shell command."""
    front_matter = {"setup": "false"}
    with pytest.raises(Exit) as exc_info:
        run_setup(front_matter)
    assert exc_info.value.exit_code == 1


def test_run_setup_with_mixed_commands():
    """Test run_setup with mix of successful and failing commands."""
    front_matter = {"setup": "echo 'First command'\nfalse"}
    with pytest.raises(Exit) as exc_info:
        run_setup(front_matter)
    assert exc_info.value.exit_code == 1


def test_run_setup_with_whitespace_in_commands():
    """Test run_setup handles commands with whitespace correctly."""
    front_matter = {"setup": "  echo 'Test'  \n  echo 'Another test'  "}
    result = run_setup(front_matter)
    assert result is None
